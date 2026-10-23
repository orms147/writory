"""Khoá chống chạy đôi: một truyện chỉ một lần viết chương (cùng khoá với tạo lại lựa chọn và
phân loại ô tự viết), một truyện chỉ một câu hỏi người kể, một phiên khởi tạo chỉ một lần gọi
model (G8, D-46, D-56). Lần gọi thứ hai không chờ: báo STORY_BUSY ngay, để key người chơi không bị
trừ tiền hai lần.

Người kể có khoá riêng (`narrator`) vì hỏi người kể không mất lượt truyện (design §6.6): được hỏi
khi chương đang được viết, chỉ không được hỏi hai câu cùng lúc.

Cách làm: advisory lock mức phiên của Postgres (`pg_try_advisory_lock`) trên chính kết nối của yêu
cầu, giữ suốt việc. Nhả khi việc xong hoặc lỗi (`finally`), và Postgres tự nhả khi kết nối đóng,
kể cả khi tiến trình chết giữa chừng: không cần cột trạng thái hay hạn giờ. Khoá lồng được trên
cùng một kết nối, nên mỗi yêu cầu phải có kết nối riêng (`api/deps.get_pg_conn`).
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Literal

import psycopg

from writory.errors import ErrorCode, WritoryError
from writory.safety.redact import redact

log = logging.getLogger(__name__)

LockScope = Literal["story", "narrator", "setup"]


class StoryBusyError(WritoryError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(ErrorCode.STORY_BUSY, detail)


def _lock_name(scope: LockScope, key: str) -> str:
    return f"writory:{scope}:{key}"


@contextmanager
def job_lock(conn: psycopg.Connection, scope: LockScope, key: str) -> Iterator[None]:
    """Giữ khoá `scope:key` trên `conn` trong khối `with`. Đã có người giữ: StoryBusyError.

    Tên khoá băm ra số 64 bit (`hashtextextended`); hai tên trùng số thì lần sau báo bận nhầm,
    xác suất không đáng kể."""
    name = _lock_name(scope, key)
    row = conn.execute("SELECT pg_try_advisory_lock(hashtextextended(%s, 0))", (name,)).fetchone()
    if not row[0]:
        raise StoryBusyError(f"{scope} {key} đang chạy ở yêu cầu khác")
    try:
        yield
    finally:
        try:
            conn.execute("SELECT pg_advisory_unlock(hashtextextended(%s, 0))", (name,))
        except Exception as exc:  # noqa: BLE001 — kết nối hỏng: đóng nó là Postgres tự nhả
            log.warning("nhả khoá %s không được: %s", name, redact(f"{type(exc).__name__}: {exc}"))


def held_job_locks(conn: psycopg.Connection) -> int:
    """Số khoá chạy đôi đang được kết nối khác giữ: mỗi khoá là một việc đang gọi model (viết
    chương, tạo lại lựa chọn, ô tự viết, hỏi người kể, khởi tạo). Lệnh tắt server dùng để cảnh báo
    trước khi cắt ngang (`deploy/prod-down.ps1`, D-103). Chỉ đếm, không đọc tên truyện hay người."""
    row = conn.execute(
        "SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted "
        "AND pid <> pg_backend_pid()").fetchone()
    return int(row[0])


def main(*, conn: psycopg.Connection | None = None) -> int:
    """`python -m writory.db.locks`: in số việc đang chạy (một số nguyên), đọc `POSTGRES_DSN`."""
    if conn is not None:
        print(held_job_locks(conn))
        return 0
    from writory.config import Settings
    from writory.db.connection import connect

    with connect(Settings()) as own:
        print(held_job_locks(own))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
