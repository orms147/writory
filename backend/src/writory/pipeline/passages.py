"""Kho đoạn trên trang: chia đoạn và BM25 (D-73, D-81, D-85).

MỘT code cho hai nơi dùng:
- bài đo A: hệ `rag` và hệ `graph_quotes` (`pipeline.bench_a_systems`);
- sản phẩm: ngữ cảnh của model dàn ý và model viết (`pipeline.scene`, `pipeline.chapter`), để cảnh
  mới thấy nguyên văn điều đã hiện trên trang (cửa đã mở, ai nói gì), không chỉ đồ thị và tóm tắt.

BM25 Okapi thuần Python: không phụ thuộc, tất định, không tốn lời gọi model. Không đọc đồ thị, nên
không tự chạm lớp truth; nơi gọi quyết định đưa kết quả cho vai nào (G1) và bọc chữ ra sao (G4).
"""

import itertools
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# --- chuẩn hoá chữ -------------------------------------------------------------------------------


def flat(text: str) -> str:
    """NFC, hạ chữ thường, mọi ký tự không phải chữ/số thành một khoảng trắng. GIỮ dấu tiếng Việt:
    bỏ dấu thì "Minh" trùng "mình" (đại từ), "thù" trùng "thư"."""
    return " ".join(re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold()))


# --- BM25 ------------------------------------------------------------------------------------------

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


class PagePool:
    """Các đoạn của một tập chương, đã dựng chỉ mục. `chapters`: số chương → văn đã hiện cho người
    chơi (các cảnh nối lại). Dựng một lần, hỏi nhiều lần: một lượt viết chương hỏi ở dàn ý, ở viết,
    và ở mỗi lần viết lại."""

    def __init__(self, chapters: Mapping[int, str], *, chunk_chars: int) -> None:
        self._chunks = [c for ch in sorted(chapters)
                        for c in chunk_chapter(ch, chapters[ch], chunk_chars=chunk_chars)]
        self._index = Bm25Index(self._chunks)
        self._by_key = {(c.chapter, c.index): c for c in self._chunks}

    @property
    def size(self) -> int:
        return len(self._chunks)

    def top(self, query: str, *, top_k: int, max_chars: int | None = None,
            neighbors: int = 0) -> list[Chunk]:
        """Tối đa `top_k` đoạn điểm cao nhất, sắp theo thứ tự truyện. `max_chars`: tổng độ dài chữ
        tối đa; vượt thì bỏ đoạn điểm thấp trước, giữ đoạn điểm cao nhất ngay cả khi riêng nó đã
        vượt (một đoạn cụt giữa câu tệ hơn một đoạn dài).

        `neighbors` (D-96): mỗi đoạn trúng kéo theo tối đa `neighbors` đoạn liền sau nó trong CÙNG
        chương, vì câu trả lời hay nằm ở đoạn tiếp ngay sau đoạn có từ khoá (người nhận thẻ ở câu
        sau lời hẹn). Đoạn kế chỉ vào khi còn chỗ trong `max_chars`, theo thứ hạng của đoạn trúng; các
        đoạn trúng không bao giờ bị đoạn kế đẩy ra."""
        if neighbors < 0:
            raise ValueError(f"neighbors phải >= 0, nhận {neighbors}")
        ranked = self._index.top(query, top_k)
        if max_chars is not None:
            kept: list[Chunk] = []
            used = 0
            for c in ranked:
                if kept and used + len(c.text) > max_chars:
                    break
                kept.append(c)
                used += len(c.text)
            ranked = kept
        picked = list(ranked)
        if neighbors:
            have = {(c.chapter, c.index) for c in picked}
            used = sum(len(c.text) for c in picked)
            for hit in ranked:
                for step in range(1, neighbors + 1):
                    nxt = self._by_key.get((hit.chapter, hit.index + step))
                    if nxt is None or (nxt.chapter, nxt.index) in have:
                        continue
                    if max_chars is not None and used + len(nxt.text) > max_chars:
                        break
                    picked.append(nxt)
                    have.add((nxt.chapter, nxt.index))
                    used += len(nxt.text)
        return sorted(picked, key=lambda c: (c.chapter, c.index))
