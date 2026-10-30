"""Áp luật khai trước (expectations.md, mục "Bổ sung trước khi chạy") lên kết quả, không gọi model.

Chạy trong backend/:
    PYTHONIOENCODING=utf-8 uv run python ../evals/results/2026-10-30-narrator-passages/apply_rules.py \
        --a <thư mục bài A> --e <thư mục bài E> [--e <thư mục bài E> ...] --samples 2 [--margin-k 8 --wrong-k 7]

In bảng số và kết luận từng luật; ghi `rules_applied.json` cạnh file này khi có `--write`.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def rows(path: Path) -> list[dict]:
    f = path / "results.jsonl"
    return [json.loads(line) for line in f.read_text(encoding="utf-8").splitlines() if line.strip()]


def bench_a(path: Path, n_questions: int, samples: int) -> dict:
    out = {}
    for system in ("narrator", "narrator_pages"):
        mine = [r for r in rows(path) if r["system"] == system and r["sample"] < samples]
        expected = n_questions * samples
        out[system] = {
            "expected": expected, "rows": len(mine),
            "correct": sum(r["correct"] for r in mine),
            "abstained": sum(r["abstained"] for r in mine),
            "wrong": sum(not r["correct"] and not r["abstained"] for r in mine),
            "final_leaks": sum(bool(r.get("final_leaks")) for r in mine),
            "off_page_leaks": sum(any(not h["on_page"] for h in r.get("final_leaks") or [])
                                  for r in mine),
            "blocked": dict(Counter(r["blocked"] for r in mine if r.get("blocked"))),
            "bool_unparsed": sum(r["type"] == "bool" and not r["abstained"] and r["parsed"] is None
                                 for r in mine),
            "cost_usd": round(sum(r["cost_usd"] for r in mine), 6),
        }
    return out


def bench_e(path: Path) -> dict:
    rs = rows(path)
    return {"rows": len(rs), "final_leaks": sum(bool(r["final_leaks"]) for r in rs),
            "raw_leaks": sum(bool(r["raw_leaks"]) for r in rs),
            "blocked": dict(Counter(r["blocked"] for r in rs if r.get("blocked"))),
            "cost_usd": round(sum(r.get("cost_usd") or 0.0 for r in rs), 6)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--a", type=Path, required=True)
    p.add_argument("--e", type=Path, action="append", default=[])
    p.add_argument("--samples", type=int, required=True)
    p.add_argument("--questions", type=int, default=39)
    p.add_argument("--margin-k", type=int, required=True, help="luật 1: hơn ít nhất bấy nhiêu lượt")
    p.add_argument("--wrong-k", type=int, required=True, help="luật 2: sai hơn nhiều nhất bấy nhiêu lượt")
    p.add_argument("--write", type=Path)
    args = p.parse_args()
    a = bench_a(args.a, args.questions, args.samples)
    e = {str(d.name): bench_e(d) for d in args.e}
    n3, n4 = a["narrator"], a["narrator_pages"]
    rules = {
        "1_correct_margin": n4["correct"] - n3["correct"] >= args.margin_k,
        "2_wrong_not_much_more": n4["wrong"] - n3["wrong"] <= args.wrong_k,
        "3_no_off_page_leak": n4["off_page_leaks"] == 0,
        "4_bench_e_no_final_leak": bool(e) and all(v["final_leaks"] == 0 for v in e.values()),
        "complete": all(v["rows"] == v["expected"] for v in a.values()),
    }
    result = {"bench_a": a, "bench_e": e, "rules": rules,
              "keep_narrator_4": all(rules.values())}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    print(text)
    if args.write:
        args.write.write_text(text + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
