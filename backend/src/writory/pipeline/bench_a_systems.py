"""Bài đo A: năm "hệ trả lời" (đối thủ) của bài đo bộ nhớ (design §9 A; D-72, D-73).

Mỗi hệ nhận cùng bộ chương đã viết sẵn và dựng NGỮ CẢNH cho một câu hỏi hỏi sau khi đã đọc tới hết
chương N. Cùng một model trả lời nhận ngữ cảnh đó, nên khác biệt giữa các hệ chỉ nằm ở bộ nhớ:

  graph    đồ thị WriTory: nối thực thể trong câu hỏi với đồ thị, lấy lân cận và lịch sử tới hết
           chương N, chỉ qua `GraphState` (lớp graph/, G10). Cộng chương N nếu `recent`.
  none     không bộ nhớ: chỉ chương N.
  rolling  tóm tắt từng chương 1..N-1 nối lại (vai `summary`, đúng thứ pipeline lưu, D-49) cộng
           chương N.
  rag      BM25 trên các đoạn của chương 1..N-1 (D-73) cộng chương N.
  full     nhét cả truyện: chương 1..N.

"Chương N" là chương người viết vừa viết xong; mọi hệ (trừ `full`, vốn có tất cả) đều thấy nó, vì
bộ nhớ cần đo là bộ nhớ về các chương CŨ HƠN. Không hệ nào thấy chương sau N.
"""

import itertools
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from writory.guard.state import EdgeRow, GraphState

SYSTEMS = ("graph", "none", "rolling", "rag", "full")
SYSTEM_LABELS = {
    "graph": "Đồ thị WriTory",
    "none": "Không bộ nhớ (chỉ chương N)",
    "rolling": "Tóm tắt cuộn + chương N",
    "rag": "RAG BM25 + chương N",
    "full": "Nhét cả truyện (chương 1..N)",
}


# --- chuẩn hoá chữ -------------------------------------------------------------------------------


def flat(text: str) -> str:
    """NFC, hạ chữ thường, mọi ký tự không phải chữ/số thành một khoảng trắng. GIỮ dấu tiếng Việt:
    bỏ dấu thì "Minh" trùng "mình" (đại từ), "thù" trùng "thư"."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


def contains_phrase(flat_text: str, phrase: str) -> bool:
    """`flat_text` đã qua `flat`; `phrase` chưa. Khớp trọn từ."""
    p = flat(phrase)
    return bool(p) and re.search(rf"(?<!\w){re.escape(p)}(?!\w)", flat_text) is not None


class AliasIndex:
    """Tên và biệt danh → id thực thể, khớp trọn từ, tên dài trước (nên "Lan" không trúng bên
    trong "Phạm Thị Lan"). Hai id trùng một tên: giữ id đầu tiên."""

    def __init__(self, names: Mapping[str, Sequence[str]]) -> None:
        by_alias: dict[str, str] = {}
        for entity_id, aliases in names.items():
            for alias in aliases:
                by_alias.setdefault(flat(alias), entity_id)
        by_alias.pop("", None)
        self._ordered = sorted(by_alias.items(), key=lambda kv: (-len(kv[0]), kv[0]))

    def find(self, text: str) -> list[str]:
        """Id thực thể được nhắc tới trong `text`, theo thứ tự xuất hiện đầu tiên."""
        work = flat(text)
        hits: list[tuple[int, str]] = []
        for alias, entity_id in self._ordered:
            pattern = re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")
            for m in pattern.finditer(work):
                hits.append((m.start(), entity_id))
                work = work[:m.start()] + "#" * (m.end() - m.start()) + work[m.end():]
        seen: dict[str, int] = {}
        for pos, entity_id in sorted(hits):
            seen.setdefault(entity_id, pos)
        return list(seen)


# --- ngữ cảnh -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Context:
    system: str
    chapter: int  # đã đọc tới hết chương này
    text: str  # đúng chữ đưa cho model trả lời
    facts: frozenset[str] = frozenset()  # hệ đồ thị: khoá các điều đã đưa vào (cho oracle, test)
    detail: Mapping[str, object] = field(default_factory=dict)  # số liệu cho báo cáo


def chapter_block(story: Mapping[int, str], chapter: int) -> str:
    return f"[Chương {chapter}]\n{story[chapter].strip()}"


def context_none(story: Mapping[int, str], chapter: int) -> Context:
    return Context("none", chapter, chapter_block(story, chapter))


def context_full(story: Mapping[int, str], chapter: int) -> Context:
    text = "\n\n".join(chapter_block(story, c) for c in sorted(story) if c <= chapter)
    return Context("full", chapter, text)


def context_rolling(story: Mapping[int, str], chapter: int,
                    rolling: Mapping[int, str]) -> Context:
    """`rolling[k]`: bản tóm tắt cuộn của chương 1..k. Chương 1 không có phần tóm tắt."""
    parts = []
    if chapter > 1:
        parts.append(f"[Tóm tắt các chương 1–{chapter - 1}]\n{rolling[chapter - 1].strip()}")
    parts.append(chapter_block(story, chapter))
    return Context("rolling", chapter, "\n\n".join(parts))


# --- BM25 (đối thủ RAG, D-73) ----------------------------------------------------------------------

# Âm tiết chức năng rất thường gặp, không giúp phân biệt đoạn.
STOPWORDS = frozenset(
    ["là", "của", "và", "có", "không", "được", "ở", "đã", "bị", "thì", "mà", "cho", "với", "một", "những", "các", "ai", "gì", "nào", "đâu", "hay", "chưa", "còn", "bao", "nhiêu", "thế", "này", "đó", "kia", "khi", "sẽ", "đang", "rất", "như", "từ", "đến", "trong", "trên", "dưới", "ra", "vào", "lên", "xuống"]
)


def tokens(text: str) -> list[str]:
    """Âm tiết (bỏ âm tiết chức năng) cộng cặp âm tiết liền nhau, vì từ tiếng Việt
    thường gồm 2 âm tiết."""
    syllables = [t for t in flat(text).split() if t not in STOPWORDS]
    return syllables + [f"{a}_{b}" for a, b in itertools.pairwise(syllables)]


@dataclass(frozen=True)
class Chunk:
    chapter: int
    index: int
    text: str


def chunk_chapter(chapter: int, text: str, *, chunk_chars: int) -> list[Chunk]:
    """Đoạn văn liền nhau gộp tới khi đủ `chunk_chars` ký tự (câu thoại một dòng quá ngắn để tự
    đứng). Bỏ dòng tiêu đề markdown."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text)
                  if p.strip() and not p.lstrip().startswith("#")]
    chunks: list[Chunk] = []
    buf: list[str] = []
    for p in paragraphs:
        buf.append(p)
        if sum(len(x) for x in buf) >= chunk_chars:
            chunks.append(Chunk(chapter, len(chunks), "\n".join(buf)))
            buf = []
    if buf:
        chunks.append(Chunk(chapter, len(chunks), "\n".join(buf)))
    return chunks


class Bm25Index:
    """BM25 Okapi thuần Python. Không phụ thuộc, tất định, không tốn lời gọi model."""

    def __init__(self, chunks: Sequence[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1, self.b = k1, b
        self._tf = [Counter(tokens(c.text)) for c in self.chunks]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._avg = (sum(self._len) / len(self._len)) if self._len else 0.0
        df: Counter[str] = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(self.chunks)
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def scores(self, query: str) -> list[float]:
        q = Counter(tokens(query))
        out = []
        for tf, length in zip(self._tf, self._len, strict=True):
            s = 0.0
            for term in q:
                f = tf.get(term, 0)
                if f:
                    norm = f + self.k1 * (1 - self.b + self.b * length / (self._avg or 1.0))
                    s += self._idf[term] * f * (self.k1 + 1) / norm
            out.append(s)
        return out

    def top(self, query: str, k: int) -> list[Chunk]:
        """k đoạn điểm cao nhất (điểm 0 thì bỏ), hoà thì đoạn ở chương trước, đoạn đứng trước."""
        scored = sorted(
            ((s, c) for s, c in zip(self.scores(query), self.chunks, strict=True) if s > 0),
            key=lambda sc: (-sc[0], sc[1].chapter, sc[1].index),
        )
        return [c for _, c in scored[:k]]


def context_rag(story: Mapping[int, str], chapter: int, question: str, *, top_k: int,
                chunk_chars: int) -> Context:
    old = [c for ch in sorted(story) if ch < chapter
           for c in chunk_chapter(ch, story[ch], chunk_chars=chunk_chars)]
    hits = sorted(Bm25Index(old).top(question, top_k), key=lambda c: (c.chapter, c.index))
    parts = []
    if hits:
        parts.append("[Các đoạn liên quan trong chương trước]\n" + "\n\n".join(
            f"(chương {c.chapter})\n{c.text}" for c in hits))
    parts.append(chapter_block(story, chapter))
    return Context("rag", chapter, "\n\n".join(parts),
                   detail={"retrieved": [(c.chapter, c.index) for c in hits],
                           "pool": len(old)})


# --- đồ thị (đối thủ 0) -----------------------------------------------------------------------------

LINKED_ENTITY_CAP = 6
LINES_PER_ENTITY_CAP = 40
GRAPH_CHARS_CAP = 6000


def edge_key(e: EdgeRow) -> str:
    return f"edge:{e.type}:{e.source}>{e.target}@{e.valid_from_chapter}"


@dataclass
class _Facts:
    keys: set[str] = field(default_factory=set)


class GraphReader:
    """Đọc đồ thị tới hết chương N, chỉ qua `GraphState` (nền Neo4j qua lớp graph/ hoặc gói trong
    bộ nhớ). Cửa sổ hiệu lực của cạnh bị cắt ở N: cạnh đóng ở chương sau N vẫn "còn hiệu lực"."""

    def __init__(self, state: GraphState, chapter: int) -> None:
        self.state, self.chapter = state, chapter
        self._names = state.named_nodes()
        self._nodes: dict[str, tuple[str, dict]] = {}
        self._edge_cache: dict[tuple[str, str, str], list[EdgeRow]] = {}

    # nút
    def _load(self, ids: Sequence[str]) -> None:
        missing = [i for i in ids if i not in self._nodes]
        if missing:
            for node_id, row in self.state.nodes(missing).items():
                self._nodes[node_id] = (row.label, dict(row.props))

    def label_of(self, node_id: str) -> str:
        self._load([node_id])
        return self._nodes.get(node_id, ("?", {}))[0]

    def title(self, node_id: str) -> str:
        """Tên với nút có tên; chữ mô tả với Event, Fact, Lie."""
        if node_id in self._names:
            return self._names[node_id][0]
        self._load([node_id])
        label, props = self._nodes.get(node_id, ("?", {}))
        for key in ("description", "text", "content", "title"):
            if props.get(key):
                return str(props[key])
        return node_id if label == "?" else f"{label} {node_id}"

    def chapter_of(self, node_id: str) -> int | None:
        self._load([node_id])
        value = self._nodes.get(node_id, ("?", {}))[1].get("chapter")
        return int(value) if isinstance(value, int) else None

    # cạnh
    def edges(self, edge_type: str, *, source: str | None = None,
              target: str | None = None) -> list[EdgeRow]:
        key = (edge_type, source or "", target or "")
        if key not in self._edge_cache:
            self._edge_cache[key] = self.state.edges_at(
                edge_type, self.chapter, source_id=source, target_id=target, ever=True)
        return self._edge_cache[key]

    def end_chapter(self, e: EdgeRow) -> int | None:
        """Chương cuối còn đúng của cạnh đã đóng; None nếu còn hiệu lực ở chương N."""
        if e.valid_to_chapter is None or e.valid_to_chapter > self.chapter:
            return None
        return e.valid_to_chapter - 1

    def span(self, e: EdgeRow) -> str:
        end = self.end_chapter(e)
        start = e.valid_from_chapter
        if end is None:
            return "đúng từ trước chương 1 tới nay" if start == 0 else (
                f"đúng từ cuối chương {start} tới nay")
        begin = "trước chương 1" if start == 0 else f"cuối chương {start}"
        return f"đúng từ {begin} tới cuối chương {end}"

    def died_at(self, character: str) -> EdgeRow | None:
        deaths = self.edges("DIED_IN", source=character)
        return min(deaths, key=lambda e: e.valid_from_chapter) if deaths else None


def _sorted(edges: Sequence[EdgeRow]) -> list[EdgeRow]:
    return sorted(edges, key=lambda e: (e.valid_from_chapter, e.id))


def build_graph_context(
    state: GraphState, question: str, chapter: int, *, story: Mapping[int, str] | None = None,
    recent: bool = True,
) -> Context:
    """Ngữ cảnh đồ thị cho một câu hỏi hỏi sau chương `chapter`. `story` chỉ để thêm chương N.

    Thứ tự khối: danh sách nhân vật (còn sống/đã chết), mỗi thực thể nêu trong câu hỏi, các lời nói
    dối và sự kiện mà chúng dẫn tới. Quá GRAPH_CHARS_CAP thì bỏ khối cuối; `facts` chỉ gồm khoá của
    những khối còn lại."""
    reader = GraphReader(state, chapter)
    index = AliasIndex(reader._names)
    linked = index.find(question)[:LINKED_ENTITY_CAP]
    if not linked:  # câu không nêu tên ai: lấy nhân vật chính, ít nhất có chỗ bắt đầu
        linked = [state.protagonist_id()]
    header = (f"Đồ thị trí nhớ của truyện, đúng tới hết chương {chapter}. Mỗi dòng là một sự thật "
              "đã ghi; điều không có trong danh sách 'đã biết' của một nhân vật là điều người đó "
              "chưa biết.")
    keys: set[str] = set()
    texts = [header]
    used = len(header)

    def take(text: str, block_keys: set[str]) -> None:
        nonlocal used
        if used + len(text) + 2 > GRAPH_CHARS_CAP:
            return
        texts.append(text)
        keys.update(block_keys)
        used += len(text) + 2

    take(*_roster_block(reader))
    lies: dict[str, None] = {}
    events: dict[str, None] = {}
    for entity in linked:
        facts = _Facts()
        take(_entity_block(reader, entity, facts, lies, events), facts.keys)
    for lie in lies:
        facts = _Facts()
        take(_lie_block(reader, lie, facts), facts.keys)
    for event in events:
        facts = _Facts()
        take(_event_block(reader, event, facts), facts.keys)
    graph_text = "\n\n".join(texts)
    parts = [graph_text]
    if recent and story is not None:
        parts.append(chapter_block(story, chapter))
    return Context("graph", chapter, "\n\n".join(parts), frozenset(keys),
                   {"linked": linked, "graph_chars": len(graph_text)})


def _roster_block(r: GraphReader) -> tuple[str, set[str]]:
    """Mọi nhân vật và tình trạng cuối chương N: câu hỏi tổng hợp ("ai đã chết") không nêu tên ai."""
    labels = r.state.node_labels(sorted(r._names))
    keys: set[str] = set()
    lines = []
    for node_id in sorted(r._names, key=lambda i: r._names[i][0]):
        if labels.get(node_id) != "Character":
            continue
        death = r.died_at(node_id)
        keys.add(f"status:{node_id}")
        status = "còn sống" if death is None else f"ĐÃ CHẾT (từ cuối chương {death.valid_from_chapter})"
        lines.append(f"- {r._names[node_id][0]}: {status}")
    head = f"## Danh sách nhân vật, tình trạng cuối chương {r.chapter}"
    return "\n".join([head, *lines[:LINES_PER_ENTITY_CAP]]), keys


def _entity_block(r: GraphReader, entity: str, facts: _Facts, lies: dict[str, None],
                  events: dict[str, None]) -> str:
    names = r._names.get(entity, (entity,))
    kind = {"Character": "nhân vật", "Location": "nơi chốn", "Item": "đồ vật",
            "Faction": "phe nhóm"}.get(r.label_of(entity), "thực thể")
    head = f"## {names[0]} ({kind})" + (f", còn gọi: {', '.join(names[1:])}" if len(names) > 1 else "")
    facts.keys.add(f"entity:{entity}")
    lines: list[str] = []

    if r.label_of(entity) == "Character":
        death = r.died_at(entity)
        facts.keys.add(f"status:{entity}")
        if death is None:
            lines.append(f"- Tình trạng cuối chương {r.chapter}: còn sống.")
        else:
            lines.append(f"- Tình trạng cuối chương {r.chapter}: ĐÃ CHẾT (từ cuối chương "
                         f"{death.valid_from_chapter}).")

    def add(e: EdgeRow, text: str) -> None:
        facts.keys.add(edge_key(e))
        lines.append(f"- {text} ({r.span(e)}).")

    for e in _sorted(r.edges("HOLDS", source=entity)):
        add(e, f"Giữ {r.title(e.target)}")
    for e in _sorted(r.edges("HOLDS", target=entity)):
        add(e, f"{r.title(e.source)} giữ {names[0]}")
    for e in _sorted(r.edges("LOCATED_AT", source=entity)):
        add(e, f"Ở {r.title(e.target)}")
    for e in _sorted(r.edges("LOCATED_AT", target=entity)):
        add(e, f"{r.title(e.source)} ở {names[0]}")
    for e in _sorted(r.edges("MEMBER_OF", source=entity)):
        add(e, f"Thuộc {r.title(e.target)}")
    for e in _sorted(r.edges("MEMBER_OF", target=entity)):
        add(e, f"{r.title(e.source)} thuộc {names[0]}")
    for e in _sorted(r.edges("RELATES_TO", source=entity) + r.edges("RELATES_TO", target=entity)):
        who, whom = r.title(e.source), r.title(e.target)
        add(e, f"Quan hệ của {who} với {whom}: {e.props.get('kind', '?')} "
               f"(mức {e.props.get('score', '?')})")
    for e in _sorted(r.edges("PARTICIPATED_IN", source=entity)):
        role = f"; vai: {e.props['role']}" if e.props.get("role") else ""
        add(e, f"Tham gia sự kiện chương {r.chapter_of(e.target) or e.valid_from_chapter}: "
               f"{r.title(e.target)}{role}")
        events.setdefault(e.target)
    for e in _sorted(r.edges("DIED_IN", source=entity)):
        add(e, f"Chết trong sự kiện: {r.title(e.target)}")
        events.setdefault(e.target)
    for e in _sorted(r.edges("KNOWS", source=entity)):
        how = f"; cách biết: {e.props['how']}" if e.props.get("how") else ""
        told = f"; người kể: {r.title(e.props['told_by'])}" if e.props.get("told_by") else ""
        if r.label_of(e.target) == "Lie":
            add(e, f"Đã biết đó là lời nói dối: «{r.title(e.target)}»{how}{told}")
            lies.setdefault(e.target)
        else:
            add(e, f"Đã biết: {r.title(e.target)}{how}{told}")
    for e in _sorted(r.edges("TOLD", source=entity)):
        add(e, f"Đã nói một lời dối ở chương {r.chapter_of(e.target) or e.valid_from_chapter}: "
               f"«{r.title(e.target)}»")
        lies.setdefault(e.target)
    for e in _sorted(r.edges("TOLD_TO", target=entity)):
        add(e, f"Đã nghe một lời dối: «{r.title(e.source)}»")
        lies.setdefault(e.source)
    for e in _sorted(r.edges("REVEALED_TO_PLAYER", source=entity)):
        if e.props.get("quote"):
            add(e, f"Trên trang chương {e.valid_from_chapter}: «{e.props['quote']}»")
    return "\n".join([head, *lines[:LINES_PER_ENTITY_CAP]])


def _lie_block(r: GraphReader, lie: str, facts: _Facts) -> str:
    facts.keys.add(f"lie:{lie}")
    speakers = r.edges("TOLD", target=lie)
    hearers = r.edges("TOLD_TO", source=lie)
    knowers = r.edges("KNOWS", target=lie)
    for e in (*speakers, *hearers, *knowers):
        facts.keys.add(edge_key(e))
    who = ", ".join(r.title(e.source) for e in speakers) or "?"
    to = ", ".join(r.title(e.target) for e in hearers) or "?"
    speaker_ids = {e.source for e in speakers}
    aware = [f"{r.title(e.source)} (từ cuối chương {e.valid_from_chapter})"
             for e in _sorted(knowers) if e.source not in speaker_ids]
    status = ("; những người ngoài người nói đã biết đó là lời dối: " + ", ".join(aware)
              if aware else "; chưa ai ngoài người nói biết đó là lời dối")
    chap = r.chapter_of(lie)
    return (f"## Lời nói dối: «{r.title(lie)}»\n- Chương {chap}; người nói: {who}; "
            f"người nghe: {to}{status}.")


def _event_block(r: GraphReader, event: str, facts: _Facts) -> str:
    people = _sorted(r.edges("PARTICIPATED_IN", target=event) + r.edges("DIED_IN", target=event))
    facts.keys.add(f"node:{event}")
    for e in people:
        facts.keys.add(edge_key(e))
    chap = r.chapter_of(event)
    who = "; ".join(
        f"{r.title(e.source)}" + (f" ({e.props['role']})" if e.props.get("role") else "")
        + (" (đã chết)" if e.type == "DIED_IN" else "")
        for e in people)
    return f"## Sự kiện (chương {chap}): {r.title(event)}\n- Người liên quan: {who or '?'}."
