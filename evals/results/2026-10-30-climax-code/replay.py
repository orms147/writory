"""Dựng lại mục tiêu chương của các truyện đã lưu bằng code HIỆN HÀNH của thư mục chạy nó (D-142). Không
gọi model, không Neo4j.

  cd <thư mục repo>/backend && uv run python ../evals/results/2026-10-30-climax-code/replay.py <out.json>

Chạy một lần ở checkout main (`3ec3b85`, "cũ") và một lần ở nhánh `feature/climax-code` ("mới"), rồi
`compare.py` so hai tệp. Với mỗi lượt có dấu mốc và mỗi chương 1..N đã ghi: state = các gói chương 0..N-1
(OverlayState), `chapter_goals` với các giá trị `limits.context` của config hiện hành, dựng chữ bằng
`render_chapter_goals`. Ghi: mục "Mốc cốt truyện" (từng dòng), phần còn lại của mục tiêu, trạng thái mốc,
cờ `gap`, id mốc bộ trích còn được đánh dấu (`pending_milestones`), id mốc đã xong. Tham số `climax_aftermath`
chỉ truyền khi code hỗ trợ.
"""

import inspect
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
from writory.config import REPO_ROOT, load_config  # noqa: E402
from writory.graph import ChangePackage  # noqa: E402
from writory.guard.state import EmptyState, OverlayState  # noqa: E402
from writory.pipeline.pacing import chapter_goals, render_chapter_goals  # noqa: E402
from writory.pipeline.story_plan import StoryPlan  # noqa: E402

RESULTS = REPO_ROOT / "evals" / "results"
RUNS = [
    "2026-10-29-run-long-after-ky-ao-2", "2026-10-29-run-long-after-ky-ao",
    "2026-10-29-run-long-after-tu-tien", "2026-10-29-run-psab-a1", "2026-10-30-run-psab-a2",
    "2026-10-29-run-psab-b1", "2026-10-30-run-psab-b1-r3",
]
SECTION = "### Mốc cốt truyện"


def split_text(parts) -> tuple[list[str], str]:
    """(các dòng của mục "Mốc cốt truyện", phần còn lại) của chữ mục tiêu chương."""
    text = "\n".join(str(p) for p in parts)
    lines = text.split("\n")
    if SECTION not in lines:
        return [], text
    i = lines.index(SECTION)
    j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("### ")), len(lines))
    return lines[i + 1:j], "\n".join(lines[:i] + lines[j:])


def replay(run: str, config) -> dict:
    truth = json.loads((RESULTS / run / "truth_dump.json").read_text(encoding="utf-8"))
    plan = StoryPlan.model_validate(truth["plan"])
    packages = {int(n): ChangePackage.model_validate(p) for n, p in truth["packages"].items()}
    ctx = config.limits.context
    extra = {}
    if "climax_aftermath" in inspect.signature(chapter_goals).parameters:
        extra["climax_aftermath"] = ctx.climax_aftermath_chapters
    out = {}
    for chapter in range(1, max(packages) + 1):
        state = OverlayState(EmptyState(), [packages[n] for n in range(chapter)])
        goals = chapter_goals(
            plan, chapter, state, standstill_chapters=ctx.standstill_chapters,
            unplanned_goal=ctx.unplanned_chapter_goal, idle_chapters=ctx.idle_chapters,
            milestone_lookahead=ctx.milestone_lookahead, phase_shift_every=ctx.phase_shift_every,
            **extra)
        milestone_lines, rest = split_text(render_chapter_goals(goals, scene=1, scene_count=2))
        out[str(chapter)] = {
            "milestone_lines": milestone_lines, "rest": rest,
            "statuses": [[m.number, m.kind, m.status] for m in goals.milestones],
            "gap": goals.gap,
            "pending": [p.number for p in goals.pending_milestones],
            "done": [list(x) for x in goals.milestones_done],
        }
    return {"plan_milestones": [[i, m.kind, m.from_chapter, m.to_chapter]
                                for i, m in enumerate(plan.milestones, 1)],
            "chapters": out}


if __name__ == "__main__":
    config = load_config()
    result = {run: replay(run, config) for run in RUNS if (RESULTS / run / "truth_dump.json").exists()}
    Path(sys.argv[1]).write_bytes(json.dumps(result, ensure_ascii=False, indent=1).encode("utf-8"))
    print("ok", len(result), "lượt")
