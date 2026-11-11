"""Lượt hỏi đáp người kể được lưu trong Postgres và đưa lại cho người kể (D-162).
Đọc thật từ Postgres + Neo4j; chỉ model (FakeLLM) và story_plan được thay."""

import html

import pytest
from fastapi.testclient import TestClient

from tests.graph.test_notebook_api import _app, _story
from tests.moderation_fixtures import moderation_reply
from tests.unit.test_narrator import CFG, reply
from tests.unit.test_narrator_history import HISTORY_OPEN, with_history
from tests.unit.test_narrator_pages import CFG4
from writory.db import (
    NarratorTurnRow,
    add_narrator_turn,
    committed_player_view,
    narrator_turns,
)
from writory.db.chapters import StoryNotFoundError
from writory.graph import public_entries
from writory.llm.fake import FakeLLM
from writory.pipeline.narrator import NOT_KNOWN
from writory.safety.wrap import CLOSE_TAG

pytestmark = pytest.mark.graph


# --- lớp db ---------------------------------------------------------------------------------------


def test_turns_are_kept_in_order_per_story_and_chapter(pg, driver, new_db_story_id):
    a, b = new_db_story_id(), new_db_story_id()
    for sid in (a, b):
        _story(pg, driver, sid, 1)
    add_narrator_turn(pg, a, 1, "câu một", "đáp một", [1])
    add_narrator_turn(pg, a, 1, "câu hai", NOT_KNOWN, [])
    add_narrator_turn(pg, a, 2, "chương khác", "đáp", [2, 1])
    add_narrator_turn(pg, b, 1, "truyện khác", "đáp", [])
    assert narrator_turns(pg, a, 1) == [
        NarratorTurnRow("câu một", "đáp một", (1,)),
        NarratorTurnRow("câu hai", NOT_KNOWN, ()),
    ]
    assert narrator_turns(pg, a, 2) == [NarratorTurnRow("chương khác", "đáp", (1, 2))]
    assert narrator_turns(pg, a, 3) == []


def test_turn_of_unknown_story_is_not_found(pg, new_db_story_id):
    with pytest.raises(StoryNotFoundError):
        add_narrator_turn(pg, new_db_story_id(), 1, "câu", "đáp", [])


def test_deleting_the_story_deletes_its_turns(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 1)
    add_narrator_turn(pg, sid, 1, "câu", "đáp", [])
    pg.execute("DELETE FROM stories WHERE id = %s", (sid,))
    assert pg.execute("SELECT count(*) FROM narrator_turns WHERE story_id = %s",
                      (sid,)).fetchone()[0] == 0


# --- API: lưu và đọc lại ----------------------------------------------------------------------------


def test_an_answered_question_is_stored_and_read_back(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    view = committed_player_view(pg, driver, sid)
    gu, chapter = next((r, e.since_chapter) for r, e in public_entries(view)
                       if e.id == "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu]),
                             reply(False, None, [])])
    with TestClient(_app(pg, driver, fake=fake)) as client:
        client.post(f"/stories/{sid}/narrator", json={"question": "Lão Gù chết ở đâu?"})
        client.post(f"/stories/{sid}/narrator", json={"question": "Ai giết lão?"})
        turns = client.get(f"/stories/{sid}/narrator/turns")
    assert turns.status_code == 200
    assert turns.json() == {"chapter": 3, "turns": [
        {"question": "Lão Gù chết ở đâu?", "answer": "Lão Gù chết sau miếu Bà.",
         "source_chapters": [chapter]},
        {"question": "Ai giết lão?", "answer": NOT_KNOWN, "source_chapters": []},
    ]}


def test_turns_endpoint_only_lists_the_committed_chapter(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    add_narrator_turn(pg, sid, 2, "câu của chương trước", "đáp", [])
    with TestClient(_app(pg, driver)) as client:
        body = client.get(f"/stories/{sid}/narrator/turns").json()
    assert body == {"chapter": 3, "turns": []}


def test_turns_of_unknown_story_is_404(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    with TestClient(_app(pg, driver), raise_server_exceptions=False) as client:
        resp = client.get(f"/stories/{sid}/narrator/turns")
    assert (resp.status_code, resp.json()["code"]) == (404, "STORY_NOT_FOUND")


def test_a_blocked_answer_is_not_stored(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    view = committed_player_view(pg, driver, sid)
    gu = next(r for r, e in public_entries(view) if e.id == "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu])])
    votes = [moderation_reply()] * CFG.moderation.input_votes
    app = _app(pg, driver, fake=fake, moderation=[*votes, moderation_reply(("gore", "extreme"))])
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(f"/stories/{sid}/narrator", json={"question": "Lão Gù chết ở đâu?"})
    assert resp.json()["code"] == "NARRATOR_ANSWER_BLOCKED"
    assert narrator_turns(pg, sid, 3) == []


def test_a_question_over_the_limit_is_not_stored(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    limit = CFG.limits.rate_limit.narrator_questions_per_chapter
    fake = FakeLLM.scripted([reply(False, None, [])] * limit)
    with TestClient(_app(pg, driver, fake=fake), raise_server_exceptions=False) as client:
        for n in range(limit + 1):
            client.post(f"/stories/{sid}/narrator", json={"question": f"Câu {n}?"})
    assert [t.question for t in narrator_turns(pg, sid, 3)] == [f"Câu {n}?" for n in range(limit)]


# --- API: lịch sử vào context của người kể -----------------------------------------------------------


def _user(fake: FakeLLM, call: int) -> str:
    [user] = [m.content for m in fake.calls[call] if m.role == "user"]
    return user


def test_switched_on_the_second_question_carries_the_first_turn(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    view = committed_player_view(pg, driver, sid)
    gu = next(r for r, e in public_entries(view) if e.id == "e_gu_death")
    fake = FakeLLM.scripted([reply(True, "Lão Gù chết sau miếu Bà.", [gu]),
                             reply(False, None, [])])
    with TestClient(_app(pg, driver, fake=fake, config=with_history())) as client:
        client.post(f"/stories/{sid}/narrator", json={"question": "Lão Gù chết ở đâu?"})
        client.post(f"/stories/{sid}/narrator", json={"question": "Thế chết thế nào?"})
    assert HISTORY_OPEN not in _user(fake, 0)
    second = _user(fake, 1)
    block = html.unescape(second.split(HISTORY_OPEN, 1)[1].split(CLOSE_TAG, 1)[0])
    assert "Lão Gù chết ở đâu?" in block and "Lão Gù chết sau miếu Bà." in block


def test_switched_off_stored_turns_never_reach_the_model(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    add_narrator_turn(pg, sid, 3, "Lão Gù chết ở đâu?", "Lão Gù chết sau miếu Bà.", [3])
    fake = FakeLLM.scripted([reply(False, None, [])])
    with TestClient(_app(pg, driver, fake=fake, config=CFG4)) as client:
        client.post(f"/stories/{sid}/narrator", json={"question": "Thế chết thế nào?"})
    assert HISTORY_OPEN not in _user(fake, 0)
    assert "miếu Bà" not in _user(fake, 0).split('source="narrator_question"', 1)[1]


def test_turns_of_an_earlier_chapter_are_not_sent(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story(pg, driver, sid, 3)
    add_narrator_turn(pg, sid, 2, "Câu hỏi của chương hai?", "Đáp của chương hai.", [2])
    fake = FakeLLM.scripted([reply(False, None, [])])
    with TestClient(_app(pg, driver, fake=fake, config=with_history())) as client:
        client.post(f"/stories/{sid}/narrator", json={"question": "Thế còn ông ấy?"})
    assert "Câu hỏi của chương hai?" not in _user(fake, 0)
