"""Phép kiểm truy hồi đoạn của bài đo A, không gọi model (D-96).

Với mỗi câu hỏi có câu trích bằng chứng ở chương CŨ hơn chương hỏi (chương hỏi thì hệ nào cũng
đã được xem nguyên văn), lấy đoạn như hệ `graph_quotes` (BM25 trên chương 1..N-1) và hỏi: trong
các đoạn lấy về có câu trích bằng chứng nào không? Đếm số câu trúng cho từng cặp (`top_k`,
`neighbors`) cùng số ký tự đoạn trích trung bình, để chọn số cho `limits.context` mà không tốn
tiền: trúng là điều kiện cần của việc model trả lời đúng, chưa phải điều kiện đủ (model còn phải
đọc đúng, xem `evals/results/2026-10-22-memory-ky-ao-vua-1-facts-s3/notes.md`).
"""

from collections.abc import Sequence
from dataclasses import dataclass

from writory.pipeline.bench_a_data import BenchData
from writory.pipeline.bench_a_systems import retrieve
from writory.pipeline.passages import flat


@dataclass(frozen=True)
class RecallRow:
    top_k: int
    neighbors: int
    hit: int  # số câu có ít nhất một câu trích bằng chứng nằm trong các đoạn lấy về
    mean_chars: float  # số ký tự đoạn trích trung bình mỗi câu


@dataclass(frozen=True)
class RecallTable:
    total: int  # số câu có bằng chứng ở chương cũ
    rows: list[RecallRow]


def recall_table(data: BenchData, *, top_ks: Sequence[int], neighbors: Sequence[int],
                 max_chars: int | None) -> RecallTable:
    old = []
    for q in data.questions.questions:
        quotes = [flat(e.quote) for e in q.evidence if e.chapter < q.ask_chapter]
        if quotes:
            old.append((q, quotes))
    rows: list[RecallRow] = []
    chunk_chars = data.run.rag.chunk_chars
    for top_k in top_ks:
        for n in neighbors:
            hit = 0
            chars = 0
            for q, quotes in old:
                hits, _ = retrieve(data.story, [c for c in data.story if c < q.ask_chapter],
                                   q.question, top_k=top_k, chunk_chars=chunk_chars,
                                   neighbors=n, max_chars=max_chars)
                text = flat(" ".join(c.text for c in hits))
                hit += any(quote in text for quote in quotes)
                chars += sum(len(c.text) for c in hits)
            rows.append(RecallRow(top_k, n, hit, chars / len(old) if old else 0.0))
    return RecallTable(len(old), rows)


def table_text(table: RecallTable, *, max_chars: int | None) -> str:
    cap = "không trần" if max_chars is None else f"trần {max_chars} ký tự"
    lines = [f"Truy hồi đoạn, {table.total} câu có bằng chứng ở chương cũ ({cap}).", "",
             "| top_k | đoạn kế | trúng | ký tự đoạn trích TB |", "|---|---|---|---|"]
    lines += [f"| {r.top_k} | {r.neighbors} | {r.hit}/{table.total} | {r.mean_chars:.0f} |"
              for r in table.rows]
    return "\n".join(lines)
