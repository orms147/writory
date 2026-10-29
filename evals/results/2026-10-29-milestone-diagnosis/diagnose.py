"""Chẩn đoán mốc D-116 từ dữ liệu đã có, KHÔNG gọi model (chỉ đọc `truth_dump.json`, `report.json`).

Chạy từ `backend/`:  uv run python ../evals/results/2026-10-29-milestone-diagnosis/diagnose.py
Đầu ra (in ra, lưu thành `diagnose.txt`):
  A. mục "Mốc cốt truyện" trong mục tiêu chương của đề dàn ý/viết, dựng lại bằng chính
     `chapter_goals` + `render_chapter_goals`, cho tu-tien-3 (baseline, không theo dõi mốc),
     tu-tien sau (D-116 bật) ở các chương 5-11, cùng khoảng lộ của bí mật `fact_su_gia_that`;
  B. mốc chưa xảy ra bộ trích được thấy ở từng chương (đúng `_pending_milestones`), ky-ao-2 ch16-24;
  C. mọi mục `rejected` của dấu mốc, mọi lượt viết, ở hai lượt chạy.
Lưu ý: dựng lại cho ĐỀ cảnh đầu của chương (đồ thị đến hết chương trước, `done_extra` rỗng).
"""

import json
import sys
from pathlib import Path

from writory.config import load_config
from writory.graph import ChangePackage
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.pacing import chapter_goals, render_chapter_goals
from writory.pipeline.story_plan import StoryPlan

RESULTS = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
CTX = load_config().limits.context


def load(name: str):
    dump = json.loads((RESULTS / name / "truth_dump.json").read_text(encoding="utf-8"))
    plan = StoryPlan.model_validate(dump["plan"])
    packs = {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()}
    return dump, plan, packs


def goals_for(plan, packs, chapter, *, track_milestones: bool):
    state = OverlayState(EmptyState(), [packs[n] for n in sorted(packs) if n <= chapter - 1])
    return chapter_goals(
        plan, chapter, state, standstill_chapters=CTX.standstill_chapters,
        unplanned_goal=CTX.unplanned_chapter_goal, idle_chapters=CTX.idle_chapters,
        milestone_lookahead=CTX.milestone_lookahead if track_milestones else None)


def milestone_section(goals) -> list[str]:
    text = [p if isinstance(p, str) else p.text for p in render_chapter_goals(
        goals, scene=1, scene_count=2)]
    joined = "".join(text)
    out, on = [], False
    for ln in joined.splitlines():
        if ln.startswith("### "):
            on = ln.startswith("### Mốc cốt truyện")
        if on:
            out.append(ln)
    return out


def secrets_line(goals) -> str:
    return "; ".join(f"{s.fact_id}:{s.status}({s.from_chapter}-{s.to_chapter})" for s in goals.secrets) or "-"


def part_a() -> None:
    print("== A. Mục 'Mốc cốt truyện' của đề dàn ý/viết, tu-tien (cùng kế hoạch, cùng thế giới)")
    for name, track in (("2026-10-29-run-long-tu-tien-3", False), ("2026-10-29-run-long-after-tu-tien", True)):
        dump, plan, packs = load(name)
        print(f"\n--- {name} (theo dõi mốc D-116: {track}); bí mật fact_su_gia_that khoảng lộ "
              + str([(s.reveal_from_chapter, s.reveal_to_chapter) for s in plan.secrets if s.fact_id == "fact_su_gia_that"]))
        for ch in range(5, 12):
            if ch - 1 not in packs:
                continue
            g = goals_for(plan, packs, ch, track_milestones=track)
            print(f"\n[ch{ch}] bí mật trong đề: {secrets_line(g)}")
            for ln in milestone_section(g):
                print("   " + ln[:230])


def part_b() -> None:
    print("\n\n== B. Mốc chưa xảy ra bộ trích được thấy (D-116), ky-ao-2")
    dump, plan, packs = load("2026-10-29-run-long-after-ky-ao-2")
    for ch in range(14, 25):
        if ch - 1 not in packs:
            continue
        g = goals_for(plan, packs, ch, track_milestones=True)
        pend = [f"m{m.number}({m.from_chapter}-{m.to_chapter})" for m in g.pending_milestones]
        done = [f"m{n}@ch{c}" for n, c in g.milestones_done]
        print(f"ch{ch}: bộ trích thấy {pend}; đã xong {done}")


def part_c() -> None:
    print("\n\n== C. Mục `rejected` của dấu mốc (mọi chương, mọi lượt viết, mọi cảnh)")
    for name in ("2026-10-29-run-long-after-tu-tien", "2026-10-29-run-long-after-ky-ao-2"):
        dump, _, _ = load(name)
        n_reviews = n_rej = 0
        for attempts in dump["chapters"].values():
            for attempt in attempts:
                for review in attempt.get("reviews", []):
                    n_reviews += 1
                    n_rej += sum(1 for desc, _ in review.get("rejected", []) if str(desc).startswith("mốc"))
        print(f"{name}: {n_reviews} lượt soát cảnh, {n_rej} dấu mốc bị từ chối")


part_a()
part_b()
part_c()


def part_d() -> None:
    """D. Mọi lượt Dài có `truth_dump.json`: khoảng cách từ chương tới khoảng của mốc 'kế tiếp' (đúng như
    đề dàn ý hiển thị, theo dõi mốc bật cho lượt sau D-116, tắt cho lượt trước) và chương đó có cảnh
    nào bị người canh báo `early_reveal` ở lượt viết đầu hay không. Chỉ đếm, không kết luận nhân quả."""
    print("\n\n== D. early_reveal theo khoảng cách tới mốc 'kế tiếp' (tất cả lượt Dài có truth_dump)")
    rows = []
    for d in sorted(RESULTS.glob("*run-long-*")):
        if not (d / "truth_dump.json").exists() or "baseline" in d.name:
            continue
        dump, plan, packs = load(d.name)
        track = "after" in d.name
        for ch_s, attempts in dump["chapters"].items():
            ch = int(ch_s)
            if ch - 1 not in packs and ch != 1:
                continue
            g = goals_for(plan, packs, ch, track_milestones=track)
            nxt = [m for m in g.milestones if m.status == "next"]
            gap = (nxt[0].from_chapter - ch) if nxt else None
            first = attempts[0]
            early = any(x["kind"] == "early_reveal" for r in first.get("reviews", []) for x in r.get("issues", []))
            rows.append((d.name, ch, gap, early))
    buckets = {}
    for _, ch, gap, early in rows:
        key = "không có mốc kế tiếp" if gap is None else ("1-2" if gap <= 2 else "3-4" if gap <= 4 else "5+")
        n, e = buckets.get(key, (0, 0))
        buckets[key] = (n + 1, e + int(early))
    for key in ("1-2", "3-4", "5+", "không có mốc kế tiếp"):
        n, e = buckets.get(key, (0, 0))
        print(f"khoảng cách tới khoảng của mốc kế tiếp = {key}: {n} chương, {e} chương có early_reveal ở lượt viết đầu")
    print("\nchương có early_reveal ở lượt viết đầu (lượt, chương, khoảng cách):")
    for name, ch, gap, early in rows:
        if early:
            print(f"  {name} ch{ch} gap={gap}")


part_d()
