"""Bài đo A: khung chạy với model giả (D-72, D-81). Oracle = 100% ở hai hệ đồ thị, null = 0%, mỗi hệ
dựng đúng ngữ cảnh, chi phí ghi theo hệ, chạy tiếp được, trần ngân sách chặn trước lời gọi. Không
mạng."""

import dataclasses
import json
from collections import defaultdict
from pathlib import Path

import pytest

from writory.config import ConfigError, load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import ChatResult, LLMClient, Usage
from writory.pipeline import bench_a
from writory.pipeline.bench_a import (
    ERRORS,
    RESULTS,
    SUMMARIES,
    AnswerOutput,
    FakeAnswerer,
    RunOptions,
    answer_messages,
    check_options,
    compute_report,
    main,
    plan_text,
    resolve_systems,
    run_bench,
    select_questions,
    wilson,
)
from writory.pipeline.bench_a_data import load_data
from writory.pipeline.bench_a_systems import SYSTEMS
from writory.pipeline.summary import SummaryOutput
from writory.quality.bench_d import Store

DATA = load_data()
CONFIG = load_config()
QUESTIONS = list(DATA.questions.questions)


def run(tmp_path: Path, **kw) -> tuple[int, Store, list[str]]:
    logs: list[str] = []
    opts = RunOptions(out=tmp_path / "out", dry_run=kw.pop("dry_run", True),
                      samples=kw.pop("samples", 1), **kw)
    code = _run(opts, logs)
    return code, Store(opts.out), logs


def _run(opts: RunOptions, logs: list[str], **extra) -> int:
    import asyncio

    return asyncio.run(run_bench(DATA, opts, config=CONFIG, log=logs.append, **extra))


def accuracy(store: Store) -> dict[str, float]:
    rows = store.rows(RESULTS)
    by = defaultdict(list)
    for r in rows:
        by[r["system"]].append(r["correct"])
    return {s: sum(v) / len(v) for s, v in by.items()}


# --- khung kiểm: oracle, null, wrong ------------------------------------------------------------


def test_oracle_is_perfect_on_the_graph_systems_and_on_full_story(tmp_path):
    code, store, _ = run(tmp_path, fake="oracle")
    acc = accuracy(store)
    assert code == 0
    assert acc["graph"] == 1.0 and acc["graph_quotes"] == 1.0 and acc["full"] == 1.0
    # các hệ còn lại là trần của chúng nếu model đọc hoàn hảo: none không biết chương cũ
    assert acc["none"] < 0.7 and acc["rolling"] < 0.7 and 0.5 < acc["rag"] < 1.0


def test_oracle_none_is_right_exactly_when_the_page_it_sees_has_the_evidence(tmp_path):
    _, store, _ = run(tmp_path, fake="oracle", systems=["none"])
    from writory.pipeline.bench_a_data import context_supports

    for row in store.rows(RESULTS):
        q = DATA.question(row["id"])
        expected = context_supports(q, bench_a.ContextBuilder(
            DATA, DATA.state_at, {}).build("none", q), DATA)
        assert row["correct"] is expected, row["id"]


def test_null_model_scores_zero_and_only_abstains(tmp_path):
    _, store, _ = run(tmp_path, fake="null")
    rows = store.rows(RESULTS)
    assert len(rows) == len(QUESTIONS) * len(SYSTEMS)
    assert not any(r["correct"] for r in rows) and all(r["abstained"] for r in rows)


def test_wrong_model_scores_zero_without_abstaining(tmp_path):
    _, store, _ = run(tmp_path, fake="wrong", systems=["graph", "none"])
    rows = store.rows(RESULTS)
    assert not any(r["correct"] for r in rows) and not any(r["abstained"] for r in rows)


# --- mỗi hệ nhận đúng ngữ cảnh qua đường chạy thật -----------------------------------------------------


def test_runner_sends_each_system_its_own_context(tmp_path):
    answerer = FakeAnswerer(DATA, "oracle")
    opts = RunOptions(out=tmp_path / "o", dry_run=True, samples=1,
                      question_ids=["item-06"])  # hỏi ở chương 5
    assert _run(opts, [], answerer=answerer) == 0
    asked = [m for call in answerer.calls for m in call if m.role == "user"
             and "Câu hỏi:" in m.content]
    by_marker = {
        "full": [m for m in asked if "[Chương 1]" in m.content and "[Chương 4]" in m.content],
        "graph": [m for m in asked if "Đồ thị trí nhớ của truyện" in m.content
                  and "[Đoạn trên trang" not in m.content],
        "graph_quotes": [m for m in asked if "Đồ thị trí nhớ của truyện" in m.content
                         and "[Đoạn trên trang tìm theo câu hỏi]" in m.content],
        "rolling": [m for m in asked if "Tóm tắt giả của chương 4" in m.content],
        "rag": [m for m in asked if "[Các đoạn liên quan" in m.content],
    }
    assert all(len(v) == 1 for v in by_marker.values()), {k: len(v) for k, v in by_marker.items()}
    matched = [m for group in by_marker.values() for m in group]
    none_only = [m for m in asked if m not in matched]
    assert len(none_only) == 1 and "[Chương 4]" not in none_only[0].content
    # G4: tư liệu nằm trong khối dữ liệu của vai user, không vào system
    for call in answerer.calls:
        system = " ".join(m.content for m in call if m.role == "system")
        assert "<player_data" not in system and "[Chương" not in system


def test_answer_prompt_states_the_chapter_and_the_answer_form():
    q = DATA.question("item-04")
    ctx = bench_a.ContextBuilder(DATA, DATA.state_at, {}).build("none", q)
    system, user = answer_messages(q, ctx)
    assert "Không biết" in system.content and "chỉ dựa" in system.content.lower()
    assert "tới hết chương 4" in user.content and "Chỉ trả lời" in user.content
    assert q.question in user.content


# --- chi phí và nhật ký --------------------------------------------------------------------------------


def test_cost_is_recorded_per_system_and_summaries_belong_to_rolling(tmp_path):
    _, store, _ = run(tmp_path, fake="oracle")
    report = compute_report(DATA, store, SYSTEMS, QUESTIONS, 1)
    rows = store.rows(RESULTS)
    assert all(r["calls"] and r["cost_usd"] > 0 for r in rows)
    sums = store.rows(SUMMARIES)
    assert [s["chapter"] for s in sums] == [1, 2, 3, 4]  # câu hỏi xa nhất ở chương 5
    assert all(s["calls"] and s["cost_usd"] > 0 for s in sums)
    for system, data in report["systems"].items():
        assert data["cost_answer_usd"] == pytest.approx(
            sum(r["cost_usd"] for r in rows if r["system"] == system))
        assert data["cost_build_usd"] == (pytest.approx(sum(s["cost_usd"] for s in sums))
                                          if system == "rolling" else 0.0)
    meta = store.read_meta()
    assert meta["runs"][-1]["spent_usd"] == pytest.approx(
        sum(r["cost_usd"] for r in rows) + sum(s["cost_usd"] for s in sums))


def test_summaries_are_only_built_for_the_rolling_system(tmp_path):
    _, store, _ = run(tmp_path, systems=["graph", "none"])
    assert store.rows(SUMMARIES) == []


def test_summary_md_has_one_row_per_system_and_marks_the_draft(tmp_path):
    _, store, _ = run(tmp_path)
    text = (store.root / "summary.md").read_text(encoding="utf-8")
    assert "CHỦ DỰ ÁN DUYỆT 21/10/2026" in text and "Chạy khô (model giả): True" in text
    assert "Câu nhớ và câu suy luận" in text
    for label in bench_a.SYSTEM_LABELS.values():
        assert label in text
    assert "Theo nhóm câu hỏi" in text and "Theo khoảng cách" in text


def test_meta_records_commit_data_hashes_and_models(tmp_path):
    _, store, _ = run(tmp_path)
    meta = store.read_meta()
    fp = meta["fingerprint"]
    assert meta["bench"] == "A" and "commit" in meta["runs"][0]
    assert set(fp["data_sha256"]) >= {"questions.yaml", "run.yaml", "sample-story/graph.yaml"}
    assert fp["answerer"]["model"] == CONFIG.models.roles.narrator
    assert fp["summarizer"]["model"] == CONFIG.models.roles.summary


# --- chạy tiếp, lỗi, trần -------------------------------------------------------------------------------


def test_second_run_in_the_same_folder_asks_nothing_new(tmp_path):
    opts = RunOptions(out=tmp_path / "o", dry_run=True, samples=1)
    first = FakeAnswerer(DATA)
    assert _run(opts, [], answerer=first) == 0
    n_first = len(first.calls)
    second = FakeAnswerer(DATA)
    assert _run(opts, [], answerer=second) == 0
    assert second.calls == [] and n_first > 0
    assert len(Store(opts.out).rows(RESULTS)) == len(QUESTIONS) * len(SYSTEMS)


def test_changed_data_refuses_to_continue_into_old_results(tmp_path):
    out = tmp_path / "o"
    assert _run(RunOptions(out=out, dry_run=True, samples=1, systems=["none"]), []) == 0
    with pytest.raises(ConfigError, match="khác"):
        _run(RunOptions(out=out, dry_run=True, samples=1, systems=["none"], fake="null"), [])


class FailingSummaries(FakeAnswerer):
    async def chat(self, model, messages, *, response_schema=None, extra=None):
        if response_schema is SummaryOutput:
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="giả")
        return await super().chat(model, messages, response_schema=response_schema, extra=extra)


def test_missing_summary_costs_only_the_rolling_system(tmp_path):
    opts = RunOptions(out=tmp_path / "o", dry_run=True, samples=1)
    assert _run(opts, [], answerer=FailingSummaries(DATA)) == 0
    store = Store(opts.out)
    rows, errors = store.rows(RESULTS), store.rows(ERRORS)
    assert {r["system"] for r in rows} == set(SYSTEMS) - {"rolling"} | (
        {"rolling"} if any(q.ask_chapter == 1 for q in QUESTIONS) else set())
    assert any(e["code"] == "CONTEXT_MISSING" and e["system"] == "rolling" for e in errors)
    report = compute_report(DATA, store, SYSTEMS, QUESTIONS, 1)
    assert report["systems"]["rolling"]["overall"]["n"] == len(QUESTIONS)
    assert report["systems"]["rolling"]["overall"]["answered"] < len(QUESTIONS)  # lỗi tính chưa đúng


class BrokenJson(LLMClient):
    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        self.calls += 1
        return ChatResult(text="không phải json", usage=Usage(cost_usd=0.0), model=model,
                          finish_reason="stop")

    async def stream(self, model, messages):  # pragma: no cover
        raise NotImplementedError
        yield


def test_bad_json_is_retried_then_logged_not_scored(tmp_path):
    opts = RunOptions(out=tmp_path / "o", dry_run=True, samples=1, systems=["none"],
                      question_ids=["item-01"])
    llm = BrokenJson()
    assert _run(opts, [], answerer=llm) == 0
    store = Store(opts.out)
    assert store.rows(RESULTS) == []
    [error] = store.rows(ERRORS)
    assert error["code"] == ErrorCode.RETRY_LIMIT_REACHED.value and error["system"] == "none"
    assert llm.calls == CONFIG.limits.retries.extract_schema_retry + 1


def test_budget_blocks_the_call_before_it_is_made(tmp_path):
    answerer = FakeAnswerer(DATA)
    opts = RunOptions(out=tmp_path / "o", dry_run=False, budget=0.0001, samples=1,
                      graph_backend="memory")
    logs: list[str] = []
    assert _run(opts, logs, answerer=answerer) == 2
    assert answerer.calls == [] and any("DỪNG (budget)" in line for line in logs)
    assert Store(opts.out).rows(RESULTS) == []


def test_budget_counts_earlier_runs_in_the_same_folder(tmp_path):
    out = tmp_path / "o"
    ok = RunOptions(out=out, dry_run=False, budget=5.0, samples=1, systems=["none"],
                    question_ids=["item-01"], graph_backend="memory")
    assert _run(ok, [], answerer=FakeAnswerer(DATA)) == 0
    spent = json.loads((out / "meta.json").read_text(encoding="utf-8"))["runs"][-1]["spent_usd"]
    assert spent > 0
    tight = RunOptions(out=out, dry_run=False, budget=spent, samples=1, systems=["none"],
                       question_ids=["item-02"], graph_backend="memory")
    assert _run(tight, [], answerer=FakeAnswerer(DATA)) == 2


def test_real_run_needs_a_budget_and_a_client(tmp_path):
    with pytest.raises(ConfigError, match="--budget"):
        check_options(RunOptions(out=tmp_path, dry_run=False))
    with pytest.raises(ConfigError, match="client"):
        _run(RunOptions(out=tmp_path / "o", dry_run=False, budget=1.0), [])


def test_options_are_validated_before_anything_runs(tmp_path):
    for bad in (RunOptions(out=tmp_path, systems=["bing"]),
                RunOptions(out=tmp_path, groups=["xyz"]),
                RunOptions(out=tmp_path, samples=0),
                RunOptions(out=tmp_path, concurrency=0)):
        with pytest.raises(ConfigError):
            check_options(bad)
    with pytest.raises(ConfigError, match="không có"):
        select_questions(DATA, RunOptions(out=tmp_path, question_ids=["nope-01"]))
    assert [q.group for q in select_questions(DATA, RunOptions(out=tmp_path, groups=["lie"]))] \
        == ["lie"] * 11


# --- báo cáo ---------------------------------------------------------------------------------------------


def test_report_counts_missing_rows_as_not_correct(tmp_path):
    opts = RunOptions(out=tmp_path / "o", dry_run=True, samples=1, systems=["graph"],
                      question_ids=["item-01", "item-02"])
    assert _run(opts, []) == 0
    report = compute_report(DATA, Store(opts.out), ["graph"], QUESTIONS, 1)
    overall = report["systems"]["graph"]["overall"]
    assert (overall["k"], overall["n"], overall["answered"]) == (2, len(QUESTIONS), 2)
    assert overall["ci"][1] < 0.2


def test_wilson_interval():
    assert wilson(0, 0) is None
    low, high = wilson(44, 44)
    assert 0.9 < low < 1.0 and high == pytest.approx(1.0)
    low, high = wilson(0, 10)
    assert low == pytest.approx(0.0) and 0.2 < high < 0.4


def test_plan_prices_every_system_without_calling_a_model():
    text = plan_text(DATA, CONFIG, samples=3)
    for label in bench_a.SYSTEM_LABELS.values():
        assert label in text
    assert "ƯỚC TÍNH THÔ" in text and "Tổng ước tính" in text


def test_plan_prices_only_the_hybrid_system_when_asked():
    text = plan_text(DATA, CONFIG, samples=3, systems=["graph_quotes"])
    assert bench_a.SYSTEM_LABELS["graph_quotes"] in text
    assert bench_a.SYSTEM_LABELS["graph"] + " |" not in text and "Tổng ước tính" in text


# --- hệ tuỳ chọn trong run.yaml (D-81) -------------------------------------------------------------------


def with_hybrid(enabled: bool):
    run = DATA.run.model_copy(update={"graph_quotes": DATA.run.graph_quotes.model_copy(
        update={"enabled": enabled})})
    return dataclasses.replace(DATA, run=run)


def test_hybrid_system_is_on_by_default_and_listed_after_graph():
    assert DATA.run.graph_quotes.enabled is True
    assert resolve_systems(DATA.run, []) == list(SYSTEMS)
    assert SYSTEMS.index("graph_quotes") == SYSTEMS.index("graph") + 1


def test_switched_off_hybrid_is_left_out_by_default_and_refused_when_named(tmp_path):
    off = with_hybrid(False)
    assert resolve_systems(off.run, []) == [s for s in SYSTEMS if s != "graph_quotes"]
    assert resolve_systems(off.run, ["graph", "none"]) == ["graph", "none"]
    with pytest.raises(ConfigError, match="graph_quotes.enabled"):
        resolve_systems(off.run, ["graph_quotes"])
    import asyncio

    opts = RunOptions(out=tmp_path / "o", dry_run=True, samples=1, question_ids=["item-01"])
    assert asyncio.run(run_bench(off, opts, config=CONFIG, log=lambda _: None)) == 0
    store = Store(opts.out)
    assert "graph_quotes" not in {r["system"] for r in store.rows(RESULTS)}
    assert "graph_quotes" not in store.read_meta()["runs"][-1]["systems"]
    with pytest.raises(ConfigError, match="graph_quotes.enabled"):
        plan_text(off, CONFIG, samples=1, systems=["graph_quotes"])


def test_meta_records_the_resolved_systems_of_a_default_run(tmp_path):
    _, store, _ = run(tmp_path, question_ids=["item-01"])
    assert store.read_meta()["runs"][-1]["systems"] == list(SYSTEMS)


# --- dòng lệnh -----------------------------------------------------------------------------------------------


def test_cli_dry_run_summary_and_plan(tmp_path, capsys):
    out = tmp_path / "cli"
    assert main(["run", "--dry-run", "--out", str(out), "--samples", "1", "--systems",
                 "graph,none", "--groups", "alive"]) == 0
    assert (out / "summary.md").exists() and (out / "results.jsonl").exists()
    capsys.readouterr()
    assert main(["summary", "--out", str(out)]) == 0
    assert "Độ chính xác chung" in capsys.readouterr().out
    assert main(["plan", "--samples", "1", "--systems", "graph"]) == 0
    assert "Đồ thị WriTory" in capsys.readouterr().out
    assert main(["plan", "--samples", "1", "--systems", "graph_quotes"]) == 0
    assert bench_a.SYSTEM_LABELS["graph_quotes"] in capsys.readouterr().out
    hybrid = tmp_path / "cli-hybrid"
    assert main(["run", "--dry-run", "--out", str(hybrid), "--samples", "1", "--systems",
                 "graph_quotes", "--groups", "relation"]) == 0
    rows = Store(hybrid).rows(RESULTS)
    assert rows and {r["system"] for r in rows} == {"graph_quotes"} and all(r["correct"] for r in rows)


def test_cli_rejects_missing_label_bad_label_and_unknown_system(tmp_path, capsys):
    assert main(["run", "--dry-run"]) == 1
    assert main(["run", "--dry-run", "--label", "Bad Label"]) == 1
    assert main(["run", "--dry-run", "--out", str(tmp_path / "x"), "--systems", "bing"]) == 1
    assert "Lỗi:" in capsys.readouterr().err
    assert not (tmp_path / "x").exists()


def test_cli_real_run_without_a_key_fails_before_creating_anything(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    out = tmp_path / "real"
    code = main(["run", "--out", str(out), "--budget", "1", "--env-file",
                 str(tmp_path / "không-có.env")])
    assert code == 1 and not out.exists()
    err = capsys.readouterr().err
    assert "OPENROUTER_API_KEY" in err


def test_answer_schema_rejects_extra_fields():
    with pytest.raises(ValueError):
        AnswerOutput.model_validate({"answer": "x", "reason": "y"})
