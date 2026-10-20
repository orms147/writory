"""Dependency của API (D-41). Test thay từng hàm qua `app.dependency_overrides`.

Hàm đọc dữ liệu là `def` thường: FastAPI chạy chúng trong threadpool, nên driver Neo4j và
psycopg (đồng bộ) không chặn event loop. Mặc định nào chưa làm được thì fail closed.
"""

import asyncio
from collections.abc import Iterator, Mapping
from typing import Annotated

import psycopg
from fastapi import Depends, Request
from neo4j import Driver

from writory.config import AppConfig
from writory.db import committed_player_view, connect, take_narrator_question
from writory.errors import ErrorCode, WritoryError
from writory.graph import PlayerView, named_nodes
from writory.llm.cost import MeteredClient
from writory.pipeline.narrator import NarratorQuota
from writory.pipeline.story_plan import StoryPlan


def get_app_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_pg_conn(request: Request) -> Iterator[psycopg.Connection]:
    """Một kết nối Postgres (autocommit) cho mỗi request; đóng sau khi trả lời."""
    conn = connect(request.app.state.settings)
    try:
        yield conn
    finally:
        conn.close()


def get_neo4j_driver(request: Request) -> Driver:
    driver = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise RuntimeError("app chưa có Neo4j driver")  # lỗi cấu hình app → INTERNAL_ERROR
    return driver


PgConn = Annotated[psycopg.Connection, Depends(get_pg_conn)]
Neo4jDriver = Annotated[Driver, Depends(get_neo4j_driver)]


def get_player_view(story_id: str, conn: PgConn, driver: Neo4jDriver) -> PlayerView:
    """player_view ở chương đã commit (D-6). Truyện không có → STORY_NOT_FOUND (404).
    TODO(G10, tuần 5): kiểm truyện thuộc người đang đăng nhập; chưa có đăng nhập nên router
    chỉ mount khi bật `enable_dev_routes` (D-41)."""
    return committed_player_view(conn, driver, story_id)


def get_truth_names(story_id: str, driver: Neo4jDriver) -> Mapping[str, tuple[str, ...]]:
    """Tên lớp truth, CHỈ cho bộ dò lộ (G2). Không bao giờ đưa vào phản hồi hay context model."""
    return named_nodes(driver, story_id)


def get_story_plan(story_id: str) -> StoryPlan:
    """TODO(pipeline): chưa có nơi lưu `story_plan`. Fail closed: không có kế hoạch thì không
    chạy đủ bộ dò lộ (G2), nên không trả lời."""
    raise NotImplementedError("chưa có nơi lưu story_plan")


def get_narrator_llm(story_id: str) -> MeteredClient:
    """TODO(tuần 5): giải mã key OpenRouter của người chơi (`safety.crypto`), dựng
    `MeteredClient(OpenRouterClient(key), CostTracker(config.limits.cost_usd,
    story_spent_usd=<nhật ký chi phí>))`. Chưa có nơi lưu key nên báo thiếu key, không bao giờ
    dùng key của chủ dự án."""
    raise WritoryError(ErrorCode.PLAYER_KEY_MISSING, detail="chưa có nơi lưu key người chơi")


class PostgresNarratorQuota:
    """Bộ đếm câu hỏi người kể trong Postgres (`db.take_narrator_question`)."""

    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    async def take(self, story_id: str, chapter: int, limit: int) -> bool:
        return await asyncio.to_thread(take_narrator_question, self._conn, story_id, chapter,
                                       limit)


def get_narrator_quota(conn: PgConn) -> NarratorQuota:
    return PostgresNarratorQuota(conn)
