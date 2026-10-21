"""Dependency của API đọc thật từ Postgres (D-44): bản kế hoạch ẩn, key người chơi đã mã hoá, nhật
ký chi phí, kiểm chủ truyện. Chỉ model (FakeLLM qua nhà máy client) được thay."""

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.api_fixtures import FAKE_KEY, AllowAllQuota, KeyedFactory, dev_settings
from tests.moderation_fixtures import ModeratedLLM
from tests.unit.test_narrator import CFG, PLAN, reply
from writory.api import create_app, deps
from writory.api.deps import DEV_OWNER_ID
from writory.db import (
    commit_chapter,
    committed_player_view,
    create_story,
    create_story_with_plan,
    delete_player_key,
    save_player_key,
    story_spent_usd,
)
from writory.graph import public_entries, read_sample
from writory.llm.fake import FakeLLM

pytestmark = pytest.mark.graph

SAMPLE = read_sample()


async def _ok() -> bool:
    return True


def _commit_through(pg, driver, sid, up_to):
    for n in range(up_to + 1):
        ch = SAMPLE.chapters[n]
        commit_chapter(pg, driver, sid, n, [ch.text] if ch.text else [], ch.package)


@pytest.fixture
def dev_key(pg):
    """Key giả của người chơi dev, lưu mã hoá; dọn sau test (bảng dùng chung giữa các test)."""
    yield lambda cipher: save_player_key(pg, DEV_OWNER_ID, cipher.encrypt(SecretStr(FAKE_KEY)))
    delete_player_key(pg, DEV_OWNER_ID)


def _app(pg, driver, fake: FakeLLM):
    app = create_app(dev_settings(), health_checks={"neo4j": _ok}, config=CFG)
    app.dependency_overrides[deps.get_pg_conn] = lambda: pg
    app.dependency_overrides[deps.get_neo4j_driver] = lambda: driver
    factory = KeyedFactory(ModeratedLLM(fake))  # kiểm duyệt đầu vào (G9) mặc định cho qua
    app.dependency_overrides[deps.get_llm_factory] = lambda: factory
    app.dependency_overrides[deps.get_call_quota] = AllowAllQuota  # xem make_app của test_play_api
    return app, factory


def test_narrator_reads_plan_and_key_from_postgres_and_logs_cost(pg, driver, new_db_story_id,
                                                                  dev_key):
    sid = new_db_story_id()
    create_story_with_plan(pg, sid, owner_id=DEV_OWNER_ID, length_level="short", brief="b",
                           plan=PLAN)
    _commit_through(pg, driver, sid, 3)
    view = committed_player_view(pg, driver, sid)
    gu_death = next(r for r, e in public_entries(view) if e.id == "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu_death])], cost_usd=0.003)
    app, factory = _app(pg, driver, fake)
    dev_key(app.state.key_cipher)
    with TestClient(app) as client:
        resp = client.post(f"/stories/{sid}/narrator", json={"question": "Lão Gù chết ở đâu?"})
    assert resp.json()["answer"] == "Lão Gù chết sau miếu Bà."
    assert factory.keys == [FAKE_KEY]
    rows = pg.execute("SELECT owner_id, chapter, role, model FROM llm_costs WHERE story_id = %s "
                      "ORDER BY id", (sid,)).fetchall()
    # Kiểm duyệt câu hỏi (G9, D-57) rồi người kể; cả hai ghi nhật ký ở chương đang đọc.
    assert rows == [(DEV_OWNER_ID, 3, "moderate", CFG.models.roles.moderate),
                    (DEV_OWNER_ID, 3, "narrator", CFG.models.roles.narrator)]
    assert story_spent_usd(pg, sid) == pytest.approx(0.003)


def test_story_without_plan_fails_closed(pg, driver, new_db_story_id, dev_key):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short", owner_id=DEV_OWNER_ID)
    _commit_through(pg, driver, sid, 3)
    fake = FakeLLM.scripted([])
    app, _ = _app(pg, driver, fake)
    dev_key(app.state.key_cipher)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(f"/stories/{sid}/narrator", json={"question": "Lan là ai?"})
    assert (resp.status_code, resp.json()["code"]) == (500, "INTERNAL_ERROR")
    assert fake.calls == []


def test_story_of_another_owner_is_404(pg, driver, new_db_story_id):
    """G10 (đường ống): truyện không thuộc người đang dùng báo giống truyện không có."""
    sid = new_db_story_id()
    create_story_with_plan(pg, sid, owner_id="someone-else", length_level="short", brief="b",
                           plan=PLAN)
    _commit_through(pg, driver, sid, 1)
    app, _ = _app(pg, driver, FakeLLM.scripted([]))
    with TestClient(app, raise_server_exceptions=False) as client:
        for resp in (client.get(f"/stories/{sid}/notebook"),
                     client.post(f"/stories/{sid}/narrator", json={"question": "?"})):
            assert resp.status_code == 404
            assert resp.json()["code"] == "STORY_NOT_FOUND"
            assert sid not in resp.text


def test_narrator_without_saved_key_reports_missing_key(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    create_story_with_plan(pg, sid, owner_id=DEV_OWNER_ID, length_level="short", brief="b",
                           plan=PLAN)
    _commit_through(pg, driver, sid, 3)
    delete_player_key(pg, DEV_OWNER_ID)
    fake = FakeLLM.scripted([])
    app, factory = _app(pg, driver, fake)
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(f"/stories/{sid}/narrator", json={"question": "Lan là ai?"})
    assert (resp.status_code, resp.json()["code"]) == (400, "PLAYER_KEY_MISSING")
    assert factory.keys == [] and fake.calls == []
