"""Bản kế hoạch truyện ẩn (`story_plan`) và thiết lập truyện (`stories.brief`) trong Postgres (D-44).

Bản kế hoạch chứa bí mật và khoảng lộ: chỉ pipeline, người canh và bộ dò lộ đọc nó; không có đường
nào đưa nó ra API (G1).
"""

import psycopg
from psycopg.types.json import Jsonb

from writory.db.chapters import StoryRecord, get_story
from writory.graph.story import require_story_id
from writory.pipeline.story_plan import StoryPlan


def create_story_with_plan(
    conn: psycopg.Connection, story_id: str, *, owner_id: str, length_level: str, brief: str,
    plan: StoryPlan,
) -> StoryRecord:
    """Tạo truyện cùng bản kế hoạch và thiết lập trong một transaction: có cả hai hoặc không có gì."""
    require_story_id(story_id)
    with conn.transaction():
        conn.execute(
            "INSERT INTO stories (id, owner_id, length_level, brief) VALUES (%s, %s, %s, %s)",
            (story_id, owner_id, length_level, brief),
        )
        conn.execute(
            "INSERT INTO story_plans (story_id, plan) VALUES (%s, %s)",
            (story_id, Jsonb(plan.model_dump(mode="json"))),
        )
    return get_story(conn, story_id)


def load_story_plan(conn: psycopg.Connection, story_id: str) -> StoryPlan | None:
    """None: truyện không có bản kế hoạch (ví dụ truyện mẫu nạp tay). Nơi gọi phải fail closed."""
    row = conn.execute(
        "SELECT plan FROM story_plans WHERE story_id = %s", (story_id,)
    ).fetchone()
    return None if row is None else StoryPlan.model_validate(row[0])


def load_story_brief(conn: psycopg.Connection, story_id: str) -> str | None:
    row = conn.execute("SELECT brief FROM stories WHERE id = %s", (story_id,)).fetchone()
    return None if row is None else row[0]


def set_story_brief(conn: psycopg.Connection, story_id: str, brief: str) -> None:
    """Cho truyện tạo ngoài luồng khởi tạo (truyện mẫu, test)."""
    conn.execute("UPDATE stories SET brief = %s, updated_at = now() WHERE id = %s",
                 (brief, story_id))


def save_story_plan(conn: psycopg.Connection, story_id: str, plan: StoryPlan) -> None:
    """Cho truyện tạo ngoài luồng khởi tạo (truyện mẫu, test). Đã có thì báo lỗi, không ghi đè."""
    conn.execute("INSERT INTO story_plans (story_id, plan) VALUES (%s, %s)",
                 (story_id, Jsonb(plan.model_dump(mode="json"))))
