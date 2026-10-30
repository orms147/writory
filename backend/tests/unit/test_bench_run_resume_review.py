"""Review độc lập của `bench_run --resume` (D-124, D-130): những chỗ chưa có test. Model giả, kho trong bộ nhớ."""

import json

import pytest

from tests.pipeline_fixtures import OverlayStore
from tests.unit.test_bench_run_resume import DownLLM, first_leg, packages, resume, setup, straight
from tests.unit.test_pipeline_bench_run import make_run, rows
from writory.config import ConfigError
from writory.pipeline import bench_run
from writory.pipeline.bench_run import GraphRunStore, spent_usd_of

# --- dòng JSONL ghi dở -------------------------------------------------------------------------------


def cut_last_line(path, keep_chars=12):
    """Dòng cuối bị cắt giữa chừng (tiến trình chết khi đang ghi): không có xuống dòng, JSON dở."""
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([*lines[:-1], lines[-1][:keep_chars]]), encoding="utf-8")
    return json.loads(lines[-1])


async def test_a_half_written_last_line_of_calls_is_dropped_and_the_numbering_continues(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    whole = rows(out_1 / "calls.jsonl")
    lost = cut_last_line(out_1 / "calls.jsonl")
    assert lost["seq"] == whole[-1]["seq"]

    run2, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1, chapters=total)
    assert code == bench_run.EXIT_OK
    calls = rows(out_2 / "calls.jsonl")
    assert [c["seq"] for c in calls] == list(range(1, len(calls) + 1))
    assert run2.budgeted.spent_usd == pytest.approx(spent_usd_of(calls))
    point = json.loads((out_2 / "meta.json").read_text(encoding="utf-8"))["resume_points"][0]
    assert point["spent_usd_before"] == pytest.approx(spent_usd_of(whole[:-1]))


async def test_a_half_written_last_event_is_dropped_and_the_chain_still_ends_like_a_straight_run(
        tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store_a, out_a = await straight(tmp_path, config, scenario, total)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    last = cut_last_line(out_1 / "events.jsonl")
    assert last["type"] == "choice_picked" and last["chapter"] == 2

    _, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1, chapters=total)
    assert code == bench_run.EXIT_OK and store.committed == total
    def picked(out):
        return [(e["chapter"], e["index"]) for e in rows(out / "events.jsonl")
                if e.get("type") == "choice_picked"]

    assert picked(out_2) == picked(out_a)
    assert packages(store)[:3] == packages(store_a)[:3]


async def test_a_broken_line_in_the_middle_is_refused_and_nothing_is_written(tmp_path):
    config, scenario, total = setup(tmp_path)
    _, store, out_1, _ = await first_leg(tmp_path, config, scenario, total, chapters=2)
    lines = (out_1 / "calls.jsonl").read_text(encoding="utf-8").splitlines()
    lines[3] = lines[3][:10]
    (out_1 / "calls.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="dòng 4"):
        await resume(tmp_path, config, scenario, total, store, out_1, chapters=total)
    assert not (tmp_path / "leg2").exists()


# --- kho thật: chương không còn ---------------------------------------------------------------------


def test_scene_texts_of_a_chapter_the_store_does_not_have_is_empty_not_a_crash():
    """`chapter_scenes` trả None khi chương chưa commit; `scene_texts` từng làm `list(None)` và chạy tiếp chết
    bằng TypeError thay vì dừng với câu giải thích (`_resume_choices`)."""

    class NoRow:
        def execute(self, *_a, **_k):
            return self

        def fetchone(self):
            return None

    assert GraphRunStore(NoRow(), None, "s").scene_texts(7) == []


async def test_resume_stops_with_a_reason_when_the_store_has_no_text_for_the_last_chapter(tmp_path):
    """Chương cuối đã ghi mà chưa có lựa chọn, kho không còn văn của nó: dừng có mã, không chết bằng ngoại lệ."""
    config, scenario, total = setup(tmp_path)
    store = OverlayStore("s")
    run1, _, _, out_1 = make_run(tmp_path, config=config, scenario=scenario, store=store,
                                 out=tmp_path / "leg1", llm=DownLLM(total, down_schemas={"ChoicesOutput"}))
    assert await run1.run() == bench_run.EXIT_ABORT and store.committed == 1
    store.scene_texts = lambda number: []
    run2, _, code = await resume(tmp_path, config, scenario, total, store, out_1)
    assert code == bench_run.EXIT_ABORT and run2.stop["where"] == "resume: chương 1"
