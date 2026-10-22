"""Bài đo A trên truyện do pipeline viết (D-83): nạp văn chương và đồ thị từ thư mục kết quả của
`pipeline.bench_run`, đề khoá theo hash, đáp án gốc lấy từ trang và cờ `graph_agrees` kiểm bằng code
với đồ thị bộ trích đã dựng. Không mạng, không Neo4j."""

import asyncio
import shutil
from collections import Counter
from pathlib import Path

import pytest
import yaml

from writory.config import REPO_ROOT, ConfigError, load_config
from writory.pipeline import bench_a
from writory.pipeline.bench_a import (
    RESULTS,
    ContextBuilder,
    RunOptions,
    compute_report,
    main,
    plan_text,
    run_bench,
)
from writory.pipeline.bench_a_data import (
    DATA_DIR,
    Question,
    QuestionsFile,
    check_question,
    context_supports,
    derive,
    distance_bin,
    load_data,
    oracle_answer,
    run_chapter_text,
    score_answer,
)
from writory.pipeline.bench_a_systems import build_graph_context
from writory.quality.bench_d import Store

QUESTIONS_FILE = "questions-ky-ao-vua-1.yaml"
RUN_DIR = REPO_ROOT / "evals" / "results" / "2026-10-21-run-ky-ao-vua-1"
RUN = load_data(questions_file=QUESTIONS_FILE)
QS = RUN.questions.questions
NAMES = RUN.state_at(10).named_nodes()
CONFIG = load_config()


def q(qid: str) -> Question:
    return RUN.question(qid)


def copy_scenario(tmp_path: Path, *, run_dir: Path | None = None) -> tuple[Path, Path, dict]:
    """Bản sao đề (và tuỳ chọn trỏ `run_dir` sang chỗ khác) để sửa trong test."""
    data_dir = tmp_path / "memory"
    shutil.copytree(DATA_DIR, data_dir)
    path = data_dir / QUESTIONS_FILE
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if run_dir is not None:
        raw["run_dir"] = str(run_dir)
    return data_dir, path, raw


def write(path: Path, raw: dict) -> None:
    path.write_text(yaml.safe_dump(raw, allow_unicode=True, sort_keys=False), encoding="utf-8")


# --- nạp truyện từ thư mục kết quả ----------------------------------------------------------------


def test_run_story_loads_every_chapter_and_the_extracted_graph():
    assert RUN.questions.story == "run"
    assert RUN.chapters == tuple(range(1, 11))
    assert RUN.source == "evals/results/2026-10-21-run-ky-ao-vua-1"
    assert RUN.state_at(10).protagonist_id() == "protagonist"
    assert {"tran_mac", "tao_van_chi", "thep_dinh_phong"} <= set(NAMES)
    # gói chương 0 có mặt: nút từ khởi tạo đọc được ở chương 1
    assert RUN.state_at(1).nodes(["fact_tran_mac_ban_tin"])


def test_chapter_text_is_the_prose_without_harness_notes_or_choices():
    for n, text in RUN.story.items():
        assert "Lựa chọn cuối chương" not in text and "← đã chọn" not in text, n
        assert "_Lựa chọn dẫn tới chương này" not in text and not text.startswith("# Chương"), n
    assert RUN.story[1].startswith("Giữa những lều quán bỏ trống")
    assert RUN.story[10].rstrip().endswith("đã sát đến cửa.")
    assert "* * *" in RUN.story[4]  # chỗ ngắt cảnh giữ nguyên


def test_run_chapter_text_strips_status_action_and_finished_lines():
    raw = ("# Chương 12\n\n_Trạng thái: dừng. Chỉ gồm các cảnh đã hiện._\n\n"
           "_Lựa chọn dẫn tới chương này: [Hành động] Đi._\n\nCảnh một.\n\n* * *\n\nCảnh hai.\n\n"
           "_Hết truyện._\n\n## Lựa chọn cuối chương\n\n1. Đi tiếp.  ← đã chọn\n")
    assert run_chapter_text(raw) == "Cảnh một.\n\n* * *\n\nCảnh hai.\n"


def test_hashes_cover_every_file_read():
    files = {"truth_dump.json", *(f"chapters/ch{n:02d}.md" for n in range(1, 11))}
    assert set(RUN.questions.run_sha256) == files
    assert set(RUN.hashes) == {QUESTIONS_FILE, "run.yaml", *(f"run/{f}" for f in files)}
    assert all(RUN.hashes[f"run/{f}"] == RUN.questions.run_sha256[f] for f in files)


def test_a_changed_chapter_is_refused_by_its_pinned_hash(tmp_path):
    run_dir = tmp_path / "run"
    shutil.copytree(RUN_DIR, run_dir)
    with (run_dir / "chapters" / "ch03.md").open("a", encoding="utf-8") as f:
        f.write("\nMột câu chèn thêm sau khi đề đã khai.\n")
    data_dir, path, raw = copy_scenario(tmp_path, run_dir=run_dir)
    write(path, raw)
    with pytest.raises(ConfigError, match="chapters/ch03.md"):
        load_data(data_dir, questions_file=QUESTIONS_FILE)


def test_pins_must_list_exactly_the_files_read(tmp_path):
    data_dir, path, raw = copy_scenario(tmp_path, run_dir=RUN_DIR)
    del raw["run_sha256"]["chapters/ch10.md"]
    write(path, raw)
    with pytest.raises(ConfigError, match="chapters/ch10.md"):
        load_data(data_dir, questions_file=QUESTIONS_FILE)


def test_missing_run_folder_is_a_config_error(tmp_path):
    data_dir, path, raw = copy_scenario(tmp_path, run_dir=tmp_path / "không-có")
    write(path, raw)
    with pytest.raises(ConfigError, match="truth_dump.json"):
        load_data(data_dir, questions_file=QUESTIONS_FILE)


def test_story_kind_and_run_fields_go_together():
    base = RUN.questions.model_dump()
    with pytest.raises(ValueError, match="run_dir"):
        QuestionsFile.model_validate({**base, "run_dir": None})
    with pytest.raises(ValueError, match="run_sha256"):
        QuestionsFile.model_validate({**base, "run_sha256": {}})
    sample = load_data().questions.model_dump()
    with pytest.raises(ValueError, match="run_dir"):
        QuestionsFile.model_validate({**sample, "run_dir": "evals/results/x"})


def test_sample_story_questions_still_need_a_derive_that_matches_the_hand_built_graph():
    sample = load_data().questions.model_dump()
    first = {**sample["questions"][0], "graph_agrees": False}
    with pytest.raises(ValueError, match="graph_agrees"):
        QuestionsFile.model_validate({**sample, "questions": [first, *sample["questions"][1:]]})


# --- đề -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("question", QS, ids=[x.id for x in QS])
def test_every_question_checks_out_against_the_page_and_the_graph(question):
    assert check_question(question, RUN) == []


def test_question_set_is_marked_approved_by_the_owner():
    assert RUN.questions.status == "CHỦ DỰ ÁN DUYỆT 22/10/2026"
    header = (DATA_DIR / QUESTIONS_FILE).read_text(encoding="utf-8").splitlines()[:8]
    assert any("CHỦ DỰ ÁN DUYỆT 22/10/2026" in line for line in header)


def test_question_set_leans_on_old_chapters():
    assert 30 <= len(QS) <= 45
    by_group = Counter(x.group for x in QS)
    assert set(by_group) == {"item", "alive", "knows", "relation"}  # trang không có lời nói dối
    assert all(n >= 5 for n in by_group.values())
    bins = Counter(distance_bin(x.distance) for x in QS)
    assert set(bins) == {"0", "1-2", "3+"} and bins["3+"] * 2 > len(QS)
    early_late = [x.id for x in QS if x.fact_chapter <= 3 and x.ask_chapter >= 9]
    assert len(early_late) >= 6, early_late
    assert {x.answer.type for x in QS} == {"entities", "bool", "choice", "text"}
    assert any(x.inference for x in QS) and any(x.graph_agrees for x in QS)


def test_the_two_secrets_are_asked_before_and_after_their_reveal():
    """Trần Mặc bán tin lộ ở chương 6, giao ước gia tộc Phó ở chương 8 (kế hoạch, truth_dump.json)."""
    sold = {x.ask_chapter: x.answer.gold for x in QS
            if (x.derive or {}).get("to") == "fact_tran_mac_ban_tin" and x.answer.type == "bool"}
    pact = {x.ask_chapter: x.answer.gold for x in QS
            if (x.derive or {}).get("to") == "fact_gia_toc_giu_manh" and x.answer.type == "bool"}
    assert sold == {5: False, 6: True} and pact == {7: False, 9: True}


# --- graph_agrees: đáp án từ trang, đồ thị bộ trích kiểm bằng code ---------------------------------------


def test_claiming_the_graph_agrees_when_it_does_not_is_caught():
    bad = q("knows-02").model_copy(update={"graph_agrees": True})
    assert any("khác đồ thị" in p for p in check_question(bad, RUN))


def test_claiming_the_graph_disagrees_when_it_agrees_is_caught():
    bad = q("item-01").model_copy(update={"graph_agrees": False})
    assert any("graph_agrees: false nhưng đồ thị" in p for p in check_question(bad, RUN))


def test_a_typo_in_a_derive_node_id_is_caught_even_when_the_graph_disagrees():
    spec = {**q("knows-02").derive, "to": "fact_tran_mac_ban_tn"}
    bad = q("knows-02").model_copy(update={"derive": spec})
    assert any("không có nút" in p for p in check_question(bad, RUN))


def test_question_without_derive_must_say_the_graph_disagrees():
    raw = q("item-03").model_dump()
    with pytest.raises(ValueError, match="derive"):
        Question.model_validate({**raw, "graph_agrees": True})


def test_edge_since_gives_the_chapter_the_graph_recorded():
    spec = {"op": "edge_since", "type": "KNOWS", "from": "protagonist"}
    state = RUN.state_at(10)
    assert derive({**spec, "to": "fact_tran_mac_ban_tin"}, state, 10) == "chương 9"
    assert derive({**spec, "to": "fact_gia_toc_giu_manh"}, state, 10) == "chương 10"


def test_extracted_graph_records_the_token_loan_only_as_close_and_reopen():
    """Nền của item-03/04: ở chương 4 không có cạnh HOLDS nào của Trần Mặc."""
    holds = RUN.state_at(10).edges_at("HOLDS", 10, target_id="thep_dinh_phong", ever=True)
    assert {(e.source, e.valid_from_chapter, e.valid_to_chapter) for e in holds} == {
        ("protagonist", 0, 4), ("protagonist", 4, None)}


# --- oracle và chấm ---------------------------------------------------------------------------------


@pytest.mark.parametrize("question", QS, ids=[x.id for x in QS])
def test_oracle_answer_scores_correct(question):
    assert score_answer(question, oracle_answer(question, NAMES), NAMES)["correct"] is True


def test_protagonist_answers_are_accepted_by_name_or_as_the_narrator():
    for answer in ("Phó Cảnh Hành", "Nhân vật chính", "Tôi", "Người kể chuyện"):
        assert score_answer(q("alive-01"), answer, NAMES)["correct"] is True, answer
    assert score_answer(q("alive-01"), "Tào Vân Chi", NAMES)["correct"] is False


def test_graph_oracle_falls_back_to_the_page_when_the_extracted_graph_is_wrong():
    """knows-02: đồ thị chưa có cạnh KNOWS ở chương 6, nhưng chương 6 (chương N) có lời thú nhận."""
    question = q("knows-02")
    state = RUN.state_at(6)
    with_page = build_graph_context(state, question.question, 6, story=RUN.story, recent=True)
    without = build_graph_context(state, question.question, 6, story=RUN.story, recent=False)
    assert context_supports(question, with_page, RUN)
    assert not context_supports(question, without, RUN)


def test_graph_oracle_never_trusts_keys_of_a_graph_that_disagrees():
    question = q("knows-03")  # đồ thị nói "chương 9": có khoá, nhưng khoá dẫn tới đáp án sai
    ctx = build_graph_context(RUN.state_at(10), question.question, 10, story=RUN.story,
                              recent=False)
    assert "edge:KNOWS:protagonist>fact_tran_mac_ban_tin@9" in ctx.facts
    assert not context_supports(question, ctx, RUN)


@pytest.mark.parametrize("system", ["graph", "graph_quotes"])
def test_graph_context_has_the_keys_for_every_question_the_graph_agrees_on(system):
    builder = ContextBuilder(RUN, RUN.state_at, {})
    missing = [x.id for x in QS if x.graph_agrees
               and not context_supports(x, builder.build(system, x), RUN)]
    assert missing == []


def run_dry(tmp_path: Path, **kw) -> Store:
    opts = RunOptions(out=tmp_path / "out", dry_run=True, samples=1, **kw)
    assert asyncio.run(run_bench(RUN, opts, config=CONFIG, log=lambda _: None)) == 0
    return Store(opts.out)


def test_dry_run_oracle_is_perfect_on_full_and_matches_support_elsewhere(tmp_path):
    store = run_dry(tmp_path, systems=["graph", "graph_quotes", "none", "rag", "full"])
    rows = store.rows(RESULTS)
    assert len(rows) == len(QS) * 5
    builder = ContextBuilder(RUN, RUN.state_at, {})
    for r in rows:
        question = q(r["id"])
        expected = context_supports(question, builder.build(r["system"], question), RUN)
        assert r["correct"] is expected, (r["id"], r["system"])
    assert all(r["correct"] for r in rows if r["system"] == "full")
    graph = [r for r in rows if r["system"] == "graph"]
    assert not all(r["correct"] for r in graph)  # bộ trích bỏ sót: trần của hệ đồ thị dưới 100%


def test_meta_and_summary_name_the_story_and_split_by_graph_agreement(tmp_path):
    store = run_dry(tmp_path, systems=["graph", "full"])
    meta = store.read_meta()
    assert meta["story"] == RUN.source and meta["status"] == RUN.questions.status
    assert set(meta["fingerprint"]["data_sha256"]) == set(RUN.hashes)
    text = (store.root / "summary.md").read_text(encoding="utf-8")
    assert RUN.source in text and RUN.questions.status in text
    assert "Đồ thị bộ trích có đáp án hay không" in text
    report = compute_report(RUN, store, ["graph", "full"], list(QS), 1)
    split = report["systems"]["full"]["by_graph"]
    assert split["agrees"]["n"] == sum(x.graph_agrees for x in QS)
    assert split["disagrees"]["n"] == sum(not x.graph_agrees for x in QS)


def test_sample_story_summary_has_no_graph_agreement_split(tmp_path):
    opts = RunOptions(out=tmp_path / "s", dry_run=True, samples=1, systems=["graph"],
                      question_ids=["item-01"])
    assert asyncio.run(run_bench(load_data(), opts, config=CONFIG, log=lambda _: None)) == 0
    text = (opts.out / "summary.md").read_text(encoding="utf-8")
    assert "Đồ thị bộ trích có đáp án hay không" not in text
    assert Store(opts.out).read_meta()["story"] == "sample-story"


def test_plan_prices_the_long_story_without_calling_a_model():
    text = plan_text(RUN, CONFIG, samples=3)
    assert f"Bài A: {len(QS)} câu × 3 lần" in text and "Tổng ước tính" in text
    for label in bench_a.SYSTEM_LABELS.values():
        assert label in text


def test_cli_dry_run_and_plan_pick_the_story_from_the_question_file(tmp_path, capsys):
    out = tmp_path / "cli"
    assert main(["run", "--dry-run", "--out", str(out), "--samples", "1", "--systems", "full",
                 "--questions-file", QUESTIONS_FILE, "--groups", "item"]) == 0
    rows = Store(out).rows(RESULTS)
    assert rows and all(r["correct"] for r in rows)
    capsys.readouterr()
    assert main(["plan", "--samples", "1", "--questions-file", QUESTIONS_FILE]) == 0
    assert "Tổng ước tính" in capsys.readouterr().out


def test_the_new_facts_variant_loads_and_every_flag_matches_its_graph():
    """D-93: đề dẫn xuất cho đồ thị có Fact mới: `load_data` kiểm cờ `graph_agrees` và `derive` của từng
    câu với đúng đồ thị của lần phát lại (hash các file khoá đề theo đúng truyện)."""
    data = load_data(questions_file="questions-ky-ao-vua-1-facts.yaml")
    flags = {q.id: q.graph_agrees for q in data.questions.questions}
    assert flags["item-07"] and flags["knows-02"] and not flags["item-11"]
    assert data.source == "evals/results/2026-10-22-new-facts-replay-1"
    # Cùng câu hỏi, cùng đáp án gốc với đề truyện vừa: chỉ cờ và derive của 12 câu đổi.
    base = {q.id: q.answer for q in RUN.questions.questions}
    assert {q.id: q.answer for q in data.questions.questions} == base
    changed = {q.id for q in data.questions.questions if q.graph_agrees != RUN.question(q.id).graph_agrees}
    assert len(changed) == 12
