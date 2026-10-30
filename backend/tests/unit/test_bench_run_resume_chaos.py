"""Chạy tiếp qua nhiều lượt chết ở những chỗ khác nhau (D-124, D-130): mọi cách dừng rồi chạy tiếp phải về
đúng kết quả chạy liền, số thứ tự lời gọi không trùng, và tiền đã tiêu cộng đúng. Model giả, kho trong bộ nhớ."""

import json

import pytest

from tests.pipeline_fixtures import OverlayStore
from tests.unit.test_bench_run_resume import packages, picks, setup
from tests.unit.test_pipeline_bench_run import make_run, rows
from writory.config import ConfigError
from writory.errors import ErrorCode, WritoryError
from writory.pipeline import bench_run
from writory.pipeline.bench_run import DryRunLLM, spent_usd_of


class DiesAtCall(DryRunLLM):
    """Gọi thứ `at` (tính cả lời gọi sau) trở đi lỗi không thử lại được: mạng đứt cho cả lượt."""

    def __init__(self, total, *, at, **kw):
        super().__init__(total, **kw)
        self.at, self.count = at, 0

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        self.count += 1
        if self.count >= self.at:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail="giả: đứt mạng")
        return await super().chat(model, messages, response_schema=response_schema, extra=extra)


async def straight_run(tmp_path, config, scenario):
    run, _, store, out = make_run(tmp_path, config=config, scenario=scenario,
                                  store=OverlayStore("s"), out=tmp_path / "straight")
    assert await run.run() == bench_run.EXIT_OK
    return run, store, out


async def chain(tmp_path, config, scenario, total, cuts):
    """Lượt 1 chết ở lời gọi cuts[0], mỗi lượt sau chạy tiếp từ lượt liền trước và chết ở cuts[i]; lượt cuối
    không chết. Trả (danh sách (run, out), store) hoặc None nếu một lượt chạy tiếp bị từ chối (ví dụ lượt
    trước chưa khởi tạo xong)."""
    store = OverlayStore("s")
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=store,
                              out=tmp_path / "leg1", llm=DiesAtCall(total, at=cuts[0]))
    await run.run()
    legs = [(run, out)]
    for i, at in enumerate([*cuts[1:], None], start=2):
        llm = DiesAtCall(total, at=at) if at is not None else None
        nxt, _, _, nxt_out = make_run(tmp_path, config=config, scenario=scenario, store=store,
                                      out=tmp_path / f"leg{i}", resume=legs[-1][1], llm=llm)
        try:
            await nxt.run()
        except ConfigError as e:
            return str(e)
        legs.append((nxt, nxt_out))
    return legs, store


def combos():
    """Vài điểm chết đại diện (mỗi chương khoảng 11 lời gọi sau 4 lời gọi khởi tạo); bản đầy đủ hơn
    (9 điểm đầu x 6 điểm sau x 3 điểm thứ ba) đã chạy một lần khi review và đều xanh."""
    yield from ((a,) for a in (14, 20, 30, 38))
    yield from ((17, 4), (26, 7), (30, 2), (20, 11), (38, 1))
    yield from ((14, 4, 2), (30, 7, 4), (38, 1, 2), (20, 2, 4))


@pytest.mark.parametrize("cuts", list(combos()), ids=lambda c: "-".join(map(str, c)))
async def test_any_chain_of_failed_legs_ends_where_a_straight_run_ends(tmp_path, cuts):
    config, scenario, total = setup(tmp_path)
    _, store_a, out_a = await straight_run(tmp_path, config, scenario)
    built = await chain(tmp_path, config, scenario, total, cuts)
    if isinstance(built, str):
        pytest.skip(built[:300])
    legs, store = built
    last_run, last_out = legs[-1]

    assert store.committed == total and last_run.finished
    assert packages(store) == packages(store_a)
    assert picks(last_out) == picks(out_a)

    calls = rows(last_out / "calls.jsonl")
    seqs = [c["seq"] for c in calls]
    assert seqs == list(range(1, len(seqs) + 1)), "số thứ tự lời gọi phải liền và không trùng"
    assert last_run.budgeted.spent_usd == pytest.approx(spent_usd_of(calls))

    report = json.loads((last_out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "done" and report["story_finished"] is True
    assert report["cost"]["total_usd"] == pytest.approx(
        sum(c.get("cost_usd") or 0.0 for c in calls))
    meta = json.loads((last_out / "meta.json").read_text(encoding="utf-8"))
    points = meta.get("resume_points") or []
    assert [p["leg"] for p in points] == list(range(2, len(legs) + 1))
    spent_before = [p["spent_usd_before"] for p in points]
    assert spent_before == sorted(spent_before)

    # Mỗi chương đã ghi đúng một lần `choice_picked`, kể cả chương mà lượt trước ghi xong mà chưa có lựa chọn.
    events = rows(last_out / "events.jsonl")
    chosen = [e["chapter"] for e in events if e.get("type") == "choice_picked"]
    assert chosen == sorted(set(chosen))

    # Số lượt thử của từng chương nối tiếp nhau, không trùng số.
    for chapter in range(1, total + 1):
        numbers = [a["attempt"] for a in last_run.attempts if a["chapter"] == chapter]
        assert numbers == sorted(set(numbers)), (chapter, numbers)


# --- trần --budget cộng dồn qua các lượt ------------------------------------------------------------


@pytest.mark.parametrize("fractions", [(0.45, 3), (0.45, 0.7, 0.95, 4)])
async def test_the_total_cap_holds_in_every_leg_and_the_chain_still_ends_like_a_straight_run(
        tmp_path, fractions):
    config, scenario, total = setup(tmp_path)
    run_a, _, store_a, out_a = make_run(
        tmp_path, config=config, scenario=scenario, store=OverlayStore("s"), out=tmp_path / "straight",
        llm=DryRunLLM(total, cost_usd=0.01))
    assert await run_a.run() == bench_run.EXIT_OK
    whole = spent_usd_of(rows(out_a / "calls.jsonl"))
    store = OverlayStore("s")
    source = None
    for i, share in enumerate(fractions, start=1):
        cap = round(whole * share, 6)
        extra = {"resume": source} if source else {}
        run, _, _, out = make_run(tmp_path, config=config, scenario=scenario, store=store,
                                  out=tmp_path / f"cap{i}", budget_usd=cap,
                                  llm=DryRunLLM(total, cost_usd=0.01), **extra)
        try:
            await run.run()
        except ConfigError as e:
            pytest.skip(str(e)[:200])
        calls = rows(out / "calls.jsonl")
        assert run.budgeted.spent_usd <= cap + 1e-9, (i, run.budgeted.spent_usd, cap)
        assert run.budgeted.spent_usd == pytest.approx(spent_usd_of(calls))
        seqs = [c["seq"] for c in calls]
        assert seqs == list(range(1, len(seqs) + 1))
        source = out
    assert store.committed == total and run.finished
    assert packages(store) == packages(store_a)
