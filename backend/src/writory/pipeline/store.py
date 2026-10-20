"""Kho truyện mà đường đi một chương đọc và ghi (D-36).

`ChapterStore` là giao thức; `GraphStore` cài trên Neo4j + Postgres bằng các hàm có sẵn của
`writory.graph` (Cypher chỉ nằm trong graph/, G10) và `writory.db` (ghi chương theo D-6). Test
nhanh dùng một kho trong bộ nhớ cùng giao thức (tests/pipeline_fixtures.py).

Mọi lần đọc là trạng thái ĐÃ COMMIT. Thay đổi của các cảnh trước trong chương đang viết chưa
nằm ở đây; pipeline phủ chúng lên bằng `OverlayState`.
"""

from collections.abc import Mapping, Sequence
from typing import Protocol

import psycopg
from neo4j import Driver

from writory.db import (
    chapter_records,
    commit_chapter,
    current_chapter,
    load_chapter_summaries,
    save_chapter_summary,
)
from writory.graph import ChangePackage, NodeRow, PlayerView, player_view, story_nodes
from writory.graph.context import PlanLike, WriterContext, writer_context
from writory.guard.state import GraphState, Neo4jState
from writory.pipeline.extract import Entity


class ChapterStore(Protocol):
    def committed_chapter(self) -> int | None:
        """Chương đã commit cuối (None = truyện chưa có chương 0)."""
        ...

    def has_pending(self) -> bool:
        """Truyện còn chương `pending` (D-6): chưa được viết chương mới."""
        ...

    def state(self) -> GraphState:
        """Đồ thị đã commit, cho người canh, bộ dò lộ và danh sách cạnh đang hiệu lực."""
        ...

    def catalogue(self) -> list[Entity]:
        """Mọi nút của truyện, làm danh mục thực thể cho bộ trích (G11: chỉ tham chiếu id có sẵn)."""
        ...

    def writer_context(
        self, as_of_chapter: int, present_ids: Sequence[str], plan: PlanLike | None, *,
        max_neighbors: int | None,
    ) -> WriterContext:
        """Ngữ cảnh lớp truth cho dàn ý và model viết (D-28)."""
        ...

    def commit(self, number: int, scenes: list[str], package: ChangePackage) -> None:
        """Ghi chương, tất cả hoặc không gì (D-6). Lỗi thì ném WritoryError, không ghi gì."""
        ...

    def player_view(self, chapter: int) -> PlayerView:
        """Lớp người chơi biết ở chương đã commit (G1)."""
        ...

    def summaries(self, chapters: Sequence[int]) -> dict[int, str]:
        """Tóm tắt đã lưu của các chương này (D-49); chương thiếu thì không có khoá."""
        ...

    def save_summary(self, chapter: int, text: str) -> None:
        """Lưu tóm tắt của chương đã ghi. Đã có thì giữ bản cũ."""
        ...


def entities_from_rows(rows: Mapping[str, NodeRow]) -> list[Entity]:
    return [Entity.from_node(nid, row.label, row.props) for nid, row in sorted(rows.items())]


class GraphStore:
    """Neo4j + Postgres. `conn` ở chế độ autocommit (writory.db.connect)."""

    def __init__(self, conn: psycopg.Connection, driver: Driver, story_id: str) -> None:
        self._conn = conn
        self._driver = driver
        self._story_id = story_id

    def committed_chapter(self) -> int | None:
        return current_chapter(self._conn, self._story_id)

    def has_pending(self) -> bool:
        return any(r.status == "pending" for r in chapter_records(self._conn, self._story_id))

    def state(self) -> GraphState:
        return Neo4jState(self._driver, self._story_id)

    def catalogue(self) -> list[Entity]:
        return entities_from_rows(story_nodes(self._driver, self._story_id))

    def writer_context(self, as_of_chapter, present_ids, plan, *, max_neighbors) -> WriterContext:
        return writer_context(self._driver, self._story_id, as_of_chapter, present_ids, plan,
                              max_neighbors=max_neighbors)

    def commit(self, number: int, scenes: list[str], package: ChangePackage) -> None:
        commit_chapter(self._conn, self._driver, self._story_id, number, scenes, package)

    def player_view(self, chapter: int) -> PlayerView:
        return player_view(self._driver, self._story_id, chapter)

    def summaries(self, chapters: Sequence[int]) -> dict[int, str]:
        return load_chapter_summaries(self._conn, self._story_id, chapters)

    def save_summary(self, chapter: int, text: str) -> None:
        save_chapter_summary(self._conn, self._story_id, chapter, text)
