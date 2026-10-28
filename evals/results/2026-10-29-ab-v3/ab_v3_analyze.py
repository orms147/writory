"""Cũ so với v3 theo luật quyết định đã khai ở docs/eval.md (a478343).
python ab_v3_analyze.py <repo_root>"""

import json
import statistics as st
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
repo = Path(sys.argv[1])
R = repo / "evals" / "results"
NEW = "2026-10-29"
WORLDS = ["tu-tien", "ky-ao", "trinh-tham"]
JUDGES = {"sonnet": 0.50, "muse": 0.71}  # ngưỡng tổng đã khai (T_J)
CRITS = None


def rows(d):
    return [json.loads(x) for x in (d / "results.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]


def load(d):
    key = json.loads((d / "key.json").read_text(encoding="utf-8"))
    arm = {lb: ("v3" if "-v3-" in v["run"] else "cu") for lb, v in key.items()}
    solo, compare, cost = {}, [], 0.0
    for r in rows(d):
        cost += r.get("cost_usd") or 0.0
        if r["status"] != "ok":
            continue
        if r["kind"] == "solo":
            solo[arm[r["labels"][0]]] = {c: v["score"] for c, v in r["result"].items()}
        elif r["kind"] == "compare":
            compare.append((tuple(arm[x] for x in r["labels"]), arm[r["result"]["ranking"][0]]))
    return solo, compare, cost


result = {}
for judge, T in JUDGES.items():
    print(f"\n######## {judge}  (ngưỡng tổng đã khai T = {T})")
    diffs, world_crit, total_cost = [], {}, 0.0
    for w in WORLDS:
        pair_means = []
        for i in (1, 2):
            d = R / f"{NEW}-ab-{w}-pair{i}-{judge}"
            if not (d / "results.jsonl").exists():
                print(f"  {w} cặp {i}: chưa có kết quả")
                continue
            solo, compare, cost = load(d)
            total_cost += cost
            if set(solo) != {"cu", "v3"}:
                print(f"  {w} cặp {i}: thiếu solo {sorted(solo)}")
                continue
            m_cu, m_v3 = st.mean(solo["cu"].values()), st.mean(solo["v3"].values())
            diffs.append(m_v3 - m_cu)
            pair_means.append(solo)
            cmp = "; ".join(f"{'/'.join(o)} -> nhất {win}" for o, win in compare)
            print(f"  {w} cặp {i}: cũ {m_cu:.3f}  v3 {m_v3:.3f}  chênh {m_v3 - m_cu:+.3f}   chi phí {cost:.4f}" + (f"   so sánh: {cmp}" if cmp else ""))
        if pair_means:
            for c in pair_means[0]["cu"]:
                world_crit.setdefault(c, {})[w] = st.mean(p["v3"][c] - p["cu"][c] for p in pair_means)
    if not diffs:
        continue
    mean_diff = st.mean(diffs)
    print(f"  chênh_{judge} = trung bình {len(diffs)} cặp của (v3 − cũ) = {mean_diff:+.3f}   (ngưỡng {T})")
    print("  chênh trung bình của thế giới theo tiêu chí (v3 − cũ):")
    drop_fail = []
    for c, per in world_crit.items():
        bad = [w for w, v in per.items() if v < -1.0]
        print(f"    {c:24s} {{{', '.join(f'{w}: {v:+.1f}' for w, v in per.items())}}}  tụt quá 1 điểm ở {len(bad)} thế giới")
        if len(bad) >= 2:
            drop_fail.append(c)
    print(f"  tiêu chí tụt quá 1 điểm ở ≥ 2 thế giới: {drop_fail or 'không'}")
    result[judge] = (mean_diff, T, drop_fail, total_cost)

print("\n######## kết luận theo luật đã khai")
if len(result) == 2:
    ds, dm = result["sonnet"][0], result["muse"][0]
    ok_drop = not result["sonnet"][2] and not result["muse"][2]
    if ds >= 0.50 and dm >= 0.71 and ok_drop:
        verdict = "v3 THẮNG"
    elif ds <= -0.50 and dm <= -0.71:
        verdict = "v3 THUA"
    else:
        verdict = "CHƯA PHÂN BIỆT ĐƯỢC"
    print(f"  chênh_Sonnet {ds:+.3f} (cần ≥ +0,50), chênh_Muse {dm:+.3f} (cần ≥ +0,71), không tiêu chí tụt quá 1 điểm ở ≥ 2 thế giới: {ok_drop}")
    print(f"  => {verdict}")
print("chi phí giám khảo:", {j: round(v[3], 4) for j, v in result.items()})
