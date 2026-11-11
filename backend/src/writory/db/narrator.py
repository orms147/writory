"""Đếm câu hỏi người kể theo truyện và chương trong Postgres (G8, D-40, D-66), và lưu các lượt
hỏi đáp đã xong (D-162)."""

from collections.abc import Iterable
from dataclasses import dataclass

import psycopg

from writory.db.chapters import StoryNotFoundError
from writory.graph.story import require_chapter, require_story_id


def take_narrator_question(
    conn: psycopg.Connection, story_id: str, chapter: int, limit: int
) -> bool:
    """Giữ một lượt hỏi ở chương `chapter` nếu còn lượt; trả False khi đã dùng đủ `limit`.

    Một câu lệnh: kiểm và tăng cùng lúc, nên hai yêu cầu đồng thời không vượt được `limit`.
    Lượt đã giữ không trả lại, kể cả khi lời gọi model sau đó lỗi (D-40); chỉ câu trả lời bị kiểm
    duyệt chặn mới trả lại lượt (`release_narrator_question`, D-137)."""
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


def release_narrator_question(conn: psycopg.Connection, story_id: str, chapter: int) -> None:
    """Trả lại một lượt đã giữ ở chương `chapter`, không xuống dưới 0. Chỉ cho câu trả lời người
    kể bị kiểm duyệt chặn (G9, D-137): câu hỏi của người chơi không có lỗi, như câu hỏi bị chặn
    không mất lượt (D-57). Một câu lệnh; chương chưa hỏi câu nào thì không có gì để trả."""
    require_story_id(story_id)
    require_chapter(chapter)
    conn.execute(
        "UPDATE narrator_questions SET asked = asked - 1, updated_at = now() "
        "WHERE story_id = %s AND chapter = %s AND asked > 0",
        (story_id, chapter),
    )


def narrator_questions_asked(conn: psycopg.Connection, story_id: str, chapter: int) -> int:
    """Số lượt đã giữ ở chương `chapter` (0 khi chưa hỏi câu nào), để báo số câu còn lại."""
    require_story_id(story_id)
    require_chapter(chapter)
    row = conn.execute(
        "SELECT asked FROM narrator_questions WHERE story_id = %s AND chapter = %s",
        (story_id, chapter),
    ).fetchone()
    return 0 if row is None else row[0]


@dataclass(frozen=True)
class NarratorTurnRow:
    """Một lượt hỏi đáp đã lưu (D-162): câu người chơi hỏi, đúng chữ đã hiện, chương nguồn đã hiện."""

    question: str
    answer: str
    source_chapters: tuple[int, ...] = ()


def add_narrator_turn(conn: psycopg.Connection, story_id: str, chapter: int, question: str,
                      answer: str, source_chapters: Iterable[int]) -> None:
    """Ghi một lượt hỏi đáp đã xong ở chương `chapter`. Chỉ gọi sau khi câu trả lời đã qua mọi phép
    kiểm và sắp hiện (G11): `answer` là đúng chữ người chơi thấy, không phải câu thô của model."""
    require_story_id(story_id)
    require_chapter(chapter)
    try:
        conn.execute(
            "INSERT INTO narrator_turns (story_id, chapter, question, answer, source_chapters) "
            "VALUES (%s, %s, %s, %s, %s)",
            (story_id, chapter, question, answer, sorted(set(source_chapters))),
        )
    except psycopg.errors.ForeignKeyViolation as exc:
        raise StoryNotFoundError(f"không có truyện {story_id}") from exc


def narrator_turns(conn: psycopg.Connection, story_id: str, chapter: int) -> list[NarratorTurnRow]:
    """Các lượt hỏi đáp của chương `chapter`, cũ trước. Luôn lọc theo truyện (G10)."""
    require_story_id(story_id)
    require_chapter(chapter)
    rows = conn.execute(
        "SELECT question, answer, source_chapters FROM narrator_turns "
        "WHERE story_id = %s AND chapter = %s ORDER BY id",
        (story_id, chapter),
    ).fetchall()
    return [NarratorTurnRow(q, a, tuple(src)) for q, a, src in rows]
