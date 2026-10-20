"""Tóm tắt chương (migration 0004, D-49): chữ máy chủ dùng nội bộ, không bao giờ ra API.

Lưu sau khi chương đã ghi; mỗi chương một bản, bản đầu được giữ. Thiếu tóm tắt thì chương sau vẫn
chạy, nên lỗi ở đây không được làm hỏng chương đã ghi (nơi gọi bắt lỗi và ghi log).
"""

from collections.abc import Sequence

import psycopg

from writory.graph.story import require_chapter, require_story_id


def save_chapter_summary(conn: psycopg.Connection, story_id: str, chapter: int, text: str) -> None:
    require_story_id(story_id)
    require_chapter(chapter)
    if chapter < 1 or not text.strip():
        raise ValueError("tóm tắt cần chương >= 1 và chữ không rỗng")
    conn.execute(
        "INSERT INTO chapter_summaries (story_id, chapter, summary) VALUES (%s, %s, %s) "
        "ON CONFLICT (story_id, chapter) DO NOTHING",
        (story_id, chapter, text),
    )


def load_chapter_summaries(
    conn: psycopg.Connection, story_id: str, chapters: Sequence[int]
) -> dict[int, str]:
    """Chương → tóm tắt, chỉ các chương có tóm tắt."""
    require_story_id(story_id)
    rows = conn.execute(
        "SELECT chapter, summary FROM chapter_summaries WHERE story_id = %s AND chapter = ANY(%s)",
        (story_id, list(chapters)),
    ).fetchall()
    return {chapter: summary for chapter, summary in rows}
