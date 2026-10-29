"""Số đo bằng code cho truyện mức Dài (đo nền, nhánh eval/long-baseline). Cùng định nghĩa cho mọi lần
chạy để so lần cũ (long-tu-tien-2) với lần mới.

  python long_metrics.py <thư mục chạy> [<thư mục chạy> ...]      (in JSON mỗi lần chạy, mỗi dòng một lần)

Đọc `truth_dump.json` (gói thay đổi từng chương, `plan_vs_result` ở `report.json`), `chapters/chNN.md`,
`calls.jsonl`. Không gọi model.

1. stalled_chapters: chương KHÔNG đổi trạng thái, tức không có tín hiệu nào trong:
   - mạch gỡ hoặc bí mật lộ đúng chương đó (`plan_vs_result` ở report.json);
   - đổi nơi: có cạnh LOCATED_AT mở ở chương đó tới một nơi khác với nơi cuối cùng đã biết của cùng nhân vật
     (nhân vật chưa có nơi nào thì tính là có nơi mới);
   - vật đổi chủ: có cạnh HOLDS mở ở chương đó;
   - người bị thương, chết, bị bắt, mất tích: câu của Fact mới ở chương đó khớp HARM (YẾU: regex trên Fact;
     đồ thị không có thuộc tính sống/chết, nên đây là chặn dưới).
   Mốc kế hoạch (`story_plan.milestones`) KHÔNG phải trạng thái ghi trong đồ thị, nên không vào tín hiệu.
   stalled_wide: như trên nhưng thêm có cạnh RELATES_TO / MEMBER_OF / FEELS mở ở chương đó (quan hệ hay cảm xúc
   đổi); chỉ để thấy tín hiệu nào đang gánh.
2. protagonist_no_location: số chương mà cuối chương không có cạnh LOCATED_AT nào còn hiệu lực của nhân vật
   chính (`valid_from <= N` và `valid_to` rỗng hoặc `> N`, graph-schema.md); protagonist_multi_location: số
   chương có từ hai cạnh trở lên.
3. procedural_per_chapter: số lần từ thủ tục mỗi chương (PROC: ghi, ghi lại, ghi nhận, ghi chép, sổ, bản ghi,
   biên bản, nghị sự, đối chiếu, xác nhận, điều khoản), theo cùng định nghĩa cho mọi thế giới; trung bình ba đoạn
   đầu / giữa / cuối truyện.
4. static_end_ratio, waiting_choice_sets, duplicate_openers: lấy nguyên từ `prose_metrics.py` của baseline A/B.
5. bigram_overlap_prev: độ giống (Jaccard trên tập cặp âm tiết liền nhau) giữa văn chương N và hai chương
   liền trước, trung bình; vòng lặp theo NGHĨA nên cao hơn ở chương lặp cảnh/hồ sơ dù không trùng nguyên
   văn (6-gram thì không bắt được, notes long-tu-tien-2). Proxy, không có nhãn tay để hiệu chuẩn.
   place_returns: số chương nhân vật chính về lại một nơi đã ở trong ba chương trước (đi rồi quay lại).
6. plan_no_milestone / plan_no_item: chương (trong cả kế hoạch, kể cả chưa viết) không có mốc nào đang mở /
   không có mốc, bí mật hay mạch nào đang mở (theo khoảng chương của `story_plan`).
7. input_tokens_by_role: token vào trung bình mỗi lời gọi (calls.jsonl, status ok), theo vai và ba đoạn truyện;
   usd_by_third: chi phí mỗi chương trung bình theo ba đoạn.
"""

import importlib.util
import itertools
import json
import re
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
PM = Path(__file__).resolve().parent.parent / "2026-10-28-ab-baseline" / "prose_metrics.py"
spec = importlib.util.spec_from_file_location("prose_metrics", PM)
prose_metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prose_metrics)

HARM = re.compile(r"\b(chết|tử vong|hy sinh|bị thương|trọng thương|bị bắt|bị giam|bị giết|mất tích|ngã xuống|"
                  r"bị phản|bị hại|tử trận)\b", re.IGNORECASE)
PROC = re.compile(r"\b(ghi lại|ghi nhận|ghi chép|ghi|bản ghi|sổ|biên bản|nghị sự|đối chiếu|xác nhận|điều khoản)\b",
                  re.IGNORECASE)
PROTAGONIST = "protagonist"


def bigrams(text: str) -> set[tuple[str, str]]:
    words = re.findall(r"[^\W\d_]+", text.lower())
    return set(itertools.pairwise(words))


def thirds(n: int) -> list[range]:
    a, b = round(n / 3), round(2 * n / 3)
    return [range(1, a + 1), range(a + 1, b + 1), range(b + 1, n + 1)]


def avg(xs):
    xs = list(xs)
    return round(st.mean(xs), 4) if xs else None


def metrics(run: Path) -> dict:
    truth = json.loads((run / "truth_dump.json").read_text(encoding="utf-8"))
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    packages = {int(k): v for k, v in truth["packages"].items()}
    n = max(packages)  # số chương đã ghi (gói 0 là khởi tạo)
    pvr = report["plan_vs_result"]
    resolved = {t["resolved_chapter"] for t in pvr["threads"] if t.get("resolved_chapter")}
    revealed = {s["revealed_chapter"] for s in pvr["secrets"] if s.get("revealed_chapter")}

    # nơi cuối cùng đã biết theo nhân vật, và các cạnh LOCATED_AT của nhân vật chính với khoảng hiệu lực
    last_place: dict[str, str] = {}
    for p in packages[0]["edges"]:
        if p["type"] == "LOCATED_AT":
            last_place[p["from"]] = p["to"]
    loc_edges = []  # (from_chapter, to_chapter|None, place)
    closes: dict[str, int] = {}
    for num in sorted(packages):
        for c in packages[num]["close"]:
            closes[c["id"]] = c["valid_to_chapter"]
    for num in sorted(packages):
        for e in packages[num]["edges"]:
            if e["type"] == "LOCATED_AT" and e["from"] == PROTAGONIST:
                loc_edges.append((e["valid_from_chapter"], closes.get(e["id"]), e["to"]))

    rows, no_loc, multi_loc = [], [], []
    for num in range(1, n + 1):
        pkg = packages[num]
        moved = False
        for e in pkg["edges"]:
            if e["type"] == "LOCATED_AT":
                moved |= last_place.get(e["from"]) != e["to"]
                last_place[e["from"]] = e["to"]
        item = any(e["type"] == "HOLDS" for e in pkg["edges"])
        harm = any(x["label"] == "Fact" and HARM.search(x["props"].get("text", "")) for x in pkg["nodes"])
        social = any(e["type"] in ("RELATES_TO", "MEMBER_OF", "FEELS") for e in pkg["edges"])
        signals = {"thread": num in resolved, "secret": num in revealed, "moved": moved, "item": item,
                   "harm": harm}
        strict = any(signals.values())
        open_here = [e for e in loc_edges if e[0] <= num and (e[1] is None or e[1] > num)]
        if not open_here:
            no_loc.append(num)
        if len(open_here) > 1:
            multi_loc.append(num)
        rows.append({"chapter": num, "signals": [k for k, v in signals.items() if v], "stalled": not strict,
                     "stalled_wide": not (strict or social), "new_facts": sum(
                         1 for x in pkg["nodes"] if x["label"] == "Fact")})

    chapters = {int(f.stem[2:]): f.read_text(encoding="utf-8") for f in (run / "chapters").glob("ch*.md")}
    proc = {k: len(PROC.findall(prose_metrics.CHOICES_HEADING.join(v.split(prose_metrics.CHOICES_HEADING)[:1])))
            for k, v in chapters.items()}
    parts = thirds(n)
    plan, total = truth["plan"], truth["plan_progress"]["total_chapters"]
    open_ms, open_all = [0] * (total + 2), [0] * (total + 2)
    windows = ([(m["from_chapter"], m["to_chapter"], True) for m in plan["milestones"]]
               + [(x["reveal_from_chapter"], x["reveal_to_chapter"], False) for x in plan["secrets"]]
               + [(x["resolve_from_chapter"], x["resolve_to_chapter"], False)
                  for x in plan["must_resolve_threads"]])
    for a, b, is_milestone in windows:
        for c in range(a, b + 1):
            open_all[c] += 1
            open_ms[c] += is_milestone
    grams = {k: bigrams(v.split(prose_metrics.CHOICES_HEADING)[0]) for k, v in chapters.items()}
    overlap = {}
    for k in sorted(grams):
        prev = [grams[j] for j in (k - 1, k - 2) if j in grams]
        if prev:
            overlap[k] = st.mean(len(grams[k] & g) / max(1, len(grams[k] | g)) for g in prev)
    place_at = {}
    for num in range(1, n + 1):
        here = [e for e in loc_edges if e[0] <= num and (e[1] is None or e[1] > num)]
        if here:
            place_at[num] = here[-1][2]
    returns = [k for k in sorted(place_at)
               if k - 1 in place_at and place_at[k] != place_at[k - 1]
               and place_at[k] in {place_at.get(k - j) for j in (2, 3)}]

    calls = [json.loads(x) for x in (run / "calls.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    by_role = defaultdict(lambda: [[] for _ in parts])
    usd = defaultdict(float)
    for c in calls:
        if c.get("status") != "ok":
            continue
        ch = c.get("chapter") or 0
        usd[ch] += c.get("cost_usd") or 0.0
        for i, rng in enumerate(parts):
            if ch in rng:
                by_role[c["role"]][i].append(c.get("prompt_tokens") or 0)

    pm = prose_metrics.metrics(run)
    return {
        "run": run.name, "chapters": n, "plan_chapters": report["chapters_planned"],
        "story_finished": report["story_finished"],
        "stalled_chapters": [r["chapter"] for r in rows if r["stalled"]],
        "stalled_count": sum(r["stalled"] for r in rows),
        "stalled_wide_count": sum(r["stalled_wide"] for r in rows),
        "protagonist_no_location": no_loc, "protagonist_multi_location": multi_loc,
        "procedural_per_chapter": {str(k): v for k, v in sorted(proc.items())},
        "procedural_by_third": [avg(proc[c] for c in rng if c in proc) for rng in parts],
        "bigram_overlap_prev_by_third": [avg(overlap[c] for c in rng if c in overlap) for rng in parts],
        "place_returns": returns, "places_visited": len(set(place_at.values())),
        "plan_no_milestone": [c for c in range(1, total + 1) if not open_ms[c]],
        "plan_no_item": [c for c in range(1, total + 1) if not open_all[c]],
        "static_end": pm["static_end"], "static_end_ratio": pm["static_end_ratio"],
        "waiting_choice_sets": pm["waiting_choice_sets"], "choice_sets": pm["choice_sets"],
        "duplicate_openers": pm["duplicate_openers"],
        "input_tokens_by_role_third": {r: [avg(v) for v in vs] for r, vs in sorted(by_role.items())},
        "usd_per_chapter_by_third": [avg(usd[c] for c in rng) for rng in parts],
        "usd_total": report["cost"]["total_usd"], "usd_per_chapter": pm["usd_per_chapter"],
        "rewrites": report["rewrites"], "new_facts_by_chapter": [r["new_facts"] for r in rows],
        "signals_by_chapter": {r["chapter"]: r["signals"] for r in rows},
    }


if __name__ == "__main__":
    for d in sys.argv[1:]:
        print(json.dumps(metrics(Path(d)), ensure_ascii=False))
