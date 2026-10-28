"""Phân tích nhiễu giám khảo: 3 lần chấm cùng hai truyện bằng mỗi giám khảo.
python noise_analyze.py <repo_root> <ngày>"""

import json
import math
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
repo = Path(sys.argv[1])
day = sys.argv[2]
R = repo / "evals" / "results"
DIRS = {
    "sonnet": [R / "2026-10-22-model-bakeoff-1", R / f"{day}-judge-noise-sonnet-2", R / f"{day}-judge-noise-sonnet-3"],
    "muse": [R / "2026-10-28-model-bakeoff-muse-1", R / f"{day}-judge-noise-muse-2", R / f"{day}-judge-noise-muse-3"],
}
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447}


def rows(d):
    return [json.loads(x) for x in (d / "results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def load(d):
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    label_model = {lb: v["model"] for lb, v in key.items()}
    solo, compare, cost, quotes = {}, {}, 0.0, [0, 0]
    for r in rows(d):
        if r["status"] != "ok":
            continue
        cost += r["cost_usd"]
        qf = r.get("quote_found") or {}
        vals = qf["evidence"] if "evidence" in qf else list(qf.values())
        quotes[0] += sum(v is not None for v in vals)
        quotes[1] += sum(v is False for v in vals)
        if r["kind"] == "solo":
            solo[label_model[r["labels"][0]]] = {c: v["score"] for c, v in r["result"].items()}
        elif r["kind"] == "compare":
            compare[tuple(label_model[x] for x in r["labels"])] = [label_model[x] for x in r["result"]["ranking"]]
    return solo, compare, cost, quotes


summary = {}
for judge, dirs in DIRS.items():
    runs = [load(d) for d in dirs]
    models = sorted(runs[0][0])
    crits = list(runs[0][0][models[0]])
    print(f"\n######## {judge}: {len(runs)} lần chấm; chi phí {[round(r[2], 4) for r in runs]}; "
          f"trích sai/kiểm {[tuple(r[3][::-1]) for r in runs]}")
    means = {m: [st.mean(r[0][m].values()) for r in runs] for m in models}
    sds = {}
    for m in models:
        v = means[m]
        sds[m] = st.stdev(v)
        print(f"  {m}: điểm TB solo mỗi lần {[round(x, 3) for x in v]}  TB {st.mean(v):.3f}  độ lệch chuẩn {sds[m]:.3f}  biên độ {max(v) - min(v):.3f}")
    pooled = math.sqrt(st.mean([s * s for s in sds.values()]))
    df = len(models) * (len(runs) - 1)
    print(f"  độ lệch chuẩn gộp (σ) {pooled:.3f}, bậc tự do {df}")
    # từng tiêu chí
    print("  tiêu chí: giá trị 3 lần (theo model) | độ lệch chuẩn TB qua các model | số lần khác nhau")
    crit_sd = {}
    for c in crits:
        per = {m: [r[0][m][c] for r in runs] for m in models}
        sd = st.mean([st.pstdev(v) for v in per.values()])
        crit_sd[c] = sd
        diff = sum(len(set(v)) > 1 for v in per.values())
        print(f"    {c:24s} {per}  sd {sd:.3f}  model dao động {diff}/{len(models)}")
    worst = sorted(crit_sd.items(), key=lambda kv: -kv[1])
    print("  dao động nhiều nhất:", [(c, round(s, 3)) for c, s in worst[:3]])
    # so sánh: thứ tự trình bày
    print("  so sánh (xếp hạng, nhãn là model; trình bày theo thứ tự trong khoá):")
    first_last = []
    for i, r in enumerate(runs, 1):
        for order, rank in sorted(r[1].items()):
            presented_last = order[-1]
            first_last.append(rank[0] == presented_last)
            print(f"    lần {i} trình bày {[o.split('/')[0] for o in order]} -> nhất {rank[0].split('/')[0]}"
                  f"{'  (truyện trình bày SAU)' if rank[0] == presented_last else '  (truyện trình bày TRƯỚC)'}")
    print(f"  nhất = truyện trình bày sau: {sum(first_last)}/{len(first_last)}")
    flips = 0
    for i, r in enumerate(runs, 1):
        ranks = list(r[1].values())
        flips += ranks[0][0] != ranks[1][0]
    print(f"  số lần (trong {len(runs)}) hai thứ tự cho hai người nhất khác nhau: {flips}")
    summary[judge] = {"pooled": pooled, "df": df, "sd": sds, "means": means}

print("\n######## ngưỡng chênh tối thiểu (95%, hai phía) giữa hai hệ A/B, chỉ tính nhiễu của giám khảo")
print("  chênh = t(0,975; df) × σ × √(2/k): k = số lần chấm trung bình mỗi truyện; mỗi hệ một truyện")
for judge, s in summary.items():
    t = T975[s["df"]]
    print(f"  {judge}: σ {s['pooled']:.3f}, df {s['df']}, t {t}")
    for k in (1, 2, 3):
        print(f"    k={k}: {t * s['pooled'] * math.sqrt(2 / k):.2f} điểm (thang 1-5)")
    print(f"    sàn hạt thang: 1 điểm một tiêu chí = {1/7:.3f} điểm TB 7 tiêu chí")
