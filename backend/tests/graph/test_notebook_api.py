"""Sổ tay và hỏi người kể qua API trên truyện mẫu đã commit qua db (D-6, D-40, D-41).
Đọc thật từ Postgres + Neo4j; chỉ model (FakeLLM) và story_plan được thay."""

import json

import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from tests.api_fixtures import MASTER_KEY
from tests.moderation_fixtures import ModeratedLLM, moderation_reply
from tests.unit.test_narrator import CFG, PLAN, metered, reply
from tests.unit.test_narrator_pages import CFG4, PASSAGES_OPEN, passage_block
from writory.api import create_app, deps
from writory.api.deps import DEV_OWNER_ID
from writory.config import Settings
from writory.db import (
    commit_chapter,
    committed_page_texts,
    committed_player_view,
    create_story,
    narrator_questions_asked,
    release_narrator_question,
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


def _app(pg, driver, *, fake: FakeLLM | None = None, moderation=(), config=CFG):
    settings = Settings(
        _env_file=None, neo4j_uri="bolt://unused", neo4j_user="u", neo4j_password="p",
        postgres_dsn="postgresql://unused", player_key_encryption_key=MASTER_KEY,
        enable_dev_routes=True,
    )
    app = create_app(settings, health_checks={"neo4j": _ok}, config=config)
    app.dependency_overrides[deps.get_pg_conn] = lambda: pg
    app.dependency_overrides[deps.get_neo4j_driver] = lambda: driver
    app.dependency_overrides[deps.get_story_plan] = lambda: PLAN
    if fake is not None:
        llm = metered(ModeratedLLM(fake, moderation))  # kiểm duyệt (G9) mặc định cho qua
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
    assert [(a.status_code, a.json()) for a in answers] == [
        (200, {"answer": NOT_KNOWN, "remaining": limit - n, "source_chapters": []})
        for n in range(1, limit + 1)]
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


# --- câu trả lời bị kiểm duyệt chặn thì trả lại lượt (G9, D-137) ------------------------------------


def test_release_narrator_question_gives_back_one_turn_and_never_goes_below_zero(
        pg, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short")
    assert [take_narrator_question(pg, sid, 1, 2) for _ in range(2)] == [True, True]
    release_narrator_question(pg, sid, 1)
    assert narrator_questions_asked(pg, sid, 1) == 1
    assert [take_narrator_question(pg, sid, 1, 2) for _ in range(2)] == [True, False]
    for _ in range(3):
        release_narrator_question(pg, sid, 1)
    assert narrator_questions_asked(pg, sid, 1) == 0
    release_narrator_question(pg, sid, 5)  # chương chưa hỏi câu nào: không có gì để trả
    assert narrator_questions_asked(pg, sid, 5) == 0
    assert take_narrator_question(pg, sid, 5, 1) is True


def test_blocked_answer_does_not_use_a_question_in_postgres(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    view = committed_player_view(pg, driver, sid)
    gu = next(r for r, e in public_entries(view) if e.id == "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu])])
    votes = [moderation_reply()] * CFG.moderation.input_votes
    # Truyện không chọn mức u tối: mức mặc định; máu me tả kéo dài vượt trần của nó.
    blocked = moderation_reply(("gore", "extreme"))
    app = _app(pg, driver, fake=fake, moderation=[*votes, blocked])
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(f"/stories/{sid}/narrator", json={"question": "Lão Gù chết ở đâu?"})
        remaining = client.get(f"/stories/{sid}/narrator").json()
    assert (resp.status_code, resp.json()["code"]) == (502, "NARRATOR_ANSWER_BLOCKED")
    assert "miếu Bà" not in resp.text
    assert narrator_questions_asked(pg, sid, 3) == 0
    assert remaining == {"remaining": CFG.limits.rate_limit.narrator_questions_per_chapter}


# --- đoạn đã hiện trên trang (D-143): chỉ chương đã commit ------------------------------------------


def _pending(pg, sid: str, number: int, scenes: list[str]) -> None:
    """Một chương còn `pending` (đã ghi Postgres, chưa áp sang Neo4j): chữ của nó chưa hiện."""
    pg.execute("INSERT INTO chapters (story_id, commit_id, number, status, scenes) "
               "VALUES (%s, %s, %s, 'pending', %s)",
               (sid, f"pending-{number}", number, Jsonb(scenes)))


def test_committed_page_texts_skip_pending_chapters_and_chapter_zero(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 4)
    _pending(pg, sid, 5, [SAMPLE.chapters[5].text])
    texts = committed_page_texts(pg, sid, 10)
    assert sorted(texts) == [1, 2, 3, 4]
    assert texts[2] == SAMPLE.chapters[2].text
    assert sorted(committed_page_texts(pg, sid, 2)) == [1, 2]
    assert committed_page_texts(pg, sid, 0) == {}


def test_narrator_reads_only_pages_of_committed_chapters(pg, driver, new_db_story_id):
    """Chương 5 (tên thật "Lý Thất") còn pending: người kể ở chương 4 không thấy chữ nào của nó."""
    sid = new_db_story_id()
    _story(pg, driver, sid, 4)
    _pending(pg, sid, 5, [SAMPLE.chapters[5].text])
    fake = FakeLLM.scripted([reply(False, None, [])])
    with TestClient(_app(pg, driver, fake=fake, config=CFG4)) as client:
        resp = client.post(f"/stories/{sid}/narrator",
                           json={"question": "Gã lái đò mặt sẹo tên thật là gì? Lý Thất là ai?"})
    assert resp.status_code == 200
    [messages] = fake.calls
    [user] = [m.content for m in messages if m.role == "user"]
    assert PASSAGES_OPEN in user
    block = passage_block(user)
    assert "Lý Thất" not in block and "Chương 5:" not in block
