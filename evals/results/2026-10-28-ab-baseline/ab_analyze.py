"""Nhiễu giữa các lần VIẾT (cùng cấu hình, cùng thế giới), đo bằng hai giám khảo, mỗi truyện chấm 1 lần.
python ab_analyze.py <repo_root> <ngày>"""

import json
import math
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
repo, day = Path(sys.argv[1]), sys.argv[2]
R = repo / "evals" / "results"
WORLDS = ["tu-tien", "ky-ao", "trinh-tham"]
JUDGES = ["sonnet", "muse"]
SIGMA_JUDGE = {"sonnet": 0.082, "muse": 0.117}  # chấm lại cùng văn, 2026-10-28-judge-noise-sonnet-2/notes.md
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447}


def rows(d):
    return [json.loads(x) for x in (d / "results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def load(d):
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    run_of = {lb: v["run"].rsplit("/", 1)[-1].rsplit("-", 1)[-1] for lb, v in key.items()}  # "1" / "2"
    solo, compare, cost = {}, [], 0.0
    for r in rows(d):
        if r["status"] != "ok":
            continue
        cost += r["cost_usd"]
        if r["kind"] == "solo":
            solo[run_of[r["labels"][0]]] = {c: v["score"] for c, v in r["result"].items()}
        elif r["kind"] == "compare":
            compare.append((tuple(run_of[x] for x in r["labels"]), run_of[r["result"]["ranking"][0]]))
    return solo, compare, cost


per_judge = {}
for judge in JUDGES:
    print(f"\n######## {judge}")
    vars_, crit_diffs, firsts, total_cost = [], {}, [], 0.0
    for w in WORLDS:
        d = R / f"{day}-ab-{w}-cu-{judge}"
        if not (d / "results.jsonl").exists():
            print(f"  {w}: chưa có kết quả")
            continue
        solo, compare, cost = load(d)
        total_cost += cost
        if set(solo) != {"1", "2"}:
            print(f"  {w}: thiếu solo ({sorted(solo)})")
            continue
        m1, m2 = st.mean(solo["1"].values()), st.mean(solo["2"].values())
        diff = m1 - m2
        vars_.append(diff * diff / 2)
        for c in solo["1"]:
            crit_diffs.setdefault(c, []).append(solo["1"][c] - solo["2"][c])
        print(f"  {w}: điểm TB cu-1 {m1:.3f}  cu-2 {m2:.3f}  chênh {diff:+.3f}   chi phí giám khảo {cost:.4f}")
        for order, winner in compare:
            print(f"      so sánh trình bày {order} -> nhất cu-{winner}"
                  f" ({'trình bày TRƯỚC' if winner == order[0] else 'trình bày SAU'})")
            firsts.append(winner == order[0])
    if not vars_:
        continue
    sigma = math.sqrt(st.mean(vars_))
    df = len(vars_)
    print(f"  σ_tổng (viết + một lần chấm) = √(trung bình d²/2 qua {df} thế giới) = {sigma:.3f}, bậc tự do {df}")
    sj = SIGMA_JUDGE[judge]
    sw2 = sigma * sigma - sj * sj
    print(f"  σ_chấm (đo ở judge-noise) = {sj:.3f}; σ_viết² = σ_tổng² − σ_chấm² = {sw2:.4f}"
          f" -> σ_viết ≈ {math.sqrt(sw2) if sw2 > 0 else 0.0:.3f}{' (âm, chặn ở 0)' if sw2 <= 0 else ''}")
    t = T975.get(df)
    for name, factor in (("1 thế giới, mỗi hệ 1 truyện chấm 1 lần", math.sqrt(2)),
                         (f"TB {df} thế giới (mỗi hệ {df} truyện)", math.sqrt(2 / df))):
        print(f"  ngưỡng chênh 95%: {name}: t({df}) {t} × σ_tổng × {factor:.3f} = {t * sigma * factor:.2f} điểm")
    print("  chênh từng tiêu chí giữa cu-1 và cu-2 (theo thế giới):", {c: v for c, v in crit_diffs.items()})
    print("  số tiêu chí chênh ≠ 0 / tổng ô:", sum(x != 0 for v in crit_diffs.values() for x in v), "/",
          sum(len(v) for v in crit_diffs.values()))
    print(f"  so sánh: nhất là truyện trình bày TRƯỚC {sum(firsts)}/{len(firsts)} lượt (cùng cấu hình: kỳ vọng ~50%)")
    per_judge[judge] = (sigma, df, total_cost)
print("\nchi phí giám khảo:", {j: round(v[2], 4) for j, v in per_judge.items()})
