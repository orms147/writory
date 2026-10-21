"""Sổ tay và hỏi người kể qua API trên truyện mẫu đã commit qua db (D-6, D-40, D-41).
Đọc thật từ Postgres + Neo4j; chỉ model (FakeLLM) và story_plan được thay."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.api_fixtures import MASTER_KEY
from tests.moderation_fixtures import ModeratedLLM
from tests.unit.test_narrator import CFG, PLAN, metered, reply
from writory.api import create_app, deps
from writory.api.deps import DEV_OWNER_ID
from writory.config import Settings
from writory.db import (
    commit_chapter,
    committed_player_view,
    create_story,
    take_narrator_question,
)
from writory.graph import public_entries, read_sample
from writory.llm.fake import FakeLLM
from writory.pipeline.narrator import NOT_KNOWN

pytestmark = pytest.mark.graph

SAMPLE = read_sample()


def _story(pg, driver, sid, up_to):
    create_story(pg, sid, length_level="short", owner_id=DEV_OWNER_ID)
    for n in range(up_to + 1):
        ch = SAMPLE.chapters[n]
        commit_chapter(pg, driver, sid, n, [ch.text] if ch.text else [], ch.package)


async def _ok() -> bool:
    return True


def _app(pg, driver, *, fake: FakeLLM | None = None):
    settings = Settings(
        _env_file=None, neo4j_uri="bolt://unused", neo4j_user="u", neo4j_password="p",
        postgres_dsn="postgresql://unused", player_key_encryption_key=MASTER_KEY,
        enable_dev_routes=True,
    )
    app = create_app(settings, health_checks={"neo4j": _ok}, config=CFG)
    app.dependency_overrides[deps.get_pg_conn] = lambda: pg
    app.dependency_overrides[deps.get_neo4j_driver] = lambda: driver
    app.dependency_overrides[deps.get_story_plan] = lambda: PLAN
    if fake is not None:
        llm = metered(ModeratedLLM(fake))  # kiểm duyệt đầu vào (G9) mặc định cho qua
        app.dependency_overrides[deps.get_narrator_llm] = lambda: llm
    return app


def test_notebook_reads_committed_player_view(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 4)
    with TestClient(_app(pg, driver)) as client:
        resp = client.get(f"/stories/{sid}/notebook")
    assert resp.status_code == 200
    body = resp.json()
    view = committed_player_view(pg, driver, sid)
    assert body["chapter"] == view.chapter == 4
    assert [(e["ref"], e["text"]) for e in body["entries"]] == [
        (r, e.text) for r, e in public_entries(view)
    ]
    text = json.dumps(body, ensure_ascii=False)
    assert "Lý Thất" not in text and "ly_that" not in text
    assert sid not in text


def test_notebook_of_unknown_story_is_404(pg, driver, new_db_story_id):
    sid = new_db_story_id()  # chưa tạo
    with TestClient(_app(pg, driver), raise_server_exceptions=False) as client:
        resp = client.get(f"/stories/{sid}/notebook")
    assert resp.status_code == 404
    assert resp.json()["code"] == "STORY_NOT_FOUND"


def test_narrator_quota_is_counted_in_postgres(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    limit = CFG.limits.rate_limit.narrator_questions_per_chapter
    fake = FakeLLM.scripted([reply(False, None, [])] * limit)
    with TestClient(_app(pg, driver, fake=fake), raise_server_exceptions=False) as client:
        answers = [client.post(f"/stories/{sid}/narrator", json={"question": "Lan là ai?"})
                   for _ in range(limit)]
        last = client.post(f"/stories/{sid}/narrator", json={"question": "Thêm?"})
    assert [(a.status_code, a.json()) for a in answers] == [(200, {"answer": NOT_KNOWN})] * limit
    assert (last.status_code, last.json()["code"]) == (429, "NARRATOR_LIMIT_REACHED")
    assert len(fake.calls) == limit


def test_take_narrator_question_is_per_story_and_chapter(pg, driver, new_db_story_id):
    a, b = new_db_story_id(), new_db_story_id()
    create_story(pg, a, length_level="short")
    create_story(pg, b, length_level="short")
    assert [take_narrator_question(pg, a, 1, 2) for _ in range(3)] == [True, True, False]
    assert take_narrator_question(pg, a, 2, 2) is True  # chương mới: lượt mới
    assert take_narrator_question(pg, b, 1, 2) is True  # truyện khác không bị ảnh hưởng
    assert take_narrator_question(pg, a, 3, 0) is False


def test_take_narrator_question_for_unknown_story_is_not_found(pg, new_db_story_id):
    from writory.db import StoryNotFoundError

    with pytest.raises(StoryNotFoundError):
        take_narrator_question(pg, new_db_story_id(), 1, 2)
