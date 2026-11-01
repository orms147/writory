"""Đếm chuỗi thoại liền nhau trong tts.txt (mỗi dòng thoại là “…”): chỉ số khách quan cho D-156, không gọi model."""
import json
import sys
from pathlib import Path


def stats(text: str, max_run: int = 2) -> dict:
    runs, cur, lines, dialogue = [], 0, 0, 0
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue  # dòng trống không cắt chuỗi (giọng đọc máy đọc liền)
        lines += 1
        if line.startswith("“"):
            cur += 1
            dialogue += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    words = len(text.split())
    over = [r for r in runs if r > max_run]
    return {"words": words, "dialogue_lines": dialogue, "runs_over_2": len(over), "longest_run": max(runs or [0]),
            "runs_over_2_per_1000_words": round(1000 * len(over) / max(words, 1), 2)}


for p in sys.argv[1:]:
    print(Path(p).parent.name, json.dumps(stats(Path(p).read_text(encoding="utf-8")), ensure_ascii=False))
