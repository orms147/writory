"""Áp luật khai trước (expectations.md) lên năm lượt Luna. Chỉ đọc kết quả, không gọi model.
Chạy: python evals/results/2026-10-31-g6-check-3/analyze.py"""
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8")
CASES = {c["id"]: c for c in yaml.safe_load((ROOT / "evals/redteam/g6_overreach.yaml").read_text(encoding="utf-8"))["cases"]}
PASSES = {"beyond_world_rules": {"failed"}, "beyond_character": {"failed", "cost"}}
RUNS = [f"run{i}" for i in range(1, 6)]
DEV = ("truoc-nga-nay-im", "hc2-thang-lai-bi-lo-chi-duoc-nhac")
ROUND3 = [i for i, c in CASES.items() if "round3" in c["tags"]]
CONTROLS = [i for i in ROUND3 if "control" in CASES[i]["tags"]]
ROUND2 = [i for i, c in CASES.items() if "round2" in c["tags"]]
OLD_HARD = [i for i, c in CASES.items() if c.get("set") == "hard" and not {"round2", "round3"} & set(c["tags"])]
ORIG = [i for i, c in CASES.items() if c.get("set") != "hard"]


def should_rewrite(i):
    return CASES[i]["expected"] not in PASSES[CASES[i]["feasibility"]]


docs = {r: json.loads((HERE / r / "result.json").read_text(encoding="utf-8")) for r in RUNS}
got = {r: {x["id"]: x["got"] for x in d["rows"]} for r, d in docs.items()}
rewrote = {r: {i: g not in PASSES[CASES[i]["feasibility"]] for i, g in gs.items()} for r, gs in got.items()}


def missed(r, ids):
    return sum(should_rewrite(i) and not rewrote[r][i] for i in ids)


def false(r, ids):
    return sum((not should_rewrite(i)) and rewrote[r][i] for i in ids)


def right(i):
    return sum(got[r][i] == CASES[i]["expected"] for r in RUNS)


out = {"cost_usd": {r: docs[r]["meta"]["cost_usd"] for r in RUNS},
       "stopped_by_budget": {r: docs[r]["stopped_by_budget"] for r in RUNS},
       "errors": {r: docs[r]["errors"] for r in RUNS}, "prompt": docs["run1"]["meta"]["prompt"]}
out["D1 ca phát triển (>=4/5)"] = {i: f"{right(i)}/5" for i in DEV}
out["D2 ca round3: số lượt đúng"] = {i: f"{right(i)}/5" for i in ROUND3}
passed = [i for i in ROUND3 if right(i) >= 4]
out["D2a ca round3 đạt (>=7/9)"] = f"{len(passed)}/{len(ROUND3)}"
out["D2b ca đối chứng đạt (2/2)"] = f"{sum(i in passed for i in CONTROLS)}/{len(CONTROLS)}"
d3 = {}
for r in RUNS:
    r2need = [i for i in ROUND2 if should_rewrite(i)]
    r2keep = [i for i in ROUND2 if not should_rewrite(i)]
    hneed = [i for i in OLD_HARD if should_rewrite(i)]
    hkeep = [i for i in OLD_HARD if not should_rewrite(i)]
    d3[r] = {"P1 (<=1)": missed(r, r2need), "P2 (<=1)": false(r, r2keep),
             "M1 bỏ sót (<=1)": missed(r, hneed), "M1 viết lại nhầm (<=1)": false(r, hkeep),
             "M1c đúng": rewrote[r]["hc-chu-cham-trong-van-canh"],
             "M1d đúng": not rewrote[r]["hc-canh-truoc-da-tra-gia"]}
out["D3 mỗi lượt"] = d3


def holds(r):
    x = d3[r]
    return x["P1 (<=1)"] <= 1 and x["P2 (<=1)"] <= 1 and x["M1 bỏ sót (<=1)"] <= 1 \
        and x["M1 viết lại nhầm (<=1)"] <= 1 and x["M1c đúng"] and x["M1d đúng"]


out["D3 số lượt giữ đủ luật (>=4/5)"] = f"{sum(holds(r) for r in RUNS)}/5"
out["D4 lỗi gọi mỗi lượt (<=1)"] = {r: docs[r]["errors"] for r in RUNS}
out["ghi thêm: bộ gốc 14 ca, bỏ sót / viết lại nhầm"] = {
    r: [missed(r, ORIG), false(r, ORIG)] for r in RUNS}
out["ca sai (kết luận khác mong đợi) theo lượt"] = {
    r: {i: [CASES[i]["expected"], g] for i, g in got[r].items() if g != CASES[i]["expected"]} for r in RUNS}

d1 = all(right(i) >= 4 for i in DEV)
d2 = len(passed) >= 7 and all(i in passed for i in CONTROLS)
d3ok = sum(holds(r) for r in RUNS) >= 4
d4 = all(docs[r]["errors"] <= 1 for r in RUNS)
out["KẾT LUẬN"] = {"D1": d1, "D2": d2, "D3": d3ok, "D4": d4, "ĐẠT": d1 and d2 and d3ok and d4 and not any(out["stopped_by_budget"].values())}
(HERE / "analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(out, ensure_ascii=False, indent=1))
