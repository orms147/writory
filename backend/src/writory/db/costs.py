"""Nhật ký chi phí: một dòng mỗi lời gọi model, theo truyện, chương và vai (G8, D-10, D-44, D-64).

`story_spent_usd` là số đã tiêu của truyện, nạp vào `CostTracker(story_spent_usd=...)` để trần mỗi
truyện tính cả các chương trước, câu hỏi người kể và bước khởi tạo. Dòng có `cost_usd` NULL (phản
hồi không có usage.cost, client không ước tính) không cộng được; `CostTracker` đã dừng ở lời gọi
đó (D-10). Dòng `estimated` mang chi phí tối đa của lời gọi không có usage và được cộng như số
thật, tới khi tra lại theo `generation_id` thay bằng số thật (D-64, migration 0007).

`owner_costs` là số người chơi đã trả bằng key của mình (`/player/costs`, D-66): theo `owner_id` của
dòng, kể cả phiên khởi tạo bỏ dở và dòng ước tính chưa tra lại; tháng là tháng dương lịch theo UTC.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

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
    cached_tokens: int | None = None  # token vào đọc từ cache prompt (D-96)


def record_cost(
    conn: psycopg.Connection, *, owner_id: str, entry: CostEntry, story_id: str | None = None,
    setup_id: str | None = None, chapter: int | None = None,
) -> None:
    if story_id is None and setup_id is None:
        raise ValueError("dòng chi phí cần story_id hoặc setup_id")
    conn.execute(
        "INSERT INTO llm_costs (owner_id, story_id, setup_session_id, chapter, role, model, "
        "prompt_tokens, completion_tokens, cost_usd, estimated, generation_id, cached_tokens) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (owner_id, story_id, setup_id, chapter, entry.role, entry.model, entry.prompt_tokens,
         entry.completion_tokens, entry.cost_usd, entry.estimated, entry.generation_id,
         entry.cached_tokens),
    )


def story_spent_usd(conn: psycopg.Connection, story_id: str) -> float:
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) FROM llm_costs WHERE story_id = %s", (story_id,)
    ).fetchone()
    return float(row[0])


# Vai là việc của người chơi bên ngoài đường viết chương, hoặc của bước khởi tạo: không tính vào
# chi phí "một chương" (D-87). `moderate` còn lại gồm cả kiểm duyệt ô tự viết (rất nhỏ).
NON_CHAPTER_ROLES = ("narrator", "classify", "setup")


def chapter_costs(conn: psycopg.Connection, story_id: str) -> list[float]:
    """Chi phí thật của từng chương đã ghi (số chương >= 1) của truyện, tăng theo số chương: tổng
    mọi lời gọi gắn chương đó (kể cả lượt viết lại, lượt tạo lại lựa chọn), trừ `NON_CHAPTER_ROLES`.
    Chỉ chương `committed`. Dòng thiếu chi phí không cộng được (D-10)."""
    rows = conn.execute(
        "SELECT c.chapter, SUM(c.cost_usd) FROM llm_costs c "
        "WHERE c.story_id = %s AND c.chapter >= 1 AND c.cost_usd IS NOT NULL "
        "AND c.role <> ALL (%s) "
        "AND EXISTS (SELECT 1 FROM chapters ch WHERE ch.story_id = c.story_id "
        "AND ch.number = c.chapter AND ch.status = 'committed') "
        "GROUP BY c.chapter ORDER BY c.chapter",
        (story_id, list(NON_CHAPTER_ROLES)),
    ).fetchall()
    return [float(usd) for _, usd in rows]


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


def utc_month(now: datetime) -> tuple[datetime, datetime]:
    """Tháng dương lịch theo UTC chứa `now`: [đầu tháng, đầu tháng sau) (D-66)."""
    if now.tzinfo is None:
        raise ValueError("now phải có múi giờ")
    start = now.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = (start.replace(year=start.year + 1, month=1) if start.month == 12
           else start.replace(month=start.month + 1))
    return start, end


@dataclass(frozen=True)
class OwnerCosts:
    total_usd: float
    this_month_usd: float
    stories: tuple[tuple[str, float], ...]  # (story_id, đã tiêu), truyện tiêu gần nhất trước


def owner_costs(conn: psycopg.Connection, owner_id: str, *, now: datetime) -> OwnerCosts:
    """Số đã tiêu của một người chơi: tổng, tháng UTC chứa `now`, và theo từng truyện."""
    start, end = utc_month(now)
    total, month = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0), "
        "COALESCE(SUM(cost_usd) FILTER (WHERE created_at >= %s AND created_at < %s), 0) "
        "FROM llm_costs WHERE owner_id = %s",
        (start, end, owner_id),
    ).fetchone()
    rows = conn.execute(
        "SELECT story_id, COALESCE(SUM(cost_usd), 0) FROM llm_costs "
        "WHERE owner_id = %s AND story_id IS NOT NULL "
        "GROUP BY story_id ORDER BY MAX(created_at) DESC, story_id",
        (owner_id,),
    ).fetchall()
    return OwnerCosts(float(total), float(month), tuple((sid, float(usd)) for sid, usd in rows))
