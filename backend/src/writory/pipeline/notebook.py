"""Sổ tay cho người kể: dựng chữ, và truy hồi khi sổ tay lớn (design §6.6, D-59).

Truyện ngắn: sổ tay nhỏ, gửi nguyên. Truyện dài: sổ tay có thể hàng trăm mục, tốn token và loãng.
Khi vượt ngưỡng (`limits.narrator_notebook`), chỉ gửi phần liên quan tới câu hỏi:
1. mục có chữ hiện hoặc biệt danh trùng câu hỏi (so bỏ dấu, không phân biệt hoa thường, trọn từ);
2. vài mục khớp từ khoá hiếm trong câu hỏi, khi tên không trùng (điểm IDF);
3. hàng xóm 1-2 bước của các mục trên theo quan hệ `about` trong `PlayerView`, hai chiều;
4. luôn kèm các mục (và lời nói dối) gần đây nhất.

G1: hàm chỉ nhận `PlayerView` và câu hỏi, nên không thể chạm lớp truth: lọc theo player_view
TRƯỚC, truy hồi SAU. Mã công khai (m1, l1...) luôn lấy từ sổ tay đầy đủ (`public_entries`), nên một
mục giữ nguyên mã dù chỉ gửi một phần. Không dùng vector DB: đủ cho vài trăm mục có tên riêng;
đề xuất embedding nằm ở báo cáo của D-59.
"""

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass

from writory.config import NarratorNotebookLimits
from writory.graph import PlayerEntry, PlayerLie, PlayerView, public_entries, public_lies
from writory.safety.leak import strip_diacritics

KIND_LABEL = {
    "Character": "Nhân vật",
    "Location": "Nơi chốn",
    "Item": "Đồ vật",
    "Faction": "Phe nhóm",
    "Fact": "Điều đã biết",
    "Event": "Sự việc",
    "Lie": "Lời nói dối (người chơi đã biết là dối)",
}
LIES_HEADER = "Lời nói dối nhân vật chính đã nói:"

# Từ trong câu hỏi mà xuất hiện ở hơn bấy nhiêu phần sổ tay thì không giúp tìm mục (ai, là, gì...).
COMMON_TOKEN_RATIO = 0.2
# Chỗ chừa cho tiêu đề và dòng trống của phần lời nói dối khi tính ngân sách ký tự.
LIES_HEADER_RESERVE = len(LIES_HEADER) + 4
_WORD = re.compile(r"\w+")


def entry_line(ref: str, e: PlayerEntry) -> str:
    line = f"[{ref}] {KIND_LABEL.get(e.kind, e.kind)}: {e.text}"
    if e.aliases:
        line += f"; tên khác người chơi đã biết: {', '.join(e.aliases)}"
    line += f" (biết từ chương {e.since_chapter})."
    if e.quote:
        line += f' Câu trên trang: "{e.quote}"'
    return line


def lie_line(ref: str, lie: PlayerLie) -> str:
    return f"[{ref}] Chương {lie.chapter}, nói với {', '.join(lie.told_to)}: {lie.content}"


@dataclass(frozen=True)
class NotebookSelection:
    """Phần sổ tay gửi cho model, kèm mã công khai của sổ tay đầy đủ."""

    entries: tuple[tuple[str, PlayerEntry], ...]
    lies: tuple[tuple[str, PlayerLie], ...]
    total_entries: int
    total_lies: int

    @property
    def total(self) -> int:
        return self.total_entries + self.total_lies

    @property
    def partial(self) -> bool:
        return len(self.entries) + len(self.lies) < self.total

    @property
    def refs(self) -> frozenset[str]:
        return frozenset(r for r, _ in self.entries) | frozenset(r for r, _ in self.lies)


def full_selection(view: PlayerView) -> NotebookSelection:
    entries, lies = public_entries(view), public_lies(view)
    return NotebookSelection(entries, lies, len(entries), len(lies))


def render_selection(selection: NotebookSelection) -> str:
    lines = [entry_line(ref, e) for ref, e in selection.entries]
    if selection.lies:
        lines += ["", LIES_HEADER]
        lines += [lie_line(ref, lie) for ref, lie in selection.lies]
    return "\n".join(lines)


# --- so chữ -----------------------------------------------------------------------------------


def _words(text: str) -> list[str]:
    return _WORD.findall(strip_diacritics(unicodedata.normalize("NFC", text)).casefold())


def _tokens(text: str) -> set[str]:
    return {w for w in _words(text) if len(w) > 1}


def _phrase(text: str) -> str:
    return " ".join(w for w in _words(text))


def _named_in(question_phrase: str, names: Iterable[str]) -> int:
    """Độ dài (số từ) của tên dài nhất trùng trọn từ trong câu hỏi, 0 nếu không có."""
    best = 0
    for name in names:
        phrase = _phrase(name)
        if len(phrase) > 1 and f" {phrase} " in question_phrase:
            best = max(best, len(phrase.split()))
    return best


@dataclass(frozen=True)
class _Item:
    ref: str
    line: str
    names: tuple[str, ...]
    body: frozenset[str]  # từ của chữ hiện và biệt danh
    quote: frozenset[str]  # từ của câu trích: nhẹ cân hơn
    neighbours: frozenset[int]


def _scores(items: list[_Item], question_tokens: set[str]) -> list[float]:
    """Điểm IDF: tổng trọng số các từ hiếm của câu hỏi có trong mục. Từ có ở hơn
    `COMMON_TOKEN_RATIO` số mục bị bỏ."""
    n = len(items)
    df = Counter(t for it in items for t in it.body | it.quote)
    scores = []
    for it in items:
        score = 0.0
        for t in question_tokens:
            if t not in df or (n >= 5 and df[t] / n > COMMON_TOKEN_RATIO):
                continue
            idf = math.log(1 + n / df[t])
            score += idf if t in it.body else 0.5 * idf if t in it.quote else 0.0
        scores.append(score)
    return scores


def _entry_items(entries: tuple[tuple[str, PlayerEntry], ...]) -> list[_Item]:
    index = {e.id: i for i, (_, e) in enumerate(entries)}
    links: list[set[int]] = [set() for _ in entries]
    for i, (_, e) in enumerate(entries):
        for target in e.about:
            j = index.get(target)
            if j is not None and j != i:
                links[i].add(j)
                links[j].add(i)
    return [
        _Item(ref, entry_line(ref, e), (e.text, *e.aliases),
              frozenset(_tokens(" ".join((e.text, *e.aliases)))), frozenset(_tokens(e.quote or "")),
              frozenset(links[i]))
        for i, (ref, e) in enumerate(entries)
    ]


def _lie_items(lies: tuple[tuple[str, PlayerLie], ...]) -> list[_Item]:
    return [
        _Item(ref, lie_line(ref, lie), lie.told_to, frozenset(_tokens(lie.content)),
              frozenset(_tokens(" ".join(lie.told_to))), frozenset())
        for ref, lie in lies
    ]


def _seeds(items: list[_Item], question: str, keyword_entries: int, cap: int) -> list[int]:
    """Chỉ số mục làm điểm xuất phát: tên trùng trước (tên dài hơn trước, rồi mới hơn), rồi tới
    những mục khớp từ khoá hiếm. Tên trùng bị chặn ở `cap` để câu liệt kê cả sổ tay không tràn."""
    phrase = f" {_phrase(question)} "
    named = [(i, _named_in(phrase, it.names)) for i, it in enumerate(items)]
    by_name = [i for i, w in sorted(named, key=lambda p: (-p[1], -p[0])) if w][:cap]
    scores = _scores(items, _tokens(question))
    by_word = [i for i in sorted(range(len(items)), key=lambda i: (-scores[i], -i))
               if scores[i] > 0 and i not in by_name][:keyword_entries]
    return by_name + by_word


def _expand(items: list[_Item], seeds: list[int]) -> tuple[list[int], list[int]]:
    """Hàng xóm 1 bước và 2 bước (không lặp seed), mỗi tầng theo số liên kết giảm dần rồi mới hơn."""
    seen = set(seeds)
    layers: list[list[int]] = []
    frontier = seeds
    for _ in range(2):
        hits = Counter(j for i in frontier for j in items[i].neighbours if j not in seen)
        layer = sorted(hits, key=lambda j: (-hits[j], -j))
        layers.append(layer)
        seen.update(layer)
        frontier = layer
    return layers[0], layers[1]


def _fill(items: list[_Item], order: list[int], mandatory: set[int], max_items: int,
          max_chars: int) -> list[int]:
    chosen: list[int] = []
    chars = 0
    for i in order:
        size = len(items[i].line) + 1
        if i in mandatory or (len(chosen) < max_items and chars + size <= max_chars):
            chosen.append(i)
            chars += size
    return sorted(chosen)


def _unique(*groups: Iterable[int]) -> list[int]:
    return list(dict.fromkeys(i for group in groups for i in group))


def select_notebook(question: str, view: PlayerView,
                    limits: NarratorNotebookLimits) -> NotebookSelection:
    """Phần sổ tay cần gửi cho câu hỏi này. Dưới ngưỡng thì trả nguyên sổ tay."""
    max_entries = limits.require("max_entries")
    max_chars = limits.require("max_chars")
    recent = limits.require("recent_entries")
    keywords = limits.require("keyword_entries")

    full = full_selection(view)
    full_chars = sum(len(entry_line(r, e)) + 1 for r, e in full.entries) + sum(
        len(lie_line(r, lie)) + 1 for r, lie in full.lies)
    if full.total <= max_entries and full_chars <= max_chars:
        return full

    # Lời nói dối trước: ít và rẻ. Gần đây nhất luôn kèm, cộng những lời nhắc tới người nghe hoặc
    # từ khoá trong câu hỏi.
    lie_items = _lie_items(full.lies)
    lie_recent = set(range(max(0, len(lie_items) - recent), len(lie_items)))
    lie_order = _unique(sorted(lie_recent, reverse=True),
                        _seeds(lie_items, question, keywords, cap=recent + keywords)) \
        if lie_items else []
    lie_cap = min(len(lie_items), recent + keywords)
    lie_chosen = _fill(lie_items, lie_order, lie_recent, lie_cap, max_chars // 4)

    chosen_lies = tuple(full.lies[i] for i in lie_chosen)
    lie_chars = sum(len(lie_items[i].line) + 1 for i in lie_chosen)
    reserve = LIES_HEADER_RESERVE if chosen_lies else 0

    items = _entry_items(full.entries)
    recent_ix = set(range(max(0, len(items) - recent), len(items)))
    seeds = _seeds(items, question, keywords, cap=max(1, max_entries // 2))
    hop1, hop2 = _expand(items, seeds)
    order = _unique(sorted(recent_ix, reverse=True), seeds, hop1, hop2)
    chosen = _fill(items, order, recent_ix, max_entries - len(chosen_lies),
                   max_chars - lie_chars - reserve)
    return NotebookSelection(tuple(full.entries[i] for i in chosen), chosen_lies,
                             full.total_entries, full.total_lies)
