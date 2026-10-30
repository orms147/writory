"""Bài đo A, hai hệ người kể (D-143): `narrator` (đề narrator-3, chỉ sổ tay) và `narrator_pages`
(narrator-4, sổ tay + đoạn trên trang), trên truyện 10 chương ky-ao. Model giả, không mạng."""

import asyncio
import html
import re
from pathlib import Path

import pytest

from writory.config import ConfigError, load_config
from writory.pipeline import bench_a
from writory.pipeline.bench_a import (
    RESULTS,
    FakeAnswerer,
    RunOptions,
    compute_report,
    plan_text,
    resolve_systems,
    run_bench,
)
from writory.pipeline.bench_a_data import load_data
from writory.pipeline.bench_a_narrator import (
    NARRATOR_LABELS,
    NARRATOR_SYSTEMS,
    on_page,
    variant_config,
)
from writory.pipeline.narrator import NOT_KNOWN, PAGES_PROMPT_VERSION, PROMPT_VERSION
from writory.quality.bench_d import Store

CONFIG = load_config()
RUN = load_data(questions_file="questions-ky-ao-vua-1.yaml")
QS = list(RUN.questions.questions)


def run_dry(tmp_path: Path, data=RUN, answerer=None, **kw) -> tuple[int, Store]:
    opts = RunOptions(out=tmp_path / "out", dry_run=True, samples=1, **kw)
    code = asyncio.run(run_bench(data, opts, config=CONFIG, answerer=answerer,
                                 log=lambda _: None))
    return code, Store(opts.out)


def test_narrator_systems_run_only_when_named():
    assert not set(NARRATOR_SYSTEMS) & set(RUN.run.systems)
    assert resolve_systems(RUN.run, []) == list(RUN.run.systems)
    assert resolve_systems(RUN.run, ["narrator", "narrator_pages"]) == list(NARRATOR_SYSTEMS)


def test_narrator_systems_need_a_story_written_by_the_pipeline(tmp_path):
    with pytest.raises(ConfigError, match="story: run"):
        run_dry(tmp_path, data=load_data(), systems=["narrator"])


def test_narrator_pages_needs_the_pages_switched_on():
    off = CONFIG.model_copy(update={"limits": CONFIG.limits.model_copy(update={
        "narrator_pages": CONFIG.limits.narrator_pages.model_copy(update={"top_k": 0})})})
    with pytest.raises(ConfigError, match="top_k"):
        variant_config("narrator_pages", off)
    assert variant_config("narrator", CONFIG).limits.narrator_pages.top_k == 0


def test_dry_run_oracle_scores_both_narrator_systems_with_their_own_prompt(tmp_path):
    code, store = run_dry(tmp_path, systems=list(NARRATOR_SYSTEMS))
    assert code == bench_a.EXIT_OK
    rows = store.rows(RESULTS)
    assert len(rows) == len(QS) * 2
    by = {s: [r for r in rows if r["system"] == s] for s in NARRATOR_SYSTEMS}
    assert {r["narrator_prompt"] for r in by["narrator"]} == {PROMPT_VERSION}
    assert {r["narrator_prompt"] for r in by["narrator_pages"]} == {PAGES_PROMPT_VERSION}
    assert all(r["passages"] == [] for r in by["narrator"])
    assert any(r["passages"] for r in by["narrator_pages"])
    for r in rows:  # "Bạn chưa biết điều này." là kiêng, không phải câu sai
        assert r["abstained"] is (r["answer"] == NOT_KNOWN)
    correct = {s: sum(r["correct"] for r in by[s]) for s in NARRATOR_SYSTEMS}
    assert correct["narrator_pages"] > correct["narrator"]  # đoạn mang thêm câu trích bằng chứng
    assert all(not r["final_leaks"] for r in rows)
    meta = store.read_meta()
    fp = meta["fingerprint"]
    assert fp["narrator_prompts"] == {"narrator": PROMPT_VERSION,
                                      "narrator_pages": PAGES_PROMPT_VERSION}
    assert {"run/setup.json", "run/meta.json"} <= set(fp["narrator_story_sha256"])
    summary = (store.root / "summary.md").read_text(encoding="utf-8")
    for label in NARRATOR_LABELS.values():
        assert label in summary
    assert "## Người kể: lý do chặn và lộ" in summary


def test_the_narrator_never_sees_a_chapter_after_the_question(tmp_path):
    """G1 trong bài đo: đoạn chỉ từ chương 1..N; dòng chỉ có ở chương sau N không vào context."""
    answerer = FakeAnswerer(RUN)
    run_dry(tmp_path, answerer=answerer, systems=["narrator_pages"])
    later_only = {
        n: {line for line in RUN.story[n].splitlines() if len(line) > 60}
        for n in RUN.story}
    asked = 0
    for messages in answerer.calls:
        user = next(m.content for m in messages if m.role == "user")
        chapter = int(re.search(r"tới hết chương (\d+)\):", user).group(1))
        text = html.unescape(user)
        for n, lines in later_only.items():
            if n <= chapter:
                continue
            earlier = "\n".join(RUN.story[c] for c in RUN.story if c <= chapter)
            for line in lines:
                if line not in earlier:
                    assert line not in text, (chapter, n)
        for m in re.finditer(r"^\[t\d+\] Chương (\d+):$", text, re.MULTILINE):
            assert int(m.group(1)) <= chapter
        asked += 1
    assert asked == len(QS)


def test_null_fake_only_abstains_and_wrong_fake_is_never_right(tmp_path):
    _, null = run_dry(tmp_path / "n", fake="null", systems=["narrator_pages"])
    assert all(r["abstained"] and not r["correct"] for r in null.rows(RESULTS))
    _, wrong = run_dry(tmp_path / "w", fake="wrong", systems=["narrator_pages"])
    assert not any(r["correct"] for r in wrong.rows(RESULTS))


def test_report_and_summary_count_code_blocks_and_leaks_per_narrator_system(tmp_path):
    _, store = run_dry(tmp_path, systems=list(NARRATOR_SYSTEMS))
    report = compute_report(RUN, store, list(NARRATOR_SYSTEMS), QS, 1)
    for s in NARRATOR_SYSTEMS:
        n = report["narrator"][s]
        assert n["rows"] == len(QS)
        assert n["final_leaks"] == 0 and n["final_leaks_off_page"] == 0
        assert sum(n["blocked"].values()) <= n["rows"]
    assert report["narrator"]["narrator"]["mean_passages"] == 0


def test_on_page_marks_terms_the_player_has_read():
    page = "Trần Mặc rút thẻ khỏi tay áo. Lão bảo: đừng tin người lạ."
    assert on_page("Trần Mặc", page)
    assert on_page("Trần Mặc + người lạ", page)
    assert not on_page("Tạ Vân Chi", page)


def test_plan_prices_the_narrator_systems_without_calling_a_model():
    text = plan_text(RUN, CONFIG, samples=3, systems=list(NARRATOR_SYSTEMS))
    for label in NARRATOR_LABELS.values():
        assert label in text
    assert f"Bài A: {len(QS)} câu × 3 lần × 2 hệ" in text and "Tổng ước tính" in text


def test_cli_runs_the_narrator_systems_dry(tmp_path):
    out = tmp_path / "cli"
    assert bench_a.main(["run", "--dry-run", "--out", str(out), "--samples", "1",
                         "--systems", "narrator,narrator_pages",
                         "--questions-file", "questions-ky-ao-vua-1.yaml",
                         "--groups", "item"]) == 0
    rows = Store(out).rows(RESULTS)
    assert rows and {r["system"] for r in rows} == set(NARRATOR_SYSTEMS)
