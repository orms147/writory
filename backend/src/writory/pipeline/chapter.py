"""Đường đi một chương (design §6.2; D-1, D-6, D-8, D-36). Toàn bộ đồ thị LangGraph nằm ở đây.

Mỗi cảnh: dựng ngữ cảnh và mục tiêu của chương (`pipeline.pacing`, D-49) → dàn ý → viết → soát
(chuẩn hoá dấu gạch, kiểm văn, trích thay đổi, người canh, dò lộ) → viết lại tối đa
`limits.retries.rewrite_per_scene` lần → hiện. Bản viết lại có lỗi chặn mà bản trước không có thì
hiện bản trước (D-50, bổ sung D-36). Hết cảnh cuối: gộp gói các cảnh → `store.commit` (D-6, tất cả
hoặc không gì) → tóm tắt chương (`pipeline.summary`, D-49; lỗi không làm hỏng chương đã ghi) → tạo
lựa chọn từ player_view (G1). Đề của chương N nhận tóm tắt chương N-1, N-2. Chương cuối của bản
kế hoạch thì không tóm tắt, không tạo lựa chọn mà phát `story_finished` (D-50); chương sau đó bị
từ chối (`STORY_COMPLETE`).

- Người chơi chỉ nhận sự kiện (`pipeline.events`): chữ cảnh đã qua mọi phép kiểm (D-1), lựa chọn đã
  qua dò lộ (G2), câu lỗi G12. Cảnh chưa kiểm không bao giờ được phát ra.
- Không ghi gì trước bước ghi chương. Lỗi giữa chừng (mã G12) dừng chương; đồ thị và Postgres giữ
  nguyên (G11). Lỗi ở bước lựa chọn xảy ra sau khi chương đã ghi; gọi lại `make_choices`.
- Mọi lời gọi model qua `MeteredClient` (G8); cấu hình còn null thì báo lỗi trước lời gọi đầu.
- Nhật ký lỗi còn lại sau lượt viết lại chỉ ghi loại lỗi (không ghi chữ: có thể chứa bí mật).
"""

import logging
import traceback
import unicodedata
import uuid
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from writory.config import AppConfig, LimitNotSetError, WriterTier
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, NodeSpec, PlayerView
from writory.graph.context import WriterContext
from writory.graph.schema import EDGE_TYPES, NAMED_LABELS
from writory.guard import Severity, check_scene_package
from writory.guard.state import OverlayState, player_view_of
from writory.llm.base import LLMClient, reasoning_extra, require_model, role_extra
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.retry import RETRY_TRANSIENT, with_json_retries, with_retries
from writory.pipeline.choices import Choice, make_choices
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
from writory.pipeline.extract import Entity, OpenEdge, extract_changes
from writory.pipeline.pacing import ChapterGoals, chapter_goals
from writory.pipeline.scene import (
    Candidate,
    EarlierScene,
    Named,
    Rewrite,
    SceneBrief,
    SceneOutline,
    load_style_guide,
    outline_foreign_script,
    outline_messages,
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
from writory.safety.leak import check_leaks, leak_names
from writory.safety.redact import redact

log = logging.getLogger(__name__)


# --- đầu vào, đầu ra -------------------------------------------------------------------------


@dataclass(frozen=True)
class ChapterRequest:
    """Yêu cầu viết chương kế tiếp chương đã commit.

    `player_action`: lựa chọn hoặc hành động tự viết dẫn tới chương này. Hành động tự viết phải qua
    `safety.classify_action` + `ensure_in_story` (G5) trước khi tới đây. Chữ này và `story_brief`
    luôn được bọc như dữ liệu (G4). `story_brief` là chữ người chơi đã đọc lúc khởi tạo, nên bộ dò
    lộ của cảnh và của lựa chọn tính nó là chữ đã thấy (D-52).
    """

    present_ids: tuple[str, ...]  # nhân vật có mặt đầu chương (nhân vật chính luôn được thêm)
    scene_count: int  # trong `story_lengths.scenes_per_chapter`
    story_brief: str
    player_action: str | None = None
    writer_tier: str | None = None  # id trong `models.writer_tiers`; None = mức đầu
    commit_id: str | None = None  # None = tự sinh


@dataclass(frozen=True)
class ReviewIssue:
    """Một lỗi của bản viết. `feedback` đưa cho model viết lại (được thấy lớp truth): không bao giờ
    vào log hay tới người chơi."""

    source: Literal["quality", "guard", "leak"]
    kind: str
    block: bool  # còn ở bản cuối thì không hiện cảnh (G2)
    feedback: str


@dataclass(frozen=True)
class Review:
    text: str  # đã chuẩn hoá: đúng chữ người chơi sẽ thấy
    package: ChangePackage  # gói của cảnh, đã bỏ cạnh bị người canh báo
    issues: tuple[ReviewIssue, ...]
    rejected: tuple[tuple[str, str], ...]  # cạnh bộ trích bỏ (mô tả, lý do)


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


@dataclass
class ChapterOutcome:
    """Kết quả phía máy chủ. Không gửi cho người chơi."""

    chapter: int | None = None
    commit_id: str | None = None
    scenes: list[AcceptedScene] = field(default_factory=list)
    package: ChangePackage | None = None
    committed: bool = False
    blocked_scene: int | None = None
    choices: list[Choice] = field(default_factory=list)
    finished: bool = False  # chương cuối của kế hoạch đã ghi: truyện kết, không có lựa chọn
    summary: str | None = None  # tóm tắt chương vừa ghi (D-49); chữ nội bộ, không tới người chơi
    summary_error: ErrorCode | None = None  # tóm tắt lỗi: chương vẫn ghi, chương sau chạy thiếu
    summaries_missing: list[int] = field(default_factory=list)  # chương trước thiếu tóm tắt
    error: ErrorCode | None = None
    error_detail: str | None = None  # chi tiết cho log máy chủ (đã redact); không tới người chơi
    reviews: list[ReviewRecord] = field(default_factory=list)  # mọi lượt soát, theo thứ tự
    cost_usd: float = 0.0


# --- gói của chương ----------------------------------------------------------------------------


def chapter_node(number: int) -> NodeSpec:
    """Nút Chapter của chương đang viết: đích của REVEALED_TO_PLAYER và RESOLVED_IN."""
    return NodeSpec(id=f"ch{number}", label="Chapter", props={"number": number})


def merge_scene_packages(
    commit_id: str, node: NodeSpec, scene_packages: Sequence[ChangePackage]
) -> ChangePackage:
    """Gói của chương = trạng thái cuối chương (graph-schema: "ở chương N" là cuối chương N).
    Cùng id cạnh ở nhiều cảnh: lấy bản của cảnh sau. Cảnh sau đóng cạnh do cảnh trước mở: cạnh
    không vào gói (một cạnh không mở và đóng trong cùng chương, D-21)."""
    edges: dict[str, Any] = {}
    closes: dict[str, Any] = {}
    for pkg in scene_packages:
        for c in pkg.close:
            if c.id in edges:
                del edges[c.id]
            else:
                closes[c.id] = c
        for e in pkg.edges:
            edges[e.id] = e
    return ChangePackage(commit_id=commit_id, nodes=[node], edges=list(edges.values()),
                         close=list(closes.values()))


def _prune(package: ChangePackage, flagged: set[str]) -> ChangePackage:
    """Bỏ cạnh bị người canh báo: không ghi mâu thuẫn vào đồ thị (D-36)."""
    kept = [e for e in package.edges if e.id not in flagged]
    if len(kept) == len(package.edges):
        return package
    return package.model_copy(update={"edges": kept})


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


class _State(TypedDict, total=False):
    chapter: int
    commit_id: str
    protagonist: str
    header: ChangePackage  # gói chỉ có nút Chapter, phủ trước các gói cảnh
    catalogue: list[Entity]
    names: dict[str, Named]
    entity_names: list[str]  # tên, biệt danh của thực thể cho bộ kiểm lặp (D-51)
    base_edges: dict[str, OpenEdge]  # cạnh đang hiệu lực ở cuối chương trước
    scene_count: int
    scene: int  # cảnh đang làm, 1-based
    present: list[str]
    context: WriterContext
    goals: ChapterGoals  # mục tiêu của chương cho cảnh đang làm (D-49)
    outline: SceneOutline
    attempt: int
    draft: str
    finish_reason: str | None
    review: Review | None
    fallback: Review | None  # bản gần nhất của cảnh không có lỗi chặn (D-50, bổ sung D-36)
    verdict: Literal["accept", "rewrite", "block", "fallback"]
    reviews: list[ReviewRecord]
    accepted: list[AcceptedScene]
    blocked_scene: int
    package: ChangePackage
    committed: bool
    choices: list[Choice]
    final: bool  # chương này là chương cuối của bản kế hoạch
    finished: bool
    summaries: list[tuple[int, str]]  # tóm tắt chương N-2, N-1 có được (D-49)
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


CHAPTER_ROLES = ("outline", "extract", "summary", "choices")


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
        (config.quality.repetition, "ngram_words"),
        (config.quality.repetition, "max_repeats"),
        (config.quality.foreign_script, "latin_run_min_words"),
        (config.quality.narration, "min_words"),
        (config.quality.narration, _NARRATION_LIMIT[config.quality.narration.person]),
        (config.guard.relationship, "max_score_jump_without_event"),
    ):
        check(_require, section, name)
    return problems


# Ngưỡng ngôi kể dùng tới, theo ngôi đã chốt (D-51).
_NARRATION_LIMIT = {"first": "first_person_min_per_100_words",
                    "third": "first_person_max_per_100_words"}


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


def _open_edges(state: _State) -> dict[str, OpenEdge]:
    """Cạnh đang hiệu lực trước cảnh này: nền đã commit, phủ các cảnh trước (cùng nghĩa với
    OverlayState: `close` trước, cạnh mới sau)."""
    open_edges = dict(state["base_edges"])
    for pkg in _accepted_packages(state):
        for c in pkg.close:
            open_edges.pop(c.id, None)
        for e in pkg.edges:
            open_edges[e.id] = OpenEdge(e.id, e.type, e.source, e.target)
    return open_edges


def _edge_ends(state: _State) -> dict[str, tuple[str, str, str]]:
    ends = {i: (o.type, o.source, o.target) for i, o in state["base_edges"].items()}
    for pkg in _accepted_packages(state):
        ends |= {e.id: (e.type, e.source, e.target) for e in pkg.edges}
    return ends


def _brief(d: _Deps, state: _State) -> SceneBrief:
    chapter, count = state["chapter"], d.request.scene_count
    lengths = d.config.story_lengths.chapter_chars
    act = next((a.name for a in d.plan.acts if a.from_chapter <= chapter <= a.to_chapter), None)
    earlier = tuple(EarlierScene(s.number, s.text, s.package) for s in state.get("accepted", []))
    return SceneBrief(
        chapter=chapter, scene=state["scene"], scene_count=count,
        min_chars=lengths.min // count, max_chars=lengths.max // count, act=act,
        story_brief=d.request.story_brief, player_action=d.request.player_action,
        earlier=earlier, goals=state["goals"], summaries=tuple(state["summaries"]),
    )


def _writer_context(d: _Deps, state: _State, present: Sequence[str]) -> WriterContext:
    return d.store.writer_context(
        state["chapter"] - 1, present, d.plan,
        max_neighbors=d.config.limits.context.writer_max_neighbors,
    )


def _candidates(ctx: WriterContext, protagonist: str) -> list[Candidate]:
    """Nhân vật dàn ý được chọn cho có mặt: người đang có mặt và nhân vật lân cận trong ngữ cảnh."""
    out = {c.id: Candidate(c.id, Named(c.name, c.user_authored), c.id == protagonist)
           for c in ctx.present}
    for n in ctx.neighbors:
        if n.kind == "Character" and n.id not in out:
            out[n.id] = Candidate(n.id, Named(n.text, n.user_authored), n.id == protagonist)
    return list(out.values())


# --- các bước ----------------------------------------------------------------------------------


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
        r.id: OpenEdge(r.id, r.type, r.source, r.target)
        for t in EDGE_TYPES for r in base.edges_at(t, chapter)
    }
    protagonist = base.protagonist_id()
    # Tóm tắt các chương gần nhất (D-49). Thiếu thì chương vẫn chạy, chỉ ghi log và đếm.
    wanted = [c for c in range(chapter - SUMMARY_CHAPTERS, chapter) if c >= 1]
    found = d.store.summaries(wanted)
    missing = [c for c in wanted if c not in found]
    if missing:
        log.warning("chương %s: thiếu tóm tắt chương %s; viết tiếp không có chúng", chapter,
                    missing)
    return {
        "summaries": [(c, found[c]) for c in wanted if c in found],
        "summaries_missing": missing,
        "chapter": chapter,
        "commit_id": d.request.commit_id or f"ch{chapter}-{uuid.uuid4().hex[:12]}",
        "protagonist": protagonist,
        "header": ChangePackage(commit_id="header", nodes=[node]),
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
    before = OverlayState(d.store.state(), [state["header"], *_accepted_packages(state)])
    return {"context": _writer_context(d, state, state["present"]),
            "goals": chapter_goals(d.plan, state["chapter"], before)}


async def _outline(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("outline", scene=state["scene"]))
    ctx, protagonist = state["context"], state["protagonist"]
    candidates = _candidates(ctx, protagonist)
    messages = outline_messages(_brief(d, state), ctx, candidates, state["names"],
                                _edge_ends(state))
    model = require_model(d.config.models.roles, "outline")
    retries = d.config.limits.retries

    async def call() -> SceneOutline:
        outline, _ = await d.llm.chat_json(model, messages, SceneOutline,
                                           extra=role_extra(d.config.models, "outline"))
        foreign = outline_foreign_script(outline, d.config.quality)
        if foreign:  # dàn ý phải viết tiếng Việt: sai thì như sai schema, thử lại (D-51, D-14)
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE,
                               detail=f"SceneOutline: chữ khác hệ ở {', '.join(foreign)}")
        return outline

    outline = await with_json_retries(call, schema_retries=retries.extract_schema_retry,
                                      transient_retries=retries.llm_transient)
    allowed = {c.id for c in candidates}
    present = list(dict.fromkeys([protagonist, *(p for p in outline.present if p in allowed)]))
    dropped = len([p for p in outline.present if p not in allowed])
    if dropped:
        log.info("chương %s cảnh %s: bỏ %s id có mặt ngoài danh sách (G11)",
                 state["chapter"], state["scene"], dropped)
    if set(present) != {c.id for c in ctx.present}:
        ctx = _writer_context(d, state, present)
    return {"outline": outline, "present": present, "context": ctx, "attempt": 1, "review": None,
            "fallback": None}


async def _write(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("write", scene=state["scene"], attempt=state["attempt"]))
    review = state.get("review")
    rewrite = (Rewrite(review.text, tuple(i.feedback for i in review.issues))
               if review is not None else None)
    messages = writer_messages(d.style_guide, _brief(d, state), state["context"],
                               state["outline"], state["names"], _edge_ends(state), rewrite)
    tier = writer_tier(d.config, d.request.writer_tier)
    extra = reasoning_extra(tier.reasoning)
    result = await with_retries(lambda: d.llm.chat(tier.model, messages, extra=extra),
                                max_retries=d.config.limits.retries.llm_transient,
                                retry_on=RETRY_TRANSIENT)
    if not result.text.strip():
        raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="model viết trả văn bản rỗng")
    return {"draft": result.text, "finish_reason": result.finish_reason}


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
    result = await with_json_retries(
        lambda: extract_changes(
            d.llm, extract_model, chapter=chapter, chapter_id=state["header"].nodes[0].id,
            commit_id=state["commit_id"], protagonist_id=state["protagonist"],
            chapter_text=text, entities=entities, open_edges=open_edges,
            extra=role_extra(cfg.models, "extract"),
        ),
        schema_retries=retries.extract_schema_retry, transient_retries=retries.llm_transient,
    )

    # 3. Người canh bằng code trên nền đã commit + gói các cảnh trước (D-23).
    base = d.store.state()
    earlier = [state["header"], *_accepted_packages(state)]
    guard = check_scene_package(chapter=chapter, current=result.package, earlier=earlier,
                                committed=base, plan=d.plan, config=cfg.guard,
                                last_scene=scene == d.request.scene_count)
    issues += [ReviewIssue("guard", g.kind.value, g.severity is Severity.BLOCK, g.detail)
               for g in guard]
    package = _prune(result.package, {i for g in guard for i in g.ids})

    # 4. Dò lộ trên chữ cảnh, với player_view gồm cả các hé lộ của chính cảnh này (G2, D-26).
    overlay = OverlayState(base, [*earlier, package])
    hits = check_leaks(text, view=player_view_of(overlay, chapter), plan=d.plan,
                       truth_names=leak_names(overlay), story_brief=d.request.story_brief)
    issues += [ReviewIssue("leak", h.kind.value, True,
                           f"lộ bí mật: đoạn «{h.excerpt}» nói ra điều người đọc chưa được biết; "
                           "viết lại để không nói ra điều đó")
               for h in hits]

    review = Review(text, package, tuple(issues), tuple(result.rejected))
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
                             state["attempt"], list(review.issues), review.rejected)
    return {"accepted": [*state["accepted"], accepted], "scene": scene + 1, "review": None}


async def _blocked(state: _State, runtime: Runtime[_Deps]) -> dict:
    review, scene = state["review"], state["scene"]
    assert review is not None
    log.warning("chương %s cảnh %s: không hiện cảnh sau %s lượt (%s)", state["chapter"], scene,
                state["attempt"], _kinds([i for i in review.issues if i.block]))
    runtime.stream_writer(blocked_event(scene))
    return {"blocked_scene": scene}


async def _commit(state: _State, runtime: Runtime[_Deps]) -> dict:
    d = runtime.context
    runtime.stream_writer(stage("commit"))
    accepted = state["accepted"]
    package = merge_scene_packages(state["commit_id"], state["header"].nodes[0],
                                   [s.package for s in accepted])
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
    try:
        text = await summarize_chapter(
            d.llm, require_model(cfg.models.roles, "summary"), chapter=chapter,
            scenes=[s.text for s in state["accepted"]],
            max_chars=_require(cfg.limits.context, "summary_max_chars"),
            retries=cfg.limits.retries, extra=role_extra(cfg.models, "summary"),
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


class ChapterRun:
    """Một lần viết chương. `events()` phát sự kiện cho người chơi; sau đó `outcome` có kết quả
    phía máy chủ. Mọi lời gọi `llm` đi qua `MeteredClient(llm, tracker)` (G8)."""

    def __init__(
        self, request: ChapterRequest, *, llm: LLMClient, store: ChapterStore,
        config: AppConfig, plan: StoryPlan, tracker: CostTracker, style_guide: str | None = None,
    ) -> None:
        allowed = config.story_lengths.scenes_per_chapter
        if not allowed.min <= request.scene_count <= allowed.max:
            raise ValueError(f"scene_count={request.scene_count} ngoài khoảng "
                             f"{allowed.min}–{allowed.max} (story_lengths.yaml)")
        guide = style_guide if style_guide is not None else load_style_guide()
        # Câu ngôi kể lấy từ cùng config mà kiểm văn dùng để bắt lệch ngôi (D-51).
        self._deps = _Deps(request, MeteredClient(llm, tracker), store, config, plan,
                           f"{guide}\n\n{narration_instruction(config.quality)}")
        self.outcome = ChapterOutcome()

    async def events(self) -> AsyncIterator[ChapterEvent]:
        final: Mapping[str, Any] = {}
        try:
            async for chunk in _GRAPH.astream({"accepted": []}, context=self._deps,
                                              stream_mode=["custom", "values"], version="v2"):
                if chunk["type"] == "custom":
                    yield chunk["data"]
                elif chunk["type"] == "values":
                    final = chunk["data"]
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
        out.choices = list(final.get("choices", []))
        out.finished = bool(final.get("finished", False))
        out.summary = final.get("summary")
        out.summary_error = final.get("summary_error")
        out.summaries_missing = list(final.get("summaries_missing", []))
        out.reviews = list(final.get("reviews", []))
        out.cost_usd = self._deps.llm.tracker.chapter_usd
