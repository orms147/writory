"""Chạy migration SQL thuần trong db/migrations/ theo thứ tự tên file (D-20).

Mỗi file chạy đúng một lần; tên file (không đuôi) được ghi vào bảng schema_migrations.
Toàn bộ các file còn thiếu chạy trong một transaction, có khoá advisory để hai tiến trình
không chạy cùng lúc. Không có migration ngược: muốn sửa thì thêm file mới.
"""

from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
_LOCK_KEY = 7_274_301  # số bất kỳ, cố định, cho pg_advisory_xact_lock


def migration_files(directory: Path = MIGRATIONS_DIR) -> list[Path]:
    return sorted(directory.glob("*.sql"))


def migrate(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Áp các migration chưa chạy. Trả danh sách tên vừa áp (rỗng nếu đã cập nhật)."""
    applied_now: list[str] = []
    with conn.transaction():
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK_KEY,))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in migration_files(directory):
            if path.stem in done:
                continue
            conn.execute(path.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied_now.append(path.stem)
    return applied_now
