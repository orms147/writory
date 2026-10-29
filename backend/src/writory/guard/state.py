"""Trạng thái đồ thị mà người canh đọc: nền đã commit + các gói chưa ghi của chương đang viết.

- `Neo4jState`: nền đã commit, đọc qua lớp graph/ (G10: Cypher chỉ nằm trong graph/).
- `OverlayState`: phủ các gói (ChangePackage) lên một nền, cùng nghĩa "ở chương N" với graph/:
  cạnh hiệu lực khi valid_from <= N và (valid_to rỗng hoặc > N); `close` trong gói đóng cả cạnh
  của nền. Phủ lên `EmptyState` thì dựng được trạng thái từ gói thuần, không cần Neo4j
  (test so với Neo4j: tests/graph/test_guard_state_parity.py).
- `player_view_of`: player_view trên một GraphState, qua đúng định nghĩa duy nhất
  `graph.build_player_view` (G1, D-16).
"""

from collections.abc import Sequence
from typing import Protocol

from neo4j import Driver

from writory.graph import (
    ChangePackage,
    EdgeRow,
    KnownRecord,
    LieRecord,
    NodeRow,
    PlayerView,
    build_player_view,
    edges_at,
    named_nodes,
    node_labels,
    node_rows,
    protagonist_id,
    story_nodes,
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
        ever: bool = False,
    ) -> list[EdgeRow]:
        """`ever=True`: mọi cạnh đã mở tới chương N, kể cả đã đóng."""
        ...

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]: ...

    def nodes(self, ids: Sequence[str]) -> dict[str, NodeRow]: ...

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        """id → (name, *aliases) của lớp truth, cho bộ dò lộ (G2)."""
        ...

    def protagonist_id(self) -> str: ...

    def all_nodes(self) -> dict[str, NodeRow]:
        """Mọi nút của truyện (id → nhãn loại + thuộc tính của truyện), lớp truth. Cho bộ xuất kịch bản
        video (D-123), không cho đường người chơi."""
        ...


def _check_type(edge_type: str) -> None:
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"kiểu cạnh không hợp lệ: {edge_type!r}")


class Neo4jState:
    def __init__(self, driver: Driver, story_id: str) -> None:
        self._driver = driver
        self._story_id = story_id

    def edges_at(self, edge_type, chapter, *, source_id=None, target_id=None,
                 ever=False) -> list[EdgeRow]:
        return edges_at(
            self._driver, self._story_id, edge_type, chapter,
            source_id=source_id, target_id=target_id, ever=ever,
        )

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]:
        return node_labels(self._driver, self._story_id, list(ids))

    def nodes(self, ids: Sequence[str]) -> dict[str, NodeRow]:
        return node_rows(self._driver, self._story_id, list(ids))

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        return named_nodes(self._driver, self._story_id)

    def protagonist_id(self) -> str:
        return protagonist_id(self._driver, self._story_id)

    def all_nodes(self) -> dict[str, NodeRow]:
        return story_nodes(self._driver, self._story_id)


class EmptyState:
    def edges_at(self, edge_type, chapter, *, source_id=None, target_id=None,
                 ever=False) -> list[EdgeRow]:
        _check_type(edge_type)
        return []

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]:
        return {}

    def nodes(self, ids: Sequence[str]) -> dict[str, NodeRow]:
        return {}

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        return {}

    def protagonist_id(self) -> str:
        raise LookupError("trạng thái rỗng: chưa có nhân vật chính")

    def all_nodes(self) -> dict[str, NodeRow]:
        return {}


def _valid_at(valid_from: int, valid_to: int | None, chapter: int) -> bool:
    return valid_from <= chapter and (valid_to is None or valid_to > chapter)


class OverlayState:
    def __init__(self, base: GraphState, packages: Sequence[ChangePackage]) -> None:
        self._base = base
        self._nodes: dict[str, NodeRow] = {}
        self._protagonist: str | None = None
        self._names: dict[str, tuple[str, ...]] = {}
        self._closes: dict[str, int] = {}
        specs = []
        for pkg in packages:
            for node in pkg.nodes:
                props = {k: v for k, v in node.props.items() if v is not None}
                self._nodes[node.id] = NodeRow(node.label, props)
                if props.get("is_protagonist") is True:
                    self._protagonist = node.id
                if node.label in NAMED_LABELS:
                    self._names[node.id] = (props["name"], *(props.get("aliases") or []))
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

    def edges_at(self, edge_type, chapter, *, source_id=None, target_id=None,
                 ever=False) -> list[EdgeRow]:
        _check_type(edge_type)

        def wanted(r: EdgeRow) -> bool:
            return (source_id is None or r.source == source_id) and (
                target_id is None or r.target == target_id
            )

        def current(valid_from: int, valid_to: int | None) -> bool:
            return valid_from <= chapter if ever else _valid_at(valid_from, valid_to, chapter)

        base = [
            EdgeRow(r.id, r.type, r.source, r.target, r.valid_from_chapter,
                    self._closes.get(r.id, r.valid_to_chapter), r.props)
            for r in self._base.edges_at(
                edge_type, chapter, source_id=source_id, target_id=target_id, ever=ever
            )
        ]
        base = [r for r in base if current(r.valid_from_chapter, r.valid_to_chapter)]
        own = [
            r for r in self._edges
            if r.type == edge_type and wanted(r)
            and current(r.valid_from_chapter, r.valid_to_chapter)
        ]
        return sorted(base + own, key=lambda r: r.id)

    def nodes(self, ids: Sequence[str]) -> dict[str, NodeRow]:
        found = {i: self._nodes[i] for i in ids if i in self._nodes}
        rest = [i for i in ids if i not in found]
        return found | (self._base.nodes(rest) if rest else {})

    def node_labels(self, ids: Sequence[str]) -> dict[str, str]:
        found = {i: self._nodes[i].label for i in ids if i in self._nodes}
        rest = [i for i in ids if i not in found]
        return found | (self._base.node_labels(rest) if rest else {})

    def named_nodes(self) -> dict[str, tuple[str, ...]]:
        return dict(sorted((self._base.named_nodes() | self._names).items()))

    def protagonist_id(self) -> str:
        return self._protagonist or self._base.protagonist_id()

    def all_nodes(self) -> dict[str, NodeRow]:
        return dict(sorted((self._base.all_nodes() | self._nodes).items()))


def player_view_of(state: GraphState, chapter: int, *, story_id: str = "") -> PlayerView:
    """player_view ở chương N trên một GraphState: gom đúng các bản ghi mà graph.player_view
    đọc từ Neo4j, rồi gọi định nghĩa duy nhất `build_player_view`."""
    try:
        protagonist: str | None = state.protagonist_id()
    except LookupError:
        protagonist = None
    reveals = [(e.source, e) for e in state.edges_at("REVEALED_TO_PLAYER", chapter, ever=True)]
    if protagonist:
        reveals += [
            (e.target, e)
            for e in state.edges_at("KNOWS", chapter, source_id=protagonist, ever=True)
        ]
    lies_told = (
        state.edges_at("TOLD", chapter, source_id=protagonist, ever=True) if protagonist else []
    )
    rows = state.nodes(sorted({n for n, _ in reveals} | {e.target for e in lies_told}))
    known = [
        KnownRecord(node, (rows[node].label,), rows[node].props, e.id, e.valid_from_chapter,
                    e.props.get("quote"), e.props.get("known_as"))
        for node, e in reveals if node in rows
    ]
    about = [(e.source, e.target) for e in state.edges_at("ABOUT", chapter, ever=True)]
    lies = []
    for told in lies_told:
        lie = rows.get(told.target)
        hearers = state.edges_at("TOLD_TO", chapter, source_id=told.target, ever=True)
        if lie is None or lie.label != "Lie" or not hearers:
            continue
        lies.append(LieRecord(told.target, lie.props.get("content", ""), lie.props.get("chapter"),
                              tuple(h.target for h in hearers)))
    return build_player_view(story_id, chapter, known, about, lies)
