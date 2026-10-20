"""Giới hạn số lời gọi model mỗi phút theo người chơi, đếm trong Postgres (G8, D-56)."""

import psycopg

WINDOW_SECONDS = 60
KEEP_WINDOWS = 5  # cửa sổ cũ hơn thế này bị xoá khi đếm


def take_llm_call(conn: psycopg.Connection, owner_id: str, limit: int, *, now: float) -> bool:
    """Giữ một lượt gọi model của `owner_id` trong phút chứa `now` (giây kể từ epoch); trả False khi
    phút đó đã dùng đủ `limit`. `now` do nơi gọi đưa vào, để test dùng đồng hồ giả.

    Cửa sổ cố định: sát ranh giới hai phút có thể qua tới 2 × `limit` lời gọi trong 60 giây. Chấp
    nhận được cho mục đích chặn vòng lặp và lạm dụng, không phải để tính tiền (trần tiền ở
    CostTracker). Một câu lệnh kiểm và tăng cùng lúc, nên yêu cầu đồng thời không vượt `limit`;
    lượt từ chối không được đếm. Lượt đã giữ không trả lại khi lời gọi model sau đó lỗi.
    """
    if limit <= 0:
        return False
    window = int(now // WINDOW_SECONDS)
    row = conn.execute(
        "INSERT INTO llm_call_windows (owner_id, window_start, calls) VALUES (%s, %s, 1) "
        "ON CONFLICT (owner_id, window_start) DO UPDATE "
        "SET calls = llm_call_windows.calls + 1 "
        "WHERE llm_call_windows.calls < %s "
        "RETURNING calls",
        (owner_id, window, limit),
    ).fetchone()
    if row is not None:
        conn.execute(
            "DELETE FROM llm_call_windows WHERE owner_id = %s AND window_start < %s",
            (owner_id, window - KEEP_WINDOWS),
        )
    return row is not None
