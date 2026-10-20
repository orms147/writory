"""Bộ đếm lời gọi model mỗi phút theo người chơi, trong Postgres (G8, D-56). Đồng hồ giả: không
sleep, không phụ thuộc giờ máy."""

import threading
import uuid

import pytest

from tests.api_fixtures import own_connections
from writory.db import take_llm_call

pytestmark = pytest.mark.graph

T0 = 1_800_000_000.0  # một thời điểm bất kỳ, chia hết cho 60 để dễ đọc


@pytest.fixture
def owner(pg):
    name = f"rl-{uuid.uuid4().hex[:10]}"
    yield name
    pg.execute("DELETE FROM llm_call_windows WHERE owner_id LIKE %s", (f"{name}%",))


def take(pg, owner, limit, now) -> bool:
    return take_llm_call(pg, owner, limit, now=now)


def test_allows_exactly_limit_calls_per_minute(pg, owner):
    assert [take(pg, owner, 3, T0 + i) for i in range(5)] == [True, True, True, False, False]


def test_rejected_calls_are_not_counted(pg, owner):
    for _ in range(6):
        take(pg, owner, 2, T0)
    (calls,) = pg.execute("SELECT calls FROM llm_call_windows WHERE owner_id = %s",
                          (owner,)).fetchone()
    assert calls == 2


def test_next_minute_starts_a_new_window(pg, owner):
    assert [take(pg, owner, 1, T0 + 59), take(pg, owner, 1, T0 + 59)] == [True, False]
    assert take(pg, owner, 1, T0 + 60) is True  # phút sau
    assert take(pg, owner, 1, T0 + 119.9) is False


def test_owners_are_counted_separately(pg, owner):
    assert take(pg, owner, 1, T0) is True
    assert take(pg, f"{owner}-b", 1, T0) is True
    assert take(pg, owner, 1, T0) is False


@pytest.mark.parametrize("limit", [0, -1])
def test_non_positive_limit_refuses_everything(pg, owner, limit):
    assert take(pg, owner, limit, T0) is False


def test_old_windows_are_pruned(pg, owner):
    take(pg, owner, 5, T0)
    take(pg, owner, 5, T0 + 60 * 30)
    rows = pg.execute("SELECT window_start FROM llm_call_windows WHERE owner_id = %s",
                      (owner,)).fetchall()
    assert [r[0] for r in rows] == [int((T0 + 60 * 30) // 60)]


def test_concurrent_calls_never_exceed_the_limit(owner):
    """16 kết nối cùng xin lượt trong một phút, trần 5: đúng 5 được. Kiểm và tăng là một câu lệnh."""
    results: list[bool] = []
    barrier = threading.Barrier(16)

    def worker() -> None:
        gen = own_connections()
        conn = next(gen)
        try:
            barrier.wait(timeout=30)
            results.append(take_llm_call(conn, owner, 5, now=T0))
        finally:
            gen.close()

    threads = [threading.Thread(target=worker) for _ in range(16)]
    [t.start() for t in threads]
    [t.join(timeout=60) for t in threads]
    assert sorted(results) == [False] * 11 + [True] * 5
