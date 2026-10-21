"""Test cần dịch vụ Docker (marker `graph`): Neo4j, và Postgres cho luồng ghi chương.
Kết nối lấy từ NEO4J_URI/USER/PASSWORD và POSTGRES_DSN, mặc định theo .env.example.

Postgres: test chạy trên database riêng `<tên>_test` (hoặc POSTGRES_TEST_DSN), tự tạo nếu chưa
có, để không đụng dữ liệu của app chạy trên máy (key người chơi dev, truyện đang chơi; D-75).
Neo4j Community chỉ có một database: mỗi test dùng story_id riêng và chỉ dọn story_id của mình."""

import os
import uuid

import psycopg
import pytest
from neo4j import GraphDatabase
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from writory.db import delete_story_record, migrate
from writory.graph import delete_story, ensure_schema, load_sample_story


@pytest.fixture(scope="session")
def driver():
    drv = GraphDatabase.driver(
        os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        auth=(
            os.environ.get("NEO4J_USER", "neo4j"),
            os.environ.get("NEO4J_PASSWORD", "change-me-local"),
        ),
    )
    drv.verify_connectivity()
    ensure_schema(drv)
    yield drv
    drv.close()


APP_DSN_DEFAULT = "postgresql://writory:change-me-local@localhost:5432/writory"


def test_dsn(app_dsn: str, explicit: str | None) -> str:
    """DSN của database test: POSTGRES_TEST_DSN nếu có, không thì tên database của app + `_test`."""
    if explicit:
        return explicit
    name = conninfo_to_dict(app_dsn).get("dbname") or "writory"
    return make_conninfo(app_dsn, dbname=name if name.endswith("_test") else f"{name}_test")


test_dsn.__test__ = False  # hàm thường, không phải test


def _ensure_database(dsn: str) -> None:
    name = conninfo_to_dict(dsn)["dbname"]
    with psycopg.connect(make_conninfo(dsn, dbname="postgres"), autocommit=True) as conn:
        if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone() is None:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


@pytest.fixture(scope="session", autouse=True)
def isolated_postgres():
    """Mọi test graph đọc POSTGRES_DSN từ môi trường (kể cả dependency của app và tiến trình con),
    nên đổi biến đó sang database test cho cả phiên pytest."""
    app_dsn = os.environ.get("POSTGRES_DSN", APP_DSN_DEFAULT)
    dsn = test_dsn(app_dsn, os.environ.get("POSTGRES_TEST_DSN"))
    assert conninfo_to_dict(dsn)["dbname"] != conninfo_to_dict(app_dsn).get("dbname"), (
        "database test trùng database của app")
    _ensure_database(dsn)
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("POSTGRES_DSN", dsn)
        yield dsn


@pytest.fixture(scope="session")
def pg(isolated_postgres):
    conn = psycopg.connect(isolated_postgres, autocommit=True)
    migrate(conn)
    yield conn
    conn.close()


def _story_ids():
    created: list[str] = []

    def make() -> str:
        sid = f"test-{uuid.uuid4().hex[:12]}"
        created.append(sid)
        return sid

    return created, make


@pytest.fixture
def new_story_id(driver):
    created, make = _story_ids()
    yield make
    for sid in created:
        delete_story(driver, sid)


@pytest.fixture
def new_db_story_id(driver, pg):
    """story_id mới; dọn cả Postgres lẫn Neo4j sau test."""
    created, make = _story_ids()
    yield make
    for sid in created:
        delete_story_record(pg, sid)
        delete_story(driver, sid)


@pytest.fixture(scope="module")
def sample_story_id(driver):
    sid = f"test-sample-{uuid.uuid4().hex[:12]}"
    load_sample_story(driver, sid)
    yield sid
    delete_story(driver, sid)
