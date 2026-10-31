"""`bench_run` ghi checkpoint sau mỗi chương (D-148): lượt bị ngắt cứng (máy khởi động lại, không kịp `_finish`) vẫn
`--resume` được, không mất tiền đã tiêu. Model giả, kho trong bộ nhớ, không mạng. "Ngắt cứng" giả bằng một
BaseException làm mọi lần ghi file sau đó chết, và `_stop`/`_finish` bị vô hiệu: tiến trình đã chết thì không ghi gì thêm."""

import json

import pytest

from tests.pipeline_fixtures import OverlayStore
from tests.unit.test_bench_run_resume import chapter_files, packages, picks, resume, setup, straight
from tests.unit.test_pipeline_bench_run import make_run, rows
from writory.config import ConfigError
from writory.pipeline import bench_run
from writory.pipeline.bench_run import spent_usd_of


class Killed(BaseException):
    """Tiến trình chết: không `except Exception` nào bắt được."""


def arm_hard_kill(run, *, after_calls: int | None = None, at_write: int | None = None, monkeypatch=None):
    """`after_calls`: chết ngay khi lời gọi thứ `after_calls + 1` định ghi vào calls.jsonl (dòng đó không được ghi).
    `at_write`: chết ở lần ghi atomic file thứ `at_write` (đếm từ 1), trước khi đổi tên: file tạm còn, file cũ nguyên."""
    state = {"dead": False, "writes": 0}
    real_append = run.files.append

    def append(name, row):
        if state["dead"]:
            raise Killed
        if after_calls is not None and name == "calls.jsonl" and row.get("seq") == after_calls + 1:
            state["dead"] = True
            raise Killed
        real_append(name, row)

    real_write = bench_run.write_atomic

    def write(path, text):
        if state["dead"]:
            raise Killed
        state["writes"] += 1
        if at_write is not None and state["writes"] == at_write:
            state["dead"] = True
            path.with_name(path.name + ".tmp").write_text(text[: len(text) // 2], encoding="utf-8")  # ghi dở
            raise Killed
        real_write(path, text)

    run.files.append = append
    run._stop = lambda *a, **k: None
    run._finish = lambda: None
    monkeypatch.setattr(bench_run, "write_atomic", write)
    return state


async def killed_run(tmp_path, config, scenario, total, monkeypatch, **kill):
    store = OverlayStore("s")
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=store, out=tmp_path / "killed")
    arm_hard_kill(run, monkeypatch=monkeypatch, **kill)
    with pytest.raises(Killed):
        await run.run()
    return run, store, out


# 48 lời gọi cho cả truyện 4 chương; mỗi chương khoảng 11 lời gọi sau 4 lời gọi khởi tạo.
KILL_POINTS = [9, 14, 17, 20, 24, 27, 31, 36, 40, 44]


@pytest.mark.parametrize("after_calls", KILL_POINTS)
async def test_a_hard_killed_run_resumes_from_its_last_checkpoint_and_ends_like_a_straight_run(
        tmp_path, monkeypatch, after_calls):
    config, scenario, total = setup(tmp_path)
    _, store_a, out_a = await straight(tmp_path, config, scenario, total)
    straight_report = json.loads((out_a / "report.json").read_text(encoding="utf-8"))

    _, store, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, after_calls=after_calls)
    monkeypatch.undo()
    meta = json.loads((out_1 / "meta.json").read_text(encoding="utf-8"))
    assert meta["status"] == "running" and meta["exit_code"] is None   # chưa chạy xong
    dead_calls = rows(out_1 / "calls.jsonl")
    assert len(dead_calls) == after_calls

    try:
        run2, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1)
    except ConfigError as e:
        assert "mới có chương 0" in str(e), e    # chưa ghi xong chương 1: chạy lại bằng --setup-from (test dưới)
        pytest.skip("lượt chết trước khi chương 1 được ghi")
    assert code == bench_run.EXIT_OK and store.committed == total and run2.finished
    assert packages(store) == packages(store_a)
    assert picks(out_2) == picks(out_a) and chapter_files(out_2) == chapter_files(out_a)

    calls = rows(out_2 / "calls.jsonl")
    assert [c["seq"] for c in calls] == list(range(1, len(calls) + 1))
    assert calls[:after_calls] == dead_calls          # phần của lượt chết giữ nguyên, kể cả phần chương dở
    report = json.loads((out_2 / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "done" and report["stop"] is None and report["story_finished"] is True
    assert report["cost"]["total_usd"] == pytest.approx(spent_usd_of(calls))
    # Chi phí: như chạy liền, cộng phần đã tiêu cho lượt chương dở bị bỏ (được đếm, không mất). Riêng lời gọi đang bay
    # lúc chết không có dòng nào (tiến trình chết thì không ghi): tối đa một lời gọi, và lượt chạy tiếp không làm lại nó
    # khi nó thuộc phần đã checkpoint.
    one_call = max(c["cost_usd"] for c in rows(out_a / "calls.jsonl"))
    assert report["cost"]["total_usd"] >= straight_report["cost"]["total_usd"] - one_call - 1e-9
    assert report["cost"]["total_usd"] - straight_report["cost"]["total_usd"] <= spent_usd_of(dead_calls) + 1e-9
    point = json.loads((out_2 / "meta.json").read_text(encoding="utf-8"))["resume_points"][0]
    assert point["spent_usd_before"] == pytest.approx(spent_usd_of(dead_calls))
    assert point["previous_stop"]["kind"] == "interrupted"


async def test_the_chapters_before_the_killed_one_cost_the_same_as_in_a_straight_run(tmp_path, monkeypatch):
    config, scenario, total = setup(tmp_path)
    _, _, out_a = await straight(tmp_path, config, scenario, total)
    by_chapter = json.loads((out_a / "report.json").read_text(encoding="utf-8"))["cost"]["by_chapter"]
    _, store, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, after_calls=31)
    monkeypatch.undo()
    _, out_2, _ = await resume(tmp_path, config, scenario, total, store, out_1)
    got = json.loads((out_2 / "report.json").read_text(encoding="utf-8"))["cost"]["by_chapter"]
    for chapter in ("0", "1", "2"):
        assert got[chapter] == by_chapter[chapter]


async def test_the_attempt_after_the_killed_one_is_numbered_after_it(tmp_path, monkeypatch):
    """Lượt chết đã gọi model cho chương dở (attempt 1) mà chưa kịp ghi attempt đó vào report: lượt chạy tiếp phải đánh số
    attempt kế tiếp theo calls.jsonl, không đè lên số cũ."""
    config, scenario, total = setup(tmp_path)
    _, store, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, after_calls=31)
    monkeypatch.undo()
    dead = rows(out_1 / "calls.jsonl")
    unfinished = store.committed + 1
    assert dead[-1]["chapter"] == unfinished and {c["attempt"] for c in dead if c["chapter"] == unfinished} == {1}
    run2, out_2, _ = await resume(tmp_path, config, scenario, total, store, out_1)
    new = [c for c in rows(out_2 / "calls.jsonl")[len(dead):] if c["chapter"] == unfinished]
    assert new and {c["attempt"] for c in new} == {2}
    assert [a["attempt"] for a in run2.attempts if a["chapter"] == unfinished] == [2]


# --- sau khởi tạo, trước chương 1 ---------------------------------------------------------------------------


async def test_a_run_killed_after_setup_can_be_continued_with_setup_from(tmp_path, monkeypatch):
    """Khởi tạo tốn tiền (Meta khoảng 0,24 USD): chết ngay sau đó thì `--setup-from` dùng lại được."""
    config, scenario, total = setup(tmp_path)
    _, _, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, after_calls=5)
    monkeypatch.undo()
    for name in ("truth_dump.json", "setup.json", "report.json"):
        assert (out_1 / name).is_file(), name
    truth = json.loads((out_1 / "truth_dump.json").read_text(encoding="utf-8"))
    assert truth["plan"] is not None and "0" in truth["packages"]
    run, _, _, _out = make_run(tmp_path, config=config, scenario=scenario, store=OverlayStore("s2"),
                                out=tmp_path / "again", setup_from=out_1)
    assert await run.run() == bench_run.EXIT_OK and run.finished


# --- ghi nguyên tử ---------------------------------------------------------------------------------------


async def test_a_checkpoint_killed_half_way_leaves_the_previous_one_intact_and_resume_ignores_the_temp_file(
        tmp_path, monkeypatch):
    config, scenario, total = setup(tmp_path)
    _, store_a, _out_a = await straight(tmp_path, config, scenario, total)
    # Mỗi lần checkpoint ghi 3 file: chết ở lần ghi thứ 13 (giữa checkpoint thứ năm), file cũ còn nguyên.
    _, store, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, at_write=13)
    monkeypatch.undo()
    leftovers = sorted(p.name for p in out_1.glob("*.tmp"))
    assert leftovers, "file tạm ghi dở phải còn lại để test có nghĩa"
    for name in ("truth_dump.json", "setup.json", "report.json"):
        json.loads((out_1 / name).read_text(encoding="utf-8"))   # file thật luôn là JSON đủ
    _, out_2, code = await resume(tmp_path, config, scenario, total, store, out_1)
    assert code == bench_run.EXIT_OK and packages(store) == packages(store_a)
    assert not list(out_2.glob("*.tmp"))


def test_write_atomic_replaces_the_file_only_when_the_new_content_is_complete(tmp_path, monkeypatch):
    target = tmp_path / "x.json"
    bench_run.write_atomic(target, "cũ")
    assert target.read_text(encoding="utf-8") == "cũ" and not list(tmp_path.glob("*.tmp"))

    def boom(src, dst):
        raise OSError("đĩa đầy")

    monkeypatch.setattr(bench_run.os, "replace", boom)
    with pytest.raises(OSError):
        bench_run.write_atomic(target, "mới")
    assert target.read_text(encoding="utf-8") == "cũ"


async def test_a_checkpoint_that_cannot_be_written_does_not_stop_the_run(tmp_path, monkeypatch):
    config, scenario, _total = setup(tmp_path)
    real = bench_run.write_atomic
    seen = {"failed": 0}

    def flaky(path, text):
        if path.name == "truth_dump.json" and seen["failed"] < 2:
            seen["failed"] += 1
            raise OSError("đĩa đầy")
        real(path, text)

    monkeypatch.setattr(bench_run, "write_atomic", flaky)
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=OverlayStore("s"), out=tmp_path / "o")
    assert await run.run() == bench_run.EXIT_OK and run.finished and seen["failed"] == 2
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))["status"] == "done"


# --- nội dung và chi phí của checkpoint ------------------------------------------------------------------------


async def test_checkpoints_say_running_and_the_final_files_say_done(tmp_path, monkeypatch):
    config, scenario, total = setup(tmp_path)
    _, _, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, after_calls=24)
    monkeypatch.undo()
    report = json.loads((out_1 / "report.json").read_text(encoding="utf-8"))
    truth = json.loads((out_1 / "truth_dump.json").read_text(encoding="utf-8"))
    assert report["status"] == "running" and report["story_finished"] is False
    assert truth["checkpoint"] is True and truth["final"] is None and truth["plan_progress"] is None

    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=OverlayStore("s2"), out=tmp_path / "ok")
    await run.run()
    final = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
    assert final.get("checkpoint") is not True and final["final"] is not None
    assert json.loads((out / "meta.json").read_text(encoding="utf-8"))["status"] == "done"


async def test_a_checkpoint_costs_a_bounded_number_of_writes_and_never_dumps_the_graph(tmp_path, monkeypatch):
    config, scenario, total = setup(tmp_path)
    writes: list[str] = []
    real = bench_run.write_atomic
    monkeypatch.setattr(bench_run, "write_atomic", lambda path, text: (writes.append(path.name), real(path, text))[1])
    run, _, _store, _out = make_run(tmp_path, config=config, scenario=scenario, store=OverlayStore("s"),
                                  out=tmp_path / "o")
    finals = {"graph": 0, "progress": 0}
    real_graph, real_progress = run._final_graph, run._plan_progress
    run._final_graph = lambda: (finals.__setitem__("graph", finals["graph"] + 1), real_graph())[1]
    run._plan_progress = lambda: (finals.__setitem__("progress", finals["progress"] + 1), real_progress())[1]
    assert await run.run() == bench_run.EXIT_OK
    # Chỉ `_finish` đọc đồ thị đầy đủ; checkpoint thì không (đồ thị cả truyện đọc mỗi chương là O(n^2) tiền kho).
    assert finals == {"graph": 1, "progress": 1}
    per_file = {name: writes.count(name) for name in set(writes)}
    chapters = total
    # Tối đa một checkpoint lúc khởi tạo, hai mỗi chương (lúc ghi chương và sau khi có lựa chọn), một lần cuối.
    assert per_file["truth_dump.json"] <= 1 + 2 * chapters + 1
    assert per_file["report.json"] == per_file["truth_dump.json"] == per_file["setup.json"]


async def test_a_resumed_run_killed_before_its_own_first_checkpoint_can_be_resumed_again(tmp_path, monkeypatch):
    """Lượt chạy tiếp sao chép phần cũ vào thư mục mới; nếu nó chết ngay trước checkpoint đầu thì thư mục mới vẫn phải
    chạy tiếp được (các lời gọi nó đã tiêu nằm ở calls.jsonl của nó)."""
    config, scenario, total = setup(tmp_path)
    _, store_a, _ = await straight(tmp_path, config, scenario, total)
    _, store, out_1 = await killed_run(tmp_path, config, scenario, total, monkeypatch, after_calls=31)
    monkeypatch.undo()
    first = len(rows(out_1 / "calls.jsonl"))
    run2, _, _, out_2 = make_run(tmp_path, config=config, scenario=scenario, store=store, out=tmp_path / "leg2",
                                 resume=out_1)
    arm_hard_kill(run2, after_calls=first + 3, monkeypatch=monkeypatch)
    with pytest.raises(Killed):
        await run2.run()
    monkeypatch.undo()
    assert len(rows(out_2 / "calls.jsonl")) == first + 3
    _run3, out_3, code = await resume(tmp_path, config, scenario, total, store, out_2, name="leg3")
    assert code == bench_run.EXIT_OK and packages(store) == packages(store_a)
    points = json.loads((out_3 / "meta.json").read_text(encoding="utf-8"))["resume_points"]
    assert [p["leg"] for p in points] == [2, 3]


async def test_a_checkpoint_writes_truth_dump_before_setup_and_report(tmp_path, monkeypatch):
    """Chết giữa ba file của một checkpoint thì truth_dump (gói chương, khớp kho) phải là file đã mới nhất: thứ tự
    ngược lại để truth_dump cũ, kho đi trước thư mục và `--resume` từ chối."""
    config, scenario, _total = setup(tmp_path)
    writes: list[str] = []
    real = bench_run.write_atomic
    monkeypatch.setattr(bench_run, "write_atomic", lambda path, text: (writes.append(path.name), real(path, text))[1])
    run, _, _, _ = make_run(tmp_path, config=config, scenario=scenario, store=OverlayStore("s"), out=tmp_path / "o")
    assert await run.run() == bench_run.EXIT_OK
    triple = [n for n in writes if n in ("truth_dump.json", "setup.json", "report.json")]
    first = [i for i, n in enumerate(triple) if n == "setup.json"]
    assert first and all(triple[i - 1] == "truth_dump.json" and triple[i + 1] == "report.json" for i in first[:-1])
    assert triple[0] == "truth_dump.json"
