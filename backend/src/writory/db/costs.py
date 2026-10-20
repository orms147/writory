"""Nhật ký chi phí: một dòng mỗi lời gọi model, theo truyện, chương và vai (G8, D-10, D-44).

`story_spent_usd` là số đã tiêu của truyện, nạp vào `CostTracker(story_spent_usd=...)` để trần mỗi
truyện tính cả các chương trước, câu hỏi người kể và bước khởi tạo. Dòng có `cost_usd` NULL (phản
hồi không có usage.cost) không cộng được; `CostTracker` đã dừng ở lời gọi đó (D-10).
"""

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class CostEntry:
    role: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None


def record_cost(
    conn: psycopg.Connection, *, owner_id: str, entry: CostEntry, story_id: str | None = None,
    setup_id: str | None = None, chapter: int | None = None,
) -> None:
    if story_id is None and setup_id is None:
        raise ValueError("dòng chi phí cần story_id hoặc setup_id")
    conn.execute(
        "INSERT INTO llm_costs (owner_id, story_id, setup_session_id, chapter, role, model, "
        "prompt_tokens, completion_tokens, cost_usd) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (owner_id, story_id, setup_id, chapter, entry.role, entry.model, entry.prompt_tokens,
         entry.completion_tokens, entry.cost_usd),
    )


def story_spent_usd(conn: psycopg.Connection, story_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_costs WHERE story_id = %s", (story_id,)
    ).fetchone()
    return float(row[0])


def setup_spent_usd(conn: psycopg.Connection, setup_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_costs WHERE setup_session_id = %s",
        (setup_id,),
    ).fetchone()
    return float(row[0])
