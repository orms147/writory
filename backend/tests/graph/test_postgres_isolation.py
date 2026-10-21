"""Test graph không bao giờ chạm database của app trên máy (D-75).

Hồi quy 21/10/2026: test graph và app dùng chung database `writory`; test xoá và ghi đè key của
người chơi dev, nên key người chơi dán vào app trên máy bị mất mỗi khi có ai chạy test.
"""

import os

import pytest
from psycopg.conninfo import conninfo_to_dict

from tests.graph.conftest import APP_DSN_DEFAULT, test_dsn

pytestmark = pytest.mark.graph


def test_test_database_name_is_derived_from_the_app_database():
    assert conninfo_to_dict(test_dsn(APP_DSN_DEFAULT, None))["dbname"] == "writory_test"
    explicit = "postgresql://u:p@h:5432/khac_test"
    assert test_dsn(APP_DSN_DEFAULT, explicit) == explicit


def test_graph_tests_run_on_the_test_database(pg, isolated_postgres):
    assert pg.execute("SELECT current_database()").fetchone()[0].endswith("_test")
    assert conninfo_to_dict(os.environ["POSTGRES_DSN"])["dbname"].endswith("_test")
    assert os.environ["POSTGRES_DSN"] == isolated_postgres
