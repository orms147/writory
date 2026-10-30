"""Đường đi một chương (design §6.2; D-1, D-6, D-8, D-36). Toàn bộ đồ thị LangGraph nằm ở đây.

Mỗi cảnh: dựng ngữ cảnh và mục tiêu của chương (`pipeline.pacing`, D-49) → dàn ý → viết → soát
(chuẩn hoá dấu gạch, kiểm văn, trích thay đổi, tự hé lộ tên trang vừa nêu, người canh, dò lộ,
kiểm duyệt nội dung G9, và kiểm vượt luật G6 khi hành động tự viết vượt luật, D-138) → viết lại tối
đa `limits.retries.rewrite_per_scene` lần → hiện. Dàn ý
cảnh cuối mà không dàn ý nào của chương định gỡ mạch đến hạn thì thử lại trong ngân sách của dàn
ý; hết lượt thì viết tiếp với dàn ý cuối (D-82). Bộ trích nhận mạch phải gỡ đang mở ở mọi lượt.
Bản viết lại có lỗi chặn mà bản trước không có thì hiện bản trước (D-50, bổ sung D-36). Hết cảnh
cuối: gộp gói các cảnh → `store.commit` (D-6, tất cả hoặc không gì) → tóm tắt chương
(`pipeline.summary`, D-49; lỗi không làm hỏng chương đã ghi) → tạo lựa chọn từ player_view (G1).
Đề của chương N nhận tóm tắt chương N-1, N-2. Chương cuối của bản kế hoạch thì không tóm tắt,
không tạo lựa chọn mà phát `story_finished` (D-50); chương sau đó bị từ chối (`STORY_COMPLETE`).

- Người chơi chỉ nhận sự kiện (`pipeline.events`): chữ cảnh đã qua mọi phép kiểm (D-1), lựa chọn đã
  qua dò lộ (G2), câu lỗi G12. Cảnh chưa kiểm không bao giờ được phát ra.
- Không ghi gì trước bước ghi chương. Lỗi giữa chừng (mã G12) dừng chương; đồ thị và Postgres giữ
  nguyên (G11). Lỗi ở bước lựa chọn xảy ra sau khi chương đã ghi; gọi lại `make_choices`.
- Mọi lời gọi model qua `MeteredClient` (G8); cấu hình còn null thì báo lỗi trước lời gọi đầu.
- Nhật ký lỗi còn lại sau lượt viết lại chỉ ghi loại lỗi (không ghi chữ: có thể chứa bí mật).
"""

import asyncio
import logging
import traceback
import unicodedata
import uuid
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from functools import partial
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from writory.config import AppConfig, LimitNotSetError, WriterTier
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, NodeSpec, PlayerView
from writory.graph.context import WriterContext, cap_page_facts
from writory.graph.schema import EDGE_TYPES, NAMED_LABELS
from writory.guard import Severity, check_scene_package
from writory.guard.state import GraphState, OverlayState, player_view_of
from writory.llm.base import LLMClient, reasoning_extra, require_model, role_extra
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.retry import RETRY_TRANSIENT, with_json_retries, with_retries
from writory.pipeline.choices import Choice, choice_effects, make_choices
from writory.pipeline.events import (
    ChapterCommitted,
    ChapterEvent,
    ChoicesReady,
    SceneReady,
    StoryFinished,
    blocked_event,
    error_event,
    stage,
)
from writory.pipeline.extract import (
    Entity,
    FactRules,
    MilestoneMark,
    OpenEdge,
    drop_unquoted_leaks,
    extract_changes,
    orphan_facts,
    without_facts,
)
from writory.pipeline.pacing import ChapterGoals, chapter_goals, stalled_after
from writory.pipeline.passages import Chunk, PagePool, opening_of
from writory.pipeline.scene import (
    Candidate,
    EarlierScene,
    Named,
    PromptTexts,
    Rewrite,
    SceneBrief,
    SceneOutline,
    keep_resolves,
    load_style_guide,
    outline_foreign_script,
    outline_messages,
    page_query,
    unplanned_threads,
    writer_messages,
)
from writory.pipeline.store import ChapterStore
from writory.pipeline.story_plan import StoryPlan
from writory.pipeline.summary import SUMMARY_CHAPTERS, summarize_chapter
from writory.quality import (
    IssueKind,
    check_meta_leak,
    check_scene,
    narration_instruction,
    normalize_dashes,
)
from writory.safety.classify import BEYOND_RULES, Feasibility
from writory.safety.leak import (
    LeakHit,
    LeakKind,
    check_leaks,
    forbidden_for_prompt,
    leak_names,
    protected_ids,
)
from writory.safety.moderate import Source, Verdict, moderate, rewrite_feedback
from writory.safety.overreach import check_overreach, needs_rewrite
from writory.safety.overreach import rewrite_feedback as overreach_feedback
from writory.safety.redact import redact
from writory.safety.reveal import auto_reveals

log = logging.getLogger(__name__)


# --- đầu vào, đầu ra -------------------------------------------------------------------------


@dataclass(frozen=True)
class ChapterRequest:
    """Yêu cầu viết chương kế tiếp chương đã commit.

    `player_action`: lựa chọn hoặc hành động tự viết dẫn tới chương này. Hành động tự viết phải qua
    `safety.classify_action` + `ensure_in_story` (G5) trước khi tới đây. Chữ này và `story_brief`
    luôn được bọc như dữ liệu (G4). `story_brief` là chữ người chơi đã đọc lúc khởi tạo, nên bộ dò
    lộ của cảnh và của lựa chọn tính nó là chữ đã thấy (D-52).

    `choice`: khi `player_action` đến từ một lựa chọn có sẵn (không phải ô tự viết), truyền cả lựa
    chọn đó để lời nói dối và nội tâm của nó được ghi vào gói của chính chương này (D-55).

    `feasibility`: bộ phân loại chấm hành động tự viết (G6, D-138). Vượt luật (`BEYOND_RULES`) thì
    mục tiêu chương đòi thất bại hay cái giá, và mỗi bản viết qua `safety.overreach`. None (lựa chọn
    có sẵn, chương 1) hay trong luật: không có gì thêm.
    """

    present_ids: tuple[str, ...]  # nhân vật có mặt đầu chương (nhân vật chính luôn được thêm)
    scene_count: int  # trong `story_lengths.scenes_per_chapter`
    story_brief: str
    player_action: str | None = None
    writer_tier: str | None = None  # id trong `models.writer_tiers`; None = mức đầu
    # Mức u tối của truyện, khoá trong `moderation.darkness_levels`; None = mức mặc định (G9, D-57)
    darkness_level: str | None = None
    commit_id: str | None = None  # None = tự sinh
    choice: Choice | None = None  # lựa chọn dẫn tới chương này; tác động của nó vào gói (D-55)
    feasibility: Feasibility | None = None  # G6, D-138: chỉ có với hành động tự viết


@dataclass(frozen=True)
class ReviewIssue:
    """Một lỗi của bản viết. `feedback` đưa cho model viết lại (được thấy lớp truth): không bao giờ
    vào log hay tới người chơi."""

    source: Literal["quality", "guard", "leak", "moderation", "overreach"]
    kind: str
    block: bool  # còn ở bản cuối thì không hiện cảnh (G2)
    feedback: str


@dataclass(frozen=True)
class Review:
    text: str  # đã chuẩn hoá: đúng chữ người chơi sẽ thấy
    package: ChangePackage  # gói của cảnh, đã bỏ cạnh bị người canh báo
    issues: tuple[ReviewIssue, ...]
    rejected: tuple[tuple[str, str], ...]  # cạnh bộ trích bỏ (mô tả, lý do)
    milestones: tuple[MilestoneMark, ...] = ()  # mốc đã diễn ra trên chữ này (D-116)


@dataclass(frozen=True)
class ReviewRecord:
    """Một lượt soát, giữ ở phía máy chủ để đo người canh và kiểm văn (D-43). `issues` có
    `feedback` (lớp truth): không vào log chung hay tới người chơi."""

    scene: int
    attempt: int
    # `fallback`: bản này còn lỗi chặn nên hiện bản trước, bản chỉ có lỗi mức viết lại (D-50)
    verdict: Literal["accept", "rewrite", "block", "fallback"]
    issues: tuple[ReviewIssue, ...]
    rejected: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class AcceptedScene:
    number: int
    text: str
    package: ChangePackage
    outline: SceneOutline
    attempts: int
    unresolved: list[ReviewIssue]  # lỗi còn lại ở bản được hiện (design §6.2 bước 4: ghi nhật ký)
    rejected: tuple[tuple[str, str], ...]
    # Id mạch đến hạn mà hết lượt thử dàn ý vẫn không dàn ý nào của chương định gỡ (D-82); lớp
    # truth, chỉ cho máy chủ đo.
    unplanned_threads: tuple[str, ...] = ()
    # Mốc đã diễn ra trong cảnh được hiện (D-116): chỉ cảnh được nhận mới có dấu; vào nút Chapter lúc
    # commit. Bản nháp bị trả lại không để lại dấu.
    milestones: tuple[MilestoneMark, ...] = ()


@dataclass
class ChapterOutcome:
    """Kết quả phía máy chủ. Không gửi cho người chơi."""

    chapter: int | None = None
    commit_id: str | None = None
    scenes: list[AcceptedScene] = field(default_factory=list)
    package: ChangePackage | None = None
    committed: bool = False
    blocked_scene: int | None = None
    blocked_code: ErrorCode | None = None  # mã của `scene_blocked` (D-138: G2 hay G6)
    choices: list[Choice] = field(default_factory=list)
    finished: bool = False  # chương cuối của kế hoạch đã ghi: truyện kết, không có lựa chọn
    summary: str | None = None  # tóm tắt chương vừa ghi (D-49); chữ nội bộ, không tới người chơi
    summary_error: ErrorCode | None = None  # tóm tắt lỗi: chương vẫn ghi, chương sau chạy thiếu
    summaries_missing: list[int] = field(default_factory=list)  # chương trước thiếu tóm tắt
    error: ErrorCode | None = None
    error_detail: str | None = None  # chi tiết cho log máy chủ (đã redact); không tới người chơi
    reviews: list[ReviewRecord] = field(default_factory=list)  # mọi lượt soát, theo thứ tự
    cost_usd: float = 0.0
    # Mục tiêu chương có câu đòi đổi pha (D-119); bộ đo ghi vào report.json.
    phase_shift: bool = False


# --- gói của chương ----------------------------------------------------------------------------


def chapter_node(number: int) -> NodeSpec:
    """Nút Chapter của chương đang viết: đích của REVEALED_TO_PLAYER và RESOLVED_IN."""
    return NodeSpec(id=f"ch{number}", label="Chapter", props={"number": number})


def merge_scene_packages(
    commit_id: str, node: NodeSpec, scene_packages: Sequence[ChangePackage],
    prelude: ChangePackage | None = None, milestones: Sequence[MilestoneMark] = (),
) -> ChangePackage:
    """Gói của chương = trạng thái cuối chương (graph-schema: "ở chương N" là cuối chương N).
    Cùng id cạnh ở nhiều cảnh: lấy bản của cảnh sau. Cảnh sau đóng cạnh do cảnh trước mở: cạnh
    không vào gói (một cạnh không mở và đóng trong cùng chương, D-21).

    `prelude`: tác động của lựa chọn dẫn tới chương (D-55), coi như xảy ra trước cảnh 1: nút của
    nó vào gói, cạnh và `close` của nó đi qua cùng phép gộp như một cảnh.

    `milestones`: mốc các cảnh được nhận đã đánh dấu (D-116). Vào thuộc tính `milestones` và
    `milestone_quotes` của nút Chapter; mốc đánh dấu hai lần thì giữ lần đầu."""
    marks = list({m.number: m for m in reversed(milestones)}.values())[::-1]
    if marks:
        node = node.model_copy(update={"props": {
            **node.props, "milestones": [m.number for m in marks],
            "milestone_quotes": [m.quote for m in marks]}})
    edges: dict[str, Any] = {}
    closes: dict[str, Any] = {}
    nodes: dict[str, Any] = {node.id: node, **{n.id: n for n in (prelude.nodes if prelude else [])}}
    for pkg in [*([prelude] if prelude else []), *scene_packages]:
        for n in pkg.nodes:  # Fact mới của các cảnh (D-93)
            nodes.setdefault(n.id, n)
        for c in pkg.close:
            if c.id in edges:
                del edges[c.id]
            else:
                closes[c.id] = c
        for e in pkg.edges:
            edges[e.id] = e
    return ChangePackage(commit_id=commit_id, nodes=list(nodes.values()),
                         edges=list(edges.values()), close=list(closes.values()))


def _slots(kind: str, source: str, target: str) -> set[tuple[str, ...]]:
    """Chỗ mà một cạnh chiếm: hai cạnh chung chỗ thì cạnh này thay cạnh kia. Nơi ở là một chỗ cho mỗi
    nhân vật hay đồ vật, người giữ là một chỗ cho mỗi đồ vật; đồ vật chỉ ở nơi hoặc được giữ (D-90),
    nên hai chỗ này chung nhau theo đồ vật. Các kiểu khác: theo cả cặp."""
    if kind == "LOCATED_AT":
        return {("LOCATED_AT", source), ("item", source)}
    if kind == "HOLDS":
        return {("HOLDS", target), ("item", target)}
    return {(kind, source, target)}


def _prune(package: ChangePackage, flagged: set[str],
           edge_ends: Mapping[str, tuple[str, str, str]]) -> ChangePackage:
    """Bỏ cạnh bị người canh báo: không ghi mâu thuẫn vào đồ thị (D-36). Cạnh bị bỏ không còn thay
    cạnh cũ, nên `close` của cạnh cũ đó cũng bỏ, nếu không quan hệ hay chỗ ở biến mất khỏi đồ thị
    (hồi quy ky-ao-vua-1 chương 9). `edge_ends`: id cạnh đang hiệu lực → (kiểu, từ, tới)."""
    kept = [e for e in package.edges if e.id not in flagged]
    if len(kept) == len(package.edges):
        return package
    cut = {slot for e in package.edges if e.id in flagged
           for slot in _slots(e.type, e.source, e.target)}
    still = {slot for e in kept for slot in _slots(e.type, e.source, e.target)}
    close = []
    for c in package.close:
        ends = edge_ends.get(c.id)
        slots = _slots(*ends) if ends is not None else set()
        if slots & cut and not slots & still:
            continue
        close.append(c)
    return package.model_copy(update={"edges": kept, "close": close})


# --- trạng thái đồ thị LangGraph ----------------------------------------------------------------


@dataclass
class _Deps:
    """Phụ thuộc của một lần chạy (runtime context của LangGraph): không nằm trong state."""

    request: ChapterRequest
    llm: MeteredClient
    store: ChapterStore
    config: AppConfig
    plan: StoryPlan
    style_guide: str
    # Chỉ cho bộ đo (evals): nhận câu hỏi và id đoạn của mỗi lần lấy đoạn trên trang (D-85).
    on_quotes: Callable[[dict[str, Any]], None] | None = None
    prompts: PromptTexts | None = None  # chỉ bộ đo: đề ghi đè (D-109)


class _State(TypedDict, total=False):
    chapter: int
    commit_id: str
    protagonist: str
    header: ChangePackage  # nút Chapter + tác động của lựa chọn (prelude), phủ trước các gói cảnh
    prelude: ChangePackage | None  # chỉ phần tác động của lựa chọn; None nếu không có gì để ghi
    catalogue: list[Entity]
    names: dict[str, Named]
    entity_names: list[str]  # tên, biệt danh của thực thể cho bộ kiểm lặp (D-51)
    base_edges: dict[str, OpenEdge]  # cạnh đang hiệu lực ở cuối chương trước
    scene_count: int
    scene: int  # cảnh đang làm, 1-based
    present: list[str]
    context: WriterContext
    page_pool: PagePool  # đoạn của các chương đã ghi, dựng một lần mỗi chương (D-85)
    goals: ChapterGoals  # mục tiêu của chương cho cảnh đang làm (D-49)
    outline: SceneOutline
    unplanned: list[str]  # mạch đến hạn dàn ý cảnh cuối vẫn bỏ sau mọi lượt thử (D-82)
    attempt: int
    draft: str
    finish_reason: str | None
    review: Review | None
    fallback: Review | None  # bản gần nhất của cảnh không có lỗi chặn (D-50, bổ sung D-36)
    verdict: Literal["accept", "rewrite", "block", "fallback"]
    reviews: list[ReviewRecord]
    accepted: list[AcceptedScene]
    blocked_scene: int
    blocked_code: ErrorCode
    package: ChangePackage
    committed: bool
    choices: list[Choice]
    final: bool  # chương này là chương cuối của bản kế hoạch
    finished: bool
    summaries: list[tuple[int, str]]  # tóm tắt chương N-2, N-1 có được (D-49)
    openings: list[tuple[int, str]]  # câu mở của các chương gần nhất, nếu cờ bật (D-110)
    summaries_missing: list[int]
    summary: str | None
    summary_error: ErrorCode | None


def _require(section, name: str):
    try:
        return section.require(name)
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None


def writer_tier(config: AppConfig, tier_id: str | None) -> WriterTier:
    """Mức model viết theo id; None = mức đầu. Danh sách rỗng là lỗi cấu hình."""
    tiers = config.models.writer_tiers
    if not tiers:
        raise WritoryError(ErrorCode.CONFIG_MODEL_NOT_SET, detail="models.writer_tiers rỗng")
    if tier_id is None:
        return tiers[0]
    for tier in tiers:
        if tier.id == tier_id:
            return tier
    raise ValueError(f"không có mức model viết {tier_id!r}")


CHAPTER_ROLES = ("outline", "extract", "summary", "choices", "moderate", "overreach")


def config_problems(config: AppConfig, tier_id: str | None = None) -> list[WritoryError]:
    """Mọi model và ngưỡng một chương cần mà còn null, theo thứ tự kiểm. Rỗng là đủ (D-36).
    Lệnh chạy cả truyện dùng hàm này để báo một lần mọi chỗ thiếu (D-42)."""
    problems: list[WritoryError] = []

    def check(fn, *args) -> None:
        try:
            fn(*args)
        except WritoryError as e:
            problems.append(e)

    for role in CHAPTER_ROLES:
        check(require_model, config.models.roles, role)
    check(writer_tier, config, tier_id)
    for section, name in (
        (config.limits.cost_usd, "per_scene"),
        (config.limits.cost_usd, "per_chapter"),
        (config.limits.cost_usd, "per_story"),
        (config.limits.context, "writer_max_neighbors"),
        (config.limits.context, "summary_max_chars"),
        (config.limits.context, "page_quotes_top_k"),
        (config.limits.context, "forbidden_names_max"),
        (config.limits.context, "standstill_chapters"),
        (config.quality.repetition, "ngram_words"),
        (config.quality.repetition, "max_repeats"),
        (config.quality.foreign_script, "latin_run_min_words"),
        (config.quality.narration, "min_words"),
        (config.quality.narration, _NARRATION_LIMIT[config.quality.narration.person]),
        (config.guard.relationship, "max_score_jump_without_event"),
    ):
        check(_require, section, name)
    check(_require, config.limits.facts, "max_new_per_chapter")
    if config.limits.facts.max_new_per_chapter:  # 0 = tắt: các giá trị còn lại không cần (D-93)
        for name in ("text_max_chars", "duplicate_overlap", "related_overlap", "grounded_min",
                     "writer_max_page_facts"):
            check(_require, config.limits.facts, name)
    if config.limits.context.previous_openings:  # 0 = tắt: độ dài không cần (D-110)
        check(_require, config.limits.context, "previous_opening_max_chars")
    if config.limits.context.page_quotes_top_k:  # 0 = tắt: hai giá trị còn lại không cần (D-85)
        for name in ("page_quotes_chunk_chars", "page_quotes_max_chars"):
            check(_require, config.limits.context, name)
    return problems


# Ngưỡng ngôi kể dùng tới, theo ngôi đã chốt (D-51).
_NARRATION_LIMIT = {"first": "first_person_min_per_100_words",
                    "third": "first_person_max_per_100_words"}


def overreach_of(request: ChapterRequest) -> Feasibility | None:
    """Loại vượt luật của hành động dẫn tới chương (G6, D-138), hay None nếu không phải."""
    if request.player_action and request.feasibility in BEYOND_RULES:
        return request.feasibility
    return None


def _preflight(d: _Deps) -> None:
    """Mọi model và ngưỡng cần cho chương phải đã đặt, trước lời gọi model đầu tiên."""
    problems = config_problems(d.config, d.request.writer_tier)
    if problems:
        raise problems[0]
    d.llm.tracker.ensure_budget()


def entity_names(catalogue: Sequence[Entity], view: PlayerView) -> list[str]:
    """Tên và biệt danh thực thể cho bộ kiểm lặp (D-51): tên thật và biệt danh của mọi nút có tên
    trong danh mục, cộng tên người chơi biết (`known_as`) và biệt danh trong player_view. Nhắc lại
    các tên này không phải lặp từ. Chỉ dùng để đếm, không vào prompt hay tới người chơi."""
    named = [t for e in catalogue if e.label in NAMED_LABELS for t in (e.text, *e.aliases)]
    known = [t for e in view.entries if e.kind in NAMED_LABELS for t in (e.text, *e.aliases)]
    return list(dict.fromkeys(named + known))


def _accepted_packages(state: _State) -> list[ChangePackage]:
    return [s.package for s in state.get("accepted", [])]


def _earlier_packages(state: _State) -> list[ChangePackage]:
    """Mọi gói đã có trước cảnh đang làm: phần mở đầu của chương (nút Chapter và tác động của
    lựa chọn) rồi các cảnh đã nhận."""
    return [state["header"], *_accepted_packages(state)]


def _open_edges(state: _State) -> dict[str, OpenEdge]:
    """Cạnh đang hiệu lực trước cảnh này: nền đã commit, phủ các cảnh trước (cùng nghĩa với
    OverlayState: `close` trước, cạnh mới sau)."""
    open_edges = dict(state["base_edges"])
    for pkg in _earlier_packages(state):
        for c in pkg.close:
            open_edges.pop(c.id, None)
        for e in pkg.edges:
            open_edges[e.id] = OpenEdge(e.id, e.type, e.source, e.target, e.props.get("known_as"))
    return open_edges


def _edge_ends(state: _State) -> dict[str, tuple[str, str, str]]:
    ends = {i: (o.type, o.source, o.target) for i, o in state["base_edges"].items()}
    for pkg in _earlier_packages(state):
        ends |= {e.id: (e.type, e.source, e.target) for e in pkg.edges}
    return ends


def _brief(d: _Deps, state: _State) -> SceneBrief:
    chapter, count = state["chapter"], d.request.scene_count
    lengths = d.config.story_lengths.chapter_chars
    act = next((a.name for a in d.plan.acts if a.from_chapter <= chapter <= a.to_chapter), None)
    earlier = tuple(EarlierScene(s.number, s.text, s.package) for s in state.get("accepted", []))
    # Tên cấm trên trang, cùng hàm với bộ dò lộ ở bước soát (D-91), trên nền đã commit cộng các
    # cảnh trước: đúng player_view mà bộ dò sẽ thấy, trừ hé lộ của chính cảnh đang viết.
    overlay = OverlayState(d.store.state(), _earlier_packages(state))
    forbidden = forbidden_for_prompt(
        overlay, view=player_view_of(overlay, chapter), plan=d.plan,
        story_brief=d.request.story_brief, scope="scene")
    return SceneBrief(
        chapter=chapter, scene=state["scene"], scene_count=count,
        min_chars=lengths.min // count, max_chars=lengths.max // count, act=act,
        story_brief=d.request.story_brief, player_action=d.request.player_action,
        earlier=earlier, goals=state["goals"], summaries=tuple(state["summaries"]),
        openings=tuple(state.get("openings", ())),
        forbidden=tuple(forbidden),
        forbidden_max=_require(d.config.limits.context, "forbidden_names_max"),
        prompts=d.prompts,
    )


def _writer_context(d: _Deps, state: _State, present: Sequence[str]) -> WriterContext:
    ctx = d.store.writer_context(
        state["chapter"] - 1, present, d.plan,
        max_neighbors=d.config.limits.context.writer_max_neighbors,
        personality_max_chars=d.config.limits.context.character_personality_max_chars,
        appearance_max_chars=d.config.limits.context.character_appearance_max_chars,
    )
    keep = d.config.limits.facts.writer_max_page_facts  # Fact sinh từ trang có trần (D-93)
    return replace(ctx, known_facts=cap_page_facts(ctx.known_facts, keep)) if keep else ctx


def _previous_openings(d: _Deps, chapter: int) -> list[tuple[int, str]]:
    """Câu mở của `previous_openings` chương gần nhất đã ghi (D-110). Tắt (0): không hỏi kho."""
    limits = d.config.limits.context
    keep = limits.previous_openings
    if keep <= 0:
        return []
    texts = d.store.chapter_texts(range(max(1, chapter - keep), chapter))
    found = ((c, opening_of(texts[c], _require(limits, "previous_opening_max_chars")))
             for c in sorted(texts))
    return [(c, text) for c, text in found if text]


def _fact_rules(d: _Deps, state: _State, scene: int) -> FactRules:
    """Luật Fact mới cho cảnh này: trần tính cho cả chương, trừ số đã tạo ở các cảnh trước (D-93)."""
    f = d.config.limits.facts
    cap = _require(f, "max_new_per_chapter")
    if cap == 0:
        return FactRules(0, 1, scene, 1.0, 1.0)
    made = sum(1 for s in state.get("accepted", []) for n in s.package.nodes if n.label == "Fact")
    return FactRules(
        max_new=max(0, cap - made), max_chars=_require(f, "text_max_chars"), scene=scene,
        duplicate_overlap=_require(f, "duplicate_overlap"), grounded_min=_require(f, "grounded_min"),
        related_overlap=_require(f, "related_overlap"))


def _quotes(d: _Deps, state: _State, outline: SceneOutline | None = None) -> list[Chunk]:
    """Đoạn đã hiện trên trang cho dàn ý (chưa có `outline`) hoặc cho model viết (D-85). Chỉ chữ của
    các chương đã ghi: các cảnh trước của chương này đã nằm nguyên văn trong đề (`_earlier`)."""
    pool, limits = state.get("page_pool"), d.config.limits.context
    if pool is None or pool.size == 0:  # tắt (`page_quotes_top_k: 0`) hoặc chưa có chương nào
        return []
    query = page_query(_brief(d, state), state["context"], outline)
    hits = pool.top(query, top_k=_require(limits, "page_quotes_top_k"),
                    max_chars=_require(limits, "page_quotes_max_chars"),
                    neighbors=limits.page_quotes_neighbors)
    if d.on_quotes is not None:
        d.on_quotes({"chapter": state["chapter"], "scene": state["scene"],
                     "attempt": state.get("attempt"), "role": "writer" if outline else "outline",
                     "query": query, "passages": [[c.chapter, c.index] for c in hits]})
    return hits


def _candidates(ctx: WriterContext, protagonist: str) -> list[Candidate]:
    """Nhân vật dàn ý được chọn cho có mặt: người đang có mặt và nhân vật lân cận trong ngữ cảnh."""
    out = {c.id: Candidate(c.id, Named(c.name, c.user_authored), c.id == protagonist)
           for c in ctx.present}
    for n in ctx.neighbors:
        if n.kind == "Character" and n.id not in out:
            out[n.id] = Candidate(n.id, Named(n.text, n.user_authored), n.id == protagonist)
    return list(out.values())


# --- các bước ----------------------------------------------------------------------------------


def _choice_prelude(
    choice: Choice | None, chapter: int, protagonist: str, base: GraphState,
    base_edges: Mapping[str, OpenEdge],
) -> ChangePackage | None:
    """Tác động của lựa chọn dẫn tới chương này (D-55), đọc trên đồ thị đã commit tới chương trước.
    Id không còn trong đồ thị là dữ liệu hỏng: dừng trước khi gọi model, không ghi nửa vời (G11).
    Người nghe đã chết bị bỏ; không ai nghe được thì lời dối không ghi (ghi log, không chữ)."""
    if choice is None:
        return None
    wanted = {protagonist, *choice.listeners, *choice.about}
    missing = sorted(wanted - set(base.node_labels(sorted(wanted))))
    if missing:
        raise WritoryError(ErrorCode.INTERNAL_ERROR,
                           detail=f"lựa chọn {choice.id} nhắc tới nút không có: {missing}")
    dead = {i for i in choice.listeners if base.edges_at("DIED_IN", chapter, source_id=i)}
    if dead:
        log.warning("chương %s: lựa chọn %s: bỏ người nghe đã chết %s", chapter, choice.id,
                    sorted(dead))
    open_feels = {o.target: o.id for o in base_edges.values()
                  if o.type == "FEELS" and o.source == protagonist}
    prelude = choice_effects(choice, chapter=chapter, protagonist=protagonist, dead=dead,
                             open_feels=open_feels)
    if choice.lie is not None and not prelude.nodes:
        log.warning("chương %s: lựa chọn %s: không ai còn sống để nghe lời dối, không ghi",
                    chapter, choice.id)
    return prelude if prelude.nodes or prelude.edges or prelude.close else None


async def _start(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    _preflight(d)
    if d.store.has_pending():
        raise WritoryError(ErrorCode.CHAPTER_PENDING, detail="truyện còn chương pending")
    committed = d.store.committed_chapter()
    if committed is None:
        raise ValueError("truyện chưa có chương 0 (thế giới lúc khởi tạo)")
    chapter = committed + 1
    if chapter > d.plan.total_chapters:
        raise WritoryError(ErrorCode.STORY_COMPLETE,
                           detail=f"chương {chapter} vượt kế hoạch {d.plan.total_chapters} chương")
    d.llm.tracker.start_chapter()
    node = chapter_node(chapter)
    catalogue = d.store.catalogue()
    if any(e.id == node.id for e in catalogue):
        raise ValueError(f"id nút chương {node.id} đã có trong truyện")
    catalogue.append(Entity(node.id, "Chapter", f"Chương {chapter}"))
    base = d.store.state()
    base_edges = {
        r.id: OpenEdge(r.id, r.type, r.source, r.target, r.props.get("known_as"))
        for t in EDGE_TYPES for r in base.edges_at(t, chapter)
    }
    protagonist = base.protagonist_id()
    prelude = _choice_prelude(d.request.choice, chapter, protagonist, base, base_edges)
    if prelude is not None:
        catalogue += [Entity.from_node(n.id, n.label, n.props) for n in prelude.nodes]
    # Tóm tắt các chương gần nhất (D-49). Thiếu thì chương vẫn chạy, chỉ ghi log và đếm.
    wanted = [c for c in range(chapter - SUMMARY_CHAPTERS, chapter) if c >= 1]
    found = d.store.summaries(wanted)
    missing = [c for c in wanted if c not in found]
    if missing:
        log.warning("chương %s: thiếu tóm tắt chương %s; viết tiếp không có chúng", chapter,
                    missing)
    # Tắt (`page_quotes_top_k: 0`): không dựng kho đoạn, đề y như khi chưa có tính năng (D-85).
    pool = None
    if _require(d.config.limits.context, "page_quotes_top_k") > 0:
        pool = PagePool(d.store.chapter_texts(range(1, chapter)),
                        chunk_chars=_require(d.config.limits.context, "page_quotes_chunk_chars"))
    return {
        **({"page_pool": pool} if pool is not None else {}),
        "openings": _previous_openings(d, chapter),
        "summaries": [(c, found[c]) for c in wanted if c in found],
        "summaries_missing": missing,
        "chapter": chapter,
        "commit_id": d.request.commit_id or f"ch{chapter}-{uuid.uuid4().hex[:12]}",
        "protagonist": protagonist,
        "header": ChangePackage(
            commit_id="header", nodes=[node, *(prelude.nodes if prelude else [])],
            edges=prelude.edges if prelude else [], close=prelude.close if prelude else []),
        "prelude": prelude,
        "catalogue": catalogue,
        "names": {e.id: Named(e.text, e.user_authored) for e in catalogue},
        "entity_names": entity_names(catalogue, d.store.player_view(committed)),
        "base_edges": base_edges,
        "scene_count": d.request.scene_count,
        "scene": 1,
        "present": list(dict.fromkeys([protagonist, *d.request.present_ids])),
        "accepted": [],
        "final": chapter >= d.plan.total_chapters,
    }


async def _context(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("context", scene=state["scene"]))
    d.llm.tracker.start_scene()
    # Mục tiêu đọc trên nền đã commit phủ các cảnh trước của chương: cảnh trước đã lộ hay đã gỡ
    # thì cảnh này không bị giục nữa (D-49).
    before = OverlayState(d.store.state(), _earlier_packages(state))
    # Mốc các cảnh trước của chính chương này đã đánh dấu: chưa vào nút Chapter, nên truyền riêng.
    marked = {m.number: state["chapter"] for s in state["accepted"] for m in s.milestones}
    return {"context": _writer_context(d, state, state["present"]),
            "goals": chapter_goals(
                d.plan, state["chapter"], before,
                milestone_lookahead=d.config.limits.context.milestone_lookahead,
                done_extra=marked,
                standstill_chapters=_require(d.config.limits.context, "standstill_chapters"),
                unplanned_goal=d.config.limits.context.unplanned_chapter_goal,
                idle_chapters=d.config.limits.context.idle_chapters,
                phase_shift_every=d.config.limits.context.phase_shift_every,
                overreach=overreach_of(d.request))}


async def _outline(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("outline", scene=state["scene"]))
    ctx, protagonist = state["context"], state["protagonist"]
    candidates = _candidates(ctx, protagonist)
    messages = outline_messages(_brief(d, state), ctx, candidates, state["names"],
                                _edge_ends(state), _quotes(d, state))
    model = require_model(d.config.models.roles, "outline")
    retries = d.config.limits.retries
    goals, last_scene = state["goals"], state["scene"] >= d.request.scene_count
    earlier = [s.outline for s in state["accepted"]]
    # Dàn ý đúng mọi điều trừ chỗ bỏ mạch đến hạn: dùng được khi hết lượt (D-82).
    usable: list[SceneOutline] = []

    async def call() -> SceneOutline:
        outline, _ = await d.llm.chat_json(model, messages, SceneOutline,
                                           extra=role_extra(d.config.models, "outline"))
        foreign = outline_foreign_script(outline, d.config.quality)
        if foreign:  # dàn ý phải viết tiếng Việt: sai thì như sai schema, thử lại (D-51, D-14)
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE,
                               detail=f"SceneOutline: chữ khác hệ ở {', '.join(foreign)}")
        # Id mạch lạ bị bỏ như `present` (G11); cảnh cuối mà mạch đến hạn không dàn ý nào của
        # chương định gỡ thì coi là sai, thử lại trong cùng ngân sách (D-82).
        outline = keep_resolves(outline, goals)
        missing = unplanned_threads(goals, [*earlier, outline], last_scene=last_scene)
        if missing:
            usable.append(outline)
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE,
                               detail=f"SceneOutline: cảnh cuối chương bỏ {len(missing)} mạch "
                                      "đến hạn")
        return outline

    try:
        outline = await with_json_retries(call, schema_retries=retries.extract_schema_retry,
                                          transient_retries=retries.llm_transient,
                                          backoff=retries.transient_backoff_seconds)
        unplanned: list[str] = []
    except WritoryError as e:
        if e.code is not ErrorCode.RETRY_LIMIT_REACHED or not usable:
            raise
        # Hết lượt mà dàn ý vẫn bỏ mạch đến hạn: không làm hỏng chương, viết tiếp với dàn ý cuối
        # dùng được; người canh vẫn đòi gỡ ở bước soát (D-49). Log chỉ ghi số, không id hay chữ.
        outline = usable[-1]
        unplanned = unplanned_threads(goals, [*earlier, outline], last_scene=last_scene)
        log.warning("chương %s cảnh %s: hết lượt thử dàn ý, %s mạch đến hạn chưa có dàn ý nào "
                    "định gỡ; viết tiếp", state["chapter"], state["scene"], len(unplanned))
    allowed = {c.id for c in candidates}
    present = list(dict.fromkeys([protagonist, *(p for p in outline.present if p in allowed)]))
    dropped = len([p for p in outline.present if p not in allowed])
    if dropped:
        log.info("chương %s cảnh %s: bỏ %s id có mặt ngoài danh sách (G11)",
                 state["chapter"], state["scene"], dropped)
    if set(present) != {c.id for c in ctx.present}:
        ctx = _writer_context(d, state, present)
    return {"outline": outline, "unplanned": unplanned, "present": present, "context": ctx,
            "attempt": 1, "review": None, "fallback": None}


async def _write(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("write", scene=state["scene"], attempt=state["attempt"]))
    review = state.get("review")
    rewrite = (Rewrite(review.text, tuple(i.feedback for i in review.issues))
               if review is not None else None)
    messages = writer_messages(d.style_guide, _brief(d, state), state["context"],
                               state["outline"], state["names"], _edge_ends(state), rewrite,
                               _quotes(d, state, state["outline"]))
    tier = writer_tier(d.config, d.request.writer_tier)
    extra = reasoning_extra(tier.reasoning)
    result = await with_retries(lambda: d.llm.chat(tier.model, messages, extra=extra),
                                max_retries=d.config.limits.retries.llm_transient,
                                retry_on=RETRY_TRANSIENT,
                                backoff=d.config.limits.retries.transient_backoff_seconds)
    if not result.text.strip():
        raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="model viết trả văn bản rỗng")
    return {"draft": result.text, "finish_reason": result.finish_reason}


def _leak_feedback(hit: LeakHit) -> str:
    """Lời nhắn cho lượt viết lại (lớp truth, không tới người chơi). Tên bị lộ thì nói người đọc
    đã biết nút đó là gì để dùng thay, hoặc nói nút chưa hé lộ nên đừng nêu tên (D-91)."""
    base = (f"lộ bí mật: đoạn «{hit.excerpt}» nói ra điều người đọc chưa được biết; "
            "viết lại để không nói ra điều đó")
    if hit.kind is not LeakKind.NAME:
        return base
    if hit.shown_as is not None:
        return (f"{base}. Người đọc chỉ biết nhân vật hay vật này là «{hit.shown_as}»: "
                f"dùng «{hit.shown_as}» thay vào")
    return f"{base}. Tên này chưa được hé lộ: đừng nêu tên, tả bằng vai hay dáng vẻ"


_QUALITY_LABELS = {
    IssueKind.LENGTH: "độ dài", IssueKind.REPETITION: "lặp từ", IssueKind.CLICHE: "sáo ngữ",
    IssueKind.FOREIGN_SCRIPT: "lẫn chữ khác hệ", IssueKind.DIALOGUE_FORMAT: "định dạng lời thoại",
    IssueKind.UNCLOSED_QUOTE: "ngoặc kép không đóng",
    IssueKind.META_LEAK: "lọt chữ của đề bài hoặc suy nghĩ của người viết",
    IssueKind.NARRATION_PERSON: "ngôi kể",
}


async def _review(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    chapter, scene, attempt = state["chapter"], state["scene"], state["attempt"]
    runtime.stream_writer(stage("review", scene=scene, attempt=attempt))
    cfg = d.config
    text = normalize_dashes(unicodedata.normalize("NFC", state["draft"]).strip())

    # 1. Kiểm văn bằng code (design §6.5 mục 5). Lọt suy luận/chữ của prompt là mức chặn (D-30).
    quality = check_scene(text, scenes_in_chapter=d.request.scene_count, quality=cfg.quality,
                          lengths=cfg.story_lengths, names=state["entity_names"]
                          ) + check_meta_leak(text)
    issues = [
        ReviewIssue("quality", q.kind.value, q.kind is IssueKind.META_LEAK,
                    f"{_QUALITY_LABELS[q.kind]}: {q.detail}; đoạn: «{q.excerpt}»")
        for q in quality
    ]
    if state.get("finish_reason") == "length":
        issues.append(ReviewIssue("quality", "truncated", False,
                                  "bản viết bị cắt giữa chừng vì quá dài; viết gọn hơn"))

    # 2. Trích thay đổi trên đúng chữ sẽ hiện (câu trích G3 đối chiếu với chữ này).
    retries = cfg.limits.retries
    extract_model = require_model(cfg.models.roles, "extract")
    entities, open_edges = state["catalogue"], list(_open_edges(state).values())
    # Nút có tên không được thêm tên mới (D-136): bí mật bảo vệ nó chưa có trong player_view trước cảnh
    # này (đường người chơi, bất kể khoảng lộ: tên mới nối hai tên trong sổ tay, D-61).
    locked = protected_ids(d.plan, player_view_of(
        OverlayState(d.store.state(), _earlier_packages(state)), chapter), "player_path")
    result = await with_json_retries(
        lambda: extract_changes(
            d.llm, extract_model, chapter=chapter, chapter_id=state["header"].nodes[0].id,
            commit_id=state["commit_id"], protagonist_id=state["protagonist"],
            chapter_text=text, entities=entities, open_edges=open_edges,
            # Mạch phải gỡ chưa gỡ trước cảnh này, kèm hạn; không kèm dàn ý định gỡ gì (D-82).
            threads=state["goals"].threads, extra=role_extra(cfg.models, "extract"),
            fact_rules=_fact_rules(d, state, scene),
            milestones=state["goals"].pending_milestones,
            milestones_done=dict(state["goals"].milestones_done), locked=locked,
        ),
        schema_retries=retries.extract_schema_retry, transient_retries=retries.llm_transient,
        backoff=retries.transient_backoff_seconds,
    )
    base = d.store.state()
    earlier = _earlier_packages(state)

    # 3. Tự hé lộ (D-62): nút có tên mà trang nêu, chưa có trong player_view (kể cả hé lộ bộ trích
    # vừa ghi), không phải nhân vật chính hay tên đang được kế hoạch bảo vệ (D-61).
    extracted = OverlayState(base, [*earlier, result.package])
    seen = player_view_of(extracted, chapter)
    here = state["header"].nodes[0].id
    auto = auto_reveals(
        text, chapter=chapter, chapter_id=here, names=extracted.named_nodes(), view=seen,
        skip={state["protagonist"], *protected_ids(d.plan, seen, "scene")},
        # Tên mới cho nút đã hé lộ (D-136): không với nút bị khoá, không với nút đã hé lộ ở chương này
        # (cùng id cạnh: gộp cảnh sẽ đè lần trước).
        no_new_name={*locked, *(e.source for p in [*earlier, result.package] for e in p.edges
                                if e.type == "REVEALED_TO_PLAYER" and e.target == here)},
    )
    scene_package = (result.package.model_copy(update={"edges": [*result.package.edges, *auto]})
                     if auto else result.package)
    if auto:
        log.info("chương %s cảnh %s lượt %s: tự hé lộ %s nút", chapter, scene, attempt, len(auto))

    # 4. Người canh bằng code trên nền đã commit + gói các cảnh trước (D-23).
    guard = check_scene_package(chapter=chapter, current=scene_package, earlier=earlier,
                                committed=base, plan=d.plan, config=cfg.guard,
                                last_scene=scene == d.request.scene_count)
    issues += [ReviewIssue("guard", g.kind.value, g.severity is Severity.BLOCK, g.detail)
               for g in guard]
    package = _prune(scene_package, {i for g in guard for i in g.ids}, _edge_ends(state))

    # 4b. Chữ lớp truth sổ tay sẽ hiện (Fact, Event, Lie mới vào player_view, kể cả Fact mới D-93) không
    # được nói tên hay bí mật mà câu trích của nó không nói (G2, D-134). Sau người canh, để người canh
    # vẫn thấy mọi hé lộ bộ trích ghi. Lộ thì bỏ cạnh (Fact mới: bỏ cả Fact), không chặn cảnh.
    package, held = drop_unquoted_leaks(package, before=OverlayState(base, earlier),
                                        chapter=chapter, protagonist_id=state["protagonist"],
                                        plan=d.plan, story_brief=d.request.story_brief)
    result.rejected.extend(held)
    orphans = orphan_facts(package)  # Fact mới mất hết KNOWS vào tay người canh (D-93)
    if orphans:
        package = without_facts(package, orphans)
        result.rejected.extend((f"Fact mới {i}", "thiếu KNOWS sau khi người canh cắt: bỏ Fact")
                               for i in sorted(orphans))

    # 5. Dò lộ trên chữ cảnh (G2, D-26, D-61), với player_view gồm cả các hé lộ bộ trích ghi cho
    # chính cảnh này. Hé lộ tự động của cảnh này không tính: câu trích của nó là câu của chính chữ
    # đang dò, tính vào thì mọi tên khác trong câu đó thành "đã thấy".
    auto_ids = {e.id for e in auto}
    checked = package.model_copy(update={"edges": [e for e in package.edges
                                                   if e.id not in auto_ids]})
    overlay = OverlayState(base, [*earlier, checked])
    hits = check_leaks(text, view=player_view_of(overlay, chapter), plan=d.plan,
                       truth_names=leak_names(overlay), story_brief=d.request.story_brief,
                       scope="scene")
    issues += [ReviewIssue("leak", h.kind.value, True, _leak_feedback(h)) for h in hits]

    # 6. Kiểm duyệt nội dung trên đúng chữ sẽ hiện (G9, D-57). Mọi vi phạm đều ở mức chặn: vượt
    # mức thì viết lại một lần, còn thì không hiện (bản sạch trước đó, nếu có, được hiện thay).
    mod = await moderate(text, source=Source.SCENE, llm=d.llm, config=cfg,
                         darkness_level=d.request.darkness_level)
    if mod.verdict is not Verdict.ALLOW:
        issues += [
            ReviewIssue("moderation", category.value, True,
                        rewrite_feedback(replace(mod, categories=(category,)),
                                         config=cfg.moderation,
                                         darkness_level=d.request.darkness_level))
            for category in mod.categories
        ]

    # 7. G6 (D-138): hành động tự viết vượt luật thì trang, tính tới hết cảnh này, không được chiều
    # theo: vượt luật thế giới chỉ được thất bại, vượt sức nhân vật thì thất bại hay trả giá
    # (`overreach.PASSES`). Không qua là lỗi chặn: viết lại trong cùng giới hạn, còn thì không hiện.
    overreach = overreach_of(d.request)
    if overreach is not None:
        assert d.request.player_action is not None
        judged = await check_overreach(
            action=d.request.player_action, feasibility=overreach,
            earlier=[s.text for s in state["accepted"]], scene_text=text, llm=d.llm, config=cfg)
        if needs_rewrite(overreach, judged.verdict):
            issues.append(ReviewIssue("overreach", judged.verdict.value, True,
                                      overreach_feedback(overreach)))

    review = Review(text, package, tuple(issues), tuple(result.rejected), result.milestones)
    if result.rejected:
        log.info("chương %s cảnh %s lượt %s: bộ trích bỏ %s cạnh", chapter, scene, attempt,
                 len(result.rejected))
    blocking = any(i.block for i in issues)
    # Bản gần nhất không có lỗi chặn: hiện nó nếu bản cuối có lỗi chặn (D-50, bổ sung D-36).
    fallback = state.get("fallback") if blocking else review
    if not issues:
        verdict = "accept"
    elif attempt < 1 + retries.rewrite_per_scene:
        verdict = "rewrite"
    elif blocking:
        verdict = "block" if fallback is None else "fallback"
    else:
        verdict = "accept"
    if issues:
        log.info("chương %s cảnh %s lượt %s: %s lỗi (%s) -> %s", chapter, scene, attempt,
                 len(issues), _kinds(issues), verdict)
    if verdict == "fallback":
        assert fallback is not None
        log.warning("chương %s cảnh %s: bản viết lại có lỗi chặn (%s); hiện bản trước, chỉ còn lỗi "
                    "mức viết lại (%s)", chapter, scene, _kinds([i for i in issues if i.block]),
                    _kinds(fallback.issues))
    record = ReviewRecord(scene, attempt, verdict, review.issues, review.rejected)
    return {"review": fallback if verdict == "fallback" else review, "verdict": verdict,
            "fallback": fallback, "reviews": [*state.get("reviews", []), record],
            "attempt": attempt + 1 if verdict == "rewrite" else attempt}


def _kinds(issues: Sequence[ReviewIssue]) -> str:
    """Chỉ loại lỗi, không chữ: an toàn để ghi log (G12, D-26)."""
    return ", ".join(sorted({f"{i.source}:{i.kind}" for i in issues}))


async def _accept(state: _State, runtime: Runtime[_Deps]) -> dict:
    review, scene = state["review"], state["scene"]
    assert review is not None
    if review.issues:
        log.warning("chương %s cảnh %s: hiện bản %s còn lỗi sau lượt viết lại: %s",
                    state["chapter"], scene, state["attempt"], _kinds(review.issues))
    runtime.stream_writer(SceneReady(scene=scene, text=review.text))
    accepted = AcceptedScene(scene, review.text, review.package, state["outline"],
                             state["attempt"], list(review.issues), review.rejected,
                             tuple(state.get("unplanned", [])), review.milestones)
    out: dict = {"accepted": [*state["accepted"], accepted], "scene": scene + 1, "review": None}
    fresh = [Entity.from_node(n.id, n.label, n.props) for n in review.package.nodes]
    if fresh:  # Fact mới của cảnh này có trong danh mục và tên của các cảnh sau (D-93)
        out["catalogue"] = [*state["catalogue"], *fresh]
        out["names"] = {**state["names"], **{e.id: Named(e.text, e.user_authored) for e in fresh}}
    return out


def blocked_code(issues: Sequence[ReviewIssue]) -> ErrorCode:
    """Mã của `scene_blocked`: SCENE_OVERREACH_BLOCKED khi lỗi chặn duy nhất là trang chiều theo
    hành động vượt luật (G6, D-138); còn lỗi chặn nào khác thì câu trung tính như cũ (D-26)."""
    blocking = {i.source for i in issues if i.block}
    if blocking == {"overreach"}:
        return ErrorCode.SCENE_OVERREACH_BLOCKED
    return ErrorCode.SCENE_LEAK_BLOCKED


async def _blocked(state: _State, runtime: Runtime[_Deps]) -> dict:
    review, scene = state["review"], state["scene"]
    assert review is not None
    log.warning("chương %s cảnh %s: không hiện cảnh sau %s lượt (%s)", state["chapter"], scene,
                state["attempt"], _kinds([i for i in review.issues if i.block]))
    code = blocked_code(review.issues)
    runtime.stream_writer(blocked_event(scene, code))
    return {"blocked_scene": scene, "blocked_code": code}


async def _commit(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("commit"))
    accepted = state["accepted"]
    package = merge_scene_packages(
        state["commit_id"], state["header"].nodes[0], [s.package for s in accepted],
        prelude=state["prelude"], milestones=[m for s in accepted for m in s.milestones])
    d.store.commit(state["chapter"], [s.text for s in accepted], package)
    runtime.stream_writer(ChapterCommitted(chapter=state["chapter"]))
    return {"package": package, "committed": True}


async def _summary(state: _State, runtime: Runtime[_Deps]) -> dict:
    """Tóm tắt chương vừa ghi cho đề các chương sau (D-49). Không phát sự kiện: chữ nội bộ.

    Chương đã ghi (D-6): mọi lỗi ở đây chỉ ghi log (loại lỗi, không chữ) rồi đi tiếp; chương sau
    chạy thiếu tóm tắt này."""
    d = runtime.context
    chapter, cfg = state["chapter"], d.config
    d.llm.tracker.start_scene()  # trần mỗi cảnh áp cho bước tóm tắt như một bước riêng
    pc = state["names"].get(state["protagonist"])  # tên chuẩn trong đồ thị (D-112)
    try:
        text = await summarize_chapter(
            d.llm, require_model(cfg.models.roles, "summary"), chapter=chapter,
            scenes=[s.text for s in state["accepted"]],
            max_chars=_require(cfg.limits.context, "summary_max_chars"),
            retries=cfg.limits.retries, extra=role_extra(cfg.models, "summary"),
            protagonist_name=pc.text if pc is not None else None,
            protagonist_user_authored=pc.user_authored if pc is not None else False,
        )
        d.store.save_summary(chapter, text)
    except WritoryError as e:
        log.warning("chương %s: không tạo được tóm tắt (%s); chương đã ghi giữ nguyên", chapter, e)
        return {"summary_error": e.code}
    except Exception:  # noqa: BLE001 — chương đã ghi: lỗi tóm tắt không được làm hỏng nó (D-6)
        log.error("chương %s: lỗi không lường trước khi tóm tắt:\n%s", chapter,
                  redact(traceback.format_exc()))
        return {"summary_error": ErrorCode.INTERNAL_ERROR}
    return {"summary": text}


async def _choices(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("choices"))
    d.llm.tracker.start_scene()  # trần mỗi cảnh áp cho bước lựa chọn như một bước riêng
    chapter = state["chapter"]
    choices = await make_choices(
        d.llm, require_model(d.config.models.roles, "choices"),
        view=d.store.player_view(chapter), protagonist_id=state["protagonist"],
        last_scene_text=state["accepted"][-1].text,
        truth_names=leak_names(d.store.state()), plan=d.plan, story_brief=d.request.story_brief,
        retries=d.config.limits.retries, extra=role_extra(d.config.models, "choices"),
        moderate=partial(moderate, source=Source.CHOICES, llm=d.llm, config=d.config,
                         darkness_level=d.request.darkness_level),
        stalled=stalled_after(d.store.state(), chapter,
                              _require(d.config.limits.context, "standstill_chapters"),
                              idle_threshold=d.config.limits.context.idle_chapters),
        system_prompt=d.prompts.choices_system if d.prompts is not None else None,
    )
    runtime.stream_writer(ChoicesReady(chapter=chapter,
                                       choices=[c.for_player() for c in choices]))
    return {"choices": choices}


async def _finish(state: _State, runtime: Runtime[_Deps]) -> dict:
    """Chương cuối của kế hoạch đã ghi: truyện kết, không tạo lựa chọn (design §4.3, D-50)."""
    runtime.stream_writer(StoryFinished(chapter=state["chapter"]))
    return {"finished": True}


def _after_review(state: _State) -> str:
    return {"accept": "accept", "rewrite": "write", "block": "blocked",
            "fallback": "accept"}[state["verdict"]]


def _after_accept(state: _State) -> str:
    return "context" if len(state["accepted"]) < state["scene_count"] else "commit"


def _after_commit(state: _State) -> str:
    """Chương cuối: không tóm tắt (không còn chương sau), không lựa chọn."""
    return "finish" if state["final"] else "summary"


def _build():
    g = StateGraph(_State, context_schema=_Deps)
    for name, node in (("start", _start), ("context", _context), ("outline", _outline),
                       ("write", _write), ("review", _review), ("accept", _accept),
                       ("blocked", _blocked), ("commit", _commit), ("summary", _summary),
                       ("choices", _choices), ("finish", _finish)):
        g.add_node(name, node)
    g.add_edge(START, "start")
    g.add_edge("start", "context")
    g.add_edge("context", "outline")
    g.add_edge("outline", "write")
    g.add_edge("write", "review")
    g.add_conditional_edges("review", _after_review, ["accept", "write", "blocked"])
    g.add_conditional_edges("accept", _after_accept, ["context", "commit"])
    g.add_edge("blocked", END)
    g.add_conditional_edges("commit", _after_commit, ["summary", "finish"])
    g.add_edge("summary", "choices")
    g.add_edge("choices", END)
    g.add_edge("finish", END)
    return g.compile()


_GRAPH = _build()


# --- chạy ------------------------------------------------------------------------------------

_END = object()  # dấu hết sự kiện, từ `_pump` tới `events()`


class ChapterRun:
    """Một lần viết chương. `events()` phát sự kiện cho người chơi; sau đó `outcome` có kết quả
    phía máy chủ. Mọi lời gọi `llm` đi qua `MeteredClient(llm, tracker)` (G8)."""

    def __init__(
        self, request: ChapterRequest, *, llm: LLMClient, store: ChapterStore,
        config: AppConfig, plan: StoryPlan, tracker: CostTracker, style_guide: str | None = None,
        on_quotes: Callable[[dict[str, Any]], None] | None = None,
        prompts: PromptTexts | None = None,
    ) -> None:
        allowed = config.story_lengths.scenes_per_chapter
        if not allowed.min <= request.scene_count <= allowed.max:
            raise ValueError(f"scene_count={request.scene_count} ngoài khoảng "
                             f"{allowed.min}–{allowed.max} (story_lengths.yaml)")
        config.moderation.ceiling(request.darkness_level)  # mức u tối lạ thì báo ngay (D-57)
        guide = style_guide if style_guide is not None else load_style_guide()
        # Câu ngôi kể lấy từ cùng config mà kiểm văn dùng để bắt lệch ngôi (D-51).
        self._deps = _Deps(request, MeteredClient(llm, tracker), store, config, plan,
                           f"{guide}\n\n{narration_instruction(config.quality)}", on_quotes,
                           prompts)
        self.outcome = ChapterOutcome()
        self._task: asyncio.Task[None] | None = None
        self._cancel_sent = False

    async def events(self) -> AsyncIterator[ChapterEvent]:
        """Sự kiện của chương, theo thứ tự. Chỉ gọi một lần.

        Đồ thị chạy trong task riêng (`_pump`), không trong task của người đọc. Người đọc bị huỷ
        hay bỏ dở thì task đó nhận đúng một lần huỷ kiểu asyncio, nên LangGraph dọn được: huỷ node
        đang chạy, kể cả lời gọi model đang chờ. FastAPI huỷ stream SSE bằng cancel scope của anyio
        (huỷ lặp lại ở mọi lần chờ); huỷ kiểu đó thẳng vào LangGraph làm task dọn dẹp của nó bị huỷ
        trước khi chạy và node chạy tiếp mồ côi (D-63). Nơi cần biết chắc đường đi đã dừng hẳn (ví
        dụ trước khi nhả khoá của truyện) gọi `aclose()`."""
        if self._task is not None:
            raise RuntimeError("ChapterRun.events() chỉ chạy một lần")
        queue: asyncio.Queue[Any] = asyncio.Queue(maxsize=1)  # đồ thị không chạy trước người đọc
        task = self._task = asyncio.create_task(self._pump(queue), name="chapter-run")
        try:
            while True:
                if task.done():
                    while not queue.empty():
                        event = queue.get_nowait()
                        if event is _END:
                            return
                        yield event
                    task.result()  # task dừng mà không có dấu kết thúc: nêu lỗi của nó
                    return
                getter = asyncio.ensure_future(queue.get())
                try:
                    await asyncio.wait((getter, task), return_when=asyncio.FIRST_COMPLETED)
                finally:
                    if not getter.done():
                        getter.cancel()  # Queue.get bị huỷ không làm mất phần tử
                if getter.done() and not getter.cancelled():
                    event = getter.result()
                    if event is _END:
                        return
                    yield event
        finally:
            self._cancel()  # đã xong thì không làm gì

    async def aclose(self) -> None:
        """Huỷ đường đi nếu còn chạy và chờ nó dừng hẳn: LangGraph đã huỷ xong node đang chạy, mọi
        `finally` của lời gọi bị huỷ (kể cả nhật ký chi phí) đã chạy. Gọi lại, hay gọi khi đã xong:
        không làm gì."""
        task = self._task
        if task is None or task.done():
            return
        self._cancel()
        await asyncio.wait((task,))

    def _cancel(self) -> None:
        """Huỷ đúng một lần: lần huỷ thứ hai rơi vào lúc LangGraph đang dọn sẽ cắt ngang việc dọn."""
        task = self._task
        if task is not None and not task.done() and not self._cancel_sent:
            self._cancel_sent = True
            task.cancel()

    async def _pump(self, queue: asyncio.Queue[Any]) -> None:
        run = self._run()
        try:
            async for event in run:
                await queue.put(event)
            await queue.put(_END)
        finally:
            await run.aclose()  # `async for` không tự đóng generator khi bị huỷ giữa chừng

    async def _run(self) -> AsyncIterator[ChapterEvent]:
        final: Mapping[str, Any] = {}
        stream = _GRAPH.astream({"accepted": []}, context=self._deps,
                                stream_mode=["custom", "values"], version="v2")
        try:
            try:
                async for chunk in stream:
                    if chunk["type"] == "custom":
                        yield chunk["data"]
                    elif chunk["type"] == "values":
                        final = chunk["data"]
            finally:
                await stream.aclose()  # bị đóng ở `yield`: LangGraph huỷ node đang chạy ngay đây
        except WritoryError as e:
            log.warning("viết chương dừng: %s", e)  # str() đã redact chi tiết
            self.outcome.error = e.code
            self.outcome.error_detail = e.detail
            yield error_event(e)
        except Exception:  # noqa: BLE001 — ranh giới tới người chơi: lỗi lạ thành INTERNAL_ERROR
            log.error("viết chương: lỗi không lường trước:\n%s", redact(traceback.format_exc()))
            err = WritoryError(ErrorCode.INTERNAL_ERROR)
            self.outcome.error = err.code
            yield error_event(err)
        self._fill(final)

    def _fill(self, final: Mapping[str, Any]) -> None:
        out = self.outcome
        out.chapter = final.get("chapter")
        out.commit_id = final.get("commit_id")
        out.scenes = list(final.get("accepted", []))
        out.package = final.get("package")
        out.committed = bool(final.get("committed", False))
        out.blocked_scene = final.get("blocked_scene")
        out.blocked_code = final.get("blocked_code")
        out.choices = list(final.get("choices", []))
        out.finished = bool(final.get("finished", False))
        out.summary = final.get("summary")
        out.summary_error = final.get("summary_error")
        out.summaries_missing = list(final.get("summaries_missing", []))
        out.reviews = list(final.get("reviews", []))
        goals = final.get("goals")
        out.phase_shift = goals is not None and goals.phase_shift is not None
        out.cost_usd = self._deps.llm.tracker.chapter_usd
