"""Phát lại tín hiệu "chương liền không đổi trạng thái" (D-112) trên các lượt chạy đã có, không gọi model.

Chạy từ `backend/`: `uv run python ../evals/results/2026-10-29-idle-replay/replay.py <thư mục kết quả>...`
(thư mục tính từ `evals/results/`, cần `truth_dump.json`). Mỗi chương viết w in dòng `w:A/B[S]`:
A = dãy chương rỗng liền ngay trước w nếu mạch gỡ và bí mật lộ cũng tính là đổi; B = dãy chương rỗng
theo `pacing.idle_chapters` (chỉ nơi ở, chủ đồ vật, cái chết); S = cờ `standstill` (D-98) bật, ngưỡng 4.
"""

import json
import sys
from pathlib import Path

from writory.graph import ChangePackage
from writory.guard.plan import plan_progress
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.pacing import idle_chapters, standstill
from writory.pipeline.story_plan import StoryPlan

RESULTS = Path(__file__).resolve().parents[1]


def with_plan_events(plan: StoryPlan, state: OverlayState, writing: int) -> int:
    """Như `idle_chapters` nhưng mạch gỡ và bí mật lộ cũng làm đứt dãy (dạng đã bỏ)."""
    progress = plan_progress(plan, state, writing - 1)
    planned = {s.revealed_chapter for s in progress.secrets if s.revealed_chapter is not None}
    planned |= {t.resolved_chapter for t in progress.threads if t.resolved_chapter is not None}
    run = 0
    for chapter in range(writing - 1, 0, -1):
        if chapter in planned or idle_chapters(state, chapter + 1, 1) is None:
            break
        run += 1
    return run


for name in sys.argv[1:]:
    dump = json.loads((RESULTS / name / "truth_dump.json").read_text(encoding="utf-8"))
    packs = [ChangePackage.model_validate(dump["packages"][k]) for k in sorted(dump["packages"], key=int)]
    plan = StoryPlan.model_validate(dump["plan"])
    row = []
    for w in range(2, len(packs) + 1):
        state = OverlayState(EmptyState(), packs[:w])
        b = idle_chapters(state, w, 1)
        row.append(f"{w}:{with_plan_events(plan, state, w)}/{b.chapters if b else 0}"
                   f"{'S' if standstill(state, w, 4) else ''}")
    print(name, "- tổng", plan.total_chapters, "chương\n ", " ".join(row))
