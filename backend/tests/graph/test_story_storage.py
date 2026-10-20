"""Lưu trữ Postgres cho API truyện (migration 0003, D-44): bản kế hoạch ẩn, key người chơi đã mã
hoá (G7), phiên khởi tạo, nhật ký chi phí, lựa chọn và hành động dẫn tới chương sau."""

import uuid

import psycopg
import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from tests.pipeline_fixtures import PLAN
from writory.db import (
    CostEntry,
    SetupNotFoundError,
    SetupStepError,
    choose_setup_option,
    create_setup,
    create_story,
    create_story_with_plan,
    delete_player_key,
    finish_setup,
    get_setup,
    load_action,
    load_choice,
    load_choices,
    load_player_key,
    load_story_brief,
    load_story_plan,
    record_cost,
    save_action,
    save_choices,
    save_player_key,
    save_setup_options,
    setup_spent_usd,
    story_spent_usd,
)
from writory.safety.crypto import KeyCipher

pytestmark = pytest.mark.graph

FAKE_KEY = "sk-or-v1-" + "0badc0de" * 8
CHOICES = {"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "naming":
           {"names": "han_viet", "places": "hu_cau"}}


def _options(n=3, prefix="Bối cảnh"):
    return [{"title": f"{prefix} {i}", "intro": f"Giới thiệu {i}."} for i in range(n)]


@pytest.fixture
def setup_ids(pg):
    created: list[str] = []

    def make() -> str:
        sid = f"setup-{uuid.uuid4().hex[:12]}"
        created.append(sid)
        return sid

    yield make
    for sid in created:
        pg.execute("DELETE FROM setup_sessions WHERE id = %s", (sid,))


@pytest.fixture
def owners(pg):
    created: list[str] = []

    def make() -> str:
        owner = f"owner-{uuid.uuid4().hex[:8]}"
        created.append(owner)
        return owner

    yield make
    for owner in created:
        pg.execute("DELETE FROM player_keys WHERE owner_id = %s", (owner,))


# --- bản kế hoạch ẩn ---------------------------------------------------------------------------


def test_story_with_plan_roundtrip(pg, new_db_story_id):
    sid = new_db_story_id()
    create_story_with_plan(pg, sid, owner_id="dev", length_level="short",
                           brief="Kiếm hiệp, giọng trầm.", plan=PLAN)
    assert load_story_plan(pg, sid) == PLAN
    assert load_story_brief(pg, sid) == "Kiếm hiệp, giọng trầm."


def test_story_without_plan_loads_none(pg, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short")
    assert load_story_plan(pg, sid) is None
    assert load_story_brief(pg, sid) is None


def test_plan_is_deleted_with_story(pg, new_db_story_id):
    from writory.db import delete_story_record

    sid = new_db_story_id()
    create_story_with_plan(pg, sid, owner_id="dev", length_level="short", brief="b", plan=PLAN)
    delete_story_record(pg, sid)
    assert pg.execute("SELECT count(*) FROM story_plans WHERE story_id = %s",
                      (sid,)).fetchone()[0] == 0


# --- key người chơi (G7) -----------------------------------------------------------------------


def test_player_key_stored_only_as_ciphertext(pg, owners):
    owner = owners()
    cipher = KeyCipher(SecretStr(Fernet.generate_key().decode()))
    token = cipher.encrypt(SecretStr(FAKE_KEY))
    save_player_key(pg, owner, token)
    assert load_player_key(pg, owner) == token
    raw = pg.execute("SELECT * FROM player_keys WHERE owner_id = %s", (owner,)).fetchone()
    flat = " ".join(bytes(v).decode("latin-1") if isinstance(v, memoryview | bytes) else str(v)
                    for v in raw)
    assert FAKE_KEY not in flat and FAKE_KEY[-12:] not in flat
    assert cipher.decrypt(load_player_key(pg, owner)).get_secret_value() == FAKE_KEY


def test_player_key_replace_and_delete(pg, owners):
    owner, other = owners(), owners()
    save_player_key(pg, owner, b"token-1")
    save_player_key(pg, owner, b"token-2")
    save_player_key(pg, other, b"token-x")
    assert load_player_key(pg, owner) == b"token-2"
    assert delete_player_key(pg, owner) is True
    assert load_player_key(pg, owner) is None
    assert delete_player_key(pg, owner) is False
    assert load_player_key(pg, other) == b"token-x"


# --- phiên khởi tạo ----------------------------------------------------------------------------


def test_setup_session_steps_in_order(pg, setup_ids):
    sid = setup_ids()
    rec = create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    assert (rec.settings, rec.setting_index, rec.story_id) == (None, None, None)
    assert rec.choices == CHOICES
    with pytest.raises(SetupStepError):
        choose_setup_option(pg, sid, "settings", 0)  # chưa có lựa chọn để chọn
    with pytest.raises(SetupStepError):
        save_setup_options(pg, sid, "plots", _options(prefix="Hướng"))  # chưa chọn bối cảnh

    rec = save_setup_options(pg, sid, "settings", _options())
    assert rec.settings == _options()
    rec = choose_setup_option(pg, sid, "settings", 1)
    assert rec.setting_index == 1
    save_setup_options(pg, sid, "plots", _options(prefix="Hướng"))
    choose_setup_option(pg, sid, "plots", 2)
    save_setup_options(pg, sid, "characters", _options(prefix="Nhân vật"))
    pc = {"name": "Lục Vân", "personality": "Ít nói.", "backstory": "Con thợ rèn."}
    rec = choose_setup_option(pg, sid, "characters", 0, protagonist=pc)
    assert (rec.plot_index, rec.character_index, rec.protagonist) == (2, 0, pc)
    assert get_setup(pg, sid, owner_id="dev") == rec


def test_character_choice_needs_protagonist_and_other_steps_refuse_it(pg, setup_ids):
    sid = setup_ids()
    _ready_session(pg, sid, choose_character=False)
    with pytest.raises(ValueError):
        choose_setup_option(pg, sid, "characters", 0)
    with pytest.raises(ValueError):
        choose_setup_option(pg, sid, "plots", 0, protagonist={"name": "x"})


def test_saved_options_are_kept_not_overwritten(pg, setup_ids):
    """Hai yêu cầu tạo cùng lúc: bộ lưu trước được giữ, bộ sau bị bỏ (không đổi lựa chọn đã hiện)."""
    sid = setup_ids()
    create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    first = save_setup_options(pg, sid, "settings", _options(prefix="A"))
    second = save_setup_options(pg, sid, "settings", _options(prefix="B"))
    assert first.settings == second.settings == _options(prefix="A")


def test_choosing_again_clears_later_steps(pg, setup_ids):
    sid = setup_ids()
    create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    save_setup_options(pg, sid, "settings", _options())
    choose_setup_option(pg, sid, "settings", 0)
    save_setup_options(pg, sid, "plots", _options(prefix="Hướng"))
    choose_setup_option(pg, sid, "plots", 1)
    rec = choose_setup_option(pg, sid, "settings", 0)  # chọn lại đúng cái cũ: giữ nguyên
    assert (rec.plots, rec.plot_index) == (_options(prefix="Hướng"), 1)
    rec = choose_setup_option(pg, sid, "settings", 2)  # đổi bối cảnh: hướng cũ không còn hợp
    assert (rec.setting_index, rec.plots, rec.plot_index) == (2, None, None)


@pytest.mark.parametrize("index", [-1, 3, 99])
def test_index_outside_the_saved_options_is_refused(pg, setup_ids, index):
    sid = setup_ids()
    create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    save_setup_options(pg, sid, "settings", _options())
    with pytest.raises(SetupStepError):
        choose_setup_option(pg, sid, "settings", index)
    assert get_setup(pg, sid, owner_id="dev").setting_index is None


def test_setup_of_other_owner_is_not_found(pg, setup_ids):
    sid = setup_ids()
    create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    with pytest.raises(SetupNotFoundError):
        get_setup(pg, sid, owner_id="someone-else")
    with pytest.raises(SetupNotFoundError):
        get_setup(pg, f"setup-{uuid.uuid4().hex[:12]}", owner_id="dev")


def _ready_session(pg, sid, *, choose_character=True):
    rec = create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    for step in ("settings", "plots"):
        save_setup_options(pg, sid, step, _options())
        choose_setup_option(pg, sid, step, 0)
    rec = save_setup_options(pg, sid, "characters", _options())
    if choose_character:
        pc = {"name": "Lục Vân", "personality": "Ít nói.", "backstory": "Con thợ rèn."}
        rec = choose_setup_option(pg, sid, "characters", 0, protagonist=pc)
    return rec


def test_finish_links_story_and_freezes_session(pg, setup_ids, new_db_story_id):
    sid, story = setup_ids(), new_db_story_id()
    _ready_session(pg, sid)
    record_cost(pg, owner_id="dev", setup_id=sid,
                entry=CostEntry(role="setup", model="m", prompt_tokens=1, completion_tokens=2,
                                cost_usd=0.25))
    assert setup_spent_usd(pg, sid) == pytest.approx(0.25)
    create_story_with_plan(pg, story, owner_id="dev", length_level="short", brief="b", plan=PLAN)
    rec = finish_setup(pg, sid, story)
    assert rec.story_id == story
    # Chi phí khởi tạo tính vào trần của truyện vừa tạo (G8).
    assert story_spent_usd(pg, story) == pytest.approx(0.25)
    with pytest.raises(SetupStepError):
        finish_setup(pg, sid, story)
    with pytest.raises(SetupStepError):
        choose_setup_option(pg, sid, "settings", 1)
    with pytest.raises(SetupStepError):
        save_setup_options(pg, sid, "settings", _options())


def test_finish_requires_a_chosen_character(pg, setup_ids, new_db_story_id):
    sid, story = setup_ids(), new_db_story_id()
    _ready_session(pg, sid, choose_character=False)
    create_story_with_plan(pg, story, owner_id="dev", length_level="short", brief="b", plan=PLAN)
    with pytest.raises(SetupStepError):
        finish_setup(pg, sid, story)
    assert get_setup(pg, sid, owner_id="dev").story_id is None


# --- nhật ký chi phí ---------------------------------------------------------------------------


def test_story_spent_sums_known_costs_of_that_story_only(pg, new_db_story_id, setup_ids):
    a, b = new_db_story_id(), new_db_story_id()
    create_story(pg, a, length_level="short", owner_id="dev")
    create_story(pg, b, length_level="short", owner_id="dev")
    for story, cost in ((a, 0.1), (a, 0.05), (a, None), (b, 0.7)):
        record_cost(pg, owner_id="dev", story_id=story, chapter=1,
                    entry=CostEntry(role="writer", model="m", prompt_tokens=10,
                                    completion_tokens=20, cost_usd=cost))
    assert story_spent_usd(pg, a) == pytest.approx(0.15)
    assert story_spent_usd(pg, b) == pytest.approx(0.7)
    rows = pg.execute("SELECT role, chapter, prompt_tokens, completion_tokens FROM llm_costs "
                      "WHERE story_id = %s ORDER BY id", (a,)).fetchall()
    assert rows == [("writer", 1, 10, 20)] * 3
    sid = setup_ids()
    create_setup(pg, sid, owner_id="dev", choices=CHOICES)
    assert setup_spent_usd(pg, sid) == 0.0


def test_cost_row_needs_a_story_or_a_setup(pg):
    with pytest.raises(ValueError):
        record_cost(pg, owner_id="dev", entry=CostEntry("writer", "m", 0, 0, 0.1))


# --- lựa chọn và hành động ---------------------------------------------------------------------


def _choice(i):
    return {"id": f"choice-{i:012x}", "kind": "action", "tone": None, "text": f"Lựa chọn {i}",
            "listeners": [], "about": ["lan"], "lie": None, "feeling": None}


def test_choices_saved_once_per_chapter(pg, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short", owner_id="dev")
    first = [_choice(i) for i in range(3)]
    assert save_choices(pg, sid, 4, first) == first
    assert save_choices(pg, sid, 4, [_choice(i) for i in range(10, 13)]) == first  # giữ bộ đầu
    assert load_choices(pg, sid, 4) == first
    assert load_choices(pg, sid, 5) == []
    assert load_choice(pg, sid, 4, first[1]["id"]) == first[1]
    assert load_choice(pg, sid, 3, first[1]["id"]) is None  # sai chương
    assert load_choice(pg, sid, 4, "choice-ffffffffffff") is None


def test_action_for_next_chapter_upserts(pg, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short", owner_id="dev")
    choices = save_choices(pg, sid, 4, [_choice(i) for i in range(3)])
    assert load_action(pg, sid, 5) is None
    save_action(pg, sid, 5, source="choice", text="Hành động: Lựa chọn 0",
                choice_id=choices[0]["id"])
    assert load_action(pg, sid, 5).choice_id == choices[0]["id"]
    save_action(pg, sid, 5, source="custom", text="Tôi im lặng bỏ đi.")
    action = load_action(pg, sid, 5)
    assert (action.source, action.text, action.choice_id) == ("custom", "Tôi im lặng bỏ đi.", None)


# --- khoá chống chạy đôi (G8, D-46) ------------------------------------------------------------


def _other_conn():
    import os

    return psycopg.connect(os.environ.get(
        "POSTGRES_DSN", "postgresql://writory:change-me-local@localhost:5432/writory"),
        autocommit=True)


def test_job_lock_lets_one_connection_run_at_a_time(pg):
    from writory.db import StoryBusyError, job_lock

    key = f"story-{uuid.uuid4().hex[:12]}"
    other = _other_conn()
    try:
        with job_lock(pg, "story", key):
            with pytest.raises(StoryBusyError) as exc, job_lock(other, "story", key):
                pass
            assert exc.value.code.value == "STORY_BUSY"
            with job_lock(other, "story", f"{key}-khac"), job_lock(other, "setup", key):
                pass  # khoá theo từng truyện, từng loại việc
        with job_lock(other, "story", key):  # nhả khi xong
            pass
        with pytest.raises(RuntimeError), job_lock(pg, "story", key):
            raise RuntimeError("việc lỗi giữa chừng")
        with job_lock(other, "story", key):  # nhả cả khi lỗi
            pass
    finally:
        other.close()


def test_action_choice_must_exist(pg, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short", owner_id="dev")
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        save_action(pg, sid, 5, source="choice", text="x", choice_id="choice-000000000000")
