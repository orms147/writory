"""Lệnh chạy cả một truyện (pipeline/bench_run.py, D-42, D-43): model giả, kho truyện trong bộ nhớ,
không mạng. Bản chạy trên Neo4j + Postgres thật: tests/graph/test_bench_run.py."""

import json
import logging
import random
from pathlib import Path

import httpx
import pytest

from tests.pipeline_fixtures import FIRST_PERSON, OverlayStore, make_config
from writory.config import ConfigError, load_config
from writory.llm.openrouter import OpenRouterClient
from writory.pipeline import bench_run
from writory.pipeline.bench_run import (
    DRY_RUN_SECRET_TEXT,
    DryRunLLM,
    RunOptions,
    StoryRun,
    load_scenario,
    models_in_use,
    openrouter_client,
)
from writory.pipeline.scene import SceneOutline
from writory.quality import check_scene

SCENARIO_PATH = bench_run.DEFAULT_SCENARIO
GENERAL_FILES = ("meta.json", "setup.json", "events.jsonl", "calls.jsonl", "report.json",
                 "summary.md")
STYLE = "Văn phong thử."


# --- dựng một lần chạy --------------------------------------------------------------------------


def scenario_for(config, **changes):
    """Đề mẫu, với giá cho đúng các model config thử đang dùng (để test không phụ thuộc
    model thật trong config/models.yaml)."""
    base, _ = load_scenario(SCENARIO_PATH)
    prices = {info["model"]: {"in": 0.1, "out": 0.5}
              for info in models_in_use(config, base).values() if info["model"]}
    data = base.model_dump(mode="json", by_alias=True) | {"prices": prices} | changes
    return type(base).model_validate(data)


def trial_config(tmp_path):
    """Bản sao config/ với ngưỡng thử (tests/pipeline_fixtures.make_config), dựng một lần."""
    target = tmp_path / "config"
    return load_config(target) if target.exists() else make_config(tmp_path, **FIRST_PERSON)


def make_run(tmp_path, *, llm=None, config=None, scenario=None, store=None, out=None, **options):
    config = config or trial_config(tmp_path)
    scenario = scenario or scenario_for(config)
    total = config.story_lengths.levels[scenario.length_level].chapters.min
    llm = llm if llm is not None else DryRunLLM(total)
    store = store or OverlayStore()
    out = out or tmp_path / "out"
    run = StoryRun(scenario, "sha-test", config, llm=llm, store=store,
                   options=RunOptions(out=out, dry_run=True, **options), style_guide=STYLE,
                   log=lambda _: None)
    return run, llm, store, out


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def all_text(out: Path, *, skip: tuple[str, ...] = ()) -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(out.rglob("*"))
                     if p.is_file() and p.name not in skip)


# --- dry-run hết đường ------------------------------------------------------------------------


async def test_dry_run_goes_all_the_way_and_writes_every_file(tmp_path):
    run, llm, store, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK

    total = run.plan.total_chapters
    assert store.created == "short" and store.committed == total  # mặc định: số chương kế hoạch
    for name in (*GENERAL_FILES, "truth_dump.json"):
        assert (out / name).is_file(), name
    assert sorted(p.name for p in (out / "chapters").iterdir()) == [
        f"ch{n:02d}.md" for n in range(1, total + 1)]

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "done" and report["chapters_committed"] == total
    by_role = report["cost"]["by_role"]
    assert set(by_role) == {"setup", "outline", "writer", "extract", "summary", "choices",
                            "moderate"}
    assert all(v > 0 for v in by_role.values())
    assert sorted(report["cost"]["by_chapter"]) == [str(n) for n in range(total + 1)]
    calls = report["calls"]["by_role"]
    scenes = total * run.scenario.scene_count
    # Chương cuối: không tạo lựa chọn (D-50). Cảnh cuối của nó viết lại một lần vì model giả không
    # bao giờ hé lộ bí mật hay gỡ mạch đến hạn ở chương cuối (trễ hạn, D-49).
    # Kiểm duyệt (G9, D-57): mỗi lượt soát một cảnh một lời gọi, và mỗi bộ lựa chọn một lời gọi.
    assert calls == {"setup": 4, "outline": scenes, "writer": scenes + 1, "extract": scenes + 1,
                     "summary": total - 1, "choices": total - 1,
                     "moderate": scenes + 1 + (total - 1)}
    assert report["setup_repairs"] == {"used": 0, "kinds": {}}
    assert len(rows(out / "calls.jsonl")) == len(llm.calls)

    events = rows(out / "events.jsonl")
    kinds = [e["type"] for e in events]
    assert kinds.count("setup_options") == 3
    assert kinds.count("scene_ready") == scenes
    assert kinds.count("chapter_committed") == total + 1  # gồm chương 0
    assert kinds.count("choice_picked") == total - 1
    assert kinds.count("story_finished") == 1 and kinds[-1] == "story_finished"
    assert report["story_finished"] is True
    # Tóm tắt mọi chương trừ chương cuối (D-49); chương 1 không cần tóm tắt nào trước nó.
    assert report["summaries"] == {"made": total - 1, "failed": 0,
                                   "chapters_missing_previous": 0}
    assert report["cost"]["by_role"]["summary"] > 0
    summary_md = (out / "summary.md").read_text(encoding="utf-8")
    assert "| summary |" in summary_md and "Tóm tắt chương: tạo" in summary_md
    assert report["issues"]["left_when_shown"] == {"guard:overdue_secret": 1,
                                                   "guard:overdue_thread": 1}
    # Dàn ý giả ghi gỡ mọi mạch có id trong đề (D-82): không dàn ý nào bị thử lại vì bỏ mạch.
    assert report["outline_unplanned_threads"] == 0

    # Lựa chọn tự chọn ở chương 1 là hành động dẫn tới chương 2, đúng như người chơi bấm.
    picked = next(e for e in events if e["type"] == "choice_picked" and e["chapter"] == 1)
    writer_ch2 = [c for c in llm.calls if c[0].content.startswith(STYLE)
                  and "Chương 2, cảnh 1" in c[-1].content]
    assert writer_ch2 and picked["choice"]["text"] in writer_ch2[0][-1].content
    assert bench_run.DRY_RUN_SUMMARY in writer_ch2[0][-1].content  # tóm tắt chương 1 (D-49)

    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "done" and meta["exit_code"] == 0 and meta["dry_run"] is True
    assert meta["seed"] == run.scenario.seed and meta["git"]["commit"]
    assert set(meta["models"]) == {"setup", "outline", "writer", "extract", "summary", "choices",
                                 "moderate"}
    assert meta["models"]["writer"]["reasoning"] == "none"
    assert meta["config"]["sha256"] and meta["scenario"]["content"]["tags"]["genre"] == "tu tiên"
    chapter_1 = (out / "chapters" / "ch01.md").read_text(encoding="utf-8")
    assert bench_run.DRY_RUN_NPC_NAME in chapter_1 and "Lựa chọn" in chapter_1


def test_dry_run_scene_passes_the_repo_quality_config():
    """`--dry-run` chạy với config thật: cảnh viết tay phải qua kiểm văn, kể cả ngôi kể (D-51),
    để dry-run không tự sinh lượt viết lại."""
    repo = load_config()
    scenario, _ = load_scenario(SCENARIO_PATH)
    issues = check_scene(bench_run.DRY_RUN_SCENE, scenes_in_chapter=scenario.scene_count,
                         quality=repo.quality, lengths=repo.story_lengths)
    assert issues == []


async def test_run_stops_after_the_last_chapter_and_compares_plan_with_result(tmp_path):
    """Chương cuối kết truyện, lệnh dừng ngay sau đó (D-50). Report có mục so kế hoạch với kết quả:
    số thứ tự, khoảng, chương lộ hay gỡ; không id, không chữ (D-42)."""
    run, _, store, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    total = run.plan.total_chapters
    assert store.committed == total
    last = (out / "chapters" / f"ch{total:02d}.md").read_text(encoding="utf-8")
    assert "Lựa chọn cuối chương" not in last and "Hết truyện" in last

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["plan_vs_result"] == {
        "chapter": total, "total_chapters": total,
        "secrets": [{"n": 1, "window": [total, total], "revealed_chapter": None,
                     "status": "missed"}],
        "threads": [{"n": 1, "window": [total - 1, total], "resolved_chapter": None,
                     "status": "missed"}],
    }
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "## Kế hoạch so với kết quả" in summary and "Kết truyện: có" in summary
    general = all_text(out, skip=("truth_dump.json",))
    for text in ("t_ngoc_boi", "Bí ẩn của miếng ngọc bội", *(m.goal for m in run.plan.milestones)):
        assert text not in general, text
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert [t["thread_id"] for t in dump["plan_progress"]["threads"]] == ["t_ngoc_boi"]


def test_report_status_of_each_plan_item():
    from writory.guard.plan import PlanProgress, SecretProgress, ThreadProgress

    def secret(low, high, done):
        return SecretProgress("f", "x", False, low, high, done)

    progress = PlanProgress(5, 6, (secret(2, 3, 2), secret(2, 3, 1), secret(2, 3, 4),
                                   secret(4, 5, None), secret(5, 6, None)),
                            (ThreadProgress("t", "y", False, None, None, None),))
    report = bench_run.plan_vs_result(progress)
    assert [s["status"] for s in report["secrets"]] == [
        "on_time", "early", "late", "missed", "pending"]
    assert report["threads"] == [{"n": 1, "window": None, "resolved_chapter": None,
                                  "status": "pending"}]


def test_result_paths_are_relative_to_the_repo():
    assert bench_run.repo_path(SCENARIO_PATH) == "evals/scenarios/story_run/tu-tien-ngan.yaml"
    assert bench_run.repo_path(bench_run.REPO_CONFIG_DIR) == "config"


async def test_chapters_option_stops_early_and_never_runs_past_the_plan(tmp_path):
    run, _, store, out = make_run(tmp_path, chapters=2)
    assert await run.run() == bench_run.EXIT_OK
    assert store.committed == 2
    run, _, store, out = make_run(tmp_path, out=tmp_path / "out2", chapters=99)
    assert await run.run() == bench_run.EXIT_OK
    assert store.committed == run.plan.total_chapters
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["chapters_target"] == run.plan.total_chapters and report["chapters_clamped"]


async def test_existing_results_are_never_overwritten(tmp_path):
    run, _, _, out = make_run(tmp_path, chapters=1)
    assert await run.run() == bench_run.EXIT_OK
    again, llm, _, _ = make_run(tmp_path, out=out, chapters=1)
    with pytest.raises(ConfigError, match="đã có kết quả"):
        await again.run()
    assert llm.calls == []


# --- tách chữ bí mật ------------------------------------------------------------------------


async def test_secret_text_only_goes_to_truth_dump(tmp_path):
    run, _, _, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    general = all_text(out, skip=("truth_dump.json",))
    secret = run.plan.secrets[0]
    forbidden = [DRY_RUN_SECRET_TEXT, secret.fact_id, *(p for g in secret.leak_terms for p in g),
                 "reveal_from_chapter", "leak_terms"]
    for text in forbidden:
        assert text not in general, text
    truth = (out / "truth_dump.json").read_text(encoding="utf-8")
    for text in (DRY_RUN_SECRET_TEXT, secret.fact_id, "reveal_from_chapter"):
        assert text in truth
    dump = json.loads(truth)
    assert dump["plan"]["secrets"][0]["fact_id"] == secret.fact_id
    assert set(dump["packages"]) == {str(n) for n in range(run.plan.total_chapters + 1)}
    assert dump["final"]["chapter"] == run.plan.total_chapters
    assert any(e["type"] == "REVEALED_TO_PLAYER" for e in dump["final"]["edges"])
    assert dump["chapters"]["1"][0]["outlines"][0]["beats"]
    # Tóm tắt là chữ nội bộ (D-49): chỉ ở truth_dump, không ở file chung.
    assert dump["chapters"]["1"][0]["summary"] == bench_run.DRY_RUN_SUMMARY
    assert bench_run.DRY_RUN_SUMMARY not in general


# --- đếm lỗi, viết lại, cạnh bị bỏ ----------------------------------------------------------


class _Scripted(DryRunLLM):
    """DryRunLLM, thay câu trả lời của một vai ở lần gọi thứ k (đếm từ 1)."""

    def __init__(self, total, overrides):
        super().__init__(total)
        self.overrides = overrides  # {(vai, k): chuỗi | hàm(chữ gốc) -> chuỗi}
        self.seen: dict[str, int] = {}

    def reply(self, schema_name, text):
        role = bench_run.ROLE_BY_SCHEMA_NAME.get(schema_name, "writer")
        self.seen[role] = self.seen.get(role, 0) + 1
        answer = super().reply(schema_name, text)
        override = self.overrides.get((role, self.seen[role]))
        if override is None:
            return answer
        return override(answer) if callable(override) else override


def _with_bad_edge(answer: str) -> str:
    data = json.loads(answer)
    data["edges"].append({"type": "HOLDS", "source": "khong_co", "target": "cung_khong_co",
                          "kind": None, "score": None, "how": None, "told_by": None,
                          "quote": None, "known_as": None, "role": None})
    return json.dumps(data, ensure_ascii=False)


class _NoResolves(DryRunLLM):
    """DryRunLLM mà dàn ý không bao giờ định gỡ mạch nào."""

    def reply(self, schema_name, text):
        answer = super().reply(schema_name, text)
        if schema_name == SceneOutline.__name__:
            return json.dumps(json.loads(answer) | {"resolves": []}, ensure_ascii=False)
        return answer


async def test_outline_that_never_plans_a_due_thread_is_counted_not_fatal(tmp_path):
    """D-82: hết lượt thử mà dàn ý cảnh cuối vẫn bỏ mạch đến hạn thì truyện vẫn đi tiếp; report
    đếm số mạch như vậy (không id), id chỉ ở truth_dump."""
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, store, out = make_run(tmp_path, llm=_NoResolves(total), config=config)
    assert await run.run() == bench_run.EXIT_OK
    assert store.committed == total
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    # Mạch t_ngoc_boi chỉ đến hạn ở chương cuối, cảnh cuối (hạn gỡ total-1..total).
    assert report["outline_unplanned_threads"] == 1
    tries = 1 + config.limits.retries.extract_schema_retry
    assert report["calls"]["by_role"]["outline"] == total * run.scenario.scene_count - 1 + tries
    assert "Dàn ý cảnh cuối bỏ mạch đến hạn" in (out / "summary.md").read_text(encoding="utf-8")
    assert "t_ngoc_boi" not in all_text(out, skip=("truth_dump.json",))
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    last = dump["chapters"][str(total)][-1]["outlines"][-1]
    assert last["unplanned_threads"] == ["t_ngoc_boi"] and last["resolves"] == []


def test_resolved_in_without_quote_has_its_own_reject_group():
    assert bench_run.reject_reason("gỡ mạch mà không có câu trích (D-82)") == (
        "gỡ mạch mà không có câu trích (D-82)")


async def test_rewrites_issue_kinds_and_rejected_edges_are_counted(tmp_path):
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    cliche = "Thời gian như ngừng trôi. "
    llm = _Scripted(total, {("writer", 1): lambda a: cliche + a, ("extract", 1): _with_bad_edge})
    run, _, _, out = make_run(tmp_path, llm=llm, config=config, chapters=1)
    assert await run.run() == bench_run.EXIT_OK

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["issues"]["found"] == {"quality:cliche": 1}
    assert report["issues"]["left_when_shown"] == {}
    assert report["rewrites"] == 1
    assert report["rejected_edges"]["total"] == 1
    assert report["rejected_edges"]["by_reason"] == {"id không có trong danh mục": 1}
    # Chữ góp ý cho model viết lại (có thể chứa lớp truth) và mô tả cạnh chỉ ở truth_dump.
    general = all_text(out, skip=("truth_dump.json",))
    assert "sáo ngữ:" not in general and "khong_co" not in general
    truth = (out / "truth_dump.json").read_text(encoding="utf-8")
    assert "sáo ngữ:" in truth and "khong_co" in truth


async def test_blocked_choices_are_regenerated_like_a_player_retry(tmp_path):
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min

    def leak(answer: str) -> str:  # tên thật chưa hé lộ trong chữ lựa chọn (G2)
        data = json.loads(answer)
        data["choices"][0]["text"] = f"Đi tìm {bench_run.DRY_RUN_HIDDEN_NAME} hỏi chuyện."
        return json.dumps(data, ensure_ascii=False)

    llm = _Scripted(total, {("choices", 1): leak})
    run, _, store, out = make_run(tmp_path, llm=llm, config=config, chapters=2)
    assert await run.run() == bench_run.EXIT_OK
    assert store.committed == 2
    events = [e for e in rows(out / "events.jsonl") if e.get("chapter") == 1]
    kinds = [e["type"] for e in events]
    assert kinds.index("error") < kinds.index("choices_ready") < kinds.index("choice_picked")
    assert next(e for e in events if e["type"] == "error")["code"] == "CHOICES_LEAK_BLOCKED"
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["player_retries_used"] == {"setup": 0, "chapter": 0, "choices": 1}
    # Bộ tạo lại (dữ liệu có cấu trúc, id nút) vào truth_dump để chấm tay.
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert [c["kind"] for c in dump["chapters"]["1"][0]["choices"]] == [
        "action", "dialogue", "inner"]


def _without_secrets(answer: str) -> str:  # sai quy tắc khởi tạo: cần 1–3 bí mật
    data = json.loads(answer)
    data["secrets"] = []
    return json.dumps(data, ensure_ascii=False)


async def test_setup_repair_is_counted_in_the_report(tmp_path):
    """D-54: kế hoạch sai quy tắc được một lượt sửa trong `build_story`. Lượt đầu của "bấm thử lại"
    sửa rồi vẫn sai; lượt sau sai, sửa đúng. Report đếm lượt sửa và loại lỗi; danh sách lỗi (có id)
    chỉ ở truth_dump."""
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    llm = _Scripted(total, {("setup", k): _without_secrets for k in (4, 5, 6)})
    run, _, store, out = make_run(tmp_path, llm=llm, config=config, chapters=1)
    assert await run.run() == bench_run.EXIT_OK
    assert store.committed == 1
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["setup_repairs"] == {"used": 2, "kinds": {"secrets": 2}}
    assert report["player_retries_used"]["setup"] == 1
    assert report["calls"]["by_role"]["setup"] == 3 + 4  # 3 bước đề xuất + 2 lượt × (gọi + sửa)
    assert "Khởi tạo: lượt sửa 2 (secrets ×2)" in (out / "summary.md").read_text(encoding="utf-8")
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert [r["attempt"] for r in dump["setup_repairs"]] == [1, 2]
    problems = [p for r in dump["setup_repairs"] for p in r["problems"]]
    assert problems and all("bí mật" in p for p in problems)
    [error] = [e for e in dump["errors"] if e["where"] == "setup:build"]
    assert error["code"] == "STORY_SETUP_INVALID" and error["problems"]
    general = all_text(out, skip=("truth_dump.json",))
    assert all(p not in general for p in problems + error["problems"])


async def test_scene_blocked_after_every_retry_stops_the_run_and_keeps_files(tmp_path):
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    leak = f"{bench_run.DRY_RUN_HIDDEN_NAME} đứng sau cánh cửa. "
    llm = _Scripted(total, {("writer", k): (lambda a: leak + a) for k in range(1, 10)})
    run, _, store, out = make_run(tmp_path, llm=llm, config=config)
    assert await run.run() == bench_run.EXIT_ABORT
    assert store.committed == 0  # chỉ chương 0
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "error" and report["stop"]["code"] == "SCENE_LEAK_BLOCKED"
    assert report["player_retries_used"]["chapter"] == run.scenario.player_retries
    assert [e["type"] for e in rows(out / "events.jsonl")].count("scene_blocked") == (
        run.scenario.player_retries + 1)
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "error" and meta["exit_code"] == bench_run.EXIT_ABORT
    assert (out / "truth_dump.json").is_file() and (out / "summary.md").is_file()


# --- trần ngân sách --------------------------------------------------------------------------


async def test_budget_stops_before_a_call_that_could_exceed_and_keeps_what_was_done(tmp_path):
    """Giá vào 0, giá ra 2 USD/1M, max_tokens 1000: mỗi lời gọi giữ chỗ đúng 0,002 USD; mỗi lời
    gọi tốn 0,001. Trần 0,0105: lời gọi thứ 10 cần 0,009 + 0,002 > trần nên không được gọi."""
    config = trial_config(tmp_path)
    base = scenario_for(config)
    scenario = scenario_for(config, max_tokens_per_call=1000,
                            prices={m: {"in": 0.0, "out": 2.0} for m in base.prices})
    total = config.story_lengths.levels["short"].chapters.min
    llm = DryRunLLM(total, cost_usd=0.001)
    run, _, store, out = make_run(tmp_path, llm=llm, config=config, scenario=scenario,
                                  budget_usd=0.0105)
    assert await run.run() == bench_run.EXIT_BUDGET

    # setup 4 + chương 1: dàn ý, viết, trích (cảnh 1), dàn ý, viết (cảnh 2) = 9 lời gọi.
    assert len(llm.calls) == 9
    calls = rows(out / "calls.jsonl")
    assert len(calls) == 9 and all(c["status"] == "ok" for c in calls)
    assert sum(c["cost_usd"] for c in calls) <= 0.0105
    assert {c["reserved_usd"] for c in calls} == {0.002}
    assert all(c["extra"]["max_tokens"] == 1000 for c in calls)
    assert store.committed == 0  # chương 1 chưa ghi: không có gì nửa vời
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "budget" and report["stop"]["where"] == "chapter 1"
    assert report["cost"]["total_usd"] == pytest.approx(0.009)
    # Phần đã có vẫn được ghi: bối cảnh đã chọn, cảnh 1 đã hiện, kế hoạch và chương 0.
    assert json.loads((out / "setup.json").read_text(encoding="utf-8"))["build"]["done"]
    scene_1 = [e for e in rows(out / "events.jsonl") if e["type"] == "scene_ready"]
    assert len(scene_1) == 1
    partial = (out / "chapters" / "ch01.md").read_text(encoding="utf-8")
    assert scene_1[0]["text"] in partial and "chưa ghi" in partial
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert dump["plan"] and set(dump["packages"]) == {"0"}
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "budget" and meta["budget_usd"] == 0.0105


async def test_budget_is_required_for_a_real_run(tmp_path):
    config = trial_config(tmp_path)
    run = StoryRun(scenario_for(config), "sha", config, llm=DryRunLLM(4), store=OverlayStore(),
                   options=RunOptions(out=tmp_path / "o", dry_run=False), log=lambda _: None)
    with pytest.raises(ConfigError, match="--budget"):
        await run.run()


# --- tự chọn theo seed ------------------------------------------------------------------------


def _picks(out: Path) -> list[int]:
    return [e.get("picked", e.get("index")) for e in rows(out / "events.jsonl")
            if e["type"] in ("setup_options", "choice_picked")]


async def test_auto_pick_is_deterministic_for_a_seed(tmp_path):
    first, _, _, out_1 = make_run(tmp_path, out=tmp_path / "a", chapters=2, seed=7)
    second, _, _, out_2 = make_run(tmp_path, out=tmp_path / "b", chapters=2, seed=7)
    assert await first.run() == bench_run.EXIT_OK
    assert await second.run() == bench_run.EXIT_OK
    rng = random.Random(7)
    expected = [rng.randrange(3) for _ in range(3 + 2)]  # 3 bước khởi tạo + 2 chương
    assert _picks(out_1) == _picks(out_2) == expected
    for name in ("ch01.md", "ch02.md"):
        assert (out_1 / "chapters" / name).read_text(encoding="utf-8") == (
            out_2 / "chapters" / name).read_text(encoding="utf-8")
    assert json.loads((out_1 / "meta.json").read_text(encoding="utf-8"))["seed"] == 7


async def test_scenario_seed_is_the_default(tmp_path):
    run, _, _, out = make_run(tmp_path, chapters=1)
    assert await run.run() == bench_run.EXIT_OK
    rng = random.Random(run.scenario.seed)
    assert _picks(out) == [rng.randrange(3) for _ in range(4)]


# --- config còn null --------------------------------------------------------------------------


async def test_unset_config_fails_before_the_first_call_and_lists_every_gap(tmp_path):
    repo = trial_config(tmp_path)
    roles = repo.models.roles.model_copy(update={"setup": None})
    cost = repo.limits.cost_usd.model_copy(update={"per_story": None})
    config = repo.model_copy(update={
        "models": repo.models.model_copy(update={"roles": roles}),
        "limits": repo.limits.model_copy(update={"cost_usd": cost}),
    })
    scenario = scenario_for(repo, prices={"khac/model": {"in": 0.1, "out": 0.5}})
    llm, store = DryRunLLM(4), OverlayStore()
    run, _, _, out = make_run(tmp_path, llm=llm, config=config, scenario=scenario, store=store)
    with pytest.raises(ConfigError) as exc:
        await run.run()
    message = str(exc.value)
    for gap in ("roles.setup", "cost_usd.per_story", "prices"):
        assert gap in message
    assert llm.calls == [] and store.created is None and not out.exists()


def test_cli_reports_unset_config_without_touching_services(tmp_path, capsys, monkeypatch):
    """`main` kiểm config và đề trước khi kết nối Neo4j/Postgres hay đọc key."""
    config_dir = tmp_path / "config"
    make_config(tmp_path)  # dựng tmp_path/config
    models = config_dir / "models.yaml"
    models.write_text(models.read_text(encoding="utf-8").replace(
        "setup: deepseek/deepseek-v4-flash", "setup: null"), encoding="utf-8")
    for name in ("NEO4J_URI", "POSTGRES_DSN", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    code = bench_run.main(["--dry-run", "--config-dir", str(config_dir), "--out",
                           str(tmp_path / "out"), "--env-file", str(tmp_path / "none.env")])
    assert code == bench_run.EXIT_CONFIG
    err = capsys.readouterr().err
    assert "roles.setup" in err and not (tmp_path / "out").exists()


# --- key --------------------------------------------------------------------------------------

KEY = "sk-or-v1-" + "f00dfeed" * 8


def _transport(world: DryRunLLM, seen_auth: list[str], *, fails: int):
    """OpenRouter giả: `fails` lần đầu trả 500 có chép lại key (lỗi giữa đường), sau đó trả lời
    như model giả của --dry-run."""
    count = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_auth.append(request.headers["Authorization"])
        count["n"] += 1
        if count["n"] <= fails:
            return httpx.Response(500, json={"error": {"code": 500,
                                                       "message": f"upstream lỗi, key={KEY}"}})
        body = json.loads(request.content)
        schema = (body.get("response_format") or {}).get("json_schema", {}).get("name")
        text = world.reply(schema, body["messages"][-1]["content"])
        return httpx.Response(200, json={
            "model": body["model"],
            "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.0001},
        })

    return httpx.MockTransport(handler)


async def test_key_is_never_written_to_results_or_logs(tmp_path, monkeypatch, caplog, capsys):
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("OPENROUTER_API_KEY", KEY)
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    seen: list[str] = []
    # Lỗi 500 lặp lại quá `retries.llm_transient` lần ở bước khởi tạo đầu (D-14) thành
    # RETRY_LIMIT_REACHED; lệnh "bấm thử lại" như người chơi.
    fails = config.limits.retries.llm_transient + 1
    http = httpx.AsyncClient(transport=_transport(DryRunLLM(total), seen, fails=fails))
    client = openrouter_client(tmp_path / "none.env", http=http)
    assert isinstance(client, OpenRouterClient)
    run, _, _, out = make_run(tmp_path, llm=client, config=config, chapters=1, budget_usd=1.0)
    run.options.dry_run = False
    try:
        assert await run.run() == bench_run.EXIT_OK
    finally:
        await http.aclose()

    assert seen and all(h == f"Bearer {KEY}" for h in seen)  # key thật sự được dùng
    printed = capsys.readouterr()
    for where, text in (("kết quả", all_text(out)), ("log", caplog.text),
                        ("stdout", printed.out), ("stderr", printed.err)):
        assert KEY not in text, where
        assert "f00dfeedf00dfeed" not in text, where
    # Chi tiết lỗi (có chép key) chỉ vào truth_dump, đã redact.
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["player_retries_used"]["setup"] == 1
    assert report["calls"]["by_status"]["LLM_UNAVAILABLE"] == fails
    assert "[REDACTED]" in (out / "truth_dump.json").read_text(encoding="utf-8")


def test_real_client_reads_only_the_openrouter_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("ANTHROPIC_API_KEY=sk-ant-khong-dung\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY") as exc:
        openrouter_client(env)
    assert "sk-ant" not in str(exc.value)


# --- mức u tối của đề (D-67) ----------------------------------------------------------------------


def _spy_requests(monkeypatch) -> list:
    seen = []

    class Spy(bench_run.ChapterRun):
        def __init__(self, request, **kw):
            seen.append(request)
            super().__init__(request, **kw)

    monkeypatch.setattr(bench_run, "ChapterRun", Spy)
    return seen


@pytest.mark.parametrize("level", ["light", None])
async def test_scenario_darkness_level_is_stored_and_reaches_every_chapter(tmp_path, monkeypatch,
                                                                         level):
    """Đề khai `darkness_level` (không khai: mức mặc định). Mức được lưu theo truyện, vào thiết
    lập truyện của mọi chương và là trần kiểm duyệt của mọi chương, như đường chơi."""
    from writory.safety.moderate import darkness_brief

    config = trial_config(tmp_path)
    want = level or config.moderation.default_darkness_level
    seen = _spy_requests(monkeypatch)
    run, _, store, _ = make_run(tmp_path, config=config,
                                scenario=scenario_for(config, darkness_level=level))
    assert await run.run() == bench_run.EXIT_OK
    assert store.created_darkness == want
    assert seen and {r.darkness_level for r in seen} == {want}
    assert all(darkness_brief(config.moderation, want) in r.story_brief for r in seen)


async def test_unknown_scenario_darkness_level_fails_before_the_first_call(tmp_path):
    config = trial_config(tmp_path)
    llm, store = DryRunLLM(4), OverlayStore()
    run, _, _, out = make_run(tmp_path, llm=llm, config=config, store=store,
                              scenario=scenario_for(config, darkness_level="rat-toi"))
    with pytest.raises(ConfigError, match="darkness_level"):
        await run.run()
    assert llm.calls == [] and store.created is None and not out.exists()


@pytest.mark.parametrize("level", ["long", "novel"])
def test_bench_run_accepts_story_lengths_closed_to_players(tmp_path, level):
    """D-88: mức chưa mở cho người chơi vẫn chạy được bằng lệnh đo, để đo trước khi mở."""
    config = trial_config(tmp_path)
    assert not config.story_lengths.levels[level].player_selectable
    problems = bench_run.run_problems(config, scenario_for(config, length_level=level))
    assert not [p for p in problems if "độ dài" in p], problems

# --- dùng lại khởi tạo (--setup-from) và nhật ký đoạn trên trang (D-85) --------------------------


def _config_with_quotes(tmp_path, top_k):
    return make_config(tmp_path, **FIRST_PERSON, limits={"context": {"page_quotes_top_k": top_k}})


async def test_setup_from_reuses_plan_chapter_0_and_picks_without_a_setup_call(tmp_path):
    first, _, _, source = make_run(tmp_path / "a", out=tmp_path / "a" / "out")
    assert await first.run() == bench_run.EXIT_OK
    config = trial_config(tmp_path / "a")
    llm = DryRunLLM(4)
    again, _, store, out = make_run(tmp_path / "b", llm=llm, config=config, setup_from=source,
                                    store=OverlayStore("mem-run-2"), out=tmp_path / "b" / "out")
    assert await again.run() == bench_run.EXIT_OK

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert "setup" not in report["cost"]["by_role"] or report["cost"]["by_role"]["setup"] == 0
    assert report["calls"]["by_role"].get("setup", 0) == 0
    assert again.plan == first.plan and again.brief == first.brief
    assert again.packages[0].model_copy(update={"commit_id": ""}) == first.packages[0].model_copy(
        update={"commit_id": ""})
    assert again.packages[0].commit_id == f"{store.story_id}-ch0"
    old, new = (json.loads((d / "setup.json").read_text(encoding="utf-8")) for d in (source, out))
    assert all(old[k] == new[k] for k in ("settings", "plots", "characters"))
    assert new["build"]["reused_from"].endswith("out") and store.committed == first.plan.total_chapters
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["setup_from"] and meta["page_quotes_top_k"] == 0
    # Cùng luật chọn: dãy lựa chọn cuối chương cũng khớp khi model trả như nhau.
    assert _picks(source) == _picks(out)


async def test_setup_from_refuses_another_scenario_or_seed(tmp_path):
    first, _, _, source = make_run(tmp_path / "a", out=tmp_path / "a" / "out")
    assert await first.run() == bench_run.EXIT_OK
    config = trial_config(tmp_path / "a")
    other, _, _, _ = make_run(tmp_path / "b", config=config, setup_from=source, seed=first.seed + 1,
                              out=tmp_path / "b" / "out")
    assert await other.run() == bench_run.EXIT_ABORT
    assert "khác seed" in json.dumps(other.errors, ensure_ascii=False)
    diff, _, _, _ = make_run(tmp_path / "c", config=config, setup_from=source,
                             out=tmp_path / "c" / "out")
    diff.scenario_sha = "sha-khac"
    assert await diff.run() == bench_run.EXIT_ABORT
    assert "sha256" in json.dumps(diff.errors, ensure_ascii=False)


async def test_quotes_log_has_query_and_passage_ids_only_in_truth_dump(tmp_path):
    config = _config_with_quotes(tmp_path, 3)
    run, _, _, out = make_run(tmp_path, config=config)
    assert await run.run() == bench_run.EXIT_OK
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    quotes = dump["quotes"]
    assert quotes and {q["role"] for q in quotes} == {"outline", "writer"}
    assert all(q["query"] and q["passages"] and q["chapter"] >= 2 for q in quotes)
    assert all(len(ids) == 2 for q in quotes for ids in q["passages"])
    assert json.loads((out / "meta.json").read_text(encoding="utf-8"))["page_quotes_top_k"] == 3
    general = all_text(out, skip=("truth_dump.json",))
    assert all(q["query"] not in general for q in quotes)


async def test_quotes_log_is_empty_when_passages_are_off(tmp_path):
    run, _, _, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    assert json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))["quotes"] == []


async def test_new_facts_are_counted_and_their_rejections_are_grouped(tmp_path):
    """D-93: report đếm Fact mới đã ghi; lý do bỏ Fact mới có nhóm riêng, không rơi vào "sai schema"."""
    quote = bench_run._DRY_QUOTE
    fact = {"ref": "new_1", "text": "Mạc Vân Hà chịu chỉ cho tôi vài thế kiếm cơ bản", "quote": quote}
    bad = {"ref": "new_2", "text": "Điều hoàn toàn không có trên trang này đâu nhé",
           "quote": quote}
    edge = {"kind": None, "score": None, "how": None, "told_by": None, "quote": None,
            "known_as": None, "role": None}

    def with_facts(answer):
        data = json.loads(answer)
        data["edges"] += [
            edge | {"type": "ABOUT", "source": "new_1", "target": bench_run.DRY_RUN_NPC},
            edge | {"type": "KNOWS", "source": "protagonist", "target": "new_1", "how": "chứng kiến",
                    "quote": quote}]
        data["new_facts"] = [fact, bad]
        return json.dumps(data, ensure_ascii=False)

    config = trial_config(tmp_path)
    llm = _Scripted(config.story_lengths.levels["short"].chapters.min, {("extract", 1): with_facts})
    run, _, _, out = make_run(tmp_path, llm=llm, config=config, chapters=1)
    assert await run.run() == bench_run.EXIT_OK
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["new_facts"] == 1
    assert report["rejected_edges"]["by_reason"].get("chữ Fact không bám trang") == 1


def test_long_story_scenario_is_a_valid_long_level_scenario():
    """Đề đo mức Truyện dài (22/10/2026): đọc được, đúng mức, giá đủ cho mọi model config dùng."""
    path = SCENARIO_PATH.with_name("long-tu-tien.yaml")
    scenario, _ = load_scenario(path)
    assert scenario.length_level == "long" and scenario.version == 1
    assert scenario.scene_count >= 2 and scenario.seed != load_scenario(SCENARIO_PATH)[0].seed
    config = load_config()
    assert config.story_lengths.levels["long"].player_selectable is False  # D-88: vẫn chạy được
    priced = set(scenario.prices)
    used = {m["model"] for m in bench_run.models_in_use(config, scenario).values() if m["model"]}
    assert used <= priced


@pytest.mark.parametrize("level_id", ["short", "medium", "long", "novel"])
def test_dry_run_world_is_a_valid_plan_at_every_level(level_id):
    """Hồi quy (đề long-tu-tien): model giả chỉ dựng 4 mốc nên `--dry-run` ở mức Dài (cần 6–12 mốc)
    báo STORY_SETUP_INVALID. Thế giới giả phải qua `initial_problems` ở mọi mức."""
    from writory.pipeline.setup import BuildOutput, CharacterOption, to_story_setup

    level = load_config().story_lengths.levels[level_id]
    llm = DryRunLLM(level.chapters.min, milestones=level.milestones.min)
    world = BuildOutput.model_validate(json.loads(llm.reply("BuildOutput", "")))
    pc = CharacterOption(name="Lục Trầm", personality="Ít nói.", backstory="Mồ côi.")
    setup = to_story_setup(world, protagonist=pc, commit_id="c0", level=level)
    assert level.milestones.min <= len(setup.plan.milestones) <= level.milestones.max
    assert setup.plan.total_chapters == level.chapters.min
