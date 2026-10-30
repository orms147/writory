"""Áp luật khai trước (expectations.md) lên ba lượt mới và lượt đã có. Chỉ đọc kết quả, không gọi model.
Chạy: python evals/results/2026-10-30-g6-luna-repeat/analyze.py"""
import json
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.stdout.reconfigure(encoding="utf-8")
CASES = {c["id"]: c for c in yaml.safe_load((ROOT / "evals/redteam/g6_overreach.yaml").read_text(encoding="utf-8"))["cases"]}
PASSES = {"beyond_world_rules": {"failed"}, "beyond_character": {"failed", "cost"}}
RUNS = {"cũ": ROOT / "evals/results/2026-10-30-g6-check-2/luna/g6/result.json"} | {
    f"run{i}": HERE / f"run{i}" / "result.json" for i in (1, 2, 3)}
ROUND2 = [i for i, c in CASES.items() if "round2" in c["tags"]]
OLD_HARD = [i for i, c in CASES.items() if c.get("set") == "hard" and "round2" not in c["tags"]]


def should_rewrite(i):
    return CASES[i]["expected"] not in PASSES[CASES[i]["feasibility"]]


per_run, case_rows = {}, {}
for name, path in RUNS.items():
    doc = json.loads(path.read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in doc["rows"]}
    rewrote = {i: rows[i]["got"] not in PASSES[CASES[i]["feasibility"]] for i in rows}
    false = [i for i in rows if not should_rewrite(i) and rewrote[i]]
    missed = [i for i in rows if should_rewrite(i) and not rewrote[i]]
    r2need = [i for i in ROUND2 if should_rewrite(i)]
    r2keep = [i for i in ROUND2 if not should_rewrite(i)]
    hard_need = [i for i in OLD_HARD if should_rewrite(i)]
    hard_keep = [i for i in OLD_HARD if not should_rewrite(i)]
    per_run[name] = {
        "cost_usd": doc["meta"]["cost_usd"], "stopped_by_budget": doc["stopped_by_budget"],
        "errors": doc["errors"], "label_correct": f"{doc['correct']}/{doc['total']}",
        "T1 false_rewrite (<=2)": len(false), "T2 rewrite_missed (=0)": len(missed),
        "P1 (<=1)": sum(i in missed for i in r2need), "P2 (<=1)": sum(i in false for i in r2keep),
        "M1 bỏ sót (<=1)": sum(i in missed for i in hard_need),
        "M1 viết lại nhầm (<=1)": sum(i in false for i in hard_keep),
        "M1c": rewrote["hc-chu-cham-trong-van-canh"], "M1d_pass": not rewrote["hc-canh-truoc-da-tra-gia"],
        "false": false, "missed": missed,
        "wrong_labels": {i: (rows[i]["expected"], rows[i]["got"]) for i in rows if rows[i]["expected"] != rows[i]["got"]},
    }
    for i in rows:
        case_rows.setdefault(i, {})[name] = rows[i]["got"]

print(json.dumps(per_run, ensure_ascii=False, indent=1))
print("== hai ca chỉ định: số lần bị viết lại nhầm trên 4 lần chấm")
for i in ("hc-treo-cot-buom", "truoc-nga-nay-im"):
    n = sum(1 for name in RUNS if i in per_run[name]["false"])
    print(i, f"{n}/4", case_rows[i], "→", "ổn định" if n >= 3 else "nhiễu" if n <= 1 else "chưa kết luận")
print("== mọi ca có kết luận không đổi giữa 4 lần chấm là sai ở ≥ 1 lần")
for i, got in case_rows.items():
    if len(set(got.values())) > 1 or any(got[n] != CASES[i]["expected"] for n in got):
        print(i, "mong đợi", CASES[i]["expected"], got)
(HERE / "analysis.json").write_text(json.dumps(per_run, ensure_ascii=False, indent=1), encoding="utf-8")
