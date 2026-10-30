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
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, current_trace
from writory.llm.fake import FakeLLM
from writory.llm.openrouter import OpenRouterClient
from writory.pipeline import bench_run
from writory.pipeline.bench_run import (
    DRY_RUN_SECRET_TEXT,
    BudgetedClient,
    DryRunLLM,
    Price,
    RunOptions,
    StepTracker,
    StoryRun,
    load_scenario,
    models_in_use,
    openrouter_client,
)
from writory.pipeline.scene import SceneOutline
from writory.quality import check_scene
from writory.quality.bench_d import Budget, _maybe_billed

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
                   options=RunOptions(**{"out": out, "dry_run": True, **options}),
                   style_guide=STYLE, log=lambda _: None)
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
    # Mạch của thế giới dry-run không khai bí mật trả lời: không dời gì (D-135).
    assert report["thread_answers"] == {"threads": 1, "linked": 0, "shifted": 0,
                                        "shifted_end": 0, "dropped": 0, "mismatches": 0}
    # Fixture khởi tạo không có ngoại hình: chỉ số đếm 0, không chữ (D-122).
    assert report["appearance_variety"] == {
        "characters": report["appearance_variety"]["characters"], "with_appearance": 0,
        "starts_with_trong": 0, "opening_repeats": 0, "hair": {}, "hair_repeats": 0}
    assert report["appearance_variety"]["characters"] > 0
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
        # Bộ trích giả không đánh dấu mốc nào; mốc nào đã qua hạn thì "missed" (D-116).
        "milestones": [{"n": i, "window": [m.from_chapter, m.to_chapter], "done_chapter": None,
                        "status": "missed"} for i, m in enumerate(run.plan.milestones, 1)],
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
    with pytest.raises(ConfigError, match="đã có file"):
        await again.run()
    assert llm.calls == []


async def test_a_directory_with_files_but_no_meta_is_not_written_into(tmp_path):
    """D-130: thư mục ghi dở (không có meta.json) cũng bị từ chối; thư mục rỗng thì dùng được."""
    (tmp_path / "half").mkdir()
    (tmp_path / "half" / "calls.jsonl").write_text('{"seq": 1}\n', encoding="utf-8")
    run, llm, _, _ = make_run(tmp_path, out=tmp_path / "half", chapters=1)
    with pytest.raises(ConfigError, match="đã có file"):
        await run.run()
    assert llm.calls == []
    (tmp_path / "empty").mkdir()
    run, _, _, _ = make_run(tmp_path, out=tmp_path / "empty", chapters=1)
    assert await run.run() == bench_run.EXIT_OK


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


def _gate(inner, budget, record):
    return BudgetedClient(inner, budget=budget,
                          prices={"m": Price.model_validate({"in": 0.0, "out": 2.0})},
                          max_tokens=1000, tracker=StepTracker(load_config().limits.cost_usd),
                          record=record)


@pytest.mark.parametrize(("code", "detail"), [
    (ErrorCode.LLM_TIMEOUT, "quá hạn tổng"),  # D-113: như lời gọi bị huỷ
    (ErrorCode.LLM_UNAVAILABLE, "ReadError"),  # đứt sau khi gửi
])
async def test_a_call_that_may_have_been_billed_counts_its_maximum_against_the_budget(code, detail):
    """Như `llm.cost.maybe_billed` (D-64, D-113): lỗi sau khi gửi thì có thể đã bị tính tiền, nên trần
    --budget và số đã tiêu cộng chi phí tối đa của lời gọi (0,002 USD ở đây), không phải 0."""

    class Fails(FakeLLM):
        async def chat(self, model, messages, *, response_schema=None, extra=None):
            raise WritoryError(code, detail=detail)

    calls: list[dict] = []
    budget = Budget("run", 1.0)
    with pytest.raises(WritoryError):
        await _gate(Fails([]), budget, calls.append).chat("m", [Message(role="user", content="x")])
    assert budget.spent_usd == pytest.approx(0.002)
    assert calls[0]["status"] == code.value and calls[0]["cost_estimated_usd"] == 0.002


async def test_a_call_that_never_left_the_machine_is_not_counted():
    """Client thật báo chưa gửi (lỗi kết nối, `CallTrace.sent=False`): không tốn tiền (D-64)."""

    class NotSent(FakeLLM):
        async def chat(self, model, messages, *, response_schema=None, extra=None):
            current_trace().sent = False
            raise WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="ConnectError")

    calls: list[dict] = []
    budget = Budget("run", 1.0)
    with pytest.raises(WritoryError):
        await _gate(NotSent([]), budget, calls.append).chat("m", [Message(role="user", content="x")])
    assert budget.spent_usd == 0.0 and calls[0]["cost_estimated_usd"] is None


def test_the_other_benches_count_a_timed_out_call_as_possibly_billed():
    """bench_d, bench_e, bài F dùng `bench_d._maybe_billed`: phải theo `llm.cost.maybe_billed`."""
    assert _maybe_billed(WritoryError(ErrorCode.LLM_TIMEOUT, detail="quá hạn tổng"))
    assert _maybe_billed(WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="ReadError"))
    assert not _maybe_billed(WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 503: x"))
    assert not _maybe_billed(WritoryError(ErrorCode.WRITORY_RATE_LIMITED))


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
        "setup: openai/gpt-6-luna", "setup: null"), encoding="utf-8")
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


# --- so nhiều model viết trên cùng một thế giới (D-101): cờ ghi đè, giới hạn token, chỉ khởi tạo --


def _overrides(**changes):
    return bench_run.ModelOverrides(**changes)


def _call_rows(out: Path) -> list[dict]:
    return rows(out / "calls.jsonl")


def test_overrides_replace_only_the_writer_and_the_outline_role(tmp_path):
    config = trial_config(tmp_path)
    scenario = scenario_for(config)
    changed = bench_run.apply_model_overrides(config, scenario, _overrides(
        writer_model="w/model", writer_reasoning="omit", outline_model="o/model",
        outline_reasoning="medium"))
    used = models_in_use(changed, scenario)
    assert used["writer"]["model"] == "w/model" and used["writer"]["reasoning"] is None
    assert used["outline"] == {"model": "o/model", "reasoning": "medium"}
    before = models_in_use(config, scenario)
    for role in ("setup", "extract", "choices", "summary", "moderate"):
        assert used[role] == before[role]
    assert config.models.writer_tiers[0].model != "w/model"  # bản gốc không bị sửa


def test_no_override_leaves_the_config_untouched(tmp_path):
    config = trial_config(tmp_path)
    assert bench_run.apply_model_overrides(config, scenario_for(config), _overrides()) == config


def test_override_edits_the_tier_the_scenario_uses_not_the_first(tmp_path):
    config = trial_config(tmp_path)
    tiers = [*config.models.writer_tiers,
             config.models.writer_tiers[0].model_copy(update={"id": "alt", "model": "alt/model"})]
    config = config.model_copy(update={"models": config.models.model_copy(
        update={"writer_tiers": tiers})})
    scenario = scenario_for(config, writer_tier="alt")
    changed = bench_run.apply_model_overrides(config, scenario, _overrides(writer_model="w/model"))
    assert [t.model for t in changed.models.writer_tiers] == [tiers[0].model, "w/model"]


async def test_run_with_overrides_sends_them_and_records_them_in_meta(tmp_path):
    config = trial_config(tmp_path)
    overrides = _overrides(writer_model="w/model", writer_reasoning="omit", outline_model="o/model",
                           outline_reasoning="omit")
    scenario = scenario_for(config)
    scenario = scenario.model_copy(update={"prices": {
        **scenario.prices, "w/model": bench_run.Price(**{"in": 0.1, "out": 0.5}),
        "o/model": bench_run.Price(**{"in": 0.1, "out": 0.5})}})
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, overrides=overrides)
    assert await run.run() == bench_run.EXIT_OK
    calls = [c for c in _call_rows(out) if c["status"] == "ok"]
    by_role = {r: {c["model"] for c in calls if c["role"] == r} for r in
               ("writer", "outline", "extract", "choices")}
    assert by_role["writer"] == {"w/model"} and by_role["outline"] == {"o/model"}
    assert "w/model" not in by_role["extract"] | by_role["choices"]
    assert all("reasoning" not in c["extra"] for c in calls if c["role"] in ("writer", "outline"))
    assert any("reasoning" in c["extra"] for c in calls if c["role"] == "extract")
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["overrides"]["writer_model"] == "w/model"
    assert meta["models"]["writer"]["model"] == "w/model"
    assert meta["models"]["outline"]["model"] == "o/model"


async def test_override_without_a_price_fails_before_the_first_call(tmp_path):
    config = trial_config(tmp_path)
    run, llm, _, out = make_run(tmp_path, config=config,
                                overrides=_overrides(writer_model="w/khong-gia"))
    with pytest.raises(ConfigError, match="w/khong-gia"):
        await run.run()
    assert llm.calls == [] and not out.exists()


async def test_setup_only_stops_after_chapter_0_and_leaves_a_usable_source(tmp_path):
    first, _, store, source = make_run(tmp_path / "a", out=tmp_path / "a" / "out",
                                       setup_only=True)
    assert await first.run() == bench_run.EXIT_OK
    assert store.committed == 0 and not (source / "chapters").exists()
    assert {c["role"] for c in _call_rows(source)} <= {"setup"}
    meta = json.loads((source / "meta.json").read_text(encoding="utf-8"))
    assert meta["setup_only"] is True
    config = trial_config(tmp_path / "a")
    again, _, store2, _ = make_run(tmp_path / "b", llm=DryRunLLM(4), config=config,
                                   setup_from=source, store=OverlayStore("mem-run-2"),
                                   out=tmp_path / "b" / "out")
    assert await again.run() == bench_run.EXIT_OK
    assert again.plan == first.plan and store2.committed == first.plan.total_chapters


# --- mạch do bí mật trả lời (D-135) ---------------------------------------------------------------


def _linked_thread(answer: str) -> str:
    """Mạch của thế giới dry-run khai bí mật nội gián là câu trả lời: mạch gỡ ở chương cuối-1..cuối,
    bí mật lộ ở chương cuối, nên code dời chương đầu của khoảng gỡ."""
    data = json.loads(answer)
    data["threads"][0]["answered_by"] = [data["secrets"][0]["fact_id"]]
    return json.dumps(data, ensure_ascii=False)


async def test_thread_window_shift_is_counted_in_the_report_with_ids_only_in_truth_dump(tmp_path):
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, _, out = make_run(tmp_path, llm=_Scripted(total, {("setup", 4): _linked_thread}),
                              config=config, setup_only=True)
    assert await run.run() == bench_run.EXIT_OK
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["thread_answers"] == {"threads": 1, "linked": 1, "shifted": 1,
                                        "shifted_end": 0, "dropped": 0, "mismatches": 0}
    assert report["setup_repairs"]["used"] == 0  # code dời, không tốn lượt sửa
    assert ("Mạch phải gỡ có bí mật trả lời (D-135): 1/1; dời khoảng gỡ 1 (dời cả hạn 0); bỏ id "
            "fact thường 0; còn lệch 0.") in (out / "summary.md").read_text(encoding="utf-8")
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert dump["thread_shifts"] == [{"thread_id": "t_ngoc_boi", "before": [total - 1, total],
                                      "after": [total, total], "secrets": ["f_ha_tran_noi_gian"],
                                      "end_moved": False}]
    assert dump["plan"]["must_resolve_threads"][0]["answered_by"] == ["f_ha_tran_noi_gian"]
    general = all_text(out, skip=("truth_dump.json",))
    assert "t_ngoc_boi" not in general and "f_ha_tran_noi_gian" not in general

    # --setup-from dùng lại thế giới: số dời là của lần khởi tạo nguồn.
    again, _, _, out2 = make_run(tmp_path / "b", llm=DryRunLLM(total), config=config,
                                 setup_from=out, store=OverlayStore("mem-run-2"),
                                 out=tmp_path / "b" / "out", chapters=1)
    assert await again.run() == bench_run.EXIT_OK
    report2 = json.loads((out2 / "report.json").read_text(encoding="utf-8"))
    assert report2["thread_answers"] == report["thread_answers"]


async def test_setup_from_an_old_world_does_not_know_its_shifts(tmp_path):
    """Thư mục nguồn trước D-135 (truth_dump không có `thread_shifts`): số dời là không rõ."""
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    first, _, _, source = make_run(tmp_path / "a", out=tmp_path / "a" / "out", config=config,
                                   setup_only=True)
    assert await first.run() == bench_run.EXIT_OK
    dump = json.loads((source / "truth_dump.json").read_text(encoding="utf-8"))
    del dump["thread_shifts"], dump["answers_dropped"]
    (source / "truth_dump.json").write_text(json.dumps(dump, ensure_ascii=False), encoding="utf-8")
    again, _, _, out = make_run(tmp_path / "b", llm=DryRunLLM(total), config=config,
                                setup_from=source, store=OverlayStore("mem-run-2"),
                                out=tmp_path / "b" / "out", chapters=1)
    assert await again.run() == bench_run.EXIT_OK
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["thread_answers"]["shifted"] is None
    assert report["thread_answers"]["dropped"] is None
    assert report["thread_answers"]["mismatches"] == 0
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "dời khoảng gỡ không rõ" in summary and "bỏ id fact thường không rõ" in summary


def _plain_fact_link(answer: str) -> str:
    """Mạch của thế giới dry-run khai fact thường (không phải bí mật) là câu trả lời (D-135)."""
    data = json.loads(answer)
    plain = next(f["id"] for f in data["facts"]
                 if f["id"] not in {s["fact_id"] for s in data["secrets"]})
    data["threads"][0]["answered_by"] = [plain]
    return json.dumps(data, ensure_ascii=False)


async def test_dropped_plain_fact_link_is_counted_without_a_repair(tmp_path):
    """Chủ dự án chọn (D-135): id fact thường trong `answered_by` bị code bỏ, không tốn lượt sửa.
    Report đếm số đã bỏ; cặp (mạch, fact) có id chỉ ở truth_dump."""
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, _, out = make_run(tmp_path, llm=_Scripted(total, {("setup", 4): _plain_fact_link}),
                              config=config, setup_only=True)
    assert await run.run() == bench_run.EXIT_OK
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["thread_answers"] == {"threads": 1, "linked": 0, "shifted": 0,
                                        "shifted_end": 0, "dropped": 1, "mismatches": 0}
    assert report["setup_repairs"]["used"] == 0
    assert "bỏ id fact thường 1" in (out / "summary.md").read_text(encoding="utf-8")
    dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert dump["answers_dropped"] == [["t_ngoc_boi", "f_ngoc_boi_linh_mach"]]
    general = all_text(out, skip=("truth_dump.json",))
    assert "t_ngoc_boi" not in general and "f_ngoc_boi_linh_mach" not in general


def test_cli_parses_the_override_flags():
    args = bench_run._parser().parse_args([
        "--writer-model", "w/m", "--writer-reasoning", "omit", "--outline-model", "o/m",
        "--outline-reasoning", "low", "--setup-only"])
    overrides = bench_run.overrides_from_args(args)
    assert overrides == _overrides(writer_model="w/m", writer_reasoning="omit",
                                   outline_model="o/m", outline_reasoning="low")
    assert args.setup_only is True


def test_cli_rejects_an_unknown_reasoning_level(capsys):
    with pytest.raises(SystemExit):
        bench_run._parser().parse_args(["--writer-reasoning", "tuyet-doi"])
    assert "tuyet-doi" in capsys.readouterr().err


def test_model_bakeoff_scenario_prices_the_three_models_and_stays_a_short_story():
    scenario, _ = load_scenario(SCENARIO_PATH.with_name("model-bakeoff.yaml"))
    assert set(scenario.prices) >= {"openai/gpt-6-luna", "deepseek/deepseek-v4-flash",
                                    "tencent/hy3"}
    # `--setup-from` đòi cùng sha256 và seed, nên đề này không dùng chung file với đề khác.
    assert scenario.length_level == "short" and scenario.seed != load_scenario(SCENARIO_PATH)[0].seed


@pytest.mark.parametrize("model", ["openai/gpt-6-luna", "deepseek/deepseek-v4-flash",
                                   "tencent/hy3"])
def test_model_bakeoff_scenario_has_no_gap_for_any_of_the_three_writers(model):
    """Đủ giá cho mọi vai config đang dùng cộng model ghi đè, để lệnh không dừng ở lời gọi đầu."""
    scenario, _ = load_scenario(SCENARIO_PATH.with_name("model-bakeoff.yaml"))
    config = bench_run.apply_model_overrides(
        load_config(), scenario,
        bench_run.ModelOverrides(writer_model=model, outline_model=model))
    assert bench_run.run_problems(config, scenario) == []


# --- A/B đề viết trên cùng một thế giới (D-109) -----------------------------------------------------


def _variant_dir(root: Path, name: str = "moi") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "outline_system.md").write_text("ĐỀ DÀN Ý BIẾN THỂ", encoding="utf-8")
    (folder / "goals.yaml").write_text("push_forward: MỤC TIÊU BIẾN THỂ.\n", encoding="utf-8")
    return folder


def test_cli_parses_the_style_guide_and_prompt_variant_flags():
    args = bench_run._parser().parse_args(["--style-guide", "x.md", "--prompt-variant", "moi"])
    assert (args.style_guide, args.prompt_variant) == ("x.md", "moi")
    none = bench_run._parser().parse_args([])
    assert none.style_guide is None and none.prompt_variant is None


def test_prompts_from_args_reads_the_files_and_names_what_it_overrides(tmp_path):
    guide = tmp_path / "van-phong.md"
    guide.write_text("VĂN PHONG MỚI\n", encoding="utf-8")
    _variant_dir(tmp_path / "bien-the")
    args = bench_run._parser().parse_args(["--style-guide", str(guide), "--prompt-variant", "moi"])
    got = bench_run.prompts_from_args(args, variants_root=tmp_path / "bien-the")
    assert got.style_guide == "VĂN PHONG MỚI" and got.style_guide_path == guide
    assert got.variant.name == "moi" and got.variant.outline_system == "ĐỀ DÀN Ý BIẾN THỂ"
    plain = bench_run.prompts_from_args(bench_run._parser().parse_args([]))
    assert (plain.style_guide, plain.style_guide_path, plain.variant) == (None, None, None)


@pytest.mark.parametrize("content", ["", "  \n"])
def test_an_empty_style_guide_file_is_refused(tmp_path, content):
    guide = tmp_path / "rong.md"
    guide.write_text(content, encoding="utf-8")
    args = bench_run._parser().parse_args(["--style-guide", str(guide)])
    with pytest.raises(ConfigError, match="rỗng"):
        bench_run.prompts_from_args(args)


def test_a_missing_style_guide_file_is_refused(tmp_path):
    args = bench_run._parser().parse_args(["--style-guide", str(tmp_path / "khong-co.md")])
    with pytest.raises(ConfigError, match="không đọc được"):
        bench_run.prompts_from_args(args)


async def test_dry_run_with_a_variant_and_style_guide_sends_them_and_records_them_in_meta(tmp_path):
    from writory.pipeline.prompt_variants import load_prompt_variant

    _variant_dir(tmp_path / "bien-the")
    variant = load_prompt_variant("moi", root=tmp_path / "bien-the")
    guide = tmp_path / "van-phong.md"
    guide.write_text("VĂN PHONG MỚI", encoding="utf-8")
    config = trial_config(tmp_path)
    scenario = scenario_for(config)
    llm = DryRunLLM(config.story_lengths.levels[scenario.length_level].chapters.min)
    run = StoryRun(scenario, "sha-test", config, llm=llm, store=OverlayStore(),
                   options=RunOptions(out=tmp_path / "out", dry_run=True, prompt_variant=variant,
                                      style_guide_path=guide),
                   style_guide="VĂN PHONG MỚI", log=lambda _: None)
    assert await run.run() == bench_run.EXIT_OK
    outline_calls = [c for c in llm.calls if c[0].content.startswith("ĐỀ DÀN Ý BIẾN THỂ")]
    assert outline_calls, "lời gọi dàn ý phải mang đề biến thể"
    # câu "đẩy truyện tới" không có ở chương cuối, nên không phải lời gọi nào cũng mang nó
    assert sum("MỤC TIÊU BIẾN THỂ." in c[-1].content for c in outline_calls) >= len(outline_calls) - 2
    assert [c for c in llm.calls if c[0].content.startswith("VĂN PHONG MỚI")]
    meta = json.loads((tmp_path / "out" / "meta.json").read_text(encoding="utf-8"))
    assert meta["prompt_variant"]["name"] == "moi"
    assert meta["prompt_variant"]["overrides"] == ["outline_system", "goals:push_forward"]
    assert set(meta["prompt_variant"]["files"]) == {"outline_system.md", "goals.yaml"}
    assert meta["style_guide_path"].endswith("van-phong.md")
    assert meta["style_guide_sha256"] == bench_run._sha256("VĂN PHONG MỚI".encode())
    assert meta["prompt_versions"]["outline"] == bench_run.scene_mod.OUTLINE_PROMPT_VERSION
    assert meta["prompt_versions_overridden"] == ["outline", "writer"]


async def test_a_default_run_records_no_override(tmp_path):
    run, _, _, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["prompt_variant"] is None and meta["style_guide_path"] is None
    assert meta["prompt_versions_overridden"] == []


# --- ba cờ ngữ cảnh của đề v3: bật mặc định ở limits.yaml (D-111), meta ghi giá trị đã dùng ------


def test_prose_v3_flag_and_its_helpers_are_gone():
    import pytest
    with pytest.raises(SystemExit):
        bench_run._parser().parse_args(["--prose-v3"])
    assert not hasattr(bench_run, "apply_prose_v3") and not hasattr(bench_run, "PROSE_V3_CONTEXT")


async def test_meta_records_the_three_context_flags(tmp_path):
    run, _, _, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    assert meta["context_flags"] == {"character_personality_max_chars": 0,
                                     "previous_openings": 0, "unplanned_chapter_goal": False,
                                     "phase_shift_every": None}
    on = make_config(tmp_path / "on", **FIRST_PERSON, limits={"context": {
        "character_personality_max_chars": 240, "previous_openings": 2,
        "previous_opening_max_chars": 160, "unplanned_chapter_goal": True,
        "phase_shift_every": 4}})
    run2, _, _, out2 = make_run(tmp_path / "on", config=on)
    assert await run2.run() == bench_run.EXIT_OK
    flags = json.loads((out2 / "meta.json").read_text(encoding="utf-8"))["context_flags"]
    assert flags == {"character_personality_max_chars": 240, "previous_openings": 2,
                     "unplanned_chapter_goal": True, "phase_shift_every": 4}


async def test_report_says_which_chapters_had_the_phase_shift_line_on(tmp_path):
    """Mặc định tắt: danh sách rỗng. Bật `phase_shift_every`: `phase_shift_chapters` là đúng các chương
    đã ghi mà câu bật, khớp cờ trên từng bản ghi attempt. Truyện thử có mỗi hồi một chương, nên chương
    đầu của hồi nào cũng là đổi pha và chỉ chương 1 (chưa có hồi mới) tới nhịp khi N = 1."""
    run, _, _, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    off = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert off["phase_shift_chapters"] == [] and not any(a["phase_shift"] for a in run.attempts)

    on = make_config(tmp_path / "on", **FIRST_PERSON, limits={"context": {"phase_shift_every": 1}})
    run2, llm2, _, out2 = make_run(tmp_path / "on", config=on)
    assert await run2.run() == bench_run.EXIT_OK
    report = json.loads((out2 / "report.json").read_text(encoding="utf-8"))
    assert report["phase_shift_chapters"] == [1]
    assert report["phase_shift_chapters"] == sorted({a["chapter"] for a in run2.attempts
                                                     if a["committed"] and a["phase_shift"]})
    assert any("ĐỔI PHA" in m.content for call in llm2.calls for m in call)


# --- thân trả lời bị từ chối của mọi vai (D-115) ------------------------------------------------


class _BlankSummaryOnce(DryRunLLM):
    """Tóm tắt trống ở lần đầu (sai quy tắc sau schema), nhúng key giả để kiểm G7."""

    def __init__(self, total: int, body: str = "  ", raw: str | None = None) -> None:
        super().__init__(total)
        self.body, self.raw, self.fired = body, raw, False

    def reply(self, schema_name, text):
        if schema_name == "SummaryOutput" and not self.fired:
            self.fired = True
            if self.raw is not None:  # không phải JSON: sai schema
                return self.raw
            return json.dumps({"summary": self.body}, ensure_ascii=False)
        return super().reply(schema_name, text)


async def test_a_rejected_body_is_kept_in_rejected_jsonl_with_where_and_why(tmp_path):
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, _, out = make_run(tmp_path, llm=_BlankSummaryOnce(total), config=config)
    assert await run.run() == bench_run.EXIT_OK
    [row] = rows(out / "rejected.jsonl")
    assert row["role"] == "summary" and row["chapter"] == 1 and row["code"] == "LLM_BAD_RESPONSE"
    assert "rỗng" in row["reason"] and json.loads(row["body"]) == {"summary": "  "}
    assert row["truncated"] is False and row["body_chars"] == len(row["body"])
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["rejected_bodies"] == 1


async def test_no_rejection_means_no_file(tmp_path):
    run, _, _, out = make_run(tmp_path)
    assert await run.run() == bench_run.EXIT_OK
    assert not (out / "rejected.jsonl").exists()
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))["rejected_bodies"] == 0


async def test_a_long_body_is_cut_to_the_line_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(bench_run, "REJECTED_BODY_MAX_CHARS", 40)
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, _, out = make_run(tmp_path, llm=_BlankSummaryOnce(total, body=" " * 500), config=config)
    assert await run.run() == bench_run.EXIT_OK
    [row] = rows(out / "rejected.jsonl")
    assert len(row["body"]) == 40 and row["truncated"] is True and row["body_chars"] > 40


async def test_a_key_in_a_rejected_body_is_redacted_g7(tmp_path):
    key = "sk-or-v1-" + "0123456789abcdef" * 4
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, _, out = make_run(tmp_path, llm=_BlankSummaryOnce(total, raw=f"không phải JSON {key}"),
                              config=config)
    assert await run.run() == bench_run.EXIT_OK
    text = (out / "rejected.jsonl").read_text(encoding="utf-8")
    assert key not in text and "sk-or-v1-" not in text


async def test_rejected_bodies_stay_out_of_the_general_files(tmp_path):
    """Thân có thể mang lớp truth (dàn ý, viết): như truth_dump.json, không phải file chung."""
    assert "rejected.jsonl" not in GENERAL_FILES
    config = trial_config(tmp_path)
    total = config.story_lengths.levels["short"].chapters.min
    run, _, _, out = make_run(tmp_path, llm=_BlankSummaryOnce(total, raw="BÍ-MẬT-TRONG-THÂN"),
                              config=config)
    assert await run.run() == bench_run.EXIT_OK
    assert "BÍ-MẬT-TRONG-THÂN" not in all_text(out, skip=("truth_dump.json", "rejected.jsonl"))


def test_the_app_never_installs_the_rejection_hook():
    """G7 và D-115: thân bị từ chối chỉ được giữ ở bộ đo, không ở app."""
    from writory.config import REPO_ROOT

    src = REPO_ROOT / "backend" / "src" / "writory"
    users = sorted(p.relative_to(src).as_posix() for p in src.rglob("*.py")
                   if "watch_rejections" in p.read_text(encoding="utf-8"))
    assert users == ["llm/retry.py", "pipeline/bench_run.py"]
