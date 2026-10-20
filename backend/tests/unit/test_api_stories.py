"""Router `stories` (D-41): sổ tay và hỏi người kể. TestClient + dependency override, không Docker.

G1: phản hồi sổ tay chỉ có trường trong danh sách trắng, không id lớp truth.
G12: lỗi trả payload có mã. Router chỉ mount khi bật cờ dev (fail closed).
"""

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from writory.api import create_app, deps
from writory.api.errors import HTTP_STATUS
from writory.api.stories import router as stories_router
from writory.config import Settings
from writory.db import StoryNotFoundError
from writory.errors import ErrorCode, WritoryError
from writory.graph import PlayerView, public_entries
from writory.llm.fake import FakeLLM
from writory.pipeline.narrator import NOT_KNOWN

from .test_narrator import CFG, PLAN, MemoryQuota, metered, ref, reply, state, view

NOTEBOOK_KEYS = {"chapter", "entries", "lies"}
ENTRY_KEYS = {"ref", "kind", "text", "aliases", "since_chapter", "quote", "about"}
LIE_KEYS = {"content", "chapter", "told_to"}


def settings(*, dev: bool) -> Settings:
    return Settings(
        _env_file=None,
        neo4j_uri="bolt://neo4j.invalid:7687",
        neo4j_user="neo4j",
        neo4j_password="pw",
        postgres_dsn="postgresql://u:p@pg.invalid/db",
        player_key_encryption_key="enc",
        enable_dev_routes=dev,
    )


async def ok() -> bool:
    return True


def build(chapter: int = 4, *, fake: FakeLLM | None = None, quota: MemoryQuota | None = None,
          override_llm: bool = True, override_plan: bool = True) -> FastAPI:
    app = create_app(settings(dev=True), health_checks={"neo4j": ok}, config=CFG)

    def player_view(story_id: str) -> PlayerView:
        if story_id == "khong-co":
            raise StoryNotFoundError(f"không có truyện {story_id}")
        return view(chapter)

    app.dependency_overrides[deps.get_player_view] = player_view
    app.dependency_overrides[deps.get_truth_names] = lambda: state(chapter).named_nodes()
    q = quota or MemoryQuota()
    app.dependency_overrides[deps.get_narrator_quota] = lambda: q
    if override_plan:
        app.dependency_overrides[deps.get_story_plan] = lambda: PLAN
    if override_llm:
        llm = metered(fake or FakeLLM.scripted([reply(False, None, [])]))
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


def test_narrator_returns_answer_only():
    v = view(3)
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [ref(v, "e_gu_death")])])
    with TestClient(build(3, fake=fake)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lão Gù chết ở đâu?"})
    assert resp.status_code == 200
    assert resp.json() == {"answer": "Lão Gù chết sau miếu Bà."}


def test_narrator_not_known_is_a_normal_answer():
    with TestClient(build(4)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Ai giết Lão Gù?"})
    assert (resp.status_code, resp.json()) == (200, {"answer": NOT_KNOWN})


def test_narrator_leak_is_hidden_as_not_known():
    v = view(4)
    fake = FakeLLM.scripted([reply(True, "Gã đó là Lý Thất.", [ref(v, "ly_that")])])
    with TestClient(build(4, fake=fake)) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Gã lái đò là ai?"})
    assert (resp.status_code, resp.json()) == (200, {"answer": NOT_KNOWN})
    assert "Lý Thất" not in json.dumps(resp.json(), ensure_ascii=False)


def test_narrator_limit_is_429_g12_payload():
    cfg_limit = CFG.limits.rate_limit.narrator_questions_per_chapter
    fake = FakeLLM.scripted([reply(False, None, [])] * cfg_limit)
    with TestClient(build(3, fake=fake), raise_server_exceptions=False) as client:
        for _ in range(cfg_limit):
            assert client.post("/stories/s1/narrator", json={"question": "?"}).status_code == 200
        resp = client.post("/stories/s1/narrator", json={"question": "Thêm?"})
    assert resp.status_code == 429 == HTTP_STATUS[ErrorCode.NARRATOR_LIMIT_REACHED]
    assert resp.json() == WritoryError(ErrorCode.NARRATOR_LIMIT_REACHED).player_payload()


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
    """Chưa có nơi lưu key người chơi (tuần 5): mặc định báo thiếu key, không gọi model nào."""
    with TestClient(build(3, override_llm=False), raise_server_exceptions=False) as client:
        resp = client.post("/stories/s1/narrator", json={"question": "Lan là ai?"})
    assert resp.status_code == 400
    assert resp.json() == WritoryError(ErrorCode.PLAYER_KEY_MISSING).player_payload()


def test_narrator_without_story_plan_fails_closed():
    """Chưa có nơi lưu story_plan: không chạy được bộ dò lộ đầy đủ, nên không trả lời."""
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


def test_router_mounted_when_dev_flag_on():
    app = create_app(settings(dev=True), health_checks={"neo4j": ok}, config=CFG)
    assert {"/stories/{story_id}/notebook", "/stories/{story_id}/narrator"} <= _paths(app)


def test_router_mounted_elsewhere_without_flag_still_refuses():
    """Phòng thủ hai lớp: gắn router vào app khác mà không qua create_app thì vẫn 404."""
    app = FastAPI()
    app.include_router(stories_router)
    app.dependency_overrides[deps.get_player_view] = lambda: view(3)
    with TestClient(app) as client:
        assert client.get("/stories/s1/notebook").status_code == 404
