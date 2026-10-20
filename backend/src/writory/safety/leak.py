"""Dò lộ bí mật trên mọi chữ sắp hiện cho người chơi (G2, D-26). Bằng code, không gọi model.

"Người chơi đã thấy gì" (`_seen_text`, một chỗ duy nhất) gồm `PlayerView` (G1, D-16: chữ hiện, biệt
danh, mọi câu trích, nội dung lời nói dối của nhân vật chính) và thiết lập truyện người chơi đã đọc
lúc khởi tạo (`story_brief`: bối cảnh, hướng truyện, nhân vật chính đã chọn; D-52). Bộ dò không đọc
cạnh đồ thị.

Chuỗi cấm ở chương N, tạo từ player_view, thiết lập truyện, tên lớp truth và story_plan:
1. Tên (lớp truth, `leak_names`) của nút có tên, khi tên đó có ít nhất một từ viết hoa (tên riêng)
   mà người chơi chưa thấy (player_view hay thiết lập truyện). Biệt danh toàn chữ thường ("thanh
   kiếm") là danh từ chung, không bao giờ cấm. `name` của nút `user_authored` không bao giờ cấm (D-48).
2. Mỗi bí mật của story_plan chưa tới khoảng lộ và chưa được hé lộ: các nhóm `leak_terms`.
   Một nhóm trúng khi mọi cụm trong nhóm cùng nằm trong một câu.

So khớp trên chữ đã chuẩn hoá NFC và bỏ dấu tiếng Việt, trọn từ. Cụm nhiều từ so không phân biệt
hoa thường; cụm một từ ("Lan", "Gù") so có phân biệt hoa thường, để "hoa lan" không trúng "Lan".
Vị trí trả về tính trên chuỗi NFC (bỏ dấu giữ nguyên độ dài).
"""

import logging
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from writory.errors import ErrorCode, WritoryError
from writory.graph import NodeRow, PlayerView
from writory.pipeline.story_plan import StoryPlan

log = logging.getLogger(__name__)


class NamedState(Protocol):
    """Phần của `guard.state.GraphState` mà `leak_names` cần (Neo4jState, OverlayState)."""

    def named_nodes(self) -> dict[str, tuple[str, ...]]: ...

    def nodes(self, ids: Sequence[str]) -> Mapping[str, NodeRow]: ...


def leak_names(state: NamedState) -> dict[str, tuple[str, ...]]:
    """Tên lớp truth cho bộ dò lộ: id → (name, *aliases) của mọi nút có tên, TRỪ `name` của nút
    mang `user_authored: true` (D-48). Người chơi tự viết hay chọn tên đó (ví dụ tên nhân vật
    chính), nên nó không phải bí mật đối với người chơi, kể cả khi trang chưa hé lộ nút. Biệt danh
    của nút đó vẫn bị dò, vì model có thể gán bí danh bí mật. Mọi nơi gọi `check_leaks` lấy
    `truth_names` từ đây: quy tắc chỉ nằm một chỗ."""
    names = state.named_nodes()
    rows = state.nodes(sorted(names))
    out: dict[str, tuple[str, ...]] = {}
    for node_id, (name, *aliases) in names.items():
        row = rows.get(node_id)
        authored = row is not None and row.props.get("user_authored") is True
        kept = tuple(aliases) if authored else (name, *aliases)
        if kept:
            out[node_id] = kept
    return out

_EXCERPT_MAX_CHARS = 120
_SENTENCE = re.compile(r"[^.!?…\n]+")
_WORD = re.compile(r"[^\W\d_]+")
_SPECIAL = {"đ": "d", "Đ": "D"}


class LeakKind(StrEnum):
    NAME = "name"
    SECRET = "secret"


@dataclass(frozen=True)
class LeakHit:
    kind: LeakKind
    term: str
    start: int
    end: int
    excerpt: str


def strip_diacritics(text: str) -> str:
    """Bỏ dấu tiếng Việt, giữ hoa thường và giữ nguyên độ dài (mỗi ký tự NFC → một ký tự)."""
    out = []
    for ch in unicodedata.normalize("NFC", text):
        if ch in _SPECIAL:
            out.append(_SPECIAL[ch])
            continue
        base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
        out.append(base if len(base) == 1 else ch)
    return "".join(out)


def _pattern(term: str) -> re.Pattern:
    words = strip_diacritics(term).split()
    flags = 0 if len(words) == 1 else re.IGNORECASE
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(w) for w in words) + r"(?!\w)", flags)


def _proper_tokens(text: str) -> set[str]:
    return {strip_diacritics(w) for w in _WORD.findall(text) if w[0].isupper()}


def _seen_text(view: PlayerView, story_brief: str) -> list[str]:
    """Mọi chữ người chơi đã thấy: player_view, cộng thiết lập truyện đã đọc lúc khởi tạo (D-52).
    Chỉ dùng để quyết tên nào còn cấm; nhóm `leak_terms` của bí mật không đọc chỗ này."""
    seen = [t for e in view.entries for t in (e.text, *e.aliases, *e.quotes)]
    return [*seen, *(lie.content for lie in view.lies), story_brief]


def _forbidden_names(truth_names: Mapping[str, tuple[str, ...]], seen: list[str]) -> list[str]:
    known = set().union(*(_proper_tokens(t) for t in seen))
    terms = {name for names in truth_names.values() for name in names if _proper_tokens(name) - known}
    return sorted(terms)


def _excerpt(text: str, start: int, end: int) -> str:
    excerpt = text[start:end]
    return excerpt[:_EXCERPT_MAX_CHARS] + "…" if len(excerpt) > _EXCERPT_MAX_CHARS else excerpt


def check_leaks(
    text: str,
    *,
    view: PlayerView,
    truth_names: Mapping[str, tuple[str, ...]],
    plan: StoryPlan,
    story_brief: str,
) -> list[LeakHit]:
    """`view`: player_view ở chương của chữ này. `truth_names`: `leak_names(state)` (D-48).
    `story_brief`: thiết lập truyện người chơi đã đọc lúc khởi tạo (`setup.story_brief`, lưu ở
    `stories.brief`; D-52). Bắt buộc truyền, để không nơi gọi nào quên; truyện không có thì "",
    bộ dò chỉ chặt hơn. Không bao giờ vào prompt."""
    text = unicodedata.normalize("NFC", text)
    flat = strip_diacritics(text)
    chapter = view.chapter
    revealed = {e.id for e in view.entries}
    hits: list[LeakHit] = []

    for term in _forbidden_names(truth_names, _seen_text(view, story_brief)):
        for m in _pattern(term).finditer(flat):
            hits.append(LeakHit(LeakKind.NAME, term, m.start(), m.end(),
                                _excerpt(text, m.start(), m.end())))

    secrets = [
        s for s in plan.secrets
        if chapter < s.reveal_from_chapter and s.fact_id not in revealed
    ]
    for secret in secrets:
        if not secret.leak_terms:
            log.warning("bí mật %s không có leak_terms: bộ dò lộ không kiểm được", secret.fact_id)
    for sentence in _SENTENCE.finditer(flat):
        for secret in secrets:
            for group in secret.leak_terms:
                found = [_pattern(p).search(sentence.group()) for p in group]
                if all(found):
                    start = sentence.start() + min(m.start() for m in found)
                    end = sentence.start() + max(m.end() for m in found)
                    hits.append(LeakHit(LeakKind.SECRET, " + ".join(group), start, end,
                                        _excerpt(text, start, end)))
    return sorted(hits, key=lambda h: (h.start, h.end))


def ensure_no_leak(
    text: str,
    *,
    view: PlayerView,
    truth_names: Mapping[str, tuple[str, ...]],
    plan: StoryPlan,
    story_brief: str,
) -> None:
    """Chặn chữ có lộ bí mật (mức BLOCK, design §6.2). Lỗi không chứa chữ bị lộ, kể cả trong
    `detail` dành cho log (G12: log không chứa bí mật truyện)."""
    hits = check_leaks(text, view=view, truth_names=truth_names, plan=plan,
                       story_brief=story_brief)
    if hits:
        where = ", ".join(f"{h.kind.value}@{h.start}-{h.end}" for h in hits)
        raise WritoryError(
            ErrorCode.SCENE_LEAK_BLOCKED,
            detail=f"chương {view.chapter}: {len(hits)} chỗ trúng ({where})",
        )
