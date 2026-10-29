"""Tách chênh chi phí giữa hai lượt cùng thế giới, trong dải chương chung, theo vai:
  Δ = (n_sau − n_trước) × c_trước            ← nhiều/ít lời gọi hơn (viết lại, thử lại)
    + n_sau × (c_sau − c_trước)              ← mỗi lời gọi đắt/rẻ hơn (đề dài hơn, token vào khác)
n = số lời gọi ok trong dải, c = chi phí trung bình mỗi lời gọi ok. Chỉ đọc `calls.jsonl`.
Dùng: python cost_decomp.py <trước> <sau> <chương cuối của dải>"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
R = Path(__file__).resolve().parents[1]


def stats(name: str, last: int):
    n, usd, tok = defaultdict(int), defaultdict(float), defaultdict(int)
    for line in (R / name / "calls.jsonl").read_text(encoding="utf-8").splitlines():
        c = json.loads(line)
        if c["status"] == "ok" and 1 <= c["chapter"] <= last:
            n[c["role"]] += 1
            usd[c["role"]] += c.get("cost_usd") or 0.0
            tok[c["role"]] += c.get("prompt_tokens") or 0
    return n, usd, tok


before, after, last = sys.argv[1], sys.argv[2], int(sys.argv[3])
nb, ub, tb = stats(before, last)
na, ua, ta = stats(after, last)
total = {"calls": 0.0, "price": 0.0}
print(f"dải ch1–{last}: {before}  →  {after}")
for role in sorted(set(nb) | set(na)):
    cb = ub[role] / nb[role] if nb[role] else 0.0
    ca = ua[role] / na[role] if na[role] else 0.0
    by_calls = (na[role] - nb[role]) * cb
    by_price = na[role] * (ca - cb)
    total["calls"] += by_calls
    total["price"] += by_price
    tpb = tb[role] / nb[role] if nb[role] else 0
    tpa = ta[role] / na[role] if na[role] else 0
    print(f"  {role:9s} lời gọi {nb[role]:3d}→{na[role]:3d}  token vào/lời gọi {tpb:7.0f}→{tpa:7.0f}  "
          f"USD {ub[role]:.4f}→{ua[role]:.4f}  Δ={ua[role]-ub[role]:+.4f} (số lời gọi {by_calls:+.4f}, giá mỗi lời gọi {by_price:+.4f})")
dt = sum(ua.values()) - sum(ub.values())
print(f"  TỔNG Δ={dt:+.4f}: do số lời gọi {total['calls']:+.4f} ({100*total['calls']/dt:.0f}%), do giá mỗi lời gọi {total['price']:+.4f} ({100*total['price']/dt:.0f}%)")
