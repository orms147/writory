"""Tiến độ của bản kế hoạch trên một trạng thái đồ thị (design §6.1; D-49). Bằng code, không gọi
model.

Một định nghĩa dùng chung cho: mục tiêu của chương trong đề dàn ý và đề viết (`pipeline.pacing`),
phép kiểm "trễ hạn" của người canh (`guard.rules`), và mục so kế hoạch với kết quả của lệnh chạy cả
truyện (`pipeline.bench_run`).

- Bí mật "đã lộ" ở chương N: fact nằm trong `player_view` ở chương N (định nghĩa duy nhất, D-16:
  REVEALED_TO_PLAYER, hoặc nhân vật chính KNOWS). Chương lộ là `since_chapter` của mục đó.
- Mạch "đã gỡ" ở chương N: có cạnh RESOLVED_IN mở ở chương ≤ N. Nút `Thread` không bao giờ vào
  player_view (graph-schema.md), nên đọc từ lớp truth.
- Khoảng gỡ của mạch: khoảng trong kế hoạch; kế hoạch cũ không có thì lấy khoảng dự kiến gỡ trên
  nút `Thread` (`due_from_chapter`, `due_to_chapter`).
- Mốc "đã diễn ra" ở chương N (D-115): bộ trích đánh dấu bằng câu trích có thật, dấu nằm ở thuộc
  tính `milestones` (số thứ tự 1-based trong kế hoạch) của nút `Chapter` của chương xảy ra. Mốc
  không phải nút (không đổi khởi tạo hay `story_plan`), nên không đọc được từ cạnh; mốc đánh dấu hai
  lần thì chương đầu thắng.
- Bí mật hay mạch mà nút chưa có trong đồ thị ở chương N (gieo sau) thì bỏ qua: chưa có gì để
  lộ hay gỡ. Khởi tạo đã kiểm mọi id của kế hoạch có nút ở chương 0 (D-38).

Đọc trên `GraphState`, nên đúng cho Neo4j và cho OverlayState (nền đã commit + các cảnh trước
trong chương). Kết quả có id và chữ lớp truth: chỉ cho vai được thấy truth và cho máy chủ.
"""

from dataclasses import dataclass
from typing import Literal

from writory.guard.state import GraphState, player_view_of
from writory.pipeline.story_plan import StoryPlan

Deadline = Literal["later", "open", "due", "overdue"]


def deadline(chapter: int, low: int | None, high: int | None, *, final: bool) -> Deadline:
    """Trạng thái hạn ở chương N của một việc có khoảng [low, high]:
    `later` chưa tới khoảng; `open` trong khoảng, chưa tới chương cuối của khoảng; `due` chương
    cuối của khoảng (hoặc chương cuối của truyện); `overdue` đã qua khoảng. Không có khoảng: chỉ
    đến hạn ở chương cuối của truyện."""
    if high is not None and chapter > high:
        return "overdue"
    if final or (high is not None and chapter == high):
        return "due"
    if low is not None and chapter >= low:
        return "open"
    return "later"


@dataclass(frozen=True)
class SecretProgress:
    fact_id: str
    text: str
    user_authored: bool
    from_chapter: int
    to_chapter: int
    revealed_chapter: int | None


@dataclass(frozen=True)
class ThreadProgress:
    thread_id: str
    description: str
    user_authored: bool
    from_chapter: int | None
    to_chapter: int | None
    resolved_chapter: int | None


@dataclass(frozen=True)
class MilestoneProgress:
    number: int  # thứ tự 1-based trong kế hoạch (id `m<number>` trong đề bộ trích)
    kind: str
    goal: str
    from_chapter: int
    to_chapter: int
    done_chapter: int | None


@dataclass(frozen=True)
class PlanProgress:
    chapter: int
    total_chapters: int
    secrets: tuple[SecretProgress, ...]
    threads: tuple[ThreadProgress, ...]
    milestones: tuple[MilestoneProgress, ...] = ()

    @property
    def final(self) -> bool:
        return self.chapter >= self.total_chapters


def _int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def milestones_done(plan: StoryPlan, state: GraphState, chapter: int) -> dict[int, int]:
    """Số thứ tự mốc -> chương xảy ra, theo dấu trên nút `Chapter` ch1..chN của `state` (D-115).
    Số không phải mốc của kế hoạch bị bỏ."""
    rows = state.nodes([f"ch{n}" for n in range(1, chapter + 1)])
    done: dict[int, int] = {}
    for n in range(1, chapter + 1):
        row = rows.get(f"ch{n}")
        marks = row.props.get("milestones") if row is not None else None
        for number in marks if isinstance(marks, list) else []:
            if _int(number) is not None and 1 <= number <= len(plan.milestones):
                done.setdefault(number, n)
    return done


def plan_progress(plan: StoryPlan, state: GraphState, chapter: int) -> PlanProgress:
    """Bí mật đã lộ, mạch phải gỡ đã gỡ và mốc đã diễn ra tới hết chương N, trên `state`."""
    revealed = {e.id: e.since_chapter for e in player_view_of(state, chapter).entries}
    rows = state.nodes([*(s.fact_id for s in plan.secrets), *plan.thread_ids])
    secrets = tuple(
        SecretProgress(s.fact_id, str(rows[s.fact_id].props.get("text", "")),
                       rows[s.fact_id].props.get("user_authored") is True,
                       s.reveal_from_chapter, s.reveal_to_chapter, revealed.get(s.fact_id))
        for s in plan.secrets if s.fact_id in rows
    )
    threads = []
    for t in plan.must_resolve_threads:
        row = rows.get(t.thread_id)
        if row is None:
            continue
        low, high = t.resolve_from_chapter, t.resolve_to_chapter
        if high is None:
            low, high = _int(row.props.get("due_from_chapter")), _int(row.props.get("due_to_chapter"))
        resolved = [e.valid_from_chapter for e in state.edges_at(
            "RESOLVED_IN", chapter, source_id=t.thread_id, ever=True)]
        threads.append(ThreadProgress(
            t.thread_id, str(row.props.get("description", "")),
            row.props.get("user_authored") is True, low, high, min(resolved, default=None)))
    done = milestones_done(plan, state, chapter)
    milestones = tuple(
        MilestoneProgress(i, m.kind, m.goal, m.from_chapter, m.to_chapter, done.get(i))
        for i, m in enumerate(plan.milestones, 1))
    return PlanProgress(chapter, plan.total_chapters, secrets, tuple(threads), milestones)
