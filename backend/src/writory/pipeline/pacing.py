"""Mục tiêu của chương theo bản kế hoạch (design §6.2 bước 1, §4.3; D-49).

`chapter_goals(plan, chapter, state)` là hàm thuần (chỉ đọc): hồi và vị trí trong hồi, mốc của
chương và mốc kế tiếp, bí mật trong khoảng lộ hay đã đến hạn, mạch phải gỡ và hạn gỡ, chương này có
phải chương cuối không. "Đã lộ", "đã gỡ" và "hạn" theo `guard.plan` (player_view cho bí mật,
RESOLVED_IN cho mạch), cùng định nghĩa người canh dùng để báo trễ hạn. `state` là nền đã commit
phủ các cảnh trước của chương, nên một bí mật vừa lộ ở cảnh 1 không còn bị giục ở cảnh 2.

G1: kết quả có chữ lớp truth (bí mật, mạch, mốc). Chỉ vào đề dàn ý và đề viết, hai vai được thấy
truth (D-28). Không bao giờ vào đề tạo lựa chọn, người kể hay sự kiện cho người chơi.
G4: chữ do model khởi tạo viết (mốc, tên hồi, bí mật, mạch) đi qua `escape_text`; chữ của nút
`user_authored` bọc `UserAuthored`.
"""

from dataclasses import dataclass
from typing import Literal

from writory.guard.plan import Deadline, deadline, plan_progress
from writory.guard.state import GraphState
from writory.pipeline.story_plan import MilestoneKind, StoryPlan
from writory.safety.wrap import UserAuthored, escape_text


@dataclass(frozen=True)
class ActPosition:
    name: str
    number: int  # 1-based
    count: int
    chapter_in_act: int  # 1-based
    chapters_in_act: int

    @property
    def last_chapter_of_act(self) -> bool:
        return self.chapter_in_act == self.chapters_in_act


@dataclass(frozen=True)
class MilestoneGoal:
    kind: MilestoneKind
    goal: str
    from_chapter: int
    to_chapter: int
    status: Literal["open", "due", "next"]  # `next`: mốc kế tiếp, chưa tới khoảng


@dataclass(frozen=True)
class SecretGoal:
    """Bí mật chưa lộ đã tới khoảng lộ."""

    fact_id: str
    text: str
    user_authored: bool
    from_chapter: int
    to_chapter: int
    status: Literal["open", "due", "overdue"]


@dataclass(frozen=True)
class ThreadGoal:
    """Mạch phải gỡ, chưa gỡ."""

    thread_id: str
    description: str
    user_authored: bool
    from_chapter: int | None
    to_chapter: int | None
    status: Deadline


@dataclass(frozen=True)
class ChapterGoals:
    chapter: int
    total_chapters: int
    act: ActPosition | None
    milestones: tuple[MilestoneGoal, ...]
    secrets: tuple[SecretGoal, ...]
    threads: tuple[ThreadGoal, ...]

    @property
    def final(self) -> bool:
        return self.chapter >= self.total_chapters

    @property
    def has_due(self) -> bool:
        return (any(s.status != "open" for s in self.secrets)
                or any(t.status in ("due", "overdue") for t in self.threads)
                or any(m.status == "due" for m in self.milestones))


def _milestones(plan: StoryPlan, chapter: int, final: bool) -> tuple[MilestoneGoal, ...]:
    out = [MilestoneGoal(m.kind, m.goal, m.from_chapter, m.to_chapter,
                         "due" if final or chapter == m.to_chapter else "open")
           for m in plan.milestones if m.from_chapter <= chapter <= m.to_chapter]
    later = [m for m in plan.milestones if m.from_chapter > chapter]
    if later:
        first = min(m.from_chapter for m in later)
        out += [MilestoneGoal(m.kind, m.goal, m.from_chapter, m.to_chapter, "next")
                for m in later if m.from_chapter == first]
    return tuple(out)


def chapter_goals(plan: StoryPlan, chapter: int, state: GraphState) -> ChapterGoals:
    """Mục tiêu của chương N. `state`: trạng thái trước cảnh đang viết (nền đã commit tới N-1,
    phủ các gói cảnh trước của chương N)."""
    progress = plan_progress(plan, state, chapter)
    final = progress.final
    act = None
    if (found := plan.act_of(chapter)) is not None:
        number, a = found
        act = ActPosition(a.name, number, len(plan.acts), chapter - a.from_chapter + 1,
                          a.to_chapter - a.from_chapter + 1)
    secrets = []
    for s in progress.secrets:
        status = deadline(chapter, s.from_chapter, s.to_chapter, final=final)
        if s.revealed_chapter is None and status != "later":
            secrets.append(SecretGoal(s.fact_id, s.text, s.user_authored, s.from_chapter,
                                      s.to_chapter, status))
    threads = tuple(
        ThreadGoal(t.thread_id, t.description, t.user_authored, t.from_chapter, t.to_chapter,
                   deadline(chapter, t.from_chapter, t.to_chapter, final=final))
        for t in progress.threads if t.resolved_chapter is None
    )
    return ChapterGoals(chapter, plan.total_chapters, act, _milestones(plan, chapter, final),
                        tuple(secrets), threads)


# --- chữ trong đề ------------------------------------------------------------------------------

_KIND_TEXT = {"turning_point": "bước ngoặt", "climax": "cao trào", "ending": "kết"}
_SECRET_TEXT = {
    "due": "ĐẾN HẠN: phải hé lộ rõ cho người đọc trong chương này",
    "overdue": "QUÁ HẠN: phải hé lộ rõ cho người đọc trong chương này",
    "open": "Trong khoảng lộ, chưa tới hạn: hé lộ nếu cảnh dẫn tới; chưa lộ thì gieo manh mối rõ "
            "hơn chương trước",
}
_THREAD_TEXT = {
    "due": "ĐẾN HẠN: phải gỡ trong chương này",
    "overdue": "QUÁ HẠN: phải gỡ trong chương này",
    "open": "Có thể gỡ ở chương này",
    "later": "Chưa tới lúc gỡ, giữ cho mạch còn sống",
}
_MILESTONE_TEXT = {
    "due": "ĐẾN HẠN ở chương này",
    "open": "Đang diễn ra",
    "next": "Mốc kế tiếp, chuẩn bị dần",
}


def _window(low: int | None, high: int | None) -> str:
    if low is None or high is None:
        return "chưa đặt khoảng"
    return f"chương {low}" if low == high else f"chương {low}–{high}"


def _data(text: str, user_authored: bool) -> str | UserAuthored:
    return UserAuthored(text, "story_data") if user_authored else escape_text(text)


def render_chapter_goals(goals: ChapterGoals, *, scene: int,
                         scene_count: int) -> list[str | UserAuthored]:
    """Mục "Mục tiêu của chương" cho đề dàn ý và đề viết. Trả các phần để nối vào `user_message`;
    không bao giờ đưa vào đề của vai phục vụ người chơi (G1)."""
    parts: list[str | UserAuthored] = []
    buf: list[str] = []

    def line(*pieces: str | UserAuthored) -> None:
        current = ""
        for piece in pieces:
            if isinstance(piece, UserAuthored):
                buf.append(current)
                current = ""
                flush()
                parts.append(piece)
            else:
                current += piece
        buf.append(current)

    def flush() -> None:
        text = "\n".join(buf).strip("\n")
        if text:
            parts.append(text)
        buf.clear()

    line("## Mục tiêu của chương theo bản kế hoạch (người đọc không thấy mục này)")
    where = f"Chương {goals.chapter}/{goals.total_chapters} của truyện"
    if goals.act is not None:
        a = goals.act
        where += (f"; hồi «{escape_text(a.name)}» (hồi {a.number}/{a.count}), chương "
                  f"{a.chapter_in_act}/{a.chapters_in_act} của hồi")
    line(f"- Vị trí: {where}.")
    if not goals.final:
        line("- Chương này phải đẩy truyện tới: kết chương ở một tình thế mới, không lặp lại tình "
             "huống hay thế khó của chương trước.")
    if goals.act is not None and goals.act.last_chapter_of_act and not goals.final:
        line(f"- Đây là chương cuối của hồi «{escape_text(goals.act.name)}»: khép lại tình huống "
             "của hồi này để chương sau sang hồi mới.")
    if goals.milestones:
        line("### Mốc cốt truyện")
        for m in goals.milestones:
            line(f"- {_MILESTONE_TEXT[m.status]} ({_KIND_TEXT[m.kind]}, "
                 f"{_window(m.from_chapter, m.to_chapter)}): {escape_text(m.goal)}")
    if goals.secrets:
        line("### Bí mật đã tới khoảng lộ")
        for s in goals.secrets:
            line(f"- {_SECRET_TEXT[s.status]} (khoảng lộ {_window(s.from_chapter, s.to_chapter)}): ",
                 _data(s.text, s.user_authored))
        line("Hé lộ nghĩa là trên trang có câu nói thẳng điều đó (lời nhân vật, chứng cứ, điều nhân "
             "vật chính tận mắt thấy), không chỉ gợi ý.")
    if goals.threads:
        line("### Mạch phải gỡ trước khi kết truyện")
        for t in goals.threads:
            line(f"- {_THREAD_TEXT[t.status]} (hạn gỡ {_window(t.from_chapter, t.to_chapter)}): ",
                 _data(t.description, t.user_authored))
    last_scene = scene >= scene_count
    if goals.final:
        line("### Chương cuối")
        line("- Đây là CHƯƠNG CUỐI của truyện. Truyện kết trong chương này, tôn trọng các lựa chọn "
             "người chơi đã đi: gỡ mọi mạch còn mở (cả các mạch ở mục \"Mạch đang mở\"), hé lộ các "
             "bí mật còn lại nếu hợp lý, không mở tình huống mới.")
        if last_scene:
            line("- Cảnh này là cảnh kết của cả truyện: khép lại trọn vẹn. Không kết bằng một câu "
                 "hỏi, một thế khó hay một lựa chọn bỏ ngỏ: sau cảnh này người chơi không còn lựa "
                 "chọn nào.")
    elif goals.has_due:
        if last_scene:
            line("- Đây là cảnh cuối của chương: điều nào ĐẾN HẠN hay QUÁ HẠN ở trên mà các cảnh "
                 "trước chưa làm thì phải xảy ra trong cảnh này.")
        else:
            line(f"- Điều ĐẾN HẠN hay QUÁ HẠN phải xảy ra trong chương này, ở cảnh này hoặc cảnh "
                 f"sau (đang viết cảnh {scene}/{scene_count}).")
    flush()
    return parts
