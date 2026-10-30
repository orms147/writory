"""Phát lại bộ trích `extract-8` và `extract-11` trên chương đã lưu, n=2 (khai trước ở `expectations.md`, D-139).

`extract-11` không gộp (D-139): script này cần code của nhánh ở commit `b1f5b2d` (schema `quotes`,
`graph.quote_parts_in_text`); chạy lại đúng như lần đo thì checkout commit đó.

Chạy từ `backend/` (một mình, không song song với lượt khác dùng cùng key):
    uv run python ../evals/results/2026-10-30-climax-milestone-2/replay.py --dry-run
    uv run python ../evals/results/2026-10-30-climax-milestone-2/replay.py --budget 0.10
Đo thêm trên ca đối chứng (bổ sung cuối `expectations.md`): lần 3 đến 6, ghi vào thư mục con:
    uv run python ../evals/results/2026-10-30-climax-milestone-2/replay.py --only 2- --first-rep 3 \
        --repeats 4 --budget 0.08 --out ../evals/results/2026-10-30-climax-milestone-2/control-n6

Thư mục kết quả: `--out` (mặc định cùng thư mục với file này). Ghi `results.jsonl` (mỗi lời gọi một
dòng: ca, bản đề, lần, mốc nhận, mốc model trả, lý do bị từ chối, token, chi phí), `calls.jsonl` và
`meta.json`. Không ghi chữ chương, không ghi key (G7). `--dry-run` dùng model giả, không đọc key, không
ghi file nào.

Khác D-129 (`../2026-10-30-extract-milestone-kind/replay.py`): `extract-8` gửi đúng schema JSON của main
(`extract8_schema.json`, mốc có `quote` một chuỗi), `extract-11` gửi schema của code nhánh này (`quotes`);
mỗi ca 4 lời gọi xen kẽ 8, 11, 8, 11.

Trần chi phí: dừng trước lời gọi tiếp theo nếu chi tiêu thật + 1,5 × lời gọi đắt nhất đã thấy (hoặc
ước tính tối đa của lời gọi đầu) vượt `--budget`; hết ngân sách thì các lời gọi còn lại ghi là không chạy.
Lời gọi hỏng đường truyền (không có `usage`, có thể vẫn bị tính tiền) được tính vào trần như một lời gọi
đắt nhất đã thấy.

Lần chạy đầu (`attempt1_calls.jsonl`) chết ở lời gọi thứ 8 vì `LLM_UNAVAILABLE: ReadTimeout` và mất đầu
ra của 7 lời gọi đã xong (kết quả chỉ ghi lúc cuối). Từ đó: mỗi dòng `results.jsonl` ghi ngay khi có; lỗi
tạm (`LLM_UNAVAILABLE`, `LLM_TIMEOUT`) thử lại một lần sau `RETRY_WAIT_S` giây; lỗi khác hay hỏng lần hai
thì ghi vào `failed` của meta và chạy tiếp. Không đổi ca, đề, schema hay cách chấm.
"""

import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from writory.config import REPO_ROOT, load_config
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage
from writory.graph.schema import EDGE_TYPES
from writory.guard.state import EmptyState, OverlayState
from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, Usage, role_extra
from writory.llm.cost import CostEstimator
from writory.pipeline import extract as extract_mod
from writory.pipeline.bench_run import config_sha256
from writory.pipeline.chapter import chapter_node
from writory.pipeline.extract import (
    SYSTEM_PROMPT,
    Entity,
    ExtractedEdge,
    ExtractOutput,
    FactRules,
    NewFact,
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
# (nhóm, lượt chạy, chương); thứ tự = ưu tiên (expectations.md). Cùng ca với D-129, bỏ tầng "lặp lại"
# riêng vì mọi ca đều lặp.
CASES: list[tuple[str, str, int]] = [
    ("1-muc-tieu", TU, 19), ("1-muc-tieu", KY, 24),
    ("2-doi-chung", KY, 16), ("2-doi-chung", TU, 11), ("2-doi-chung", KY, 10), ("2-doi-chung", TU, 5),
    ("3-ngu-canh", TU, 18), ("3-ngu-canh", KY, 22), ("3-ngu-canh", KY, 23), ("3-ngu-canh", TU, 17),
]
REPEATS = 2
RETRY_WAIT_S = 10
TRANSIENT = {ErrorCode.LLM_UNAVAILABLE, ErrorCode.LLM_TIMEOUT}
V8, V11 = "extract-8", "extract-11"


def order(first_rep: int, repeats: int) -> list[tuple[str, int]]:
    """Thứ tự lời gọi của một ca: xen kẽ 8, 11 ở mỗi lần (mặc định lần 1, 2 như khai trước)."""
    return [(v, r) for r in range(first_rep, first_rep + repeats) for v in (V8, V11)]


assert order(1, REPEATS) == [(V8, 1), (V11, 1), (V8, 2), (V11, 2)]

PROMPT_8 = (HERE / "extract8_system_prompt.txt").read_text(encoding="utf-8")
PROMPT_11 = (HERE / "extract11_system_prompt.txt").read_text(encoding="utf-8")
SCHEMA_8 = json.loads((HERE / "extract8_schema.json").read_text(encoding="utf-8"))
assert extract_mod.PROMPT_VERSION == V11, extract_mod.PROMPT_VERSION
assert PROMPT_11 == SYSTEM_PROMPT, "extract11_system_prompt.txt khác SYSTEM_PROMPT của code"
assert PROMPT_8 == (RESULTS / "2026-10-30-extract-milestone-kind" / "extract8_system_prompt.txt").read_text(
    encoding="utf-8")


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _extract8_schema() -> type[BaseModel]:
    """Lớp đầu ra của main `6698094` (`extract-8`): cùng tên lớp, cùng docstring (vào `description`
    của schema), mốc có `quote` một chuỗi. Kiểm bằng `extract8_schema.json` ngay dưới."""

    class ExtractedMilestone(_Out):
        """Mốc cốt truyện đã diễn ra trên trang (D-116): `id` dạng `m<số>` trong mục "Mốc cốt truyện chưa
        xảy ra", `quote` là câu nguyên văn cho thấy điều mốc mô tả đã xảy ra."""

        id: str
        quote: str

    class ExtractOutput(_Out):  # cùng tên lớp với sản phẩm: `name` của json_schema gửi model
        edges: list[ExtractedEdge]
        close: list[str]
        new_facts: list[NewFact]
        milestones: list[ExtractedMilestone]

    return ExtractOutput


Extract8Output = _extract8_schema()
assert Extract8Output.__name__ == ExtractOutput.__name__
assert Extract8Output.model_json_schema() == SCHEMA_8, "schema extract-8 dựng lại khác main"
SCHEMAS: dict[str, type[BaseModel]] = {V8: Extract8Output, V11: ExtractOutput}


def to_extract8_user(content: str) -> str:
    """Dòng mốc theo định dạng `extract-8` (không có cột loại)."""
    content = content.replace("(id | loại | khoảng chương | mô tả)", "(id | khoảng chương | mô tả)")
    return re.sub(r"(?m)^- (m\d+) \| (?:bước ngoặt|cao trào|kết) \| ", r"- \1 | ", content)


def chapter_text(run: str, number: int) -> str:
    """Chữ chương đã ghi, bỏ tiêu đề, dòng lựa chọn dẫn tới và phần lựa chọn cuối chương (như D-129)."""
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
    messages: dict[str, list[Message]]
    pending: list
    done: dict[int, int]
    text: str
    production_marks: list[int]


def build_case(group: str, run: str, number: int, cache: dict) -> Case:
    if run not in cache:
        dump = json.loads((RESULTS / run / "truth_dump.json").read_text(encoding="utf-8"))
        cache[run] = (StoryPlan.model_validate(dump["plan"]),
                      {int(k): ChangePackage.model_validate(v) for k, v in dump["packages"].items()})
    plan, packs = cache[run]
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
    m11 = build_messages(
        chapter=number, chapter_id=node.id, protagonist_id=before.protagonist_id(), chapter_text=text,
        entities=catalogue, open_edges=open_edges, threads=goals.threads, fact_rules=rules,
        milestones=goals.pending_milestones)
    assert m11[0].content.startswith(PROMPT_11[:60])
    m8 = [Message(role="system", content=m11[0].content.replace(PROMPT_11, PROMPT_8)),
          Message(role="user", content=to_extract8_user(m11[1].content))]
    assert m8[0].content != m11[0].content
    assert (m8[1].content != m11[1].content) == bool(goals.pending_milestones)
    marks = next((n.props.get("milestones", []) for n in packs[number].nodes if n.label == "Chapter"), [])
    return Case(group, run, number, {V8: m8, V11: m11}, list(goals.pending_milestones),
                dict(goals.milestones_done), text, list(marks))


class DryLLM(LLMClient):
    """Model giả cho `--dry-run`: đánh dấu mốc đầu tiên đang chờ bằng câu trích có thật của chương (một
    đoạn với schema extract-8, hai đoạn với extract-11), để chạy hết đường chấm mà không gọi mạng."""

    def __init__(self) -> None:
        self.case: Case | None = None

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        assert self.case is not None and response_schema is not None
        paras = [p for p in self.case.text.split("\n\n") if len(p.split()) >= 8]
        first, last = " ".join(paras[0].split()[:8]), " ".join(paras[-1].split()[:8])
        marks = []
        if self.case.pending:
            mid = f"m{self.case.pending[0].number}"
            marks = ([{"id": mid, "quote": first}] if response_schema is Extract8Output
                     else [{"id": mid, "quotes": [first, last]}])
        body = {"edges": [], "close": [], "new_facts": [], "milestones": marks}
        return ChatResult(text=json.dumps(body, ensure_ascii=False),
                          usage=Usage(prompt_tokens=1, completion_tokens=1, cost_usd=0.002),
                          finish_reason="stop")

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
        yield  # pragma: no cover


class CappedLLM(LLMClient):
    """Gọi client thật, ghi chi tiêu thật, dừng khi chạm trần (xem docstring đầu file)."""

    def __init__(self, inner: LLMClient, estimator: CostEstimator, budget: float, record) -> None:
        self._inner, self._est, self._budget, self._record = inner, estimator, budget, record
        self.spent = 0.0
        self.max_call = 0.0
        self.halted: str | None = None
        self.calls = 0
        self.unknown_cost_calls = 0  # lời gọi hỏng đường truyền: không biết chi phí

    async def chat(self, model, messages, *, response_schema=None, extra=None) -> ChatResult:
        bound = self._est.bound(extra)
        reserve = 1.5 * self.max_call if self.max_call else self._est.max_cost(
            model, messages, response_schema)
        unknown = self.unknown_cost_calls * self.max_call
        if self.spent + unknown + reserve > self._budget:
            self.halted = (f"chi {self.spent:.4f} + không rõ {unknown:.4f} + giữ chỗ {reserve:.4f} "
                           f"> trần {self._budget:.2f}")
            raise RuntimeError(self.halted)
        try:
            result = await self._inner.chat(model, messages, response_schema=response_schema,
                                            extra=bound)
        except WritoryError:
            self.unknown_cost_calls += 1
            raise
        cost = result.usage.cost_usd or 0.0
        self.spent += cost
        self.max_call = max(self.max_call, cost)
        self.calls += 1
        self._record({"seq": self.calls, "cost_usd": cost, "spent_usd": round(self.spent, 6),
                      "prompt_tokens": result.usage.prompt_tokens,
                      "completion_tokens": result.usage.completion_tokens,
                      "cached_tokens": result.usage.cached_tokens,
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


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=0.10)
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--env-file", default="C:/Work/AI/WriTory/.env")
    ap.add_argument("--only", help="chỉ chạy các nhóm có tiền tố này, ví dụ 1-")
    ap.add_argument("--first-rep", type=int, default=1, help="số của lần đầu (đo thêm: 3)")
    ap.add_argument("--repeats", type=int, default=REPEATS, help="số lần mỗi bản đề mỗi ca")
    args = ap.parse_args()
    calls_order = order(args.first_rep, args.repeats)
    out = Path(args.out)
    if not args.dry_run and (out / "results.jsonl").exists():
        print("results.jsonl đã có: không ghi đè; chọn --out khác")
        return 1

    cache: dict = {}
    cases = [build_case(*c, cache) for c in CASES if not args.only or c[0].startswith(args.only)]
    cfg = load_config()
    model = cfg.models.roles.require("extract")
    extra = role_extra(cfg.models, "extract")
    estimator = CostEstimator.from_config(cfg)
    if not args.dry_run:
        out.mkdir(parents=True, exist_ok=True)
    calls_log = (out / "calls.jsonl").open("w", encoding="utf-8") if not args.dry_run else None
    results_log = (out / "results.jsonl").open("w", encoding="utf-8") if not args.dry_run else None
    current: dict = {}

    def record(row: dict) -> None:
        if calls_log:
            calls_log.write(json.dumps(current | row, ensure_ascii=False) + "\n")
            calls_log.flush()

    dry = DryLLM() if args.dry_run else None
    if dry is not None:
        inner: LLMClient = dry
    else:
        from writory.llm.openrouter import OpenRouterClient
        keys = load_keys(Path(args.env_file), ["openrouter"])
        assert keys.openrouter_api_key is not None
        inner = OpenRouterClient(keys.openrouter_api_key, deadline_s=300)
    llm = CappedLLM(inner, estimator, args.budget, record)

    async def call(messages, schema):
        for attempt in (1, 2):
            try:
                return await llm.chat_json(model, messages, schema, extra=extra)
            except WritoryError as e:
                failed.append(dict(current) | {"attempt": attempt, "code": e.code.value})
                if e.code not in TRANSIENT or attempt == 2:
                    raise
                await asyncio.sleep(RETRY_WAIT_S)
        raise AssertionError("unreachable")

    results, skipped, failed = [], [], []
    for case in cases:
        if dry is not None:
            dry.case = case
        for version, rep in calls_order:
            current.clear()
            current.update({"run": case.run, "chapter": case.chapter, "version": version, "rep": rep,
                            "group": case.group})
            try:
                raw, chat = await call(case.messages[version], SCHEMAS[version])
            except RuntimeError:
                skipped.append(dict(current))
                continue
            except WritoryError:
                continue
            output = ExtractOutput.model_validate(raw.model_dump())  # `quote` cũ thành một đoạn
            marks, rejected = accept_milestones(output, case.pending, case.done, case.text)
            results.append({
                "group": case.group, "run": case.run, "chapter": case.chapter, "version": version,
                "rep": rep, "pending": [m.number for m in case.pending], "done": case.done,
                "production_marks": case.production_marks,
                "accepted": [[m.number, list(m.parts)] for m in marks],
                "model_output": [[m.id, m.quotes] for m in output.milestones],
                "rejected": [[d, w] for d, w in rejected if str(d).startswith("mốc")],
                "cost_usd": round(chat.usage.cost_usd or 0.0, 6),
                "prompt_tokens": chat.usage.prompt_tokens,
                "cached_tokens": chat.usage.cached_tokens})
            if results_log:
                results_log.write(json.dumps(results[-1], ensure_ascii=False) + "\n")
                results_log.flush()
    if not args.dry_run:
        cfg_hash = config_sha256(REPO_ROOT / "config")
        (out / "meta.json").write_text(json.dumps({
            "bench": "climax-milestone-replay", "git": git_info(), "model": model, "extra": extra,
            "config_sha256": cfg_hash["combined"], "budget_usd": args.budget,
            "spent_usd": round(llm.spent, 6), "calls": llm.calls, "halted": llm.halted,
            "unknown_cost_calls": llm.unknown_cost_calls, "failed": failed,
            "skipped": skipped, "versions": [V8, V11], "repeats": args.repeats,
            "first_rep": args.first_rep, "only": args.only,
            "prompt_sha256": {V8: _sha(PROMPT_8), V11: _sha(PROMPT_11)},
            "cases": [list(c) for c in CASES],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(results)} lời gọi xong, bỏ qua {len(skipped)}, hỏng {len(failed)} lần, "
          f"chi {llm.spent:.4f} USD"
          + (f" (dừng: {llm.halted})" if llm.halted else "") + (" [dry-run]" if args.dry_run else ""))
    for r in results:
        g3 = sum("(G3)" in w for _, w in r["rejected"])
        print(f"  ch{r['chapter']:>2} {r['run'][-18:]:<18} {r['version']:<10} lần {r['rep']}: "
              f"nhận {[a[0] for a in r['accepted']]} (đoạn {[len(a[1]) for a in r['accepted']]}), "
              f"model trả {[m[0] for m in r['model_output']]}, G3 bỏ {g3} "
              f"(gốc {r['production_marks']}; thấy {r['pending']})")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
