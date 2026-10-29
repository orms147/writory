"""Token vào và chi phí theo vai ở các dải chương CỐ ĐỊNH (1–3, 8–10, 15–17), để so các lần chạy có số chương
khác nhau (đo nền mức Dài). Chỉ đọc `calls.jsonl`, status ok. Dùng:

  python long_compare.py <thư mục chạy> [<thư mục chạy> ...]
"""

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BANDS = [(1, 3), (8, 10), (15, 17)]
ROLES = ("writer", "outline", "extract", "choices", "summary", "moderate")


def band_stats(run: Path) -> dict:
    calls = [json.loads(x) for x in (run / "calls.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    tokens = defaultdict(list)  # (role, band) -> prompt_tokens của từng lời gọi
    usd = defaultdict(float)  # (role, band) -> USD
    for c in calls:
        if c.get("status") != "ok":
            continue
        for b in BANDS:
            if b[0] <= (c.get("chapter") or 0) <= b[1]:
                tokens[(c["role"], b)].append(c.get("prompt_tokens") or 0)
                usd[(c["role"], b)] += c.get("cost_usd") or 0.0
    width = lambda b: b[1] - b[0] + 1
    return {"run": run.name, "bands": [f"ch{a}-{b}" for a, b in BANDS],
            "input_tokens": {r: [round(st.mean(tokens[(r, b)])) if tokens[(r, b)] else None for b in BANDS]
                             for r in ROLES},
            "usd_per_chapter": {r: [round(usd[(r, b)] / width(b), 5) for b in BANDS] for r in ROLES},
            "usd_per_chapter_total": [round(sum(usd[(r, b)] for r in ROLES) / width(b), 5) for b in BANDS]}


if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(json.dumps(band_stats(Path(d)), ensure_ascii=False))
