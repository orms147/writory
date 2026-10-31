"""Độ phủ câu trích bằng chứng trong context người kể, không gọi model (D-143).

Với mỗi câu của đề bài A trên truyện ky-ao 10 chương, dựng đúng phần sổ tay và đoạn trên trang mà
người kể (`narrator-4`) sẽ nhận ở chương hỏi, rồi đếm số câu có MỌI câu trích bằng chứng nằm trong đó
(sổ tay + đoạn) và chỉ trong đoạn. Trúng là điều kiện cần của trả lời đúng, chưa phải điều kiện đủ.

Chạy trong backend/:
    PYTHONIOENCODING=utf-8 uv run python ../evals/results/2026-10-30-narrator-passages/recall_grid.py
"""

from writory.config import NarratorPagesLimits, load_config
from writory.pipeline.bench_a_data import load_data
from writory.pipeline.bench_a_narrator import NarratorSide, seen_pages
from writory.pipeline.narrator import render_notebook, render_passages, select_passages
from writory.pipeline.notebook import select_notebook
from writory.pipeline.passages import flat

GRID = [(3, 2400, 1), (3, 2400, 0), (4, 2400, 1), (4, 3600, 1), (5, 4000, 1), (6, 4800, 1),
        (8, 6000, 1)]

cfg = load_config()
for qf in ("questions-ky-ao-vua-1-facts.yaml", "questions-ky-ao-vua-1.yaml"):
    data = load_data(questions_file=qf)
    side = NarratorSide.load(data)
    print(f"== {qf}")
    print("| top_k | max_chars | đoạn kế | đủ chứng cứ (sổ tay + đoạn) | chỉ trong đoạn | ký tự đoạn TB |")
    print("|---|---|---|---|---|---|")
    for top_k, max_chars, nb in GRID:
        lim = NarratorPagesLimits(top_k=top_k, chunk_chars=500, max_chars=max_chars, neighbors=nb)
        hit = hit_pages = chars = 0
        for q in data.questions.questions:
            view = side.state(q.ask_chapter).view
            notebook = render_notebook(view, select_notebook(q.question, view,
                                                             cfg.limits.narrator_notebook))
            passages = render_passages(select_passages(q.question, view,
                                                       seen_pages(data, q.ask_chapter), lim))
            chars += len(passages)
            both = flat(notebook + "\n" + passages)
            hit += all(flat(e.quote) in both for e in q.evidence)
            hit_pages += all(flat(e.quote) in flat(passages) for e in q.evidence)
        n = len(data.questions.questions)
        print(f"| {top_k} | {max_chars} | {nb} | {hit}/{n} | {hit_pages}/{n} | {chars / n:.0f} |")
