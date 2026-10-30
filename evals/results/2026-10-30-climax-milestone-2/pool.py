"""Gộp kết quả ca đối chứng của lần chạy đầu (lần 1, 2) và lần đo thêm `control-n6/` (lần 3 đến 6), theo
phần bổ sung cuối `expectations.md`. Không gọi model, chỉ đọc `results.jsonl`.

    python evals/results/2026-10-30-climax-milestone-2/pool.py

In mỗi ca, mỗi bản đề: số lần đã chạy, số lần nhận đúng mốc gốc, dấu khác (mốc không phải mốc gốc của
chương), số câu trích mốc bị G3 từ chối; rồi tổng gộp và các phép so của luật. Dấu cần đọc tay (mọi dấu
được nhận của `extract-11` ở lần 3 đến 6) in ở cuối kèm câu trích.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
V8, V11 = "extract-8", "extract-11"
sys.stdout.reconfigure(encoding="utf-8")


def rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def short(run: str) -> str:
    return run.split("after-")[-1]  # tu-tien, ky-ao-2


def main() -> int:
    data = [r for r in rows(HERE / "results.jsonl") + rows(HERE / "control-n6" / "results.jsonl")
            if r["group"] == "2-doi-chung"]
    # chỉ so cặp (ca, lần) mà cả hai bản đề đều chạy (bổ sung: trần cắt thì bỏ cả cặp)
    ran = defaultdict(set)
    for r in data:
        ran[(r["run"], r["chapter"], r["rep"])].add(r["version"])
    paired = [r for r in data if ran[(r["run"], r["chapter"], r["rep"])] == {V8, V11}]
    stats: dict = defaultdict(lambda: {"n": 0, "hit": 0, "other": 0, "g3": 0})
    for r in paired:
        key = (short(r["run"]), r["chapter"], r["version"])
        s = stats[key]
        s["n"] += 1
        got = {a[0] for a in r["accepted"]}
        s["hit"] += bool(got & set(r["production_marks"]))
        s["other"] += len(got - set(r["production_marks"]))
        s["g3"] += sum("(G3)" in w for _, w in r["rejected"])
    total = {v: {"n": 0, "hit": 0, "other": 0, "g3": 0} for v in (V8, V11)}
    cases = sorted({(k[0], k[1]) for k in stats}, key=lambda c: (c[0], -c[1]))
    print("ca | extract-8 nhận đúng/lần, dấu khác, G3 | extract-11 nhận đúng/lần, dấu khác, G3")
    for run, ch in cases:
        parts = []
        for v in (V8, V11):
            s = stats[(run, ch, v)]
            parts.append(f"{s['hit']}/{s['n']}, {s['other']}, {s['g3']}")
            for k in total[v]:
                total[v][k] += s[k]
        print(f"{run} ch{ch} | " + " | ".join(parts))
    t8, t11 = total[V8], total[V11]
    print(f"gộp | {t8['hit']}/{t8['n']}, {t8['other']}, {t8['g3']} | {t11['hit']}/{t11['n']}, "
          f"{t11['other']}, {t11['g3']}")
    ky16 = {v: stats[("ky-ao-2", 16, v)] for v in (V8, V11)}
    print(f"hiệu gộp (11 - 8): {t11['hit'] - t8['hit']}; ky-ao ch16: "
          f"{ky16[V11]['hit'] - ky16[V8]['hit']} (8: {ky16[V8]['hit']}/{ky16[V8]['n']}, "
          f"11: {ky16[V11]['hit']}/{ky16[V11]['n']})")
    print("\nDấu được nhận của extract-11 ở lần 3 đến 6 (đọc tay):")
    for r in paired:
        if r["version"] == V11 and r["rep"] >= 3:
            for number, quote_parts in r["accepted"]:
                print(f"  {short(r['run'])} ch{r['chapter']} lần {r['rep']}: m{number} {quote_parts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
