"""Trạng thái đồ thị mà người canh đọc: nền đã commit + các gói chưa ghi của chương đang viết.

- `Neo4jState`: nền đã commit, đọc qua lớp graph/ (G10: Cypher chỉ nằm trong graph/).
- `OverlayState`: phủ các gói (ChangePackage) lên một nền, cùng nghĩa "ở chương N" với graph/:
  cạnh hiệu lực khi valid_from <= N và (valid_to rỗng hoặc > N); `close` trong gói đóng cả cạnh
  của nền. Phủ lên `EmptyState` thì dựng được trạng thái từ gói thuần, không cần Neo4j
  (test so với Neo4j: tests/graph/test_guard_state_parity.py).
"""

from collections.abc import Sequence
from typing import Protocol

from neo4j import Driver

from writory.graph import (
    ChangePackage,
    EdgeRow,
    edges_at,
    named_nodes,
    node_labels,
    protagonist_id,
)
from writory.graph.schema import EDGE_TYPES, NAMED_LABELS


class GraphState(Protocol):
    def edges_at(
        self,
        edge_type: str,
        chapter: int,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> list[EdgeRow]: ...

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]: ...

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        """id → (name, *aliases) của lớp truth, cho bộ dò lộ (G2)."""
        ...

    def protagonist_id(self) -> str: ...


def _check_type(edge_type: str) -> None:
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"kiểu cạnh không hợp lệ: {edge_type!r}")


class Neo4jState:
    def __init__(self, driver: Driver, story_id: str) -> None:
        self._driver = driver
        self._story_id = story_id

    def edges_at(self, edge_type, chapter, *, source_id=None, target_id=None) -> list[EdgeRow]:
        return edges_at(
            self._driver, self._story_id, edge_type, chapter,
            source_id=source_id, target_id=target_id,
        )

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]:
        return node_labels(self._driver, self._story_id, list(ids))

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        return named_nodes(self._driver, self._story_id)

    def protagonist_id(self) -> str:
        return protagonist_id(self._driver, self._story_id)


class EmptyState:
    def edges_at(self, edge_type, chapter, *, source_id=None, target_id=None) -> list[EdgeRow]:
        _check_type(edge_type)
        return []

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]:
        return {}

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        return {}

    def protagonist_id(self) -> str:
        raise LookupError("trạng thái rỗng: chưa có nhân vật chính")


def _valid_at(valid_from: int, valid_to: int | None, chapter: int) -> bool:
    return valid_from <= chapter and (valid_to is None or valid_to > chapter)


class OverlayState:
    def __init__(self, base: GraphState, packages: Sequence[ChangePackage]) -> None:
        self._base = base
        self._labels: dict[str, str] = {}
        self._protagonist: str | None = None
        self._names: dict[str, tuple[str, ...]] = {}
        self._closes: dict[str, int] = {}
        specs = []
        for pkg in packages:
            for node in pkg.nodes:
                self._labels[node.id] = node.label
                if node.props.get("is_protagonist") is True:
                    self._protagonist = node.id
                if node.label in NAMED_LABELS:
                    self._names[node.id] = (node.props["name"], *(node.props.get("aliases") or []))
            specs.extend(pkg.edges)
            self._closes.update({c.id: c.valid_to_chapter for c in pkg.close})
        self._edges = [
            EdgeRow(
                e.id, e.type, e.source, e.target, e.valid_from_chapter,
                e.valid_to_chapter if e.valid_to_chapter is not None else self._closes.get(e.id),
                {k: v for k, v in e.props.items() if v is not None},
            )
            for e in specs
        ]

    def edges_at(self, edge_type, chapter, *, source_id=None, target_id=None) -> list[EdgeRow]:
        _check_type(edge_type)

        def wanted(r: EdgeRow) -> bool:
            return (source_id is None or r.source == source_id) and (
                target_id is None or r.target == target_id
            )

        base = [
            r for r in self._base.edges_at(
                edge_type, chapter, source_id=source_id, target_id=target_id
            )
            if not (r.id in self._closes and self._closes[r.id] <= chapter)
        ]
        base = [
            EdgeRow(r.id, r.type, r.source, r.target, r.valid_from_chapter,
                    self._closes.get(r.id, r.valid_to_chapter), r.props)
            for r in base
        ]
        own = [
            r for r in self._edges
            if r.type == edge_type and wanted(r)
            and _valid_at(r.valid_from_chapter, r.valid_to_chapter, chapter)
        ]
        return sorted(base + own, key=lambda r: r.id)

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]:
        found = {i: self._labels[i] for i in ids if i in self._labels}
        rest = [i for i in ids if i not in found]
        return found | (self._base.node_labels(rest) if rest else {})

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        return dict(sorted((self._base.named_nodes() | self._names).items()))

    def protagonist_id(self) -> str:
        return self._protagonist or self._base.protagonist_id()
