"""Số đo MỚI cho lượt Dài sau D-112..D-121 (ngoài `../2026-10-29-run-long-baseline/long_metrics.py`).

Chạy từ `backend/`: `uv run python ../evals/results/2026-10-29-long-after-fixes/after_metrics.py <thư mục kết quả>...`
(tên thư mục tính từ `evals/results/`). Không gọi model. In mỗi lần chạy một dòng JSON:
- milestones: mốc kế hoạch (số thứ tự, khoảng chương, chương xảy ra, trạng thái) từ `report.json`;
  milestone_marks: số lần bộ trích đánh dấu mốc được nhận (nút Chapter `milestones` trong `truth_dump.json`);
  milestone_rejections: số lần dấu mốc bị từ chối, theo lý do (mục `rejected` có mô tả "mốc ...");
- flags: số chương viết mà cờ `standstill` (D-98) hay `idle` (D-112, ngưỡng của config) bật, tính lại bằng
  chính `pacing.standstill` và `pacing.idle_chapters` trên đồ thị đến hết chương trước (đúng điều mục tiêu
  chương dùng; `idle` chỉ in khi `standstill` không bật); không tính chương cuối của kế hoạch;
- rejected_bodies: số dòng `rejected.jsonl`, theo vai;
- cost: tổng USD, số lần viết lại, lỗi người canh tìm thấy theo loại.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from writory.config import load_config
from writory.graph import ChangePackage
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.pacing import idle_chapters, standstill
from writory.pipeline.story_plan import StoryPlan

RESULTS = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")


def metrics(name: str) -> dict:
    run = RESULTS / name
    report = json.loads((run / "report.json").read_text(encoding="utf-8"))
    dump = json.loads((run / "truth_dump.json").read_text(encoding="utf-8"))
    plan = StoryPlan.model_validate(dump["plan"])
    packs = {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()}
    ctx = load_config().limits.context
    done = max(packs)
    standstill_flags, idle_flags = [], []
    for w in range(2, done + 2):  # chương đang viết w, đồ thị đến hết w-1
        if w >= plan.total_chapters:
            break
        state = OverlayState(EmptyState(), [packs[n] for n in sorted(packs) if n <= w - 1])
        if standstill(state, w, ctx.standstill_chapters) is not None:
            standstill_flags.append(w)
        elif idle_chapters(state, w, ctx.idle_chapters) is not None:
            idle_flags.append(w)
    marks = {n: node.props["milestones"] for n, pkg in packs.items() for node in pkg.nodes
             if node.label == "Chapter" and node.props.get("milestones")}
    rejected: Counter[str] = Counter()
    for attempts in dump.get("chapters", {}).values():
        for attempt in attempts:
            for review in attempt.get("reviews", []):
                for desc, why in review.get("rejected", []):
                    if str(desc).startswith("mốc"):
                        rejected[why] += 1
    rej_roles: Counter[str] = Counter()
    rj = run / "rejected.jsonl"
    if rj.exists():
        for line in rj.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rej_roles[json.loads(line)["role"]] += 1
    return {
        "run": name, "status": report["status"], "stop": report["stop"],
        "chapters_committed": report["chapters_committed"], "chapters_planned": report["chapters_planned"],
        "story_finished": report["story_finished"],
        "milestones": [[m["n"], m["window"], m["done_chapter"], m["status"]] for m in report["plan_vs_result"].get("milestones", [])],  # lượt trước D-116 không có mục này
        "milestone_marks": {str(n): v for n, v in sorted(marks.items())},
        "milestone_rejections": dict(rejected),
        "standstill_flag_chapters": standstill_flags, "idle_flag_chapters": idle_flags,
        "rejected_bodies": report.get("rejected_bodies"), "rejected_bodies_by_role": dict(rej_roles),
        "usd_total": report["cost"]["total_usd"], "rewrites": report["rewrites"],
        "issues_found": report["issues"]["found"],
    }


for d in sys.argv[1:]:
    print(json.dumps(metrics(d), ensure_ascii=False))
