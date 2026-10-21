"""Đếm câu hỏi người kể theo truyện và chương trong Postgres (G8, D-40, D-66)."""

import psycopg

from writory.db.chapters import StoryNotFoundError
from writory.graph.story import require_chapter, require_story_id


def take_narrator_question(
    conn: psycopg.Connection, story_id: str, chapter: int, limit: int
) -> bool:
    """Giữ một lượt hỏi ở chương `chapter` nếu còn lượt; trả False khi đã dùng đủ `limit`.

    Một câu lệnh: kiểm và tăng cùng lúc, nên hai yêu cầu đồng thời không vượt được `limit`.
    Lượt đã giữ không trả lại, kể cả khi lời gọi model sau đó lỗi (D-40)."""
    require_story_id(story_id)
    require_chapter(chapter)
    if limit <= 0:
        return False
    try:
        row = conn.execute(
            "INSERT INTO narrator_questions (story_id, chapter, asked) VALUES (%s, %s, 1) "
            "ON CONFLICT (story_id, chapter) DO UPDATE "
            "SET asked = narrator_questions.asked + 1, updated_at = now() "
            "WHERE narrator_questions.asked < %s "
            "RETURNING asked",
            (story_id, chapter, limit),
        ).fetchone()
    except psycopg.errors.ForeignKeyViolation as exc:
        raise StoryNotFoundError(f"không có truyện {story_id}") from exc
    return row is not None


def narrator_questions_asked(conn: psycopg.Connection, story_id: str, chapter: int) -> int:
    """Số lượt đã giữ ở chương `chapter` (0 khi chưa hỏi câu nào), để báo số câu còn lại."""
    require_story_id(story_id)
    require_chapter(chapter)
    row = conn.execute(
        "SELECT asked FROM narrator_questions WHERE story_id = %s AND chapter = %s",
        (story_id, chapter),
    ).fetchone()
    return 0 if row is None else row[0]
