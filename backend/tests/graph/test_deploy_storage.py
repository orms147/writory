"""Chồng prod trên Postgres và Neo4j thật (D-103): chuẩn bị kho lúc khởi động chạy lại được, và
đếm việc đang giữ khoá chạy đôi (D-46) cho lệnh tắt server (`deploy/prod-down.ps1`)."""

import io
import os
import uuid
from contextlib import redirect_stdout

import psycopg
import pytest
from pydantic import SecretStr

from tests.api_fixtures import dev_settings
from writory.api.app import prepare_storage
from writory.db import job_lock
from writory.db import locks as locks_cli
from writory.db.locks import held_job_locks
from writory.db.migrate import migration_files

pytestmark = pytest.mark.graph


def storage_settings(dsn: str):
    return dev_settings(dev=False).model_copy(update={
        "neo4j_uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.environ.get("NEO4J_USER", "neo4j"),
        "neo4j_password": SecretStr(
            os.environ.get("NEO4J_PASSWORD", "change-me-local")),
        "postgres_dsn": SecretStr(dsn),
    })


def test_prepare_storage_migrates_and_creates_constraints_and_can_run_again(pg, driver,
                                                                            isolated_postgres):
    settings = storage_settings(isolated_postgres)
    prepare_storage(settings)
    prepare_storage(settings)  # lần khởi động sau: không lỗi, không làm lại
    done = {row[0] for row in pg.execute("SELECT version FROM schema_migrations")}
    assert {p.stem for p in migration_files()} <= done
    names = {r["name"] for r in driver.execute_query("SHOW CONSTRAINTS").records}
    assert "entity_key" in names


def test_held_job_locks_counts_jobs_of_other_connections(pg, isolated_postgres):
    with psycopg.connect(isolated_postgres, autocommit=True) as checker:
        before = held_job_locks(checker)
        key = f"deploy-{uuid.uuid4().hex[:8]}"
        with job_lock(pg, "story", key):
            assert held_job_locks(checker) == before + 1
            with job_lock(pg, "narrator", key):
                assert held_job_locks(checker) == before + 2
        assert held_job_locks(checker) == before


def test_locks_cli_prints_only_the_count(pg, isolated_postgres):
    out = io.StringIO()
    with redirect_stdout(out), psycopg.connect(isolated_postgres, autocommit=True) as checker:
        before = held_job_locks(checker)
        with job_lock(pg, "story", f"deploy-{uuid.uuid4().hex[:8]}"):
            assert locks_cli.main(conn=checker) == 0
    assert out.getvalue().strip() == str(before + 1)
