"""Router `stories` (D-41): sổ tay và hỏi người kể. TestClient + dependency override, không Docker.

G1: phản hồi sổ tay chỉ có trường trong danh sách trắng, không id lớp truth.
G12: lỗi trả payload có mã. Router chỉ mount khi bật cờ dev (fail closed).
"""

import json
from dataclasses import replace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.api_fixtures import MemoryCostLedger, MemoryKeyStore, dev_settings, offline
from tests.moderation_fixtures import ModeratedLLM, moderation_reply
from writory.api import create_app, deps
from writory.api.errors import HTTP_STATUS
from writory.api.stories import router as stories_router
from writory.config import Settings
from writory.db import StoryNotFoundError, StoryRecord
from writory.errors import ErrorCode, WritoryError
from writory.graph import PlayerView, public_entries, public_lies
from writory.llm.fake import FakeLLM
from writory.pipeline.narrator import NOT_KNOWN

from .test_narrator import CFG, PLAN, MemoryQuota, metered, ref, reply, state, view

NOTEBOOK_KEYS = {"chapter", "entries", "lies"}
ENTRY_KEYS = {"ref", "kind", "text", "aliases", "since_chapter", "quote", "about"}
LIE_KEYS = {"content", "chapter", "told_to"}


def settings(*, dev: bool) -> Settings:
    return dev_settings(dev=dev)


async def ok() -> bool:
    return True


def build(chapter: int = 4, *, fake: FakeLLM | None = None, quota: MemoryQuota | None = None,
          override_llm: bool = True, override_plan: bool = True,
          moderated: ModeratedLLM | None = None) -> FastAPI:
    app = create_app(settings(dev=True), health_checks={"neo4j": ok}, config=CFG)

    def player_view(story_id: str) -> PlayerView:
        if story_id == "khong-co":
            raise StoryNotFoundError(f"không có truyện {story_id}")
        return replace(view(chapter), story_id=story_id)  # như app thật: view của chính truyện

    # Không Docker: kết nối giả, truyện của người chơi dev, kho key rỗng, nhật ký trong bộ nhớ.
    app.dependency_overrides[deps.get_pg_conn] = lambda: None
    offline(app)
    def owned_story(story_id: str) -> StoryRecord:
        if story_id == "khong-co":  # truyện không có, hoặc của người khác (G10): cùng một lỗi
            raise StoryNotFoundError(f"không có truyện {story_id}")
        return StoryRecord(story_id, "dev", "short", chapter)

    app.dependency_overrides[deps.get_owned_story] = owned_story
    app.dependency_overrides[deps.get_key_store] = MemoryKeyStore
    app.dependency_overrides[deps.get_cost_ledger] = MemoryCostLedger
    app.dependency_overrides[deps.get_player_view] = player_view
    app.dependency_overrides[deps.get_truth_names] = lambda: state(chapter).named_nodes()
    app.dependency_overrides[deps.get_story_brief] = lambda: ""
    q = quota or MemoryQuota()
    app.dependency_overrides[deps.get_narrator_quota] = lambda: q
    if override_plan:
        app.dependency_overrides[deps.get_story_plan] = lambda: PLAN
    if override_llm:
        # Kiểm duyệt đầu vào (G9) dùng cùng client: mặc định cho qua, không lẫn vào kịch bản người kể.
        llm = metered(moderated or ModeratedLLM(fake or FakeLLM.scripted([reply(False, None, [])])))
        app.dependency_overrides[deps.get_narrator_llm] = lambda: llm
    return app


def leaves(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from leaves(v)
    elif isinstance(value, list):
        for v in value:
            yield from leaves(v)
    else:
        yield value


# --- sổ tay -----------------------------------------------------------------------------------


@pytest.mark.parametrize("chapter", [0, 1, 3, 4, 5])
def test_notebook_has_only_whitelisted_fields(chapter):
    with TestClient(build(chapter)) as client:
        resp = client.get("/stories/s1/notebook")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == NOTEBOOK_KEYS
    assert body["chapter"] == chapter
    assert all(set(e) == ENTRY_KEYS for e in body["entries"])
    assert all(set(lie) == LIE_KEYS for lie in body["lies"])
    v = view(chapter)
    assert len(body["entries"]) == len(v.entries)
    assert len(body["lies"]) == len(v.lies)


@pytest.mark.parametrize("chapter", [1, 4, 5])
def test_notebook_never_returns_truth_ids_or_names(chapter):
    with TestClient(build(chapter)) as client:
        resp = client.get("/stories/s1/notebook")
    v = view(chapter)
    truth_ids = {e.id for e in v.entries} | {lie.id for lie in v.lies}
    assert not truth_ids & {x for x in leaves(resp.json()) if isinstance(x, str)}
    assert "ly_that" not in resp.text
    if chapter == 4:
        text = json.loads(resp.text)  # bỏ escape \uXXXX để so chữ có dấu
        assert "Lý Thất" not in json.dumps(text, ensure_ascii=False)


def test_notebook_entry_content_and_about_refs():
    with TestClient(build(5)) as client:
        body = client.get("/stories/s1/notebook").json()
    v = view(5)
    by_ref = {e["ref"]: e for e in body["entries"]}
    spy = by_ref[ref(v, "f_lan_spy")]
    assert spy["kind"] == "Fact"
    assert spy["text"].startswith("Lan là gián điệp")
    assert spy["since_chapter"] == 5
    assert spy["quote"] == "Lan là người của Hội Hắc Kỳ."
    assert sorted(spy["about"]) == sorted([ref(v, "lan"), ref(v, "hac_ky")])
    stranger = by_ref[ref(v, "ly_that")]
    assert (stranger["text"], stranger["aliases"]) == ("Lý Thất", ["gã lái đò mặt sẹo"])
    assert [e["ref"] for e in body["entries"]] == [r for r, _ in public_entries(v)]
    lie = next(x for x in body["lies"] if x["chapter"] == 2)
    assert lie == {"content": "Thanh kiếm là của cha Minh để lại", "chapter": 2,
                   "told_to": ["Phạm Thị Lan"]}


def test_notebook_story_not_found_is_g12_payload():
    with TestClient(build(), raise_server_exceptions=False) as client:
        resp = client.get("/stories/khong-co/notebook")
    assert resp.status_code == 404
    assert resp.json() == WritoryError(ErrorCode.STORY_NOT_FOUND).player_payload()
    assert "khong-co" not in resp.text


# --- hỏi người kể -----------------------------------------------------------------------------


LIMIT = CFG.limits.rate_limit.narrator_questions_per_chapter
NARRATOR_KEYS = {"answer", "remaining", "source_chapters"}


def answered(answer: str, *, remaining: int = LIMIT - 1, sources=()) -> dict:
    return {"answer": answer, "remaining": remaining, "source_chapters": list(sources)}


def test_narrator_returns_answer_remaining_and_sources_only():
    v = view(3)
    gu = ref(v, "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu])])
    with TestClient(build(3, fake=fake)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lão Gù chết ở đâu?"})
    assert resp.status_code == 200
    since = next(e.since_chapter for r, e in public_entries(v) if r == gu)
    assert resp.json() == answered("Lão Gù chết sau miếu Bà.", sources=[since])


def test_narrator_not_known_is_a_normal_answer():
    with TestClient(build(4)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Ai giết Lão Gù?"})
    assert (resp.status_code, resp.json()) == (200, answered(NOT_KNOWN))


def test_narrator_leak_is_hidden_as_not_known():
    v = view(4)
    fake = FakeLLM.scripted([reply(True, "Gã đó là Lý Thất.", [ref(v, "ly_that")])])
    with TestClient(build(4, fake=fake)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Gã lái đò là ai?"})
    # Câu bị chặn không có nguồn: mã model dẫn (ở đây là mục "gã lái đò") không lộ ra.
    assert (resp.status_code, resp.json()) == (200, answered(NOT_KNOWN))
    assert "Lý Thất" not in json.dumps(resp.json(), ensure_ascii=False)


def test_narrator_leak_check_counts_the_story_brief_as_seen():
    """D-52: bộ dò lộ của người kể nhận thiết lập truyện (`stories.brief`) qua
    `deps.get_story_brief`, như mọi nơi gọi khác."""
    v = view(4)
    fake = FakeLLM.scripted([reply(True, "Gã đó là Lý Thất.", [ref(v, "ly_that")])])
    app = build(4, fake=fake)
    app.dependency_overrides[deps.get_story_brief] = lambda: "Bối cảnh: bến có lái đò Lý Thất."
    with TestClient(app) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Gã lái đò là ai?"})
    assert resp.status_code == 200
    assert resp.json() == answered("Gã đó là Lý Thất.",
                                   sources=[next(e.since_chapter for e in v.entries
                                                 if e.id == "ly_that")])


def test_narrator_limit_is_429_g12_payload():
    cfg_limit = CFG.limits.rate_limit.narrator_questions_per_chapter
    fake = FakeLLM.scripted([reply(False, None, [])] * cfg_limit)
    with TestClient(build(3, fake=fake), raise_server_exceptions=False) as client:
        for _ in range(cfg_limit):
            assert client.post("/stories/s1/narrator", json={"question": "?"}).status_code == 200
        resp = client.post("/stories/s1/narrator", json={"question": "Thêm?"})
    assert resp.status_code == 429 == HTTP_STATUS[ErrorCode.NARRATOR_LIMIT_REACHED]
    assert resp.json() == WritoryError(ErrorCode.NARRATOR_LIMIT_REACHED).player_payload()


def test_remaining_counts_down_then_the_limit_error_is_unchanged():
    """D-65: `remaining` lấy từ bộ đếm `narrator_questions` sau khi giữ lượt; câu "Bạn chưa biết
    điều này." vẫn tính một lượt (D-40). Hết lượt thì lỗi giữ nguyên như cũ."""
    fake = FakeLLM.scripted([reply(False, None, [])] * LIMIT)
    with TestClient(build(3, fake=fake), raise_server_exceptions=False) as client:
        before = client.get("/stories/s1/narrator").json()
        got = [client.post("/stories/s1/narrator", json={"question": "?"}).json()["remaining"]
               for _ in range(LIMIT)]
        after = client.get("/stories/s1/narrator").json()
        over = client.post("/stories/s1/narrator", json={"question": "Thêm?"})
    assert before == {"remaining": LIMIT}
    assert got == list(range(LIMIT - 1, -1, -1))
    assert after == {"remaining": 0}
    assert over.status_code == 429
    assert over.json() == WritoryError(ErrorCode.NARRATOR_LIMIT_REACHED).player_payload()


def test_remaining_is_per_chapter():
    quota = MemoryQuota()
    fake = FakeLLM.scripted([reply(False, None, [])])
    with TestClient(build(3, fake=fake, quota=quota)) as client:
        client.post("/stories/s1/narrator", json={"question": "?"})
    with TestClient(build(4, quota=quota)) as client:
        assert client.get("/stories/s1/narrator").json() == {"remaining": LIMIT}


def test_empty_notebook_answer_does_not_use_a_question():
    """Chương 0: sổ tay trống, không gọi model, không mất lượt (D-40), không có nguồn."""
    fake = FakeLLM.scripted([])
    with TestClient(build(0, fake=fake)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Tôi là ai?"})
    assert resp.json() == answered(NOT_KNOWN, remaining=LIMIT)
    assert fake.calls == []


def test_blocked_question_does_not_use_a_question():
    moderated = ModeratedLLM(FakeLLM.scripted([]), [moderation_reply(("real_world_harm", "strong"))])
    with TestClient(build(3, moderated=moderated), raise_server_exceptions=False) as client:
        assert client.post("/stories/s1/narrator", json={"question": "x"}).status_code == 422
        assert client.get("/stories/s1/narrator").json() == {"remaining": LIMIT}


def test_sources_of_a_lie_answer_are_the_chapter_it_was_told():
    v = view(5)
    lie = next((r, x) for r, x in public_lies(v) if x.id == "l_sword_father")
    spy = ref(v, "f_lan_spy")
    fake = FakeLLM.scripted([reply(True, "Minh từng nói thanh kiếm là của cha để lại.",
                                   [spy, lie[0], spy])])
    with TestClient(build(5, fake=fake)) as client:
        body = client.post("/stories/s1/narrator", json={"question": "Kiếm của ai?"}).json()
    assert body["source_chapters"] == sorted({lie[1].chapter, 5})
    assert all(isinstance(c, int) for c in body["source_chapters"])


def test_narrator_get_has_only_remaining_and_needs_no_key_or_model():
    """GET không gọi model, không cần key: chỉ đọc bộ đếm."""
    fake = FakeLLM.scripted([])
    with TestClient(build(3, fake=fake, override_llm=False)) as client:
        resp = client.get("/stories/s1/narrator")
    assert (resp.status_code, resp.json()) == (200, {"remaining": LIMIT})
    assert fake.calls == []


def test_narrator_get_of_unknown_story_is_404():
    """G10 (TODO đăng nhập): truyện không có hay của người khác báo cùng một lỗi."""
    with TestClient(build(), raise_server_exceptions=False) as client:
        resp = client.get("/stories/khong-co/narrator")
    assert resp.status_code == 404
    assert resp.json() == WritoryError(ErrorCode.STORY_NOT_FOUND).player_payload()


def test_narrator_get_with_limit_not_set_fails_closed():
    from .test_narrator import with_limits

    app = build(3)
    app.state.config = with_limits(rate_limit__narrator_questions_per_chapter=None)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/stories/s1/narrator")
    assert resp.status_code == 503
    assert resp.json()["code"] == "CONFIG_LIMIT_NOT_SET"


def test_narrator_bad_question_is_g12_payload():
    with TestClient(build(3), raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "  "})
    assert resp.status_code == 422
    assert resp.json() == WritoryError(ErrorCode.NARRATOR_QUESTION_EMPTY).player_payload()


def test_narrator_request_body_rejects_extra_fields():
    with TestClient(build(3)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "?", "chapter": 9})
    assert resp.status_code == 422


def test_narrator_without_player_key_fails_closed():
    """Người chơi chưa lưu key: báo thiếu key, không gọi model nào, không dùng key chủ dự án."""
    with TestClient(build(3, override_llm=False), raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lan là ai?"})
    assert resp.status_code == 400
    assert resp.json() == WritoryError(ErrorCode.PLAYER_KEY_MISSING).player_payload()


def test_narrator_without_story_plan_fails_closed(monkeypatch):
    """Truyện không có story_plan: không chạy được bộ dò lộ đầy đủ, nên không trả lời."""
    monkeypatch.setattr(deps, "load_story_plan", lambda conn, story_id: None)
    fake = FakeLLM.scripted([])
    app = build(3, fake=fake, override_plan=False)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lan là ai?"})
    assert resp.status_code == 500
    assert resp.json()["code"] == "INTERNAL_ERROR"
    assert fake.calls == []


# --- mount: fail closed ------------------------------------------------------------------------


def _paths(app: FastAPI) -> set[str]:
    # FastAPI mới bọc router con (_IncludedRouter), nên đọc đường dẫn qua schema OpenAPI.
    return set(app.openapi()["paths"])


def test_settings_dev_routes_default_off():
    s = Settings(_env_file=None, neo4j_uri="bolt://x", neo4j_user="u", neo4j_password="p",
                 postgres_dsn="postgresql://x", player_key_encryption_key="k")
    assert s.enable_dev_routes is False


def test_router_not_mounted_when_dev_flag_off():
    app = create_app(settings(dev=False), health_checks={"neo4j": ok}, config=CFG)
    assert not any(p.startswith("/stories") for p in _paths(app))
    with TestClient(app) as client:
        assert client.get("/stories/s1/notebook").status_code == 404
        assert client.post("/stories/s1/narrator", json={"question": "?"}).status_code == 404
        assert client.get("/stories/s1/narrator").status_code == 404
        assert client.get("/stories").status_code == 404


def test_router_mounted_when_dev_flag_on():
    app = create_app(settings(dev=True), health_checks={"neo4j": ok}, config=CFG)
    assert {"/stories", "/stories/{story_id}/notebook", "/stories/{story_id}/narrator"} <= _paths(
        app)
    assert {"get", "post"} <= set(app.openapi()["paths"]["/stories/{story_id}/narrator"])


def test_router_mounted_elsewhere_without_flag_still_refuses():
    """Phòng thủ hai lớp: gắn router vào app khác mà không qua create_app thì vẫn 404."""
    app = FastAPI()
    app.include_router(stories_router)
    app.dependency_overrides[deps.get_player_view] = lambda: view(3)
    with TestClient(app) as client:
        assert client.get("/stories/s1/notebook").status_code == 404


# --- kiểm duyệt đầu vào của câu hỏi (G9, D-57) ------------------------------------------------------


def test_narrator_question_is_moderated_before_quota_and_model():
    fake = FakeLLM.scripted([])  # nếu model người kể bị gọi, test đỏ
    moderated = ModeratedLLM(fake, [moderation_reply(("real_world_harm", "strong"))])
    quota = MemoryQuota()
    with TestClient(build(3, quota=quota, moderated=moderated)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Chỉ tôi cách chế thuốc nổ"})
    assert resp.status_code == HTTP_STATUS[ErrorCode.INPUT_BLOCKED] == 422
    assert resp.json()["code"] == "INPUT_BLOCKED"
    assert "real_world_harm" not in resp.text and "thuốc nổ" not in resp.text
    assert fake.calls == [] and not quota.taken
    assert len(moderated.moderation_calls) == 1


def test_allowed_question_is_moderated_once_then_answered():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [ref(v, "e_gu_death")])])
    moderated = ModeratedLLM(fake)
    with TestClient(build(3, moderated=moderated)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lão Gù chết ở đâu?"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "Lão Gù chết sau miếu Bà."
    [messages] = moderated.moderation_calls
    assert "Lão Gù chết ở đâu?" in messages[-1].content
    assert len(fake.calls) == 1
