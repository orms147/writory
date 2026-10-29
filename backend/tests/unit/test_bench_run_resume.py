"""`bench_run --resume`: chạy tiếp một lượt đã dừng giữa chừng (D-124). Model giả, kho trong bộ nhớ,
không mạng. Dừng giả ở chương k rồi chạy tiếp phải ra đúng kết quả chạy liền."""

import json
import shutil

import pytest

from tests.pipeline_fixtures import OverlayStore
from tests.unit.test_pipeline_bench_run import make_run, rows, scenario_for, trial_config
from writory.config import ConfigError
from writory.errors import ErrorCode, WritoryError
from writory.pipeline import bench_run
from writory.pipeline.bench_run import DryRunLLM


class DownLLM(DryRunLLM):
    """Như DryRunLLM nhưng báo lỗi cho vai bị tắt (mạng đứt giữa chừng)."""

    def __init__(self, total, *, down_schemas=(), down_writer=False, **kw):
        super().__init__(total, **kw)
        self.down_schemas, self.down_writer = set(down_schemas), down_writer

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        name = response_schema.__name__ if response_schema else None
        if (name is None and self.down_writer) or name in self.down_schemas:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail="giả: model không dùng được")
        return await super().chat(model, messages, response_schema=response_schema, extra=extra)


def setup(tmp_path):
    config = trial_config(tmp_path)
    scenario = scenario_for(config, player_retries=0)
    total = config.story_lengths.levels[scenario.length_level].chapters.min
    return config, scenario, total


async def straight(tmp_path, config, scenario, total):
    run, _, store, out = make_run(tmp_path, config=config, scenario=scenario,
                                  store=OverlayStore("s"), out=tmp_path / "straight")
    assert await run.run() == bench_run.EXIT_OK
    return run, store, out


async def first_leg(tmp_path, config, scenario, total, *, chapters=None, llm=None, name="leg1"):
    store = OverlayStore("s")
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=store,
                              out=tmp_path / name, chapters=chapters, llm=llm)
    code = await run.run()
    return run, store, out, code


async def resume(tmp_path, config, scenario, total, store, source, *, name="leg2", llm=None,
                 **options):
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=store,
                              out=tmp_path / name, resume=source, llm=llm, **options)
    code = await run.run()
    return run, out, code


def packages(store):
    """Gói từng chương, bỏ `commit_id` (có đuôi ngẫu nhiên mỗi lần ghi)."""
    return [p.model_dump(mode="json", by_alias=True, exclude={"commit_id"})
            for p in store.packages]


def chapter_files(out):
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((out / "chapters").iterdir())}


def picks(out):
    return [(e["chapter"], e["index"]) for e in rows(out / "events.jsonl")
            if e.get("type") == "choice_picked"]


# --- chạy tiếp giống chạy liền --------------------------------------------------------------------


async def test_resume_after_a_stop_at_chapter_k_matches_a_straight_run(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store_a, out_a = await straight(tmp_path, config, scenario, total)
    k = total - 2
    _, store_b, out_1, code = await first_leg(tmp_path, config, scenario, total, chapters=k)
    assert code == bench_run.EXIT_OK and store_b.committed == k

    run2, out_2, code2 = await resume(tmp_path, config, scenario, total, store_b, out_1)
    assert code2 == bench_run.EXIT_OK and run2.finished and store_b.committed == total

    assert packages(store_b) == packages(store_a)  # không đổi chương đã có, chương mới như chạy liền
    assert chapter_files(out_2) == chapter_files(out_a)
    assert picks(out_2) == picks(out_a)
    assert [c["role"] for c in rows(out_2 / "calls.jsonl")] == [
        c["role"] for c in rows(out_a / "calls.jsonl")]
    report_a = json.loads((out_a / "report.json").read_text(encoding="utf-8"))
    report_2 = json.loads((out_2 / "report.json").read_text(encoding="utf-8"))
    assert report_2["cost"]["total_usd"] == report_a["cost"]["total_usd"]  # cộng dồn, không mất
    assert report_2["chapters"] == report_a["chapters"]
    assert report_2["chapters_committed"] == total and report_2["story_finished"] is True


async def test_old_result_directory_is_left_untouched(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    before = {p.name: p.read_bytes() for p in sorted(out_1.rglob("*")) if p.is_file()}
    await resume(tmp_path, config, scenario, total, store, out_1)
    after = {p.name: p.read_bytes() for p in sorted(out_1.rglob("*")) if p.is_file()}
    assert before == after


async def test_meta_and_report_say_where_the_run_was_resumed_from(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    spent = json.loads((out_1 / "report.json").read_text(encoding="utf-8"))["cost"]["total_usd"]
    _, out_2, _ = await resume(tmp_path, config, scenario, total, store, out_1)
    meta = json.loads((out_2 / "meta.json").read_text(encoding="utf-8"))
    report = json.loads((out_2 / "report.json").read_text(encoding="utf-8"))
    assert meta["resumed_from"] == str(out_1).replace("\\", "/") or meta["resumed_from"].endswith(
        out_1.name)
    [point] = meta["resume_points"]
    assert point["chapter"] == 3 and point["spent_usd_before"] == spent
    assert report["resumed_from"] == meta["resumed_from"]
    assert report["resume_points"] == meta["resume_points"]
    assert meta["story_id"] == "s" and "resume_drift" not in meta


async def test_resuming_a_resumed_run_keeps_every_resume_point(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    _, out_2, _ = await resume(tmp_path, config, scenario, total, store, out_1, name="leg2",
                               chapters=3)
    _, out_3, _ = await resume(tmp_path, config, scenario, total, store, out_2, name="leg3")
    points = json.loads((out_3 / "meta.json").read_text(encoding="utf-8"))["resume_points"]
    assert [p["chapter"] for p in points] == [3, 4]


# --- dừng vì lỗi, không chỉ vì --chapters ------------------------------------------------------


async def test_resume_after_the_writer_went_down_numbers_the_new_attempt_after_the_old_ones(
        tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store_a, _ = await straight(tmp_path, config, scenario, total)

    class Dies(DryRunLLM):
        """Viết được hai chương rồi đứt mạng."""

        writer_calls = 0

        async def chat(self, model, messages, *, response_schema=None, extra=None):
            if response_schema is None:
                self.writer_calls += 1
                if self.writer_calls > 2 * scenario.scene_count:
                    raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail="giả: đứt mạng")
            return await super().chat(model, messages, response_schema=response_schema,
                                      extra=extra)

    store = OverlayStore("s")
    run1, _, _, out_1 = make_run(tmp_path, config=config, scenario=scenario, store=store,
                                 out=tmp_path / "leg1", llm=Dies(total))
    assert await run1.run() == bench_run.EXIT_ABORT
    assert store.committed == 2 and run1.stop["kind"] == "error"

    run2, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1)
    assert code == bench_run.EXIT_OK and store.committed == total
    assert packages(store) == packages(store_a)
    attempts = [(a["chapter"], a["attempt"], a["committed"]) for a in run2.attempts
                if a["chapter"] == 3]
    assert attempts == [(3, 1, False), (3, 2, True)]  # lượt mới nối sau lượt hỏng, không đè
    seqs = [c["seq"] for c in rows(out_2 / "calls.jsonl")]
    assert seqs == sorted(set(seqs))  # số thứ tự lời gọi nối tiếp, không trùng
    report = json.loads((out_2 / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "done" and report["stop"] is None
    meta = json.loads((out_2 / "meta.json").read_text(encoding="utf-8"))
    assert meta["resume_points"][0]["previous_stop"]["kind"] == "error"


async def test_resume_regenerates_choices_when_the_last_chapter_was_saved_without_them(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store_a, out_a = await straight(tmp_path, config, scenario, total)
    store = OverlayStore("s")
    run1, _, _, out_1 = make_run(tmp_path, config=config, scenario=scenario, store=store,
                                 out=tmp_path / "leg1",
                                 llm=DownLLM(total, down_schemas={"ChoicesOutput"}))
    # Chương 1 ghi xong nhưng bộ lựa chọn hỏng: lượt dừng ngay sau chương 1.
    assert await run1.run() == bench_run.EXIT_ABORT and store.committed == 1

    _, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1)
    assert code == bench_run.EXIT_OK and store.committed == total
    assert packages(store) == packages(store_a)
    assert picks(out_2) == picks(out_a)
    assert "Lựa chọn cuối chương" in chapter_files(out_2)["ch01.md"]  # chương 1 được viết lại đủ


# --- trần chi phí cộng dồn -------------------------------------------------------------------------


async def test_the_budget_counts_what_the_first_leg_already_spent(tmp_path):
    config, scenario, total = setup(tmp_path)
    run1, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    spent = run1.budgeted.spent_usd
    assert spent > 0
    with pytest.raises(ConfigError, match="trần"):
        await resume(tmp_path, config, scenario, total, store, out_1, name="leg2", budget_usd=spent)
    run2, _, code = await resume(tmp_path, config, scenario, total, store, out_1, name="leg3",
                                 budget_usd=spent * 1.02)
    assert code == bench_run.EXIT_BUDGET and run2.stop["kind"] == "budget"  # trần tổng, không phải thêm
    assert run2.budgeted.spent_usd >= spent
    meta = json.loads((tmp_path / "leg3" / "meta.json").read_text(encoding="utf-8"))
    assert meta["budget_usd"] == pytest.approx(spent * 1.02)


async def test_the_per_story_cap_keeps_counting_across_the_resume(tmp_path):
    config, scenario, total = setup(tmp_path)
    run1, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    run2, _, _ = await resume(tmp_path, config, scenario, total, store, out_1)
    assert run2.tracker.story_usd == pytest.approx(
        sum(c.get("cost_usd") or 0 for c in rows(tmp_path / "leg2" / "calls.jsonl")))
    assert run2.tracker.story_usd > run1.tracker.story_usd


# --- từ chối resume ------------------------------------------------------------------------------


def edit_meta(out, mutate):
    path = out / "meta.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    mutate(meta)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")


@pytest.mark.parametrize(("label", "mutate"), [
    ("git.commit", lambda m: m["git"].update(commit="0" * 40)),
    ("config", lambda m: m["config"]["sha256"].update(combined="khac")),
    ("scenario.sha256", lambda m: m["scenario"].update(sha256="khac")),
    ("models", lambda m: m["models"]["writer"].update(model="model/khac")),
    ("prompt_versions", lambda m: m["prompt_versions"].update(writer="writer-0")),
])
async def test_resume_is_refused_when_code_config_scenario_or_model_differ(tmp_path, label, mutate):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    edit_meta(out_1, mutate)
    before = store.committed
    with pytest.raises(ConfigError, match=label.split(".")[0]):
        await resume(tmp_path, config, scenario, total, store, out_1)
    assert store.committed == before and not (tmp_path / "leg2").exists()  # chưa ghi gì


async def test_allow_drift_resumes_and_records_what_drifted(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    edit_meta(out_1, lambda m: m["git"].update(commit="0" * 40))
    _, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1,
                                  resume_allow_drift=True)
    assert code == bench_run.EXIT_OK
    meta = json.loads((out_2 / "meta.json").read_text(encoding="utf-8"))
    assert [d["key"] for d in meta["resume_drift"]] == ["git.commit"]
    assert meta["resume_drift"][0]["was"] == "0" * 40


async def test_changing_chapters_or_budget_is_not_drift(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    _, _, code = await resume(tmp_path, config, scenario, total, store, out_1, chapters=3,
                              budget_usd=5.0)
    assert code == bench_run.EXIT_OK and store.committed == 3


async def test_a_finished_story_cannot_be_resumed(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out = await straight(tmp_path, config, scenario, total)
    with pytest.raises(ConfigError, match="kết"):
        await resume(tmp_path, config, scenario, total, store, out)


async def test_a_directory_without_truth_dump_cannot_be_resumed(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    (out_1 / "truth_dump.json").unlink()
    with pytest.raises(ConfigError, match="truth_dump"):
        await resume(tmp_path, config, scenario, total, store, out_1)


async def test_resume_needs_the_story_to_still_be_in_the_store_at_the_same_chapter(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=3)
    stale = OverlayStore("s")  # kho khác: truyện không còn
    with pytest.raises(ConfigError, match="kho"):
        await resume(tmp_path, config, scenario, total, stale, out_1)
    store.committed = 2  # kho lệch so với thư mục kết quả
    with pytest.raises(ConfigError, match="chương"):
        await resume(tmp_path, config, scenario, total, store, out_1, name="leg3")


async def test_resume_cannot_be_combined_with_setup_from_or_setup_only(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    shutil.copytree(out_1, tmp_path / "copy")
    with pytest.raises(ConfigError, match="setup"):
        await resume(tmp_path, config, scenario, total, store, out_1, setup_from=tmp_path / "copy")
    with pytest.raises(ConfigError, match="setup"):
        await resume(tmp_path, config, scenario, total, store, out_1, name="leg3", setup_only=True)


async def test_the_seed_must_still_replay_to_the_choices_that_were_picked(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=3)

    def corrupt(meta):
        meta["seed"] = meta["seed"] + 1

    edit_meta(out_1, corrupt)
    with pytest.raises(ConfigError, match="seed"):
        await resume(tmp_path, config, scenario, total, store, out_1)
