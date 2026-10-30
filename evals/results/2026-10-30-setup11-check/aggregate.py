"""Gộp số đo lại khởi tạo `setup-11` (D-135) theo `expectations.md`. Không gọi model: chỉ đọc
meta.json, report.json, calls.jsonl của các thư mục kết quả `bench_run --setup-only`.

Chạy từ `backend/` sau năm lượt đo:
    uv run python ../evals/results/2026-10-30-setup11-check/aggregate.py ../evals/results/*-run-setup11-*

Ghi `compare.json` cạnh file này (chỉ số đếm, không id, không chữ của truyện) và in bảng tóm tắt
cùng các luật quyết định đã khai trước ở `expectations.md`.
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "2026-10-29-setup10-check" / "compare.json"
sys.stdout.reconfigure(encoding="utf-8")

# Luật khai trước (expectations.md, mục "Luật quyết định").
MIN_PLANS_LINKED = 4  # trên 5 kế hoạch, số kế hoạch có ít nhất một mạch khai answered_by
MAX_RUNS_ANSWER_REPAIR = 1  # số lượt có lỗi loại answered_by ở lượt sửa D-54
COST_WATCH_FACTOR = 1.5  # chi phí khởi tạo trung bình quá 1.5 lần setup-10 thì ghi để xem lại


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_row(out: Path) -> dict:
    meta, report = _json(out / "meta.json"), _json(out / "report.json")
    calls = [json.loads(line) for line in (out / "calls.jsonl").read_text(encoding="utf-8")
             .splitlines() if line.strip()]
    build = [c for c in calls if c.get("setup_step") == "build"]
    return {
        "label": meta["label"], "seed": meta["seed"], "commit": meta["git"]["commit"],
        "dirty": meta["git"]["dirty"], "dry_run": meta["dry_run"],
        "setup_prompt": meta["prompt_versions"]["setup"], "status": report["status"],
        "setup_done": report["chapters_planned"] is not None,
        "thread_answers": report["thread_answers"],
        "setup_repairs": report["setup_repairs"],
        "player_retries_setup": report["player_retries_used"]["setup"],
        "setup_cost_usd": report["cost"]["by_role"].get("setup", 0.0),
        "build_prompt_tokens": [c.get("prompt_tokens") for c in build],
        "build_completion_tokens": [c.get("completion_tokens") for c in build],
        "appearance_variety": report["appearance_variety"],
    }


def _mean(xs: list[float]) -> float | None:
    return round(sum(xs) / len(xs), 6) if xs else None


def totals(rows: list[dict]) -> dict:
    answers = [r["thread_answers"] for r in rows if r["thread_answers"]]
    variety = [r["appearance_variety"] for r in rows if r["appearance_variety"]]

    def total(key: str, group: list[dict]) -> int:
        return sum(a[key] or 0 for a in group)

    return {
        "runs": len(rows),
        "setup_done": sum(r["setup_done"] for r in rows),
        "threads": total("threads", answers), "linked": total("linked", answers),
        "plans_with_a_link": sum(1 for a in answers if a["linked"]),
        "shifted": total("shifted", answers), "shifted_end": total("shifted_end", answers),
        "plans_shifted": sum(1 for a in answers if a["shifted"]),
        "mismatches_after": total("mismatches", answers),
        "runs_with_repair": sum(1 for r in rows if r["setup_repairs"]["used"]),
        "runs_with_answered_by_repair": sum(1 for r in rows
                                            if r["setup_repairs"]["kinds"].get("answered_by")),
        "repair_kinds": _merge([r["setup_repairs"]["kinds"] for r in rows]),
        "setup_cost_usd_mean": _mean([r["setup_cost_usd"] for r in rows]),
        "first_build_prompt_tokens_mean": _mean([r["build_prompt_tokens"][0] for r in rows
                                                 if r["build_prompt_tokens"]]),
        "first_build_completion_tokens_mean": _mean([r["build_completion_tokens"][0] for r in rows
                                                     if r["build_completion_tokens"]]),
        "characters": total("characters", variety),
        "starts_with_trong": total("starts_with_trong", variety),
        "opening_repeats": total("opening_repeats", variety),
        "hair_repeats": total("hair_repeats", variety),
    }


def _merge(counts: list[dict[str, int]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in counts:
        for k, v in c.items():
            out[k] = out.get(k, 0) + v
    return dict(sorted(out.items()))


def baseline() -> dict:
    """Năm lượt setup-10 của `2026-10-29-setup10-check/compare.json`, cùng cách gộp."""
    runs = list(_json(BASELINE)["setup-10"].values())
    variety = [r["appearance_variety"] for r in runs]
    return {
        "runs": len(runs),
        "runs_with_repair": sum(1 for r in runs if r["setup_repairs"]["used"]),
        "setup_cost_usd_mean": _mean([r["setup_cost_usd"] for r in runs]),
        "first_build_prompt_tokens_mean": _mean([r["build_prompt_tokens"][0] for r in runs]),
        "first_build_completion_tokens_mean": _mean([r["build_completion_tokens"][0]
                                                     for r in runs]),
        "characters": sum(v["characters"] for v in variety),
        "starts_with_trong": sum(v["starts_with_trong"] for v in variety),
        "opening_repeats": sum(v["opening_repeats"] for v in variety),
        "hair_repeats": sum(v["hair_repeats"] for v in variety),
    }


def verdict(rows: list[dict], t: dict, base: dict) -> list[str]:
    lines = []
    bad = [r["label"] for r in rows
           if r["dry_run"] or r["dirty"] or r["setup_prompt"] != "setup-11"]
    lines.append(f"Hợp lệ (thật, commit sạch, setup-11): {'có' if not bad else f'KHÔNG: {bad}'}")
    lines.append(f"C1 còn lệch sau khi dời = 0: {'đạt' if t['mismatches_after'] == 0 else 'TRƯỢT'}"
                 f" ({t['mismatches_after']})")
    lines.append(f"C2 khởi tạo xong {t['setup_done']}/{t['runs']}, lượt có lỗi answered_by "
                 f"{t['runs_with_answered_by_repair']} (tối đa {MAX_RUNS_ANSWER_REPAIR}): "
                 f"{'đạt' if t['setup_done'] == t['runs'] and t['runs_with_answered_by_repair'] <= MAX_RUNS_ANSWER_REPAIR else 'TRƯỢT'}")
    lines.append(f"C3 kế hoạch có liên kết {t['plans_with_a_link']}/{t['runs']} (cần ≥ "
                 f"{MIN_PLANS_LINKED}): {'đạt' if t['plans_with_a_link'] >= MIN_PLANS_LINKED else 'TRƯỢT'}")
    cost, ref = t["setup_cost_usd_mean"], base["setup_cost_usd_mean"]
    if cost is not None and ref:
        flag = "xem lại" if cost > COST_WATCH_FACTOR * ref else "bình thường"
        lines.append(f"Theo dõi chi phí: {cost:.5f} so với {ref:.5f} USD/lượt ({flag})")
    lines.append("C4 (đọc tay độ đúng của liên kết) và số liên kết sót: điền vào notes.md.")
    return lines


def main() -> None:
    dirs = [Path(a) for a in sys.argv[1:]]
    if not dirs:
        sys.exit("cần ít nhất một thư mục kết quả")
    rows = [run_row(d) for d in dirs]
    t, base = totals(rows), baseline()
    data = {"setup-11": {r["label"]: r for r in rows}, "setup-11_totals": t,
            "setup-10_baseline": base | {"source": "2026-10-29-setup10-check/compare.json"}}
    (HERE / "compare.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8", newline="\n")
    for k, v in t.items():
        print(f"{k}: {v}" + (f"   (setup-10: {base[k]})" if k in base else ""))
    print()
    print("\n".join(verdict(rows, t, base)))


if __name__ == "__main__":
    main()
