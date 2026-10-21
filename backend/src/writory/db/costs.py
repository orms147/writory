"""Nhật ký chi phí: một dòng mỗi lời gọi model, theo truyện, chương và vai (G8, D-10, D-44, D-64).

`story_spent_usd` là số đã tiêu của truyện, nạp vào `CostTracker(story_spent_usd=...)` để trần mỗi
truyện tính cả các chương trước, câu hỏi người kể và bước khởi tạo. Dòng có `cost_usd` NULL (phản
hồi không có usage.cost, client không ước tính) không cộng được; `CostTracker` đã dừng ở lời gọi
đó (D-10). Dòng `estimated` mang chi phí tối đa của lời gọi không có usage và được cộng như số
thật, tới khi tra lại theo `generation_id` thay bằng số thật (D-64, migration 0007).
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
    estimated: bool = False
    generation_id: str | None = None


def record_cost(
    conn: psycopg.Connection, *, owner_id: str, entry: CostEntry, story_id: str | None = None,
    setup_id: str | None = None, chapter: int | None = None,
) -> None:
    if story_id is None and setup_id is None:
        raise ValueError("dòng chi phí cần story_id hoặc setup_id")
    conn.execute(
        "INSERT INTO llm_costs (owner_id, story_id, setup_session_id, chapter, role, model, "
        "prompt_tokens, completion_tokens, cost_usd, estimated, generation_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (owner_id, story_id, setup_id, chapter, entry.role, entry.model, entry.prompt_tokens,
         entry.completion_tokens, entry.cost_usd, entry.estimated, entry.generation_id),
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


def pending_cost_estimates(
    conn: psycopg.Connection, *, story_id: str | None = None, setup_id: str | None = None,
    limit: int,
) -> list[tuple[int, str]]:
    """(id dòng, id generation) của các dòng ước tính còn tra lại được, cũ trước. Phạm vi là
    đúng một trong truyện hoặc phiên khởi tạo."""
    if (story_id is None) == (setup_id is None):
        raise ValueError("cần đúng một trong story_id, setup_id")
    scope = ("story_id = %s" if story_id is not None else "setup_session_id = %s")
    rows = conn.execute(
        "SELECT id, generation_id FROM llm_costs WHERE " + scope
        + " AND estimated AND generation_id IS NOT NULL ORDER BY id LIMIT %s",
        (story_id if story_id is not None else setup_id, limit),
    ).fetchall()
    return [(row_id, gen_id) for row_id, gen_id in rows]


def settle_cost_estimate(
    conn: psycopg.Connection, row_id: int, *, cost_usd: float, prompt_tokens: int,
    completion_tokens: int,
) -> None:
    """Thay số ước tính bằng chi phí thật tra theo id generation. Dòng đã thay thì không đổi."""
    conn.execute(
        "UPDATE llm_costs SET cost_usd = %s, prompt_tokens = %s, completion_tokens = %s, "
        "estimated = false WHERE id = %s AND estimated",
        (cost_usd, prompt_tokens, completion_tokens, row_id),
    )
