"""Mục tiêu của chương theo bản kế hoạch (design §6.2 bước 1, §4.3; D-49).

`chapter_goals(plan, chapter, state)` là hàm thuần (chỉ đọc): hồi và vị trí trong hồi, mốc của
chương và mốc kế tiếp, bí mật trong khoảng lộ hay đã đến hạn, mạch phải gỡ và hạn gỡ, chương này có
phải chương cuối không. "Đã lộ", "đã gỡ" và "hạn" theo `guard.plan` (player_view cho bí mật,
RESOLVED_IN cho mạch), cùng định nghĩa người canh dùng để báo trễ hạn. `state` là nền đã commit
phủ các cảnh trước của chương, nên một bí mật vừa lộ ở cảnh 1 không còn bị giục ở cảnh 2.

G1: kết quả có chữ lớp truth (bí mật, mạch, mốc). Chỉ vào đề dàn ý và đề viết, hai vai được thấy
truth (D-28); riêng mạch phải gỡ và hạn gỡ cũng vào đề bộ trích, vai vốn thấy mọi nút (D-82).
Không bao giờ vào đề tạo lựa chọn, người kể hay sự kiện cho người chơi (riêng việc "đã đứng yên",
`standstill`, chỉ là một cờ đúng/sai khi vào đề tạo lựa chọn, không mang tên nơi chốn, D-98).
G4: chữ do model khởi tạo viết (mốc, tên hồi, bí mật, mạch) đi qua `escape_text`; chữ của nút
`user_authored` bọc `UserAuthored`.
"""

from collections.abc import Iterable, Mapping
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
    # `next`: mốc kế tiếp, chưa tới khoảng. `done`: đã diễn ra rồi (D-116), khoảng trùm chương này.
    status: Literal["open", "due", "next", "done"]
    number: int = 0  # thứ tự 1-based trong kế hoạch
    done_chapter: int | None = None


@dataclass(frozen=True)
class PendingMilestone:
    """Mốc chưa diễn ra mà bộ trích được phép đánh dấu ở cảnh này (D-116)."""

    number: int
    kind: MilestoneKind
    goal: str
    from_chapter: int
    to_chapter: int


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
class RevealedSecret:
    """Bí mật đã lộ cho người chơi (ở chương trước hoặc cảnh trước của chương này)."""

    fact_id: str
    text: str
    user_authored: bool
    revealed_chapter: int


@dataclass(frozen=True)
class Standstill:
    """Nhân vật chính ở yên một nơi nhiều chương (D-98). `place` là tên nơi chốn lớp truth."""

    place: str
    user_authored: bool
    chapters: int


@dataclass(frozen=True)
class Idle:
    """Truyện không đổi trạng thái nào `chapters` chương liền (D-112)."""

    chapters: int


@dataclass(frozen=True)
class PhaseShift:
    """Đã `chapters` chương kể từ lần đổi pha trước, hoặc lần nhắc đổi pha trước (D-119)."""

    chapters: int


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
    # Bí mật đã lộ: để đề nhắc không diễn lại cảnh lộ (D-84). Chỉ vào đề dàn ý và đề viết (G1).
    revealed: tuple[RevealedSecret, ...] = ()
    # Chỉ khi `chapter_goals(standstill_chapters=N)` và nhân vật chính ở yên từ N chương (D-98).
    standstill: Standstill | None = None
    # Chương này không có mốc nào đang diễn ra và cờ `unplanned_chapter_goal` bật (D-110).
    gap: bool = False
    # Chỉ khi `chapter_goals(idle_chapters=N)` và N chương liền không đổi trạng thái nào (D-112);
    # không đặt cùng `standstill` vì một lời giục là đủ.
    idle: Idle | None = None
    # Mốc bộ trích được đánh dấu ở cảnh này, và các mốc đã xong (số thứ tự -> chương), cho đề bộ trích
    # (D-116). Rỗng khi `chapter_goals(milestone_lookahead=None)`. Chỉ vào đề dàn ý, viết và bộ trích.
    pending_milestones: tuple[PendingMilestone, ...] = ()
    milestones_done: tuple[tuple[int, int], ...] = ()
    # Chỉ khi `chapter_goals(phase_shift_every=N)` và đã tới nhịp đổi pha (D-119); không đặt cùng
    # `standstill` hay `idle`, vì chúng đã đòi đổi tình thế cụ thể hơn.
    phase_shift: PhaseShift | None = None

    @property
    def final(self) -> bool:
        return self.chapter >= self.total_chapters

    @property
    def has_due(self) -> bool:
        return (any(s.status != "open" for s in self.secrets)
                or any(t.status in ("due", "overdue") for t in self.threads)
                or any(m.status == "due" for m in self.milestones))


def _milestones(plan: StoryPlan, chapter: int, final: bool,
                done: Mapping[int, int] | None = None) -> tuple[MilestoneGoal, ...]:
    """Mốc của chương. `done`: số thứ tự -> chương đã diễn ra (D-116). Mốc đã xong mà khoảng trùm
    chương này thì ghi `done`; mốc kế tiếp bỏ qua mốc đã xong."""
    done = done or {}
    numbered = list(enumerate(plan.milestones, 1))
    out = []
    for i, m in numbered:
        if not m.from_chapter <= chapter <= m.to_chapter:
            continue
        if i in done:
            out.append(MilestoneGoal(m.kind, m.goal, m.from_chapter, m.to_chapter, "done", i,
                                     done[i]))
        else:
            out.append(MilestoneGoal(m.kind, m.goal, m.from_chapter, m.to_chapter,
                                     "due" if final or chapter == m.to_chapter else "open", i))
    later = [(i, m) for i, m in numbered if m.from_chapter > chapter and i not in done]
    if later:
        first = min(m.from_chapter for _, m in later)
        out += [MilestoneGoal(m.kind, m.goal, m.from_chapter, m.to_chapter, "next", i)
                for i, m in later if m.from_chapter == first]
    return tuple(out)


def _pending_milestones(plan: StoryPlan, chapter: int, lookahead: int | None,
                        done: Mapping[int, int]) -> tuple[PendingMilestone, ...]:
    """Mốc chưa diễn ra, bắt đầu trong `lookahead` chương tới (kể cả mốc đã qua khoảng mà chưa xong).
    Mốc kết (`ending`) không theo dõi: vốn ở chương cuối."""
    if lookahead is None:
        return ()
    return tuple(
        PendingMilestone(i, m.kind, m.goal, m.from_chapter, m.to_chapter)
        for i, m in enumerate(plan.milestones, 1)
        if i not in done and m.kind != "ending" and m.from_chapter <= chapter + lookahead)


def standstill(state: GraphState, writing_chapter: int, threshold: int | None) -> Standstill | None:
    """Nhân vật chính đã ở yên một nơi từ `threshold` chương trở lên khi viết `writing_chapter`
    (D-98). Nơi ở là cạnh `LOCATED_AT` của nhân vật chính còn hiệu lực ở cuối chương trước; nếu bộ
    trích để hai cạnh cùng mở thì lấy cạnh mở sau cùng. Không có cạnh nào, chưa có nhân vật chính,
    hay `threshold` None (tắt) thì None. Lý do dùng nơi ở: độ giống chữ giữa các chương và số cạnh
    đổi mỗi chương không tách được chương lặp khỏi chương thường (D-98)."""
    if threshold is None:
        return None
    try:
        protagonist = state.protagonist_id()
    except LookupError:
        return None
    rows = state.edges_at("LOCATED_AT", writing_chapter - 1, source_id=protagonist)
    if not rows:
        return None
    latest = max(rows, key=lambda r: r.valid_from_chapter)
    stayed = writing_chapter - latest.valid_from_chapter
    if stayed < threshold:
        return None
    node = state.nodes([latest.target]).get(latest.target)
    name = node.props.get("name") if node is not None else None
    if not isinstance(name, str) or not name.strip():
        return None
    return Standstill(name, node.props.get("user_authored") is True, stayed)


def idle_chapters(state: GraphState, writing_chapter: int, threshold: int | None) -> Idle | None:
    """Số chương liền ngay trước `writing_chapter` mà truyện không đổi trạng thái nào, nếu từ
    `threshold` trở lên (D-112). Không dựa vào một cạnh nên không mù khi bộ trích bỏ cạnh nơi ở
    (long-tu-tien-2: cờ `standstill` mù 11 chương). Một chương CÓ đổi khi có một trong:
    nhân vật hay đồ vật tới một nơi mới (`LOCATED_AT`), đồ vật sang người giữ khác (`HOLDS`), có
    người chết (`DIED_IN`). Nói lại nơi hay người giữ đã có không tính; Fact mới, quan hệ, người biết
    thêm cũng không, vì chương nào cũng có (D-93). KHÔNG tính mạch gỡ và bí mật lộ: chúng xảy ra đúng
    lịch của kế hoạch dù chương là thủ tục (long-tu-tien-2: ch9, 11, 14, 17 gỡ mạch trong đúng đoạn
    lặp ch8–17, nên đếm chúng thì dãy rỗng dài nhất chỉ 2). Không đo được mốc từ đồ thị. None = tắt."""
    if threshold is None or writing_chapter - 1 < threshold:
        return None
    # Ba lần đọc `ever=True` bất kể dãy dài bao nhiêu (D-121, review), rồi tính trong Python.
    last = writing_chapter - 1
    loc = state.edges_at("LOCATED_AT", last, ever=True)
    held = state.edges_at("HOLDS", last, ever=True)
    died = state.edges_at("DIED_IN", last, ever=True)

    def open_pairs(rows, chapter: int) -> set[tuple[str, str]]:
        return {(e.source, e.target) for e in rows if e.valid_from_chapter <= chapter
                and (e.valid_to_chapter is None or e.valid_to_chapter > chapter)}

    def changed(chapter: int) -> bool:
        if any(e.valid_from_chapter == chapter for e in died):
            return True
        return any(open_pairs(rows, chapter) - open_pairs(rows, chapter - 1)
                   for rows in (loc, held))

    run = 0
    for chapter in range(last, 0, -1):
        if changed(chapter):
            break
        run += 1
    return Idle(run) if run >= threshold else None


_idle = idle_chapters  # `chapter_goals` có tham số cùng tên


def _phase_changes(plan: StoryPlan, state: GraphState, writing_chapter: int,
                   milestone_done: Iterable[int] = ()) -> set[int]:
    """Các chương đã đổi pha tính tới `writing_chapter` (D-119), đo từ kế hoạch và đồ thị:
    - chương đầu của một hồi, trừ hồi một (kế hoạch ghi sẵn nên biết cả chương đang viết);
    - chương nhân vật chính tới một nơi mà trước đó chưa từng có cạnh `LOCATED_AT` nào của họ tới
      (nơi ở chương 0 tính là đã tới). Quay lại nơi cũ không tính: đó là dạng lặp của truyện dài;
    - chương mà một mốc kế hoạch đã diễn ra (`milestone_done`: `done_chapter` của `plan_progress`, dấu
      do bộ trích ghi ở nút `Chapter`, D-116).
    Đọc tới cuối chương `writing_chapter - 1`, như `standstill`, nên mọi cảnh của chương cho cùng kết
    quả (mốc các cảnh trước của chính chương này, `done_extra`, không tính). Không tính mạch gỡ hay bí
    mật lộ (xảy ra đúng lịch kế hoạch dù chương là thủ tục, như lý do bỏ ở `idle_chapters`, D-112)."""
    changes = {a.from_chapter for a in plan.acts if 1 < a.from_chapter <= writing_chapter}
    changes |= {c for c in milestone_done if 1 <= c < writing_chapter}
    try:
        protagonist = state.protagonist_id()
    except LookupError:
        return changes
    first: dict[str, int] = {}
    for e in state.edges_at("LOCATED_AT", writing_chapter - 1, source_id=protagonist, ever=True):
        first[e.target] = min(first.get(e.target, e.valid_from_chapter), e.valid_from_chapter)
    return changes | {c for c in first.values() if c >= 1}


def phase_shift(plan: StoryPlan, state: GraphState, writing_chapter: int,
                every: int | None, milestone_done: Iterable[int] = ()) -> PhaseShift | None:
    """Có phải chương `writing_chapter` cần câu đòi đổi pha không (D-119). Đồng hồ chạy từ chương 0 và
    chạy lại ở mỗi lần đổi pha thật (`_phase_changes`) VÀ ở mỗi lần đã nhắc; câu bật khi đã `every`
    chương từ mốc gần nhất. Vì thế nếu model không đổi gì thì câu lặp mỗi `every` chương chứ không mỗi
    chương. Tính lại tất định từ đồ thị và kế hoạch mỗi lần, không lưu trạng thái. `every` None = tắt.
    Chương cuối và việc nhường cho `standstill`, `idle` do `chapter_goals` lo; ở đó đồng hồ vẫn tính
    như đã nhắc, vì chúng cũng đã đòi đổi tình thế."""
    if every is None or writing_chapter < every:
        return None
    changes = _phase_changes(plan, state, writing_chapter, milestone_done)
    last = 0
    for chapter in range(1, writing_chapter + 1):
        if chapter in changes:
            last = chapter
        if chapter - last >= every:
            if chapter == writing_chapter:
                return PhaseShift(chapter - last)
            last = chapter
    return None


def stalled_after(state: GraphState, committed_chapter: int, threshold: int | None, *,
                  idle_threshold: int | None = None) -> bool:
    """Truyện đứng yên khi viết chương kế tiếp (đề tạo lựa chọn cuối chương `committed_chapter`):
    nhân vật chính ở yên một nơi (D-98), hoặc nhiều chương liền không đổi trạng thái nào (D-112)."""
    return (standstill(state, committed_chapter + 1, threshold) is not None
            or _idle(state, committed_chapter + 1, idle_threshold) is not None)


def chapter_goals(plan: StoryPlan, chapter: int, state: GraphState, *,
                  standstill_chapters: int | None = None,
                  unplanned_goal: bool = False,
                  idle_chapters: int | None = None,
                  milestone_lookahead: int | None = None,
                  done_extra: Mapping[int, int] | None = None,
                  phase_shift_every: int | None = None) -> ChapterGoals:
    """Mục tiêu của chương N. `state`: trạng thái trước cảnh đang viết (nền đã commit tới N-1,
    phủ các gói cảnh trước của chương N). `standstill_chapters`: ngưỡng "ở yên" (D-98), None = tắt.
    `milestone_lookahead`: theo dõi mốc đã diễn ra (D-116), None = tắt; `done_extra`: mốc các cảnh
    trước của chính chương này đã đánh dấu (chưa vào nút Chapter, số thứ tự -> chương N)."""
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
    revealed = tuple(
        RevealedSecret(s.fact_id, s.text, s.user_authored, s.revealed_chapter)
        for s in progress.secrets if s.revealed_chapter is not None
    )
    still = None if final else standstill(state, chapter, standstill_chapters)
    done: dict[int, int] = {}
    if milestone_lookahead is not None:
        done = {m.number: m.done_chapter for m in progress.milestones if m.done_chapter is not None}
        done |= {n: c for n, c in (done_extra or {}).items() if n not in done}
    milestones = _milestones(plan, chapter, final, done)
    gap = unplanned_goal and not final and all(m.status in ("next", "done") for m in milestones)
    idle = None if final or still is not None else _idle(state, chapter, idle_chapters)
    shift = (None if final or still is not None or idle is not None
             else phase_shift(plan, state, chapter, phase_shift_every,
                              [m.done_chapter for m in progress.milestones
                               if m.done_chapter is not None]))
    return ChapterGoals(chapter, plan.total_chapters, act, milestones,
                        tuple(secrets), threads, revealed, still, gap, idle,
                        _pending_milestones(plan, chapter, milestone_lookahead, done),
                        tuple(sorted(done.items())), shift)


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
}



def _window(low: int | None, high: int | None) -> str:
    if low is None or high is None:
        return "chưa đặt khoảng"
    return f"chương {low}" if low == high else f"chương {low}–{high}"


def _data(text: str, user_authored: bool) -> str | UserAuthored:
    return UserAuthored(text, "story_data") if user_authored else escape_text(text)


def resolvable(goals: ChapterGoals) -> tuple[ThreadGoal, ...]:
    """Mạch phải gỡ mà chương này được gỡ: đã tới khoảng gỡ (`open`, `due`, `overdue`). Dàn ý chỉ
    được ghi các mạch này vào `resolves` (D-82)."""
    return tuple(t for t in goals.threads if t.status != "later")


# Câu cố định của mục tiêu chương mà bộ đo được thay để so hai bản đề trên cùng một thế giới (D-109).
# Sản phẩm không bao giờ truyền `texts`: luôn dùng các câu này (`push_forward`, `milestone_next` là
# chữ của đề v3, D-111). `standstill` có chỗ điền {place} và {chapters}; tên nơi chốn vẫn đi qua
# `_data` (G4).
GOAL_DEFAULTS: dict[str, str] = {
    "push_forward": ("Chương này phải đẩy truyện tới: kết chương ở một tình thế mới, không lặp lại "
                     "tình huống hay thế khó của chương trước. Ký, ghi, đặt xuống hay hẹn để sau "
                     "không tính là tình thế mới."),
    # Mốc kế tiếp (chưa tới khoảng của nó).
    "milestone_next": ("Mốc kế tiếp, chương này đưa vào một sự kiện hay áp lực cụ thể đẩy nhân vật "
                       "chính về phía đó"),
    # Chỉ in khi `ChapterGoals.gap` (cờ `unplanned_chapter_goal`, D-110): chương không có mốc nào.
    "milestone_gap": ("Chương này không có mốc cốt truyện riêng, nên tự nó phải đổi tình thế: cuối "
                      "chương có một điều mà đầu chương chưa xảy ra hoặc chưa ai biết (người bị "
                      "thương hay bị bắt, vật đổi chủ, bí mật lộ, người đổi phe, thời hạn bắt đầu, "
                      "nơi chốn đổi). Ký, ghi, đặt xuống hay hẹn để sau không tính."),
    # Mốc đã diễn ra rồi (D-116); chương xảy ra do code điền sau câu này.
    "milestone_done": ("Mốc ĐÃ xảy ra rồi: không diễn lại, đi bước kế"),
    "standstill": ("Nhân vật chính đã ở {place} suốt {chapters} chương. Chương này PHẢI đổi tình "
                   "thế: một sự kiện mới buộc nhân vật chính rời nơi này, hoặc phá vỡ thế giằng co, "
                   "hoặc làm lộ điều chưa ai biết. Không lặp lại cảnh dò xét, chờ đợi hay thương "
                   "lượng của các chương trước."),
    # {chapters} = số chương liền không đổi trạng thái nào (D-112).
    "idle": ("Đã {chapters} chương liền truyện không đổi trạng thái nào: không ai tới nơi mới, không "
             "vật nào đổi chủ hay đổi chỗ, không ai chết. Chương này PHẢI có ít nhất một điều như vậy "
             "xảy ra trên trang, không lặp lại cảnh dò xét, chờ đợi, "
             "thương lượng hay ghi chép của các chương trước."),
    # {chapters} = số chương kể từ lần đổi pha trước, hoặc lần nhắc trước (D-119).
    "phase_shift": ("Đã {chapters} chương kể từ lần đổi pha trước (nhân vật chính tới một nơi mới, "
                    "hoặc sang hồi mới). Chương này ĐỔI PHA: đổi nơi nhân vật chính tới, hoặc đổi "
                    "người nắm quyền quyết định, hoặc đổi luật chơi (điều kiện, thời hạn hay cái giá "
                    "của cuộc chơi). KHÔNG thêm một mối nguy cùng loại với những chương trước: mối "
                    "nguy nếu có phải khác về cơ chế và về người gây ra."),
    "secret_note": ("Hé lộ nghĩa là trên trang có câu nói thẳng điều đó (lời nhân vật, chứng cứ, "
                    "điều nhân vật chính tận mắt thấy), không chỉ gợi ý."),
    "revealed_note": ("Những bí mật này đã lộ rồi: không diễn lại cảnh lộ hay lời thú nhận. Nhân "
                      "vật phản ứng với điều đã biết và đi một bước mới."),
    "thread_note": ("Gỡ mạch nghĩa là trên trang có câu trả lời rõ cho câu hỏi chính của mạch, "
                    "hoặc nhân vật đưa ra quyết định dứt khoát mà mạch đòi, nói thẳng ra. Mạch hỏi "
                    "nhiều vế thì chỉ gỡ khi mọi vế đã có câu trả lời. Gỡ phải là một bước mới: "
                    "không diễn lại nhịp đã xảy ra ở chương trước (lời thú nhận, phát hiện cũ), "
                    "không chỉ nhắc lại điều người đọc đã biết."),
}


def _fill_standstill(template: str, st: "Standstill") -> list[str | UserAuthored]:
    """Điền {place} và {chapters} vào câu `standstill`; tên nơi chốn qua `_data` (escape hoặc bọc)."""
    pieces: list[str | UserAuthored] = []
    for i, part in enumerate(template.split("{place}")):
        if i:
            pieces.append(_data(st.place, st.user_authored))
        pieces.append(part.replace("{chapters}", str(st.chapters)))
    return pieces


def render_chapter_goals(goals: ChapterGoals, *, scene: int, scene_count: int,
                         thread_ids: bool = False,
                         texts: Mapping[str, str] | None = None) -> list[str | UserAuthored]:
    """Mục "Mục tiêu của chương" cho đề dàn ý và đề viết. Trả các phần để nối vào `user_message`;
    không bao giờ đưa vào đề của vai phục vụ người chơi (G1). `thread_ids`: ghi id của mạch được
    gỡ ở chương này, để dàn ý chép vào `resolves` (D-82); đề viết không cần. `texts`: chỉ bộ đo
    (D-109), thay các câu trong `GOAL_DEFAULTS` theo khoá; None hay thiếu khoá thì dùng câu mặc định."""
    say = {**GOAL_DEFAULTS, **(texts or {})}
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
        line("- " + say["push_forward"])
    if goals.gap:
        line("- " + say["milestone_gap"])
    if goals.standstill is not None:
        line("- ", *_fill_standstill(say["standstill"], goals.standstill))
    if goals.idle is not None:
        line("- " + say["idle"].replace("{chapters}", str(goals.idle.chapters)))
    if goals.phase_shift is not None:
        line("- " + say["phase_shift"].replace("{chapters}", str(goals.phase_shift.chapters)))
    if goals.act is not None and goals.act.last_chapter_of_act and not goals.final:
        line(f"- Đây là chương cuối của hồi «{escape_text(goals.act.name)}»: khép lại tình huống "
             "của hồi này để chương sau sang hồi mới.")
    if goals.milestones:
        line("### Mốc cốt truyện")
        for m in goals.milestones:
            if m.status == "done":
                line(f"- {say['milestone_done']} (xảy ra ở chương {m.done_chapter}; "
                     f"{_KIND_TEXT[m.kind]}, {_window(m.from_chapter, m.to_chapter)}): "
                     f"{escape_text(m.goal)}")
                continue
            status_text = say["milestone_next"] if m.status == "next" else _MILESTONE_TEXT[m.status]
            line(f"- {status_text} ({_KIND_TEXT[m.kind]}, "
                 f"{_window(m.from_chapter, m.to_chapter)}): {escape_text(m.goal)}")
    if goals.secrets:
        line("### Bí mật đã tới khoảng lộ")
        for s in goals.secrets:
            line(f"- {_SECRET_TEXT[s.status]} (khoảng lộ {_window(s.from_chapter, s.to_chapter)}): ",
                 _data(s.text, s.user_authored))
        line(say["secret_note"])
    if goals.revealed:
        line("### Bí mật đã lộ (người đọc đã biết)")
        for r in goals.revealed:
            line(f"- Đã lộ ở chương {r.revealed_chapter}: ", _data(r.text, r.user_authored))
        line(say["revealed_note"])
    if goals.threads:
        line("### Mạch phải gỡ trước khi kết truyện")
        for t in goals.threads:
            # Id giữ nguyên để dàn ý chép lại; ID_PATTERN không cho `<`, `&`.
            ident = f"id {t.thread_id}, " if thread_ids and t.status != "later" else ""
            line(f"- {_THREAD_TEXT[t.status]} ({ident}hạn gỡ "
                 f"{_window(t.from_chapter, t.to_chapter)}): ", _data(t.description, t.user_authored))
        line(say["thread_note"])
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
