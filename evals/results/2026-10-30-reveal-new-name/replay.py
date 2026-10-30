"""Phát lại bộ trích `extract-8` và `extract-10` trên chương đã lưu (khai trước ở `expectations.md`, phần B).

Chạy từ `backend/` (một mình, không song song với lượt khác dùng cùng key):
    uv run python ../evals/results/2026-10-30-reveal-new-name/replay.py --dry-run
    uv run python ../evals/results/2026-10-30-reveal-new-name/replay.py --budget 0.08

Thư mục kết quả: `--out` (mặc định cùng thư mục với file này). Ghi `results.jsonl` (mỗi lời gọi một
dòng: ca, bản đề, hé lộ lần hai nhận và bỏ, hé lộ lần đầu, nhóm lý do bị bỏ, token, chi phí),
`calls.jsonl` và `meta.json`. Không ghi chữ chương, không ghi key (G7).

`extract-10` không gộp vào main (D-136): chữ đề lưu ở `extract10_system_prompt.txt`; dòng cạnh hé lộ có
"người chơi biết là" do `build_messages` của code extract-10 sinh, nên chạy lại đúng như lần đo cần checkout
commit 79a343f (nhánh feature/reveal-new-name). Ở commit sau, `build_case` dừng ở assert đề `extract-10`.

Trần chi phí như `../2026-10-30-extract-milestone-kind/replay.py`: dừng trước lời gọi tiếp theo nếu chi
tiêu thật + 1,5 × lời gọi đắt nhất đã thấy (hoặc ước tính tối đa của lời gọi đầu) vượt `--budget`.
"""

import argparse
import asyncio
import json
import subprocess
import sys
from collections import Counter
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from pathlib import Path

from writory.config import REPO_ROOT, load_config
from writory.graph import ChangePackage, read_sample
from writory.graph.schema import EDGE_TYPES, NAMED_LABELS
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, role_extra
from writory.llm.cost import CostEstimator
from writory.llm.fake import FakeLLM
from writory.pipeline import bench_c
from writory.pipeline.bench_run import reject_reason
from writory.pipeline.chapter import chapter_node
from writory.pipeline.extract import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    Entity,
    ExtractOutput,
    FactRules,
    OpenEdge,
    build_messages,
    to_package,
)
from writory.pipeline.pacing import chapter_goals
from writory.pipeline.store import entities_from_rows
from writory.pipeline.story_plan import StoryPlan
from writory.quality.bench_d import load_keys
from writory.safety.leak import protected_ids
from writory.safety.reveal import auto_reveals

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent
sys.stdout.reconfigure(encoding="utf-8")

SAMPLE = "sample"
# (ca, nguồn, chương); thứ tự = ưu tiên (expectations.md)
CASES: list[tuple[str, str, int]] = [
    ("P0", SAMPLE, 5), ("C4", SAMPLE, 4),
    ("P1", "2026-10-29-run-long-after-tu-tien", 2), ("C2", "2026-10-29-run-long-tu-tien-3", 12),
    ("P2", "2026-10-28-run-ab-trinh-tham-cu-2", 6), ("C1", "2026-10-21-run-ky-ao-vua-2", 2),
    ("P3", "2026-10-22-run-long-tu-tien-2", 5), ("C3", "2026-10-29-run-long-after-ky-ao-2", 10),
    ("P4", "2026-10-29-run-long-ky-ao-hanh-trinh-1", 2), ("P5", "2026-10-22-run-ky-ao-vua-3", 6),
]
# Tên mới đúng của mỗi ca, khai trước (expectations.md); build_case kiểm lại bằng auto_reveals.
EXPECTED: dict[str, set[tuple[str, str]]] = {
    "P0": {("ly_that", "Lý Thất")}, "C4": set(),
    "P1": {("co_hanh_chau", "Cố Hành Chu")}, "C2": set(),
    "P2": {("tran_tan", "Trần Tấn"), ("cong_an_khu_vuc", "công an khu vực")}, "C1": set(),
    "P3": {("han_tu_nguyet", "Hàn Tố Nguyệt")}, "C3": set(),
    "P4": {("ban_do_nep_gap", "Bản đồ Nếp Gấp")},
    "P5": {("lenh_goi_thu_nhat", "Lệnh Gọi Thứ Nhất"), ("lenh_goi_thu_hai", "Lệnh Gọi Thứ Hai")},
}
PROMPT_8 = (HERE / "extract8_system_prompt.txt").read_text(encoding="utf-8")
HEADER_10 = ("Cạnh đang hiệu lực trước chương này (id | kiểu | từ → tới | với cạnh hé lộ: tên "
             "người chơi biết):")
HEADER_8 = "Cạnh đang hiệu lực trước chương này (id | kiểu | từ → tới):"
NEW_NAME_REASONS = {
    "người chơi đã biết nút này dưới tên đó",
    "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)",
    "tên mới của nút có tên đang được bảo vệ (D-61)",
    "đã hé lộ ở chương này: tên mới ghi ở chương sau (D-136)",
}


def chapter_text(run: str, number: int) -> str:
    """Chữ chương đã ghi, bỏ tiêu đề, dòng lựa chọn dẫn tới và phần lựa chọn cuối chương."""
    raw = (RESULTS / run / "chapters" / f"ch{number:02d}.md").read_text(encoding="utf-8")
    body = raw.split("## Lựa chọn cuối chương")[0]
    kept = [ln for ln in body.splitlines()
            if not ln.startswith("# Chương ") and not ln.startswith("_Lựa chọn dẫn tới")]
    return "\n".join(kept).strip() + "\n"


@dataclass
class Case:
    case: str
    run: str
    chapter: int
    kw: dict  # tham số của build_messages / to_package
    shown: dict[str, tuple[str, ...]]  # nút có tên đã biết đầu chương → tên đang biết
    locked: set[str]
    expected: set[tuple[str, str]]
    messages: dict[str, list[Message]]


def build_case(case: str, run: str, number: int, cache: dict) -> Case:
    cfg = load_config()
    f = cfg.limits.facts
    rules = FactRules(max_new=f.max_new_per_chapter, max_chars=f.text_max_chars, scene=1,
                      duplicate_overlap=f.duplicate_overlap, grounded_min=f.grounded_min,
                      related_overlap=f.related_overlap)
    if run == SAMPLE:
        sample = cache.setdefault(SAMPLE, read_sample())
        entities, open_edges = bench_c.gold_state(sample, number)
        node_id = next(n.id for n in bench_c.gold_package(sample, number).nodes if n.label == "Chapter")
        before = OverlayState(EmptyState(), [c.package for c in sample.chapters if c.number < number])
        text = next(c.text for c in sample.chapters if c.number == number)
        plan, extra_kw = None, {}
        protagonist = sample.protagonist
    else:
        if run not in cache:
            dump = json.loads((RESULTS / run / "truth_dump.json").read_text(encoding="utf-8"))
            cache[run] = (StoryPlan.model_validate(dump["plan"]),
                          {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()})
        plan, packs = cache[run]
        ctx = cfg.limits.context
        before = OverlayState(EmptyState(), [packs[n] for n in sorted(packs) if n < number])
        goals = chapter_goals(
            plan, number, before, standstill_chapters=ctx.standstill_chapters,
            unplanned_goal=ctx.unplanned_chapter_goal, idle_chapters=ctx.idle_chapters,
            milestone_lookahead=ctx.milestone_lookahead)
        ids = [n.id for p in (packs[k] for k in packs if k < number) for n in p.nodes]
        entities = entities_from_rows(before.nodes(ids))
        node_id = chapter_node(number).id
        entities.append(Entity(node_id, "Chapter", f"Chương {number}"))
        open_edges = [OpenEdge(r.id, r.type, r.source, r.target, r.props.get("known_as"))
                      for t in EDGE_TYPES for r in before.edges_at(t, number)]
        text = chapter_text(run, number)
        extra_kw = {"threads": goals.threads, "milestones": goals.pending_milestones}
        protagonist = before.protagonist_id()
    view = player_view_of(before, number)
    labels = {e.id: e.label for e in entities}
    shown = {e.id: (e.text, *e.aliases) for e in view.entries if labels.get(e.id) in NAMED_LABELS}
    locked = protected_ids(plan, view, "player_path") if plan is not None else set()
    skip = {protagonist, *(protected_ids(plan, view, "scene") if plan is not None else ())}
    found = {(e.source, e.props["known_as"]) for e in auto_reveals(
        text, chapter=number, chapter_id=node_id, names=before.named_nodes(), view=view, skip=skip,
        no_new_name=locked) if e.source in shown}
    if found != EXPECTED[case]:
        raise SystemExit(f"{case}: tên mới tính được {sorted(found)} khác khai trước {sorted(EXPECTED[case])}")
    kw = {"chapter": number, "chapter_id": node_id, "protagonist_id": protagonist,
          "chapter_text": text, "entities": entities, "open_edges": open_edges,
          "fact_rules": rules, **extra_kw}
    m10 = build_messages(**kw)
    assert m10[0].content.startswith(SYSTEM_PROMPT[:60]) and HEADER_10 in m10[1].content
    stripped = build_messages(**(kw | {"open_edges": [replace(o, known_as=None) for o in open_edges]}))
    m8 = [Message(role="system", content=stripped[0].content.replace(SYSTEM_PROMPT, PROMPT_8)),
          Message(role="user", content=stripped[1].content.replace(HEADER_10, HEADER_8))]
    assert PROMPT_8 in m8[0].content and "người chơi biết là" not in m8[1].content
    return Case(case, run, number, kw, shown, set(locked), EXPECTED[case],
                {"extract-8": m8, PROMPT_VERSION: m10})


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


def score(case: Case, output: ExtractOutput) -> dict:
    """Chấm một đầu ra qua `to_package` của nhánh (luật D-136, `locked` theo kế hoạch)."""
    package, rejected = to_package(output, commit_id="replay", locked=case.locked, **{
        k: v for k, v in case.kw.items() if k not in ("chapter_id", "milestones")})
    again = [e for e in output.edges if e.type == "REVEALED_TO_PLAYER" and e.source in case.shown]
    kept = {(e.source, e.props.get("known_as")) for e in package.edges
            if e.type == "REVEALED_TO_PLAYER" and e.source in case.shown}
    why = {d: w for d, w in rejected}
    second = [{"node": e.source, "known_as": e.known_as, "quote": e.quote,
               "accepted": (e.source, e.known_as) in kept,
               "reason": why.get(f"REVEALED_TO_PLAYER {e.source}→{e.target}")} for e in again]
    first = [[e.source, e.props.get("known_as")] for e in package.edges
             if e.type == "REVEALED_TO_PLAYER" and e.source not in case.shown
             and e.props.get("known_as") is not None]
    groups = Counter(reject_reason(w) for _, w in rejected)
    return {
        "second_reveals": second,
        "expected_hit": sorted([n, k] for n, k in kept & case.expected),
        "expected_missed": sorted([n, k] for n, k in case.expected - kept),
        "first_named_reveals": first,
        "edges": len(package.edges),
        "rejected_new_name": sum(v for k, v in groups.items() if k in NEW_NAME_REASONS),
        "rejected_other": sum(v for k, v in groups.items() if k not in NEW_NAME_REASONS),
        "rejected_groups": dict(groups),
    }


def git_info() -> dict:
    def run(*a):
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True,
                              check=False).stdout.strip()
    return {"commit": run("rev-parse", "HEAD"),
            "dirty": bool(run("status", "--porcelain", "--", "backend", "config"))}


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.08)
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--env-file", default="C:/Work/AI/WriTory/.env")
    ap.add_argument("--only", help="chỉ chạy các ca có tiền tố này, ví dụ P")
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
    estimate = sum(estimator.max_cost(model, m, ExtractOutput)
                   for c in cases for m in c.messages.values())
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
        for version, messages in case.messages.items():
            current.clear()
            current.update({"case": case.case, "run": case.run, "chapter": case.chapter,
                            "version": version})
            try:
                output, chat = await llm.chat_json(model, messages, ExtractOutput, extra=extra)
            except RuntimeError:
                skipped.append(dict(current))
                continue
            results.append({**current, **score(case, output),
                            "expected": sorted([n, k] for n, k in case.expected),
                            "cost_usd": round(chat.usage.cost_usd or 0.0, 6),
                            "prompt_tokens": chat.usage.prompt_tokens})
    if not args.dry_run:
        with (out / "results.jsonl").open("w", encoding="utf-8") as fh:
            for row in results:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        (out / "meta.json").write_text(json.dumps({
            "bench": "reveal-new-name-replay", "git": git_info(), "model": model, "extra": extra,
            "budget_usd": args.budget, "spent_usd": round(llm.spent, 6), "calls": llm.calls,
            "halted": llm.halted, "skipped": skipped, "versions": ["extract-8", PROMPT_VERSION],
            "cases": [list(c) for c in CASES],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(cases)} ca, {2 * len(cases)} lời gọi; ước tính tối đa (bound của CostEstimator) "
          f"{estimate:.4f} USD")
    print(f"{len(results)} lời gọi xong, bỏ qua {len(skipped)}, chi {llm.spent:.4f} USD"
          + (f" (dừng: {llm.halted})" if llm.halted else ""))
    for r in results:
        print(f"  {r['case']} ch{r['chapter']:>2} {r['run'][-24:]:<24} {r['version']:<10} "
              f"đúng {r['expected_hit']} thiếu {r['expected_missed']} | lần hai "
              f"{[(s['node'], s['known_as'], s['accepted']) for s in r['second_reveals']]} | "
              f"bỏ khác {r['rejected_other']}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
