"""Chặn trùng hàng xóm ở Python (D-117), không cần Neo4j: `read` giả trả dòng trùng như planner lỗi."""

from writory.graph.context import _neighbors


def row(id_: str, hops: int) -> dict:
    return {"id": id_, "kind": "Faction", "text": id_, "aliases": [], "hops": hops, "ua": False,
            "personality": None, "alive": None}


class FakeRead:
    def __init__(self, limited: list[dict], full: list[dict]) -> None:
        self.limited, self.full, self.calls = limited, full, []

    def __call__(self, query: str, **params):
        self.calls.append("LIMIT $limit" in query)
        return self.limited if "LIMIT $limit" in query else self.full


def test_duplicates_are_merged_keeping_the_smallest_hops_and_the_limit_counts_nodes(caplog):
    dup = [row("a", 2), row("a", 1), row("b", 1), row("b", 1), row("c", 2)]
    read = FakeRead(limited=dup[:3], full=dup)
    with caplog.at_level("WARNING"):
        out = _neighbors(read, 2, set(), 0)
    assert [(n.id, n.hops) for n in out] == [("a", 1), ("b", 1)]  # a=1, không phải a=2
    assert read.calls == [True, False]  # lần đầu có LIMIT, lần sau không giới hạn
    assert "3 dòng, 2 node" in caplog.text  # log chỉ ghi số, không ghi id


def test_clean_rows_cost_one_query_and_stay_in_order():
    read = FakeRead(limited=[row("a", 1), row("b", 2)], full=[])
    out = _neighbors(read, 5, set(), 0)
    assert [n.id for n in out] == ["a", "b"] and read.calls == [True]


def test_no_limit_means_no_limit_clause():
    read = FakeRead(limited=[], full=[row("a", 1)])
    assert [n.id for n in _neighbors(read, None, set(), 0)] == ["a"] and read.calls == [False]
