"""Bài E với lịch sử hỏi đáp (D-162): câu hỏi của đề khai các lượt trước (`history`, ghi sẵn, không
do model sinh); người kể nhận chúng khi `limits.narrator_history.turns` > 0. Đề câu nối tiếp
`questions-followup-1.yaml` chạy hai lần, tắt và bật, để so từng cặp. Không mạng, không model thật."""

from pathlib import Path

import pytest

pytest.importorskip("anthropic")

from writory.config import REPO_ROOT, ConfigError, NarratorHistoryLimits, load_config
from writory.pipeline import bench_e as be
from writory.pipeline.narrator import NOT_KNOWN

FILE = "questions-followup-1.yaml"
HISTORY_OPEN = '<player_data source="narrator_history">'
REPO = load_config()


def with_history(turns: int):
    return REPO.model_copy(update={"limits": REPO.limits.model_copy(update={
        "narrator_history": NarratorHistoryLimits(turns=turns, max_chars=2000)})})


OFF, ON = with_history(0), with_history(5)
DATA = be.load_data(questions_file=FILE)
QUESTIONS = {q.id: q for q in DATA.questions.questions}


def opts(tmp_path: Path, **kw) -> be.RunOptions:
    return be.RunOptions(**({"out": tmp_path / "out", "dry_run": True, "samples": 1,
                             "concurrency": 4} | kw))


# --- đề -------------------------------------------------------------------------------------------


def test_every_question_declares_earlier_turns():
    assert all(q.history for q in QUESTIONS.values())


def test_the_set_has_follow_ups_to_answer_and_follow_ups_to_refuse():
    types = {q.type for q in QUESTIONS.values()}
    assert {"a", "b", "d"} <= types


def test_scripted_answers_are_things_the_narrator_could_have_shown():
    """Câu đáp ghi sẵn là chữ "đã hiện": không được chứa bí mật chưa mở ở chương đó."""
    for q in QUESTIONS.values():
        state = DATA.state_for(q)
        for turn in q.history:
            assert DATA.scorer.leaks(turn.answer, state) == [], q.id


def test_a_scripted_answer_that_leaks_makes_the_file_invalid(tmp_path):
    src = REPO_ROOT / "evals" / "scenarios" / "narrator"
    for name in ("plan.yaml", "run.yaml"):
        (tmp_path / name).write_bytes((src / name).read_bytes())
    (tmp_path / "q.yaml").write_text(
        "version: 1\ncounts: {a: 0, b: 1, c: 0, d: 0, e: 0, f: 0}\nquestions:\n"
        "  - {id: x, chapter: 1, type: b, text: \"Thế cô ấy là người của ai?\",\n"
        "     history: [{question: \"Lan là ai?\", answer: \"Lan là gián điệp của Hội Hắc Kỳ.\"}]}\n",
        encoding="utf-8")
    with pytest.raises(ConfigError, match="history"):
        be.load_data(tmp_path, questions_file="q.yaml", sample_dir=None)


def test_questions_without_history_still_load_as_before():
    v2 = be.load_data(questions_file="questions-v2.yaml")
    assert all(q.history == [] for q in v2.questions.questions)


# --- chạy -----------------------------------------------------------------------------------------


async def _calls(tmp_path, config):
    fake = be.FakeNarrator(DATA, be.oracle_reply)
    code = await be.run_bench(DATA, opts(tmp_path), config=config, narrator=fake,
                              log=lambda _line: None)
    assert code == be.EXIT_OK
    return fake.calls


def _user(messages) -> str:
    return next(m.content for m in messages if m.role == "user")


async def test_switched_on_every_call_carries_the_declared_turns(tmp_path):
    calls = await _calls(tmp_path, ON)
    assert len(calls) == len(QUESTIONS)
    for messages in calls:
        chapter, text = be.parse_narrator_messages(messages)
        q = DATA.lookup(chapter, text)
        user = _user(messages)
        assert user.count(HISTORY_OPEN) == 1, q.id
        assert user.index(HISTORY_OPEN) < user.index('source="narrator_question"')


async def test_switched_off_no_call_carries_history(tmp_path):
    calls = await _calls(tmp_path, OFF)
    assert len(calls) == len(QUESTIONS)
    assert all(HISTORY_OPEN not in _user(m) for m in calls)


async def test_dry_run_with_the_oracle_never_leaks_and_refuses_what_must_be_refused(tmp_path):
    o = opts(tmp_path)
    code = await be.run_bench(DATA, o, config=ON, log=lambda _line: None)
    assert code == be.EXIT_OK
    rows = be.Store(o.out).rows(be.RESULTS)
    assert all(not r["final_leaks"] for r in rows)
    for r in rows:
        if QUESTIONS[r["id"]].type != "a":
            assert r["final"] == NOT_KNOWN, r["id"]
        assert r["history"] == len(QUESTIONS[r["id"]].history)


# --- dấu vân tay -----------------------------------------------------------------------------------


def test_fingerprint_separates_on_from_off_and_off_is_unchanged(tmp_path):
    config_dir = REPO_ROOT / "config"
    off = be.fingerprint(DATA, config_dir, opts(tmp_path), OFF)
    on = be.fingerprint(DATA, config_dir, opts(tmp_path), ON)
    assert "narrator_history" not in off  # thư mục kết quả cũ vẫn chạy tiếp được
    assert on["narrator_history"] == {"turns": 5, "max_chars": 2000}
    assert on["narrator_prompt"] == "narrator-5" and off["narrator_prompt"] == "narrator-4"
    assert on["narrator_prompt_sha256"] != off["narrator_prompt_sha256"]


def test_unset_history_limit_is_reported_before_running():
    unset = REPO.model_copy(update={"limits": REPO.limits.model_copy(update={
        "narrator_history": NarratorHistoryLimits()})})
    assert any("narrator_history" in p for p in be.run_problems(unset, DATA))
