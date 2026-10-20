"""Lựa chọn cuối chương phía máy chủ và hành động dẫn tới chương sau (D-37, D-44).

Lựa chọn lưu kèm dữ liệu có cấu trúc (id nút thật, lời nói dối) để ghi về sau; không bao giờ ra API.
Người chơi chỉ nhận `PlayerChoice` và gửi lại id mờ `choice-…`.
"""

from dataclasses import dataclass
from typing import Any, Literal

import psycopg
from psycopg.types.json import Jsonb

from writory.graph.story import require_chapter, require_story_id

ActionSource = Literal["choice", "custom"]


@dataclass(frozen=True)
class ActionRecord:
    for_chapter: int
    source: ActionSource
    text: str
    choice_id: str | None


def save_choices(
    conn: psycopg.Connection, story_id: str, chapter: int, choices: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Lưu bộ lựa chọn của chương. Chương đã có bộ thì giữ bộ cũ và trả nó (mỗi chương một bộ)."""
    require_story_id(story_id)
    require_chapter(chapter)
    try:
        with conn.transaction():
            for position, choice in enumerate(choices):
                conn.execute(
                    "INSERT INTO chapter_choices (story_id, chapter, position, choice_id, choice) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (story_id, chapter, position, choice["id"], Jsonb(choice)),
                )
    except psycopg.errors.UniqueViolation:
        return load_choices(conn, story_id, chapter)
    return choices


def load_choices(conn: psycopg.Connection, story_id: str, chapter: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT choice FROM chapter_choices WHERE story_id = %s AND chapter = %s ORDER BY position",
        (story_id, chapter),
    ).fetchall()
    return [r[0] for r in rows]


def load_choice(
    conn: psycopg.Connection, story_id: str, chapter: int, choice_id: str
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT choice FROM chapter_choices WHERE story_id = %s AND chapter = %s AND choice_id = %s",
        (story_id, chapter, choice_id),
    ).fetchone()
    return None if row is None else row[0]


def save_action(
    conn: psycopg.Connection, story_id: str, for_chapter: int, *, source: ActionSource, text: str,
    choice_id: str | None = None,
) -> ActionRecord:
    """Thêm hoặc thay hành động dẫn tới chương `for_chapter` (chọn lại được tới khi chương đó viết)."""
    require_story_id(story_id)
    conn.execute(
        "INSERT INTO player_actions (story_id, for_chapter, source, choice_id, text) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (story_id, for_chapter) DO UPDATE SET "
        "source = EXCLUDED.source, choice_id = EXCLUDED.choice_id, text = EXCLUDED.text, "
        "updated_at = now()",
        (story_id, for_chapter, source, choice_id, text),
    )
    return ActionRecord(for_chapter, source, text, choice_id)


def load_action(conn: psycopg.Connection, story_id: str, for_chapter: int) -> ActionRecord | None:
    row = conn.execute(
        "SELECT for_chapter, source, text, choice_id FROM player_actions "
        "WHERE story_id = %s AND for_chapter = %s",
        (story_id, for_chapter),
    ).fetchone()
    return None if row is None else ActionRecord(*row)
