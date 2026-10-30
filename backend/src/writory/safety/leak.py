"""Dò lộ bí mật trên mọi chữ sắp hiện cho người chơi (G2, D-26, D-61). Bằng code, không gọi model.

"Người chơi đã thấy gì" (`_seen_text`, một chỗ duy nhất) gồm `PlayerView` (G1, D-16: chữ hiện, biệt
danh, mọi câu trích, nội dung lời nói dối của nhân vật chính) và thiết lập truyện người chơi đã đọc
lúc khởi tạo (`story_brief`: bối cảnh, hướng truyện, nhân vật chính đã chọn; D-52). Bộ dò không đọc
cạnh đồ thị. Chữ lớp truth của Fact, Event, Lie trong player_view tính là đã thấy vì sổ tay hiện nó;
pipeline chỉ cho nút chữ vào player_view khi chữ đó không nói hơn câu trích (`unquoted_leaks`, D-134).

Chuỗi cấm, tạo từ player_view, thiết lập truyện, tên lớp truth và story_plan (D-61):
1. Tên bí mật, chỉ hai loại, và chỉ khi tên đó có ít nhất một từ viết hoa (tên riêng) mà người chơi
   chưa thấy (player_view hay thiết lập truyện):
   a. tên thật bị giấu sau biệt danh: nút đã có trong player_view (người chơi biết nó qua
      `known_as`, ví dụ "gã lái đò mặt sẹo") mà tên hay biệt danh lớp truth ("Lý Thất") không
      phải tên đã hé lộ. Không coi là bị giấu: tên chứa trọn một tên đã hé lộ ("Diệp Tĩnh Lan" khi
      đã biết "Tĩnh Lan"), hoặc chung một từ viết hoa với tên đã hé lộ ("Đoàn Khương" khi đã biết
      "Đoàn sư huynh");
   b. tên được kế hoạch bảo vệ: tên và biệt danh của các nút trong `Secret.protects` của bí mật
      còn hiệu lực (xem `scope`).
   Mọi tên khác của lớp truth không bị cấm: trang nêu nó thì code tự hé lộ (`safety/reveal.py`,
   D-62). `name` của nút `user_authored` không bao giờ cấm (D-48).
2. Mỗi bí mật của story_plan còn hiệu lực: các nhóm `leak_terms`. Một nhóm trúng khi mọi cụm trong
   nhóm cùng nằm trong một câu.

`scope` (bắt buộc, không có mặc định) nói bí mật nào còn hiệu lực:
- `scene`: văn cảnh do model viết. Bí mật chưa tới khoảng lộ và chưa hé lộ, vì cảnh được phép hé lộ
  trong khoảng.
- `player_path`: mọi chữ khác tới người chơi, sinh ra từ player_view (người kể, chữ lựa chọn, lời
  nói dối và cảm xúc của lựa chọn). Mọi bí mật chưa có trong player_view, bất kể khoảng lộ: chỉ
  cảnh mới có quyền hé lộ.

So khớp trên chữ đã chuẩn hoá NFC và bỏ dấu tiếng Việt, trọn từ. Cụm nhiều từ so không phân biệt
hoa thường; cụm một từ ("Lan", "Gù") so có phân biệt hoa thường, để "hoa lan" không trúng "Lan".
Vị trí trả về tính trên chuỗi NFC (bỏ dấu giữ nguyên độ dài).
"""

import logging
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Literal, Protocol, get_args

from writory.errors import ErrorCode, WritoryError
from writory.graph import NodeRow, PlayerEntry, PlayerView
from writory.pipeline.story_plan import Secret, StoryPlan

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


# Chữ nào đang được dò (bắt buộc, không có mặc định): `scene` cho văn cảnh, `player_path` cho chữ
# sinh ra từ player_view (người kể, lựa chọn). Xem đầu file.
Scope = Literal["scene", "player_path"]

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
    # Chỉ với `NAME`: nút mang tên cấm, và tên người đọc đã biết nút đó (None nếu chưa hé lộ), để
    # lượt viết lại nói được "dùng X thay vào" (D-91).
    node_id: str | None = None
    shown_as: str | None = None


@dataclass(frozen=True)
class ForbiddenName:
    """Một tên lớp truth mà trang chưa được viết (D-61) và người đọc biết nút đó là gì (D-91).
    `shown_as`: tên người đọc đã biết (`known_as` trong player_view); None nếu nút chưa hé lộ."""

    node_id: str
    term: str
    shown_as: str | None
    user_authored: bool = False  # nút do người chơi viết: chữ vào đề phải bọc (G4)


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


def name_key(text: str) -> str:
    """Khoá so sánh tên: bỏ dấu, không phân biệt hoa thường, gộp khoảng trắng."""
    return " ".join(strip_diacritics(text).casefold().split())


def _contains_words(whole: str, part: str) -> bool:
    """`part` là một dãy từ liền nhau trong `whole` (cả hai đã qua `name_key`)."""
    w, p = whole.split(), part.split()
    return bool(p) and any(w[i:i + len(p)] == p for i in range(len(w) - len(p) + 1))


def active_secrets(plan: StoryPlan, view: PlayerView, scope: Scope) -> list[Secret]:
    """Bí mật còn hiệu lực với chữ này: chưa có trong player_view, và (với `scene`) chưa tới khoảng
    lộ. Với `player_path` thì không xét khoảng lộ: chỉ cảnh mới được hé lộ."""
    revealed = {e.id for e in view.entries}
    return [
        s for s in plan.secrets
        if s.fact_id not in revealed
        and (scope == "player_path" or view.chapter < s.reveal_from_chapter)
    ]


def protected_ids(plan: StoryPlan, view: PlayerView, scope: Scope) -> set[str]:
    """Id các nút mà tên đang được kế hoạch bảo vệ (`Secret.protects` của bí mật còn hiệu lực)."""
    return {n for s in active_secrets(plan, view, scope) for n in s.protects}


def _hidden_names(names: Sequence[str], entry: PlayerEntry) -> list[str]:
    """(a) Tên lớp truth của một nút đã có trong player_view mà người chơi chưa được biết: không
    chứa trọn một tên đã hé lộ, không nằm trọn trong một tên đã hé lộ ("Thuyền Nhỏ" khi trang gọi
    nó là "chiếc thuyền nhỏ", D-91), không chung từ viết hoa nào với tên đã hé lộ."""
    shown = (entry.text, *entry.aliases)
    keys = [name_key(t) for t in shown]
    tokens = set().union(*(_proper_tokens(t) for t in shown))
    return [n for n in names
            if not any(_contains_words(name_key(n), k) or _contains_words(k, name_key(n))
                       for k in keys)
            and not _proper_tokens(n) & tokens]


def forbidden_names(
    *, truth_names: Mapping[str, tuple[str, ...]], view: PlayerView, plan: StoryPlan,
    story_brief: str, scope: Scope,
) -> list[ForbiddenName]:
    """Mọi tên bị cấm trên trang (D-61): luật (a) và (b) ở đầu file. MỘT nguồn cho bộ dò
    (`check_leaks`) và cho đề của dàn ý và model viết (D-91): sửa luật ở đây thì cả hai theo."""
    if scope not in get_args(Scope):
        raise ValueError(f"scope phải là một trong {get_args(Scope)}, nhận {scope!r}")
    entries = {e.id: e for e in view.entries}
    candidates = [(node_id, n) for node_id, names in truth_names.items() if node_id in entries
                  for n in _hidden_names(names, entries[node_id])]  # (a)
    candidates += [(node_id, n) for node_id in sorted(protected_ids(plan, view, scope))
                   for n in truth_names.get(node_id, ())]  # (b)
    known = set().union(*(_proper_tokens(t) for t in _seen_text(view, story_brief)))
    out: dict[str, ForbiddenName] = {}
    for node_id, term in candidates:
        if _proper_tokens(term) - known and term not in out:
            shown = entries[node_id].text if node_id in entries else None
            out[term] = ForbiddenName(node_id, term, shown)
    return [out[t] for t in sorted(out)]


def forbidden_for_prompt(
    state: NamedState, *, view: PlayerView, plan: StoryPlan, story_brief: str, scope: Scope,
) -> list[ForbiddenName]:
    """`forbidden_names` cho đề của model: thêm cờ `user_authored` của nút (G4)."""
    found = forbidden_names(truth_names=leak_names(state), view=view, plan=plan,
                            story_brief=story_brief, scope=scope)
    rows = state.nodes(sorted({f.node_id for f in found}))
    return [replace(f, user_authored=bool(rows.get(f.node_id)
                                          and rows[f.node_id].props.get("user_authored") is True))
            for f in found]


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
    scope: Scope,
) -> list[LeakHit]:
    """`scope`: `scene` cho văn cảnh, `player_path` cho chữ sinh ra từ player_view (xem đầu file).
    `view`: player_view ở chương của chữ này. `truth_names`: `leak_names(state)` (D-48).
    `story_brief`: thiết lập truyện người chơi đã đọc lúc khởi tạo (`setup.story_brief`, lưu ở
    `stories.brief`; D-52). Bắt buộc truyền, để không nơi gọi nào quên; truyện không có thì "",
    bộ dò chỉ chặt hơn. Không bao giờ vào prompt."""
    if scope not in get_args(Scope):
        raise ValueError(f"scope phải là một trong {get_args(Scope)}, nhận {scope!r}")
    text = unicodedata.normalize("NFC", text)
    flat = strip_diacritics(text)
    hits: list[LeakHit] = []

    for f in forbidden_names(truth_names=truth_names, view=view, plan=plan,
                             story_brief=story_brief, scope=scope):
        for m in _pattern(f.term).finditer(flat):
            hits.append(LeakHit(LeakKind.NAME, f.term, m.start(), m.end(),
                                _excerpt(text, m.start(), m.end()), f.node_id, f.shown_as))

    secrets = active_secrets(plan, view, scope)
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


def _group_in_one_sentence(flat: str, group: Sequence[str]) -> bool:
    patterns = [_pattern(p) for p in group]
    return any(all(p.search(s.group()) for p in patterns) for s in _SENTENCE.finditer(flat))


def unquoted_leaks(
    text: str,
    quotes: Sequence[str],
    *,
    node_id: str,
    view: PlayerView,
    truth_names: Mapping[str, tuple[str, ...]],
    plan: StoryPlan,
    story_brief: str,
) -> list[str]:
    """Điều bộ dò lộ đường người chơi (`player_path`) chặn trong `text`, chữ lớp truth của một nút
    chữ (Fact, Event, Lie) sắp vào player_view, mà không câu trích nào trong `quotes` nói ra (D-134).
    Sổ tay hiện nguyên chữ này và `_seen_text` tính nó là đã thấy, nên chữ đó không được nói hơn
    trang: tên bị cấm (luật a, b ở đầu file) phải có trong một câu trích; nhóm `leak_terms` của bí
    mật còn hiệu lực phải cùng nằm trong một câu của một câu trích. Nhóm của chính bí mật `node_id`
    không tính: hé lộ bí mật là việc của cảnh, người canh (`_early_reveal`) quyết khoảng lộ; tên bí
    mật đó bảo vệ thì vẫn tính. `view`: player_view TRƯỚC gói đang xét. Trả các cụm trúng (lớp
    truth: không vào log hay lý do bị bỏ)."""
    flat = strip_diacritics(unicodedata.normalize("NFC", text))
    said = [strip_diacritics(unicodedata.normalize("NFC", q)) for q in quotes]
    out = [f.term for f in forbidden_names(truth_names=truth_names, view=view, plan=plan,
                                           story_brief=story_brief, scope="player_path")
           if _pattern(f.term).search(flat) and not any(_pattern(f.term).search(q) for q in said)]
    for secret in active_secrets(plan, view, "player_path"):
        if secret.fact_id == node_id:
            continue
        out += [" + ".join(group) for group in secret.leak_terms
                if _group_in_one_sentence(flat, group)
                and not any(_group_in_one_sentence(q, group) for q in said)]
    return out


def ensure_no_leak(
    text: str,
    *,
    view: PlayerView,
    truth_names: Mapping[str, tuple[str, ...]],
    plan: StoryPlan,
    story_brief: str,
    scope: Scope,
) -> None:
    """Chặn chữ có lộ bí mật (mức BLOCK, design §6.2). Lỗi không chứa chữ bị lộ, kể cả trong
    `detail` dành cho log (G12: log không chứa bí mật truyện)."""
    hits = check_leaks(text, view=view, truth_names=truth_names, plan=plan,
                       story_brief=story_brief, scope=scope)
    if hits:
        where = ", ".join(f"{h.kind.value}@{h.start}-{h.end}" for h in hits)
        raise WritoryError(
            ErrorCode.SCENE_LEAK_BLOCKED,
            detail=f"chương {view.chapter}: {len(hits)} chỗ trúng ({where})",
        )
