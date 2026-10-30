"""Phát lại bộ trích `extract-8` và `extract-9` trên chương đã lưu (khai trước ở `expectations.md`).

Chạy từ `backend/` (một mình, không song song với lượt khác dùng cùng key):
    uv run python ../evals/results/2026-10-30-extract-milestone-kind/replay.py --dry-run
    uv run python ../evals/results/2026-10-30-extract-milestone-kind/replay.py --budget 0.10

Thư mục kết quả: `--out` (mặc định cùng thư mục với file này). Ghi `results.jsonl` (mỗi lời gọi một
dòng: ca, bản đề, mốc nhận, mốc model trả, lý do bị từ chối, token, chi phí), `calls.jsonl` và `meta.json`.
Không ghi chữ chương, không ghi key (G7).

Trần chi phí: dừng trước lời gọi tiếp theo nếu chi tiêu thật + 1,5 × lời gọi đắt nhất đã thấy (hoặc
ước tính tối đa của lời gọi đầu) vượt `--budget`. Khác bench_run (giữ chỗ tối đa mỗi lời gọi) để dùng
được gần hết ngân sách nhỏ; hết ngân sách thì các ca còn lại ghi là không chạy.
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from writory.config import REPO_ROOT, load_config
from writory.graph import ChangePackage
from writory.graph.schema import EDGE_TYPES
from writory.guard.state import EmptyState, OverlayState
from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, role_extra
from writory.llm.cost import CostEstimator
from writory.llm.fake import FakeLLM
from writory.pipeline.chapter import chapter_node
from writory.pipeline.extract import (
    Entity,
    ExtractOutput,
    FactRules,
    OpenEdge,
    accept_milestones,
    build_messages,
)
from writory.pipeline.pacing import chapter_goals
from writory.pipeline.store import entities_from_rows
from writory.pipeline.story_plan import StoryPlan
from writory.quality.bench_d import load_keys

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
sys.stdout.reconfigure(encoding="utf-8")

TU = "2026-10-29-run-long-after-tu-tien"
KY = "2026-10-29-run-long-after-ky-ao-2"
# (nhóm, lượt chạy, chương); thứ tự = ưu tiên (expectations.md)
CASES: list[tuple[str, str, int]] = [
    ("1-muc-tieu", TU, 19), ("1-muc-tieu", KY, 24),
    ("2-doi-chung", KY, 16), ("2-doi-chung", TU, 11), ("2-doi-chung", KY, 10), ("2-doi-chung", TU, 5),
    ("3-ngu-canh", TU, 18),
    ("3-ngu-canh", KY, 22), ("3-ngu-canh", KY, 23), ("3-ngu-canh", TU, 17),
    ("4-lap-lai", TU, 19), ("4-lap-lai", KY, 24),
]
PROMPT_8 = (HERE / "extract8_system_prompt.txt").read_text(encoding="utf-8")
# extract-9 không gộp vào main (D-129): chữ đề lưu ở đây. Dòng mốc có cột loại do `build_messages` của
# code extract-9 sinh, nên chạy lại đúng như lần đo cần checkout commit 7ea8812 (nhánh feature/extract-milestone-kind).
PROMPT_9 = (HERE / "extract9_system_prompt.txt").read_text(encoding="utf-8")


def to_extract8_user(content: str) -> str:
    """Dòng mốc theo định dạng `extract-8` (không có cột loại)."""
    content = content.replace("(id | loại | khoảng chương | mô tả)", "(id | khoảng chương | mô tả)")
    return re.sub(r"(?m)^- (m\d+) \| (?:bước ngoặt|cao trào|kết) \| ", r"- \1 | ", content)


def chapter_text(run: str, number: int) -> str:
    """Chữ chương đã ghi, bỏ tiêu đề, dòng lựa chọn dẫn tới và phần lựa chọn cuối chương."""
    raw = (RESULTS / run / "chapters" / f"ch{number:02d}.md").read_text(encoding="utf-8")
    body = raw.split("## Lựa chọn cuối chương")[0]
    lines = body.splitlines()
    kept = [ln for ln in lines if not ln.startswith("# Chương ") and not ln.startswith("_Lựa chọn dẫn tới")]
    return "\n".join(kept).strip() + "\n"


@dataclass
class Case:
    group: str
    run: str
    chapter: int
    messages9: list[Message]
    messages8: list[Message]
    pending: list
    done: dict[int, int]
    text: str
    production_marks: list[int]
    chapter_id: str


def build_case(group: str, run: str, number: int, cache: dict) -> Case:
    if run not in cache:
        dump = json.loads((RESULTS / run / "truth_dump.json").read_text(encoding="utf-8"))
        cache[run] = (dump, StoryPlan.model_validate(dump["plan"]),
                      {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()})
    dump, plan, packs = cache[run]
    cfg = load_config()
    ctx = cfg.limits.context
    before = OverlayState(EmptyState(), [packs[n] for n in sorted(packs) if n <= number - 1])
    goals = chapter_goals(
        plan, number, before, standstill_chapters=ctx.standstill_chapters,
        unplanned_goal=ctx.unplanned_chapter_goal, idle_chapters=ctx.idle_chapters,
        milestone_lookahead=ctx.milestone_lookahead)
    ids = [n.id for n in (m for k, p in packs.items() if k <= number - 1 for m in p.nodes)]
    catalogue: list[Entity] = entities_from_rows(before.nodes(ids))
    node = chapter_node(number)
    catalogue.append(Entity(node.id, "Chapter", f"Chương {number}"))
    open_edges = [OpenEdge(r.id, r.type, r.source, r.target)
                  for t in EDGE_TYPES for r in before.edges_at(t, number)]
    f = cfg.limits.facts
    rules = FactRules(max_new=f.max_new_per_chapter, max_chars=f.text_max_chars, scene=1,
                      duplicate_overlap=f.duplicate_overlap, grounded_min=f.grounded_min,
                      related_overlap=f.related_overlap)
    text = chapter_text(run, number)
    kw = {"chapter": number, "chapter_id": node.id, "protagonist_id": before.protagonist_id(),
          "chapter_text": text, "entities": catalogue, "open_edges": open_edges,
          "threads": goals.threads, "fact_rules": rules, "milestones": goals.pending_milestones}
    m9 = build_messages(**kw)
    assert m9[0].content.startswith(PROMPT_9[:60])
    m8 = [Message(role="system", content=m9[0].content.replace(PROMPT_9, PROMPT_8)),
          Message(role="user", content=to_extract8_user(m9[1].content))]
    assert m8[0].content != m9[0].content
    assert (m8[1].content != m9[1].content) == bool(goals.pending_milestones)
    marks = next((n.props.get("milestones", []) for n in packs[number].nodes if n.label == "Chapter"), [])
    return Case(group, run, number, m9, m8, list(goals.pending_milestones), dict(goals.milestones_done),
                text, list(marks), node.id)


class CappedLLM(LLMClient):
    """Gọi client thật, ghi chi tiêu thật, dừng khi chạm trần (xem docstring đầu file)."""

    def __init__(self, inner: LLMClient, estimator: CostEstimator, budget: float, record) -> None:
        self._inner, self._est, self._budget, self._record = inner, estimator, budget, record
        self.spent = 0.0
        self.max_call = 0.0
        self.halted: str | None = None
        self.calls = 0

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        bound = self._est.bound(extra)
        reserve = 1.5 * self.max_call if self.max_call else self._est.max_cost(
            model, messages, response_schema)
        if self.spent + reserve > self._budget:
            self.halted = f"chi {self.spent:.4f} + giữ chỗ {reserve:.4f} > trần {self._budget:.2f}"
            raise RuntimeError(self.halted)
        result = await self._inner.chat(model, messages, response_schema=response_schema, extra=bound)
        cost = result.usage.cost_usd or 0.0
        self.spent += cost
        self.max_call = max(self.max_call, cost)
        self.calls += 1
        self._record({"seq": self.calls, "cost_usd": cost, "spent_usd": round(self.spent, 6),
                      "prompt_tokens": result.usage.prompt_tokens,
                      "completion_tokens": result.usage.completion_tokens,
                      "finish_reason": result.finish_reason})
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True, check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain",
                                                                   "--", "backend", "config"))}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.10)
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--env-file", default="C:/Work/AI/WriTory/.env")
    ap.add_argument("--only", help="chỉ chạy các nhóm có tiền tố này, ví dụ 1-")
    args = ap.parse_args()
    out = Path(args.out)
    if not args.dry_run and (out / "results.jsonl").exists():
        print("results.jsonl đã có: không ghi đè; chọn --out khác")
        return 1
    out.mkdir(parents=True, exist_ok=True)

    cache: dict = {}
    cases = [build_case(*c, cache) for c in CASES if not args.only or c[0].startswith(args.only)]
    cfg = load_config()
    model = cfg.models.roles.require("extract")
    extra = role_extra(cfg.models, "extract")
    estimator = CostEstimator.from_config(cfg)
    calls_log = (out / "calls.jsonl").open("w", encoding="utf-8") if not args.dry_run else None
    current: dict = {}

    def record(row: dict) -> None:
        if calls_log:
            calls_log.write(json.dumps(current | row, ensure_ascii=False) + "\n")
            calls_log.flush()

    if args.dry_run:
        empty = json.dumps({"edges": [], "close": [], "new_facts": [], "milestones": []})
        inner: LLMClient = FakeLLM.scripted([empty] * 200, cost_usd=0.003)
    else:
        from writory.llm.openrouter import OpenRouterClient
        keys = load_keys(Path(args.env_file), ["openrouter"])
        assert keys.openrouter_api_key is not None
        inner = OpenRouterClient(keys.openrouter_api_key, deadline_s=300)
    llm = CappedLLM(inner, estimator, args.budget, record)

    results, skipped = [], []
    for case in cases:
        for version, messages in (("extract-8", case.messages8), ("extract-9", case.messages9)):
            current.clear()
            current.update({"run": case.run, "chapter": case.chapter, "version": version,
                            "group": case.group})
            try:
                output, chat = await llm.chat_json(model, messages, ExtractOutput, extra=extra)
            except RuntimeError:
                skipped.append({"run": case.run, "chapter": case.chapter, "version": version,
                                "group": case.group})
                continue
            marks, rejected = accept_milestones(output, case.pending, case.done, case.text)
            results.append({
                "group": case.group, "run": case.run, "chapter": case.chapter, "version": version,
                "pending": [m.number for m in case.pending], "done": case.done,
                "production_marks": case.production_marks,
                "accepted": [[m.number, m.quote] for m in marks],
                "model_output": [[m.id, m.quote] for m in output.milestones],
                "rejected": [[d, w] for d, w in rejected if str(d).startswith("mốc")],
                "cost_usd": round(chat.usage.cost_usd or 0.0, 6),
                "prompt_tokens": chat.usage.prompt_tokens})
    if not args.dry_run:
        with (out / "results.jsonl").open("w", encoding="utf-8") as fh:
            for row in results:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        (out / "meta.json").write_text(json.dumps({
            "bench": "extract-milestone-kind-replay", "git": git_info(), "model": model,
            "extra": extra, "budget_usd": args.budget, "spent_usd": round(llm.spent, 6),
            "calls": llm.calls, "halted": llm.halted, "skipped": skipped,
            "versions": ["extract-8", "extract-9"], "cases": [list(c) for c in CASES],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(results)} lời gọi xong, bỏ qua {len(skipped)}, chi {llm.spent:.4f} USD"
          + (f" (dừng: {llm.halted})" if llm.halted else ""))
    for r in results:
        print(f"  ch{r['chapter']:>2} {r['run'][-18:]:<18} {r['version']}: nhận {[a[0] for a in r['accepted']]} "
              f"(gốc {r['production_marks']}; thấy {r['pending']})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
