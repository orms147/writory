"""Kết nối Postgres cho app. Test và các hàm khác nhận kết nối qua tham số."""

import psycopg

from writory.config import Settings


def connect(settings: Settings) -> psycopg.Connection:
    """Kết nối ở chế độ autocommit: mỗi thao tác trong db/ tự mở transaction của nó."""
    return psycopg.connect(settings.postgres_dsn.get_secret_value(), autocommit=True)
