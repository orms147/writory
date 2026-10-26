"""Bản kế hoạch truyện ẩn (`story_plan`) và thiết lập truyện (`stories.brief`) trong Postgres (D-44).

Bản kế hoạch chứa bí mật và khoảng lộ: chỉ pipeline, người canh và bộ dò lộ đọc nó; không có đường
nào đưa nó ra API (G1).
"""

import logging

import psycopg
from neo4j import Driver
from psycopg.types.json import Jsonb

from writory.db.chapters import StoryRecord, commit_chapter, delete_story_record, get_story
from writory.db.locks import job_lock
from writory.graph import ChangePackage, delete_story
from writory.graph.story import require_story_id
from writory.pipeline.story_plan import StoryPlan
from writory.safety.redact import redact

log = logging.getLogger(__name__)


def start_story(
    conn: psycopg.Connection, driver: Driver, story_id: str, *, owner_id: str, length_level: str,
    brief: str, plan: StoryPlan, initial: ChangePackage, darkness_level: str | None = None,
) -> StoryRecord:
    """Tạo truyện, bản kế hoạch và chương 0 (gói `initial`), tất cả hoặc không gì (G11, D-45).

    Lỗi ở bước ghi chương 0 (kể cả khi chương ở lại `pending` vì Neo4j không trả lời) thì gỡ hết
    theo `story_id` rồi ném lại lỗi: người chơi không thấy truyện nửa vời, bấm thử lại được.
    Giữ khoá `story` của truyện mới suốt lúc ghi, như viết chương, để lần áp lại lúc khởi động ở
    tiến trình khác không đụng chương 0 đang ghi dở (`db.reconcile_idle_stories`, D-105)."""
    with job_lock(conn, "story", story_id):
        create_story_with_plan(conn, story_id, owner_id=owner_id, length_level=length_level,
                               brief=brief, plan=plan, darkness_level=darkness_level)
        try:
            commit_chapter(conn, driver, story_id, 0, [], initial)
        except BaseException:
            discard_story(conn, driver, story_id)
            raise
    return get_story(conn, story_id)


def discard_story(conn: psycopg.Connection, driver: Driver, story_id: str) -> None:
    """Gỡ một truyện vừa tạo dở: Postgres trước (truyện, kế hoạch, chương, gói), rồi Neo4j.
    Neo4j không trả lời thì có thể còn nút mồ côi theo `story_id` này; không đọc được nữa, vì mọi
    lần đọc đi qua truyện trong Postgres (D-6)."""
    delete_story_record(conn, story_id)
    try:
        delete_story(driver, story_id)
    except Exception as exc:  # noqa: BLE001 — đã gỡ phần Postgres; chỉ ghi log phần còn lại
        log.warning("gỡ truyện %s trên Neo4j không được: %s", story_id,
                    redact(f"{type(exc).__name__}: {exc}"))


def create_story_with_plan(
    conn: psycopg.Connection, story_id: str, *, owner_id: str, length_level: str, brief: str,
    plan: StoryPlan, darkness_level: str | None = None,
) -> StoryRecord:
    """Tạo truyện cùng bản kế hoạch và thiết lập trong một transaction: có cả hai hoặc không có gì.
    `darkness_level`: mức u tối người chơi chọn (D-67); None = mức mặc định của config."""
    require_story_id(story_id)
    with conn.transaction():
        conn.execute(
            "INSERT INTO stories (id, owner_id, length_level, brief, darkness_level) "
            "VALUES (%s, %s, %s, %s, %s)",
            (story_id, owner_id, length_level, brief, darkness_level),
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
