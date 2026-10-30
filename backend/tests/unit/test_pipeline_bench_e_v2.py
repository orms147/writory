"""Bài E bản 2 (D-60): đề v2 không sửa đè v1, câu khó hơn, nhóm sổ tay lớn đo truy hồi.
Không mạng, không model thật; model giả chỉ thấy messages."""

import json
from pathlib import Path

import pytest

pytest.importorskip("anthropic")

from writory.config import REPO_ROOT, ConfigError, load_config
from writory.graph import public_entries
from writory.pipeline import bench_e as be
from writory.pipeline.narrator import NOT_KNOWN, render_notebook
from writory.pipeline.notebook import select_notebook

# Các test ở file này chạy đề `narrator-3` (chỉ sổ tay, có giám khảo): tắt đoạn trên trang. Đề
# `narrator-4` (D-143): tests/unit/test_pipeline_bench_e_pages.py.
_REPO = load_config()
CONFIG = _REPO.model_copy(update={"limits": _REPO.limits.model_copy(update={
    "narrator_pages": _REPO.limits.narrator_pages.model_copy(update={"top_k": 0})})})
LIMITS = CONFIG.limits.narrator_notebook
V1 = be.load_data()
V2 = be.load_data(questions_file="questions-v2.yaml")
V1_RESULT = REPO_ROOT / "evals" / "results" / "2026-10-20-narrator-luna-1"

# Câu cố tình dùng chữ khác sổ tay ("thanh kiếm" so với "Thanh Sương"): truy hồi theo chữ có thể
# trượt. Đây là điều bài đo muốn thấy (D-59, đề xuất embedding); đổi danh sách này phải có lý do.
KNOWN_RETRIEVAL_MISSES = {"p5-a-kiem-nam-o-dau"}


def opts(tmp_path: Path, **kw) -> be.RunOptions:
    base = {"out": tmp_path / "out", "dry_run": True, "samples": 1, "concurrency": 4}
    return be.RunOptions(**(base | kw))


async def run(tmp_path: Path, data=V2, **kw):
    logs: list[str] = []
    o = opts(tmp_path, **kw)
    code = await be.run_bench(data, o, config=CONFIG, log=logs.append)
    store = be.Store(o.out)
    return code, store, be.compute_report(data, store)


# --- v1 không bị sửa đè ------------------------------------------------------------------------


def test_v1_questions_are_byte_identical_to_what_the_first_run_used():
    meta = json.loads((V1_RESULT / "meta.json").read_text(encoding="utf-8"))
    assert meta["fingerprint"]["data_sha256"]["questions.yaml"] == V1.hashes["questions.yaml"]
    assert V1.questions.version == 1


def test_v2_is_a_new_file_with_a_higher_version():
    assert V2.questions.version == 2
    assert V2.files["questions"] == "questions-v2.yaml"
    assert V2.hashes["questions-v2.yaml"] != V1.hashes["questions.yaml"]
    assert V2.hashes["plan.yaml"] == V1.hashes["plan.yaml"]  # cùng kế hoạch và chuỗi cấm
    assert V2.hashes["run.yaml"] == V1.hashes["run.yaml"]


def test_v2_keeps_every_v1_question_unchanged_except_the_mislabelled_one():
    v1 = {q.id: (q, V1.texts[q.id]) for q in V1.questions.questions}
    v2 = {q.id: (q, V2.texts[q.id]) for q in V2.questions.questions}
    missing = set(v1) - set(v2)
    assert missing == {"c2-d-lop-su-that"}
    for qid in set(v1) - missing:
        assert v1[qid][0] == v2[qid][0] and v1[qid][1] == v2[qid][1], qid


def test_mislabelled_question_is_now_a_known_answer_with_the_same_words():
    old, new = V1.question("c2-d-lop-su-that"), V2.question("c2-a-chen-lenh-hoi-da-biet")
    assert old.type == "d" and new.type == "a"
    assert V1.texts[old.id] == V2.texts[new.id]
    assert V2.expected_refs[new.id] == [V2.states[2].by_truth_id["gu"]]
    assert "bỏ qua sổ tay" in V2.texts[new.id].lower()


def test_v2_has_more_hard_c_and_e_questions_than_v1():
    for t in ("c", "e"):
        assert V2.questions.counts[t] > V1.questions.counts[t], t
    new = [q for q in V2.questions.questions if q.id not in {x.id for x in V1.questions.questions}]
    assert {"c", "e"} <= {q.type for q in new}


def test_hard_questions_cover_guessing_who_is_suspect_and_stacked_steps():
    text = " ".join(V2.texts[q.id].lower() for q in V2.questions.questions if q.type in "ce")
    assert "đáng ngờ nhất" in text
    assert text.count("giả sử") >= 2  # dồn nhiều bước
    assert "ghép" in text  # ghép manh mối hợp lệ


# --- nhóm sổ tay lớn ---------------------------------------------------------------------------


def pad_questions():
    return [q for q in V2.questions.questions if q.pad]


def test_pad_group_runs_on_notebooks_larger_than_the_threshold():
    qs = pad_questions()
    assert {q.type for q in qs} == {"a", "b", "c", "d", "e"}
    for q in qs:
        view = V2.state_for(q).view
        assert len(view.entries) > LIMITS.require("max_entries"), q.id
        assert len(render_notebook(view)) > LIMITS.require("max_chars"), q.id


def test_normal_questions_keep_the_small_notebook():
    for q in V2.questions.questions:
        if not q.pad:
            assert V2.state_for(q) is V2.states[q.chapter]


def test_pad_group_text_never_repeats_a_normal_question_of_the_same_chapter():
    seen = {(q.chapter, V2.texts[q.id]) for q in V2.questions.questions if not q.pad}
    for q in pad_questions():
        assert (q.chapter, V2.texts[q.id]) not in seen, q.id


def test_padding_alone_trips_neither_the_runtime_detector_nor_the_stricter_scorer():
    for chapter, state in V2.pad_states.items():
        assert V2.scorer.leaks(render_notebook(state.view), state) == [], chapter


def test_retrieval_finds_the_grounds_of_almost_every_pad_question():
    misses = set()
    for q in pad_questions():
        if q.type != "a":
            continue
        sel = select_notebook(V2.texts[q.id], V2.state_for(q).view, LIMITS)
        assert sel.partial, q.id
        if not set(V2.expected_refs[q.id]) <= sel.refs:
            misses.add(q.id)
    assert misses == KNOWN_RETRIEVAL_MISSES


def test_retrieved_context_is_a_fraction_of_the_full_notebook():
    for q in pad_questions():
        view = V2.state_for(q).view
        sel = select_notebook(V2.texts[q.id], view, LIMITS)
        assert len(render_notebook(view, sel)) < len(render_notebook(view)) / 5, q.id


def test_public_refs_in_the_context_are_those_of_the_full_padded_notebook():
    q = V2.question("p5-a-lo-ren")
    view = V2.state_for(q).view
    full = dict(public_entries(view))
    sel = select_notebook(V2.texts[q.id], view, LIMITS)
    assert all(full[r] == e for r, e in sel.entries)
    assert V2.expected_refs[q.id][0] in {r for r, _ in sel.entries}


def test_pad_question_without_notebook_pad_is_rejected(tmp_path):
    import shutil

    import yaml

    data_dir = tmp_path / "data"
    shutil.copytree(be.DATA_DIR, data_dir)
    path = data_dir / "questions-v2.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    del doc["notebook_pad"]
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with pytest.raises(ConfigError, match="notebook_pad"):
        be.load_data(data_dir, questions_file="questions-v2.yaml")


# --- chạy khô trên v2 --------------------------------------------------------------------------


async def test_oracle_on_v2_has_no_leak_and_only_the_known_retrieval_misses_fail(tmp_path):
    code, store, report = await run(tmp_path)
    assert code == be.EXIT_OK and report["final_leaks"] == 0
    failed = {r["id"] for r in store.rows(be.RESULTS) if not r["ok"]}
    assert failed == KNOWN_RETRIEVAL_MISSES
    [row] = [r for r in store.rows(be.RESULTS) if r["id"] in KNOWN_RETRIEVAL_MISSES]
    assert row["verdict"] == "declined" and row["expected_shown"] is False


async def test_pad_rows_record_how_much_notebook_was_sent(tmp_path):
    _, store, _ = await run(tmp_path, question_ids=["p5-a-lo-ren", "c3-a-gu-chet-o-dau"])
    rows = {r["id"]: r for r in store.rows(be.RESULTS)}
    big, small = rows["p5-a-lo-ren"], rows["c3-a-gu-chet-o-dau"]
    assert big["pad"] is True and big["shown"] < LIMITS.require("max_entries") + 1
    assert big["total"] > LIMITS.require("max_entries") and big["expected_shown"] is True
    assert small["pad"] is False and small["shown"] == small["total"]


async def test_report_and_summary_have_a_retrieval_section(tmp_path):
    _, store, report = await run(tmp_path)
    pad = report["pad"]
    n_a = sum(q.type == "a" for q in pad_questions())
    assert pad["n"] == len(pad_questions()) and pad["a_n"] == n_a
    assert pad["a_expected_shown"] == n_a - len(KNOWN_RETRIEVAL_MISSES)
    assert pad["missed"] == sorted(KNOWN_RETRIEVAL_MISSES)
    assert pad["mean_shown"] < pad["mean_total"] / 5 and pad["final_leaks"] == 0
    text = be.build_summary(V2, store, report)
    assert "## Sổ tay lớn" in text and "p5-a-kiem-nam-o-dau" in text
    assert "questions-v2.yaml" in text


async def test_summary_of_a_v1_style_run_has_no_retrieval_section(tmp_path):
    _, store, report = await run(tmp_path, data=V1)
    assert report["pad"]["n"] == 0
    assert "## Sổ tay lớn" not in be.build_summary(V1, store, report)


async def test_leaker_on_v2_never_reaches_the_player_even_with_a_big_notebook(tmp_path):
    code, store, report = await run(tmp_path, fake="leaker")
    assert code == be.EXIT_OK and report["final_leaks"] == 0 and report["raw_leaks"] > 0
    assert all(r["final"] == NOT_KNOWN for r in store.rows(be.RESULTS))
    big = [r for r in store.rows(be.RESULTS) if r["pad"]]
    assert big and all(r["blocked"] in ("leak", "unknown_ref") for r in big)


async def test_resume_with_other_questions_file_is_refused(tmp_path):
    await run(tmp_path, data=V2, question_ids=["p5-a-lo-ren"])
    with pytest.raises(ConfigError, match="data_files|data_sha256"):
        await run(tmp_path, data=V1, question_ids=["c1-a-ten-kiem"])


def test_cli_plan_for_v2_counts_the_retrieved_context(capsys):
    assert be.main(["plan", "--questions-file", "questions-v2.yaml"]) == be.EXIT_OK
    out = capsys.readouterr().out
    assert str(len(V2.questions.questions)) in out


async def test_judge_sees_the_same_part_of_the_notebook_the_narrator_got(tmp_path, monkeypatch):
    seen: list[str] = []
    original = be.judge_request

    def spy(settings, notebook, chapter, question, answer):
        seen.append(notebook)
        return original(settings, notebook, chapter, question, answer)

    monkeypatch.setattr(be, "judge_request", spy)
    q = V2.question("p5-a-lo-ren")
    code, _, _ = await run(tmp_path, judge=True, question_ids=[q.id])
    assert code == be.EXIT_OK and len(seen) == 1
    view = V2.state_for(q).view
    assert seen[0] == render_notebook(view, select_notebook(V2.texts[q.id], view, LIMITS))
    assert len(seen[0]) < len(render_notebook(view)) / 5
