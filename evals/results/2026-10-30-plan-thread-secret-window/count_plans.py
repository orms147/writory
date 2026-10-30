"""Đếm trên mọi kế hoạch đã lưu trong `evals/results`: mạch phải gỡ có hạn gỡ bắt đầu TRƯỚC khoảng lộ
của bí mật cùng nội dung (không gọi model, chỉ đọc `truth_dump.json`).

Chạy từ `backend/`:  uv run python ../evals/results/2026-10-30-plan-thread-secret-window/count_plans.py

Kế hoạch không ghi mạch nào gắn với bí mật nào, nên "cùng nội dung" là heuristic có hai cách (một cặp
được coi là gắn nếu cách nào cũng trúng thì ghi riêng):
  H1  mô tả mạch chứa một cụm trong `leak_terms` của bí mật (cụm dài từ hai từ, so bỏ dấu, trọn từ);
  H2  mô tả mạch và chữ Fact của bí mật cùng chứa một tên riêng dài từ hai từ viết hoa liền nhau.
Lỗi một cặp: mạch bắt đầu gỡ trước chương mở của bí mật (`resolve_from < reveal_from`). Nặng: hạn gỡ
cuối còn trước chương mở (`resolve_to < reveal_from`), tức mạch phải gỡ xong khi bí mật chưa được lộ.
Mỗi kế hoạch tính một lần (băm JSON); lượt chạy dùng chung khởi tạo (`--setup-from`) không bị đếm lại.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

from writory.safety.leak import strip_diacritics

RESULTS = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
CAP_RUN = re.compile(r"(?:[A-ZÀ-Ỹ][^\W\d_]*)(?:\s+[A-ZÀ-Ỹ][^\W\d_]*)+")


def norm(text: str) -> str:
    return " ".join(strip_diacritics(text).lower().split())


def contains(whole: str, part: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(norm(part)) + r"(?!\w)", norm(whole)) is not None


def names(text: str) -> set[str]:
    return {norm(m.group()) for m in CAP_RUN.finditer(text)}


def main() -> None:
    plans: dict[str, dict] = {}
    for path in sorted(RESULTS.glob("*/truth_dump.json")):
        try:
            dump = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        plan = dump.get("plan")
        if not plan or not plan.get("must_resolve_threads"):
            continue
        key = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()[:12]
        if key in plans:
            plans[key]["runs"].append(path.parent.name)
            continue
        pkg0 = dump["packages"].get("0") or {}
        nodes = {n["id"]: n["props"] for n in pkg0.get("nodes", [])}
        plans[key] = {"plan": plan, "nodes": nodes, "runs": [path.parent.name]}

    n_with_windows = n_linked = n_bad = n_severe = 0
    examples = []
    rows = []
    for key, rec in plans.items():
        plan, nodes = rec["plan"], rec["nodes"]
        threads = [(t["thread_id"], t.get("resolve_from_chapter"), t.get("resolve_to_chapter"),
                    nodes.get(t["thread_id"], {}).get("description", "")) for t in plan["must_resolve_threads"] if isinstance(t, dict)]
        threads = [t for t in threads if t[1] is not None and t[3]]
        if not threads or not plan.get("secrets"):
            continue
        n_with_windows += 1
        linked, bad, severe = [], [], []
        for s in plan["secrets"]:
            text = nodes.get(s["fact_id"], {}).get("text", "")
            terms = [p for g in s.get("leak_terms", []) for p in g if len(p.split()) >= 2]
            for tid, tf, tt, desc in threads:
                h1 = any(contains(desc, p) for p in terms)
                h2 = bool(names(desc) & names(text)) if text else False
                if not (h1 or h2):
                    continue
                pair = {"thread": tid, "window": [tf, tt], "secret": s["fact_id"],
                        "reveal": [s["reveal_from_chapter"], s["reveal_to_chapter"]],
                        "h1": h1, "h2": h2, "desc": desc, "fact": text}
                linked.append(pair)
                if tf < s["reveal_from_chapter"]:
                    bad.append(pair)
                    if tt < s["reveal_from_chapter"]:
                        severe.append(pair)
        n_linked += bool(linked)
        n_bad += bool(bad)
        n_severe += bool(severe)
        rows.append((key, rec["runs"][0], len(rec["runs"]), len(plan["secrets"]), len(threads),
                     len(linked), len(bad), len(severe)))
        examples += [(key, rec["runs"][0], p) for p in bad]

    print(f"kế hoạch khác nhau có mạch kèm khoảng gỡ và bí mật: {n_with_windows} (trên {len(plans)} kế hoạch có mạch phải gỡ)")
    print(f"  có ít nhất một cặp mạch-bí mật gắn nhau (H1 hoặc H2): {n_linked}")
    print(f"  có ít nhất một cặp mạch bắt đầu gỡ trước khoảng lộ của bí mật: {n_bad}")
    print(f"  có ít nhất một cặp mạch phải gỡ XONG trước khoảng lộ của bí mật: {n_severe}")
    print("\nkey | lượt đầu | số lượt dùng | bí mật | mạch | cặp gắn | cặp lệch | cặp nặng")
    for r in rows:
        print(" | ".join(str(x) for x in r))
    print("\ncác cặp lệch (đọc tay để kiểm độ chính xác của heuristic):")
    for key, run, p in examples:
        print(f"[{key} {run}] mạch {p['thread']} gỡ {p['window']} (H1={p['h1']}, H2={p['h2']}): {p['desc']}")
        print(f"    bí mật {p['secret']} lộ {p['reveal']}: {p['fact']}")


main()
