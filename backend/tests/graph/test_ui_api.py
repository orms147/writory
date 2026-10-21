"""Endpoint cho giao diện trên Postgres + Neo4j thật (D-66): tủ truyện, chi phí người chơi, số câu
hỏi người kể còn lại và nguồn. Mỗi test dùng một người chơi riêng (`deps.get_owner_id`), vì
database dùng chung giữa các test và người chơi dev `dev` có thể còn truyện của test khác.

G1: không id lớp truth, không chữ kế hoạch. G7: không gì của key. G10 (TODO đăng nhập): chỉ dữ
liệu của người đang dùng; truyện của người khác là 404.
"""

import json
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.api_fixtures import FAKE_KEY, AllowAllQuota, captured_logs, dev_settings
from tests.moderation_fixtures import ModeratedLLM
from tests.unit.test_narrator import CFG, PLAN, metered, reply
from writory.api import create_app, deps
from writory.api.schemas import last_sentence
from writory.db import (
    CostEntry,
    chapter_scenes,
    commit_chapter,
    committed_player_view,
    create_setup,
    create_story_with_plan,
    finish_setup,
    record_cost,
    save_player_key,
    save_setup_options,
    take_narrator_question,
)
from writory.db import choose_setup_option as choose
from writory.graph import public_entries, read_sample
from writory.llm.fake import FakeLLM

pytestmark = pytest.mark.graph

SAMPLE = read_sample()
LIMIT = CFG.limits.rate_limit.narrator_questions_per_chapter
CHOICES = {"tags": {"genre": "kiếm hiệp"}, "length_level": "short",
           "naming": {"names": "viet", "places": "that"}}
PROTAGONIST = {"name": "Trần Minh", "personality": "lầm lì", "backstory": "chép sách thuê"}


async def _ok() -> bool:
    return True


@pytest.fixture
def owner(pg):
    """Một người chơi riêng cho test; dọn phiên khởi tạo, nhật ký chi phí và key của người đó."""
    name = f"ui-{uuid.uuid4().hex[:10]}"
    yield name
    pg.execute("DELETE FROM llm_costs WHERE owner_id = %s", (name,))
    pg.execute("DELETE FROM setup_sessions WHERE owner_id = %s", (name,))
    pg.execute("DELETE FROM player_keys WHERE owner_id = %s", (name,))


def make_app(pg, driver, owner_id: str, *, fake: FakeLLM | None = None, clock=None):
    app = create_app(dev_settings(), health_checks={"neo4j": _ok}, config=CFG)
    app.dependency_overrides[deps.get_pg_conn] = lambda: pg
    app.dependency_overrides[deps.get_neo4j_driver] = lambda: driver
    app.dependency_overrides[deps.get_owner_id] = lambda: owner_id
    app.dependency_overrides[deps.get_call_quota] = AllowAllQuota
    if fake is not None:
        llm = metered(ModeratedLLM(fake))  # kiểm duyệt đầu vào (G9) mặc định cho qua
        app.dependency_overrides[deps.get_narrator_llm] = lambda: llm
    if clock is not None:
        app.dependency_overrides[deps.get_clock] = lambda: (lambda: clock)  # đồng hồ giả
    return app


def make_story(pg, driver, sid: str, owner_id: str, *, up_to: int = 3, plan=PLAN) -> str:
    create_story_with_plan(pg, sid, owner_id=owner_id, length_level="short", brief="b", plan=plan)
    for n in range(up_to + 1):
        ch = SAMPLE.chapters[n]
        commit_chapter(pg, driver, sid, n, [ch.text] if ch.text else [], ch.package)
    return sid


def attach_setup(pg, sid: str, owner_id: str, *, setting: str, plot: str) -> str:
    """Phiên khởi tạo đã chốt ra truyện `sid`: bối cảnh, hướng, nhân vật đã chọn (chỉ số 1)."""
    session = f"setup-{uuid.uuid4().hex[:12]}"
    create_setup(pg, session, owner_id=owner_id, choices=CHOICES)
    save_setup_options(pg, session, "settings", [
        {"title": f"{setting} {i}" if i != 1 else setting, "intro": "Giới thiệu."}
        for i in range(3)])
    choose(pg, session, "settings", 1)
    save_setup_options(pg, session, "plots", [
        {"title": f"{plot} {i}" if i != 1 else plot, "summary": "Tóm tắt."} for i in range(3)])
    choose(pg, session, "plots", 1)
    save_setup_options(pg, session, "characters", [PROTAGONIST] * 3)
    choose(pg, session, "characters", 1, protagonist=PROTAGONIST)
    finish_setup(pg, session, sid)
    return session


def set_updated(pg, sid: str, when: datetime) -> None:
    pg.execute("UPDATE stories SET updated_at = %s WHERE id = %s", (when, sid))


def plan_strings() -> set[str]:
    def leaves(v):
        if isinstance(v, dict):
            for x in v.values():
                yield from leaves(x)
        elif isinstance(v, list):
            for x in v:
                yield from leaves(x)
        else:
            yield v
    return {s for s in leaves(PLAN.model_dump(mode="json")) if isinstance(s, str)}


# --- tủ truyện ----------------------------------------------------------------------------------


def test_story_list_is_only_the_players_stories_newest_first(pg, driver, new_db_story_id, owner):
    old, new = new_db_story_id(), new_db_story_id()
    other = new_db_story_id()
    make_story(pg, driver, old, owner, up_to=1)
    make_story(pg, driver, new, owner, up_to=2)
    make_story(pg, driver, other, "nguoi-khac", up_to=1)
    set_updated(pg, old, datetime(2026, 10, 1, tzinfo=UTC))
    set_updated(pg, new, datetime(2026, 10, 20, tzinfo=UTC))
    with TestClient(make_app(pg, driver, owner)) as client:
        body = client.get("/stories").json()
    assert [s["story_id"] for s in body["stories"]] == [new, old]
    assert other not in json.dumps(body)
    assert body["stories"][0]["updated_at"] == "2026-10-20T00:00:00+00:00"
    assert [s["chapter"] for s in body["stories"]] == [2, 1]


def test_story_list_title_is_the_chosen_plot_and_excerpt_the_last_shown_sentence(
        pg, driver, new_db_story_id, owner):
    sid = make_story(pg, driver, new_db_story_id(), owner, up_to=3)
    attach_setup(pg, sid, owner, setting="Phố Bến Sương", plot="Thanh kiếm của cha")
    with TestClient(make_app(pg, driver, owner)) as client:
        [story] = client.get("/stories").json()["stories"]
        shown = client.get(f"/stories/{sid}/chapters/3").json()["scenes"]
    assert story["title"] == "Thanh kiếm của cha"  # hướng truyện đã chọn, không phải lựa chọn khác
    assert story["last_excerpt"] == last_sentence(shown[-1])
    assert story["last_excerpt"] and story["last_excerpt"] in shown[-1]
    assert (story["length_level"], story["length_label"]) == (
        "short", CFG.story_lengths.levels["short"].label)
    assert story["finished"] is False


def test_story_without_setup_session_or_pages_has_null_title_and_excerpt(
        pg, driver, new_db_story_id, owner):
    sid = make_story(pg, driver, new_db_story_id(), owner, up_to=0)
    with TestClient(make_app(pg, driver, owner)) as client:
        [story] = client.get("/stories").json()["stories"]
    assert story["story_id"] == sid
    assert (story["chapter"], story["title"], story["last_excerpt"]) == (0, None, None)


def test_excerpt_never_comes_from_a_chapter_that_is_not_committed(pg, driver, new_db_story_id,
                                                                   owner):
    """D-6: chương `pending` chưa hiện cho người chơi; chữ của nó không được ra tủ truyện."""
    sid = make_story(pg, driver, new_db_story_id(), owner, up_to=3)
    pg.execute("INSERT INTO chapters (story_id, commit_id, number, status, scenes) "
               "VALUES (%s, %s, 4, 'pending', %s)",
               (sid, f"{sid}-ch4", json.dumps(["Chữ chưa hiện của chương dở."])))
    with TestClient(make_app(pg, driver, owner)) as client:
        [story] = client.get("/stories").json()["stories"]
    assert story["chapter"] == 3
    assert story["last_excerpt"] == last_sentence(chapter_scenes(pg, sid, 3)[-1])
    assert "chưa hiện" not in story["last_excerpt"]


def test_finished_story_is_marked_from_the_plan(pg, driver, new_db_story_id, owner):
    short = PLAN.model_copy(update={"acts": [PLAN.acts[0].model_copy(update={"to_chapter": 3})],
                                    "secrets": []})
    sid = make_story(pg, driver, new_db_story_id(), owner, up_to=3, plan=short)
    with TestClient(make_app(pg, driver, owner)) as client:
        [story] = client.get("/stories").json()["stories"]
        state = client.get(f"/stories/{sid}").json()
    assert story["finished"] is state["finished"] is True


def test_story_list_has_no_plan_text_or_truth_ids(pg, driver, new_db_story_id, owner):
    sid = make_story(pg, driver, new_db_story_id(), owner, up_to=4)
    attach_setup(pg, sid, owner, setting="Phố Bến Sương", plot="Thanh kiếm của cha")
    with TestClient(make_app(pg, driver, owner)) as client:
        text = json.dumps(client.get("/stories").json(), ensure_ascii=False)
    shown = "\n".join(chapter_scenes(pg, sid, n)[-1] for n in range(1, 5))
    hidden = {s for s in plan_strings() if s not in shown}
    assert not [s for s in hidden if s in text]
    view = committed_player_view(pg, driver, sid)
    truth_ids = {e.id for e in view.entries} | {"ly_that", "lan", "minh", "hac_ky"}
    assert not [i for i in truth_ids if f'"{i}"' in text]
    assert "Lý Thất" not in text


# --- chi phí người chơi -------------------------------------------------------------------------


def cost(pg, owner_id, usd, when, *, story_id=None, setup_id=None):
    record_cost(pg, owner_id=owner_id, entry=CostEntry("writer", "m", 1, 1, usd),
                story_id=story_id, setup_id=setup_id, chapter=1 if story_id else None)
    pg.execute("UPDATE llm_costs SET created_at = %s WHERE id = (SELECT max(id) FROM llm_costs "
               "WHERE owner_id = %s)", (when, owner_id))


def test_player_costs_sum_the_ledger_by_story_and_utc_month(pg, driver, new_db_story_id, owner):
    a = make_story(pg, driver, new_db_story_id(), owner, up_to=0)
    b = make_story(pg, driver, new_db_story_id(), owner, up_to=0)
    other = make_story(pg, driver, new_db_story_id(), "nguoi-khac", up_to=0)
    session = f"setup-{uuid.uuid4().hex[:12]}"
    create_setup(pg, session, owner_id=owner, choices=CHOICES)  # phiên bỏ dở: chưa ra truyện
    cost(pg, owner, 0.010, datetime(2026, 10, 1, 0, 0, tzinfo=UTC), story_id=a)
    cost(pg, owner, 0.020, datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC), story_id=a)  # tháng 9
    cost(pg, owner, None, datetime(2026, 10, 2, tzinfo=UTC), story_id=a)  # thiếu chi phí (D-10)
    cost(pg, owner, 0.005, datetime(2026, 10, 14, tzinfo=UTC), story_id=b)
    cost(pg, owner, 0.003, datetime(2026, 10, 3, tzinfo=UTC), setup_id=session)
    cost(pg, owner, 0.040, datetime(2026, 11, 1, tzinfo=UTC), story_id=b)  # tháng sau
    cost(pg, "nguoi-khac", 0.5, datetime(2026, 10, 5, tzinfo=UTC), story_id=other)
    try:
        now = datetime(2026, 10, 15, 12, tzinfo=UTC).timestamp()
        with TestClient(make_app(pg, driver, owner, clock=now)) as client:
            body = client.get("/player/costs").json()
    finally:
        pg.execute("DELETE FROM llm_costs WHERE owner_id = 'nguoi-khac' AND story_id = %s",
                   (other,))
    assert body["total_usd"] == pytest.approx(0.078)
    assert body["this_month_usd"] == pytest.approx(0.018)  # 1/10 0:00 UTC tính, 30/9 thì không
    assert [(s["story_id"], s["spent_usd"]) for s in body["stories"]] == [
        (b, pytest.approx(0.045)), (a, pytest.approx(0.030))]
    assert other not in json.dumps(body)


def test_player_costs_never_show_the_key(pg, driver, owner):
    app = make_app(pg, driver, owner)
    save_player_key(pg, owner, app.state.key_cipher.encrypt(SecretStr(FAKE_KEY)))
    with captured_logs() as logs, TestClient(app) as client:
        resp = client.get("/player/costs")
    assert resp.json() == {"total_usd": 0.0, "this_month_usd": 0.0, "stories": []}
    for text in (resp.text, logs.text):
        assert FAKE_KEY not in text and FAKE_KEY[9:-4] not in text
    assert FAKE_KEY[-4:] not in resp.text


# --- người kể: số câu còn lại và nguồn ----------------------------------------------------------


def test_narrator_remaining_and_sources_from_postgres(pg, driver, new_db_story_id, owner):
    sid = make_story(pg, driver, new_db_story_id(), owner, up_to=3)
    view = committed_player_view(pg, driver, sid)
    gu = next((r, e) for r, e in public_entries(view) if e.id == "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu[0]])])
    app = make_app(pg, driver, owner, fake=fake)
    app.dependency_overrides[deps.get_story_plan] = lambda: PLAN
    with TestClient(app) as client:
        before = client.get(f"/stories/{sid}/narrator").json()
        resp = client.post(f"/stories/{sid}/narrator", json={"question": "Lão Gù chết ở đâu?"})
        take_narrator_question(pg, sid, 3, LIMIT)  # câu hỏi từ nơi khác cùng chương
        after = client.get(f"/stories/{sid}/narrator").json()
    assert before == {"remaining": LIMIT}
    assert resp.json() == {"answer": "Lão Gù chết sau miếu Bà.", "remaining": LIMIT - 1,
                           "source_chapters": [gu[1].since_chapter]}
    assert after == {"remaining": LIMIT - 2}


def test_narrator_get_of_another_owners_story_is_404(pg, driver, new_db_story_id, owner):
    sid = make_story(pg, driver, new_db_story_id(), "nguoi-khac", up_to=1)
    with TestClient(make_app(pg, driver, owner), raise_server_exceptions=False) as client:
        resp = client.get(f"/stories/{sid}/narrator")
    assert (resp.status_code, resp.json()["code"]) == (404, "STORY_NOT_FOUND")
    assert sid not in resp.text
