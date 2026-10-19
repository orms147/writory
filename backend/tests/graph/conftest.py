"""Test đồ thị: cần Neo4j (docker compose up -d). Kết nối lấy từ NEO4J_URI/USER/PASSWORD,
mặc định theo .env.example. Database dùng chung, nên mỗi test dùng story_id riêng và chỉ dọn
story_id của mình."""

import os
import uuid

import pytest
from neo4j import GraphDatabase

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


@pytest.fixture
def new_story_id(driver):
    created: list[str] = []

    def make() -> str:
        sid = f"test-{uuid.uuid4().hex[:12]}"
        created.append(sid)
        return sid

    yield make
    for sid in created:
        delete_story(driver, sid)


@pytest.fixture(scope="module")
def sample_story_id(driver):
    sid = f"test-sample-{uuid.uuid4().hex[:12]}"
    load_sample_story(driver, sid)
    yield sid
    delete_story(driver, sid)
