"""Số đo bằng code cho A/B đổi pha D-119 trên truyện Dài (khai trước khi chạy; xem notes.md).

  python psab_metrics.py <từ chương> <tới chương> <thư mục chạy> [<thư mục chạy> ...]   (mỗi lần chạy một dòng JSON)

Đọc `truth_dump.json`, `report.json`, `meta.json`. Không gọi model. Mọi số tính trên dải chương
`từ chương`..min(`tới chương`, N) (N = số chương đã ghi), trừ khi ghi khác. Định nghĩa KHÔNG dùng `pacing._phase_changes`
(đó là thứ nhánh B được nhắc làm, đo bằng chính nó là vòng tròn); chỉ dùng nơi ở của nhân vật chính
(cạnh LOCATED_AT) và mốc kế hoạch.

- same_place_longest: số chương liền dài nhất mà cuối chương nhân vật chính ở cùng một nơi.
- place_returns: số chương về lại một nơi đã ở trong ba chương trước (như `long_metrics.py`).
- new_places: số nơi nhân vật chính tới LẦN ĐẦU trong dải (nơi đã ở trước dải không tính).
- milestones_done / milestones_due_on_time: mốc `done_chapter` có (cả truyện) và mốc đã tới hạn mà xong
  đúng khoảng, lấy từ `plan_vs_result.milestones` ở report.json (D-116).
- phase_shift_fired: các chương đã ghi mà mục tiêu chương có câu đổi pha (report.json); `followed`: trong số đó
  chương c mà ở c hoặc c+1 nhân vật chính tới nơi mới hoặc một mốc xong (kiểm tra rằng nhắc có tác dụng).
- stalled_count: chương không đổi trạng thái (định nghĩa `long_metrics.py`) trong dải.
- usd_per_chapter, rewrites, chapters_committed, flag (`context_flags.phase_shift_every`).
"""

import importlib.util
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
LM = Path(__file__).resolve().parent.parent / "2026-10-29-run-long-baseline" / "long_metrics.py"
spec = importlib.util.spec_from_file_location("long_metrics", LM)
long_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(long_metrics)
PROTAGONIST = "protagonist"


def place_by_chapter(truth: dict) -> tuple[dict[int, str], dict[str, int]]:
    """Nơi nhân vật chính ở cuối mỗi chương đã ghi (nơi đang hiệu lực; cạnh mở sau cùng thắng)."""
    packages = {int(k): v for k, v in truth["packages"].items()}
    closes: dict[str, int] = {}
    for num in sorted(packages):
        for c in packages[num]["close"]:
            closes[c["id"]] = c["valid_to_chapter"]
    edges = [(e["valid_from_chapter"], closes.get(e["id"]), e["to"])
             for num in sorted(packages) for e in packages[num]["edges"]
             if e["type"] == "LOCATED_AT" and e["from"] == PROTAGONIST]
    out: dict[int, str] = {}
    for num in range(1, max(packages) + 1):
        here = [e for e in edges if e[0] <= num and (e[1] is None or e[1] > num)]
        if here:
            out[num] = here[-1][2]
    first = {}
    for start, _, place in sorted(edges):
        first.setdefault(place, start)
    out[0] = next((p for s, _, p in sorted(edges) if s == 0), "")
    return out, first


def metrics(run: Path, start: int, end: int) -> dict:
    truth = json.loads((run / "truth_dump.json").read_text(encoding="utf-8"))
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    meta = json.loads((run / "meta.json").read_text(encoding="utf-8"))
    written = max(int(k) for k in truth["packages"])
    n = min(end, written)
    place_at, first_seen = place_by_chapter(truth)
    chapters = [c for c in range(start, n + 1) if c in place_at]
    longest = cur = 0
    prev = None
    for c in chapters:
        cur = cur + 1 if place_at[c] == prev else 1
        longest, prev = max(longest, cur), place_at[c]
    returns = [c for c in chapters if c - 1 in place_at and place_at[c] != place_at[c - 1]
               and place_at[c] in {place_at.get(c - j) for j in (2, 3)}]
    new_places = sorted(p for p, s in first_seen.items() if s >= start and s <= n)
    ms = report["plan_vs_result"].get("milestones", [])  # chưa có trước D-116
    due = [m for m in ms if m["window"] and m["window"][1] <= n]
    ms_done = {m["n"]: m["done_chapter"] for m in ms if m["done_chapter"]}
    fired = report.get("phase_shift_chapters", [])
    followed = []
    for c in fired:
        moved = any(s in (c, c + 1) for s in first_seen.values())
        followed.append(moved or any(d in (c, c + 1) for d in ms_done.values()))
    lm = long_metrics.metrics(run)
    stalled = [c for c in lm["stalled_chapters"] if start <= c <= n]
    cost = report["cost"]["by_chapter"]
    per = [v["total"] for k, v in cost.items() if int(k) > 0]
    return {
        "run": run.name, "flag": meta["context_flags"].get("phase_shift_every"),
        "chapters_committed": written, "window": [start, n],
        "same_place_longest": longest, "place_returns": returns, "new_places": len(new_places),
        "milestones_done": len(ms_done), "milestones_due": len(due),
        "milestones_due_on_time": sum(m["status"] == "on_time" for m in due),
        "phase_shift_fired": fired, "phase_shift_followed": sum(followed),
        "stalled_count": len(stalled), "stalled_chapters": stalled,
        "usd_total": report["cost"]["total_usd"],
        "usd_per_chapter": round(sum(per) / len(per), 4) if per else None,
        "rewrites": report["rewrites"],
    }


if __name__ == "__main__":
    first, last = int(sys.argv[1]), int(sys.argv[2])
    for d in sys.argv[3:]:
        print(json.dumps(metrics(Path(d), first, last), ensure_ascii=False))
