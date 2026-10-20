"""Người canh, phần kiểm bằng code (design §8 mục 1–2). Không gọi model.

Kiểm gói thay đổi của MỘT cảnh trước khi ghi. Trạng thái đọc ra gồm:
- `committed`: đồ thị đã commit tới chương trước (Neo4jState, hoặc OverlayState trong test);
- `earlier`: gói của các cảnh trước trong cùng chương, chưa ghi;
- `current`: gói của cảnh đang kiểm.
Theo D-21, mọi cạnh của gói chương N mở ở N, nên "ở chương N" đọc trên trạng thái phủ là đủ.

Trễ hạn (D-49) chỉ kiểm ở cảnh cuối chương (`last_scene`): hết chương mà bí mật đã đến hạn chưa
lộ, hay mạch phải gỡ đã đến hạn chưa gỡ. Mức viết lại, không bao giờ chặn người chơi: model không
lộ kịp thì truyện vẫn đi tiếp.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from writory.config import GuardConfig, LimitNotSetError
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, EdgeSpec
from writory.graph.package import TOLD, chapter_rule_problems
from writory.guard.plan import deadline, plan_progress
from writory.guard.state import GraphState, OverlayState
from writory.pipeline.story_plan import StoryPlan


class GuardKind(StrEnum):
    CHAPTER_RULE = "chapter_rule"
    DEAD_ACTOR = "dead_actor"
    AT_MOST_ONE = "at_most_one"
    TELLER_DOES_NOT_KNOW = "teller_does_not_know"
    EARLY_REVEAL = "early_reveal"
    SUDDEN_RELATIONSHIP = "sudden_relationship"
    OVERDUE_SECRET = "overdue_secret"
    OVERDUE_THREAD = "overdue_thread"


class Severity(StrEnum):
    REWRITE = "rewrite"  # viết lại cảnh, chung lượt viết lại với kiểm văn (design §6.2)
    BLOCK = "block"  # không hiện cảnh cho người chơi (lộ bí mật, design §6.2 bước 4)


@dataclass(frozen=True)
class GuardIssue:
    kind: GuardKind
    severity: Severity
    ids: tuple[str, ...]
    detail: str


# Cạnh mà nhân vật ở đầu `from` phải còn sống mới tạo được (design §8 mục 1).
_ACTS_AS_SOURCE = frozenset(
    {"PARTICIPATED_IN", "HOLDS", "TOLD", "LOCATED_AT", "KNOWS", "MEMBER_OF", "RELATES_TO"}
)
# Cạnh mà nhân vật ở đầu `to` phải còn sống: người nghe một lời nói dối.
_ACTS_AS_TARGET = frozenset({"TOLD_TO"})


def check_scene_package(
    *,
    chapter: int,
    current: ChangePackage,
    earlier: Sequence[ChangePackage],
    committed: GraphState,
    plan: StoryPlan,
    config: GuardConfig,
    last_scene: bool = False,
) -> list[GuardIssue]:
    """`last_scene`: `current` là cảnh cuối của chương (bật phép kiểm trễ hạn)."""
    before = OverlayState(committed, list(earlier))
    after = OverlayState(committed, [*earlier, current])
    return [
        *_chapter_rule(current, chapter),
        *_dead_actors(current, chapter, before),
        *_at_most_one(current, chapter, after),
        *_teller_does_not_know(current, chapter, after),
        *_early_reveal(current, chapter, after, plan),
        *_sudden_relationship(current, [*earlier, current], chapter, before, config),
        *(_overdue(chapter, after, plan) if last_scene else []),
    ]


def _issue(kind: GuardKind, ids: Sequence[str], detail: str,
           severity: Severity = Severity.REWRITE) -> GuardIssue:
    return GuardIssue(kind, severity, tuple(ids), detail)


def _chapter_rule(current: ChangePackage, chapter: int) -> list[GuardIssue]:
    return [_issue(GuardKind.CHAPTER_RULE, (), p) for p in chapter_rule_problems(current, chapter)]


def _dead_actors(current: ChangePackage, chapter: int, before: GraphState) -> list[GuardIssue]:
    """Chết ở chương trước hoặc ở cảnh trước của chương này (trạng thái `before`).
    Chết trong chính cảnh này thì hành động trong cảnh vẫn hợp lệ. Người kể (`told_by` của
    KNOWS "được kể") cũng phải còn sống."""
    actors = [(e, e.source) for e in current.edges if e.type in _ACTS_AS_SOURCE]
    actors += [(e, e.target) for e in current.edges if e.type in _ACTS_AS_TARGET]
    actors += [
        (e, e.props["told_by"]) for e in current.edges
        if e.type == "KNOWS" and e.props.get("how") == TOLD and isinstance(e.props.get("told_by"), str)
    ]
    issues = []
    for edge, who in actors:  # DIED_IN chỉ đi ra từ Character, nên không cần lọc nhãn
        deaths = before.edges_at("DIED_IN", chapter, source_id=who)
        if deaths:
            issues.append(_issue(
                GuardKind.DEAD_ACTOR, (edge.id, who, deaths[0].target),
                f"{who} đã chết ({deaths[0].target}, chương {deaths[0].valid_from_chapter}) "
                f"nhưng gói có cạnh {edge.type} {edge.id}",
            ))
    return issues


def _at_most_one(current: ChangePackage, chapter: int, after: GraphState) -> list[GuardIssue]:
    """Bất biến "tối đa một" (graph-schema.md), kiểm trước khi ghi: mỗi đồ vật một người giữ,
    một nơi; mỗi cặp A→B một RELATES_TO."""
    item_ids = {e.source for e in current.edges if e.type == "LOCATED_AT"}
    items = {i for i, label in after.node_labels(sorted(item_ids)).items() if label == "Item"}
    groups: dict[tuple, dict] = {}
    for e in current.edges:
        if e.type == "HOLDS":
            groups[("HOLDS", e.target)] = {"target_id": e.target}
        elif e.type == "RELATES_TO":
            groups[("RELATES_TO", e.source, e.target)] = {"source_id": e.source,
                                                         "target_id": e.target}
        elif e.type == "LOCATED_AT" and e.source in items:
            groups[("LOCATED_AT", e.source)] = {"source_id": e.source}
    issues = []
    for key, where in groups.items():
        rows = after.edges_at(key[0], chapter, **where)
        if len(rows) > 1:
            if key[0] == "HOLDS":
                what = f"đồ vật {key[1]} có {len(rows)} người giữ"
            elif key[0] == "LOCATED_AT":
                what = f"đồ vật {key[1]} ở {len(rows)} nơi"
            else:
                what = f"cặp {key[1]}→{key[2]} có {len(rows)} quan hệ"
            issues.append(_issue(
                GuardKind.AT_MOST_ONE, [r.id for r in rows],
                f"{what} cùng hiệu lực ở chương {chapter}; cạnh cũ phải được đóng trong gói",
            ))
    return issues


def _teller_does_not_know(
    current: ChangePackage, chapter: int, after: GraphState
) -> list[GuardIssue]:
    """KNOWS "được kể": người kể phải biết điều đó lúc kể (kể cả mới biết trong cảnh này)."""
    issues = []
    for e in current.edges:
        if e.type != "KNOWS" or e.props.get("how") != TOLD:
            continue
        teller = e.props.get("told_by")
        if not isinstance(teller, str) or not after.edges_at(
            "KNOWS", chapter, source_id=teller, target_id=e.target
        ):
            issues.append(_issue(
                GuardKind.TELLER_DOES_NOT_KNOW, (e.id, str(teller), e.target),
                f"{e.source} được {teller} kể về {e.target}, nhưng {teller} không biết điều đó "
                f"ở chương {chapter}",
            ))
    return issues


def _is_reveal(e: EdgeSpec, protagonist: str | None) -> str | None:
    """Id nút được hé lộ cho người chơi qua cạnh này, hoặc None."""
    if e.type == "REVEALED_TO_PLAYER":
        return e.source
    if e.type == "KNOWS" and e.source == protagonist:
        return e.target
    return None


def _early_reveal(
    current: ChangePackage, chapter: int, after: GraphState, plan: StoryPlan
) -> list[GuardIssue]:
    """Bí mật lộ trước khoảng dự kiến của story_plan. Ngoại lệ: cạnh ghi `by_choice` (lựa chọn
    của người chơi dẫn tới, design §6.1). Chưa kiểm id lựa chọn có thật (chưa có nút Choice)."""
    try:
        protagonist: str | None = after.protagonist_id()
    except LookupError:  # chương 0: thế giới khởi tạo có thể chưa có nhân vật chính
        protagonist = None
    issues = []
    for e in current.edges:
        node = _is_reveal(e, protagonist)
        secret = plan.secret(node) if node else None
        if secret and chapter < secret.reveal_from_chapter and "by_choice" not in e.props:
            issues.append(_issue(
                GuardKind.EARLY_REVEAL, (e.id, node),
                f"bí mật {node} lộ ở chương {chapter}, kế hoạch cho lộ từ chương "
                f"{secret.reveal_from_chapter}; không có lựa chọn nào dẫn tới",
                Severity.BLOCK,
            ))
    return issues


def _overdue(chapter: int, after: GraphState, plan: StoryPlan) -> list[GuardIssue]:
    """Cuối chương N: bí mật đến hạn (hoặc quá hạn) chưa lộ, mạch phải gỡ đến hạn chưa gỡ (D-49).
    Hạn theo `guard.plan` (cùng định nghĩa với mục tiêu của chương). Chương cuối của truyện thì
    mọi bí mật và mạch phải gỡ đều đến hạn.

    Mức viết lại; `ids` rỗng vì không có cạnh nào sai để bỏ. `detail` là góp ý cho model viết lại
    (vai được thấy truth): có chữ của bí mật hay mạch, trừ chữ người chơi viết (G4)."""
    progress = plan_progress(plan, after, chapter)

    def text(value: str, user_authored: bool) -> str:
        return "(xem mục tiêu của chương)" if user_authored else f"«{value}»"

    issues = []
    for s in progress.secrets:
        if s.revealed_chapter is None and deadline(
                chapter, s.from_chapter, s.to_chapter, final=progress.final) in ("due", "overdue"):
            issues.append(_issue(
                GuardKind.OVERDUE_SECRET, (),
                f"bí mật {s.fact_id} (khoảng lộ chương {s.from_chapter}–{s.to_chapter}) đến hết "
                f"chương {chapter} vẫn chưa được hé lộ cho người đọc: viết lại để cảnh hé lộ rõ "
                f"điều này một cách hợp lý, có câu nói thẳng trên trang: "
                f"{text(s.text, s.user_authored)}",
            ))
    for t in progress.threads:
        if t.resolved_chapter is None and deadline(
                chapter, t.from_chapter, t.to_chapter, final=progress.final) in ("due", "overdue"):
            window = (f"hạn gỡ chương {t.from_chapter}–{t.to_chapter}"
                      if t.to_chapter is not None else "phải gỡ trước khi kết")
            issues.append(_issue(
                GuardKind.OVERDUE_THREAD, (),
                f"mạch {t.thread_id} ({window}) đến hết chương {chapter} vẫn chưa được gỡ: viết "
                f"lại để cảnh gỡ mạch này một cách hợp lý: {text(t.description, t.user_authored)}",
            ))
    return issues


def _related_event(pending: Sequence[ChangePackage], people: set[str]) -> bool:
    """Có Event mới trong chương mà một trong hai nhân vật tham gia, chết trong, hoặc được nói tới."""
    events = {n.id for p in pending for n in p.nodes if n.label == "Event"}
    for e in (e for p in pending for e in p.edges):
        if e.type in ("PARTICIPATED_IN", "DIED_IN") and e.target in events and e.source in people:
            return True
        if e.type == "ABOUT" and e.source in events and e.target in people:
            return True
    return False


def _sudden_relationship(
    current: ChangePackage,
    pending: Sequence[ChangePackage],
    chapter: int,
    before: GraphState,
    config: GuardConfig,
) -> list[GuardIssue]:
    try:
        limit = config.relationship.require("max_score_jump_without_event")
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None
    issues = []
    for e in current.edges:
        new = e.props.get("score")
        if e.type != "RELATES_TO" or not isinstance(new, int):
            continue
        for old in before.edges_at("RELATES_TO", chapter, source_id=e.source, target_id=e.target):
            score = old.props.get("score")
            if not isinstance(score, int) or abs(new - score) <= limit:
                continue
            if not _related_event(pending, {e.source, e.target}):
                issues.append(_issue(
                    GuardKind.SUDDEN_RELATIONSHIP, (e.id, old.id),
                    f"quan hệ {e.source}→{e.target} đổi từ {score} sang {new} "
                    f"(quá {limit}) mà chương không có sự kiện nào liên quan",
                ))
    return issues
