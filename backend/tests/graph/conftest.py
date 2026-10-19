"""Test cần dịch vụ Docker (marker `graph`): Neo4j, và Postgres cho luồng ghi chương.
Kết nối lấy từ NEO4J_URI/USER/PASSWORD và POSTGRES_DSN, mặc định theo .env.example.
Database dùng chung, nên mỗi test dùng story_id riêng và chỉ dọn story_id của mình."""

import os
import uuid

import psycopg
import pytest
from neo4j import GraphDatabase

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


@pytest.fixture(scope="session")
def pg():
    conn = psycopg.connect(
        os.environ.get(
            "POSTGRES_DSN", "postgresql://writory:change-me-local@localhost:5432/writory"
        ),
        autocommit=True,
    )
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
