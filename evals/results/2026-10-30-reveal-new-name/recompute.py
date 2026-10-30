"""Tính lại trên lượt chạy đã lưu, KHÔNG gọi model: tự hé lộ tên chính mới (D-136) sẽ thêm cạnh nào.

Chạy từ `backend/`:
    uv run python ../evals/results/2026-10-30-reveal-new-name/recompute.py

Mỗi chương đã ghi của mọi thư mục `evals/results/*/` có `truth_dump.json` và `chapters/`: chạy
`safety.reveal.auto_reveals` (code của nhánh) trên TOÀN chữ chương (sản phẩm chạy từng cảnh), với
player_view cuối chương của lượt gốc (đã gồm hé lộ của bộ trích và tự hé lộ cũ), `skip` như sản phẩm
(nhân vật chính, nút được bảo vệ theo `scene`), `no_new_name` = nút được bảo vệ ở đường người chơi so với
player_view đầu chương, cộng nút đã hé lộ trong chính chương đó. Chỉ đếm cạnh cho nút ĐÃ có trong
player_view (tên mới); cạnh hé lộ lần đầu (khác biệt cảnh/chương) đếm riêng. Tính dồn: cạnh tên mới của
chương trước vào trạng thái của chương sau, như sản phẩm (tên đã biết thì không thêm lại).

Ghi `recompute.jsonl` (mỗi cạnh mới một dòng: lượt, chương, nút, tên đang biết, tên mới, câu trích; chữ
lớp truth của chính lượt đã lưu trong repo) và in bảng tóm tắt.
"""

import json
import sys
from collections import Counter
from pathlib import Path

from writory.graph import ChangePackage
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import protected_ids
from writory.safety.reveal import auto_reveals

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
sys.stdout.reconfigure(encoding="utf-8")


def chapter_text(run: Path, number: int) -> str | None:
    """Chữ chương đã ghi, bỏ tiêu đề, dòng lựa chọn dẫn tới và phần lựa chọn cuối chương."""
    path = run / "chapters" / f"ch{number:02d}.md"
    if not path.exists():
        return None
    body = path.read_text(encoding="utf-8").split("## Lựa chọn cuối chương")[0]
    kept = [ln for ln in body.splitlines()
            if not ln.startswith("# Chương ") and not ln.startswith("_Lựa chọn dẫn tới")]
    return "\n".join(kept).strip() + "\n"


def main() -> int:
    rows: list[dict] = []
    first_reveals = 0
    chapters = 0
    skipped: list[str] = []
    for run in sorted(p for p in RESULTS.iterdir() if (p / "truth_dump.json").exists()):
        dump = json.loads((run / "truth_dump.json").read_text(encoding="utf-8"))
        try:
            plan = StoryPlan.model_validate(dump["plan"])
            packs = {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()}
        except Exception as e:  # noqa: BLE001 — lượt cũ khác schema: ghi tên, bỏ qua
            skipped.append(f"{run.name}: {type(e).__name__}")
            continue
        added: list[ChangePackage] = []  # cạnh tên mới của các chương trước (tính dồn)
        for n in sorted(packs):
            text = chapter_text(run, n) if n >= 1 else None
            if text is None:
                continue
            chapters += 1
            before = OverlayState(EmptyState(), [*(packs[k] for k in sorted(packs) if k < n), *added])
            after = OverlayState(before, [packs[n]])
            view = player_view_of(after, n)
            here = next(x.id for x in packs[n].nodes if x.label == "Chapter")
            protagonist = after.protagonist_id()
            now = {e.source for e in packs[n].edges
                   if e.type == "REVEALED_TO_PLAYER" and e.target == here}
            locked = protected_ids(plan, player_view_of(before, n), "player_path")
            shown = {e.id: (e.text, *e.aliases) for e in view.entries}
            edges = auto_reveals(
                text, chapter=n, chapter_id=here, names=after.named_nodes(), view=view,
                skip={protagonist, *protected_ids(plan, view, "scene")},
                no_new_name={*locked, *now})
            renamed = [e for e in edges if e.source in shown]
            first_reveals += len(edges) - len(renamed)
            if renamed:
                added.append(ChangePackage(commit_id=f"recompute-{n}", nodes=[], edges=renamed))
            for e in renamed:
                rows.append({"run": run.name, "chapter": n, "node": e.source,
                             "known": list(shown[e.source]), "new": e.props["known_as"],
                             "quote": e.props["quote"]})
    with (HERE / "recompute.jsonl").open("w", encoding="utf-8", newline="\n") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    runs = Counter(r["run"] for r in rows)
    print(f"{chapters} chương, {len(runs)} lượt có tên mới, {len(rows)} cạnh tên mới, "
          f"{first_reveals} cạnh hé lộ lần đầu (chênh cảnh/chương, không tính)")
    nodes = {(r["run"], r["node"]) for r in rows}
    print(f"{len(nodes)} cặp (lượt, nút) có tên mới")
    for r in rows:
        print(f"  {r['run'][11:]:<34} ch{r['chapter']:>2} {r['node']:<24} {r['known']} -> "
              f"{r['new']!r} | {r['quote'][:90]!r}")
    if skipped:
        print("bỏ qua:", "; ".join(skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
