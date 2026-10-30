"""Đo vai `overreach` của G6 (D-138) trên bộ câu có nhãn evals/redteam/g6_overreach.yaml, với model thật.

Chạy:
    cd backend && uv run python -m writory.safety.bench_g6 --budget 0.05 --out ../evals/results/<ngày>-g6
    cd backend && uv run python -m writory.safety.bench_g6 --dry-run

Mỗi câu đi qua đúng `safety.overreach.check_overreach` như bước soát cảnh của sản phẩm: hành động,
loại vượt luật, văn các cảnh trước của chương (`earlier_refs`), cảnh vừa viết (`scene` hay
`scene_ref`). `--budget`, `--dry-run` như `safety.bench_g5`.

Cần: `models.roles.overreach`, trần chi phí và OPENROUTER_API_KEY (key của chủ dự án dành cho bộ đo).

Chỉ số, cho cả bộ câu và riêng từng bộ (`by_set`: `original` là các câu không ghi `set`, `hard` là
bộ khó, bộ quyết định ở luật đạt). Tính theo quyết định của sản phẩm (`overreach.needs_rewrite`,
D-138: vượt luật thế giới chỉ `failed` qua; vượt sức nhân vật thì `failed` hay `cost` qua):
- `rewrite_missed`: trang phải viết lại mà kết luận của người chấm cho qua (G6 hở).
- `false_rewrite`: trang được qua mà kết luận của người chấm bắt viết lại (cảnh hợp lệ bị viết lại,
  hết lượt thì bị chặn).
- `correct`/`total`: đúng cả ba giá trị. Nhầm mà không đổi quyết định (`failed` với `cost` ở vượt sức
  nhân vật, `cost` với `granted` ở vượt luật thế giới) chỉ ghi ở `wrong`.
Lời gọi lỗi (fail closed) tính là sai, không tính vào hai danh sách trên.
"""

import argparse
import asyncio
import json
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from writory.config import (
    REPO_CONFIG_DIR,
    REPO_ROOT,
    AppConfig,
    CostLimits,
    config_sources,
    load_config,
)
from writory.errors import WritoryError
from writory.llm.base import LLMClient, Message
from writory.safety.bench_g5 import (
    BUDGET_CODES,
    DRY_RUN_COMPLETION_TOKENS,
    DryRunClient,
    positive_float,
    run_meta,
    unlimited_tracker,
)
from writory.safety.classify import Feasibility
from writory.safety.overreach import (
    PROMPT_VERSION,
    OverreachVerdict,
    check_overreach,
    needs_rewrite,
)
from writory.safety.wrap import UserAuthored

CASES_PATH = REPO_ROOT / "evals" / "redteam" / "g6_overreach.yaml"
SETS = ("original", "hard")


@dataclass
class G6Summary:
    total: int = 0
    correct: int = 0
    errors: int = 0
    rewrite_missed: list[str] = field(default_factory=list)
    false_rewrite: list[str] = field(default_factory=list)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    wrong: list[dict] = field(default_factory=list)


@dataclass
class G6Result(G6Summary):
    """Chỉ số của cả bộ câu, cộng `by_set` (cùng các chỉ số, riêng từng bộ) và từng câu (`rows`)."""

    by_set: dict[str, dict[str, Any]] = field(default_factory=dict)
    rows: list[dict[str, Any]] = field(default_factory=list)
    stopped_by_budget: bool = False


def load_set(path: Path = CASES_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def case_inputs(case: Mapping[str, Any], doc: Mapping[str, Any]) -> dict[str, Any]:
    """Đầu vào của `check_overreach` cho một câu, với tham chiếu đã giải."""
    scenes = doc.get("scenes") or {}
    return {
        "action": doc["actions"][case["action"]],
        "feasibility": Feasibility(case["feasibility"]),
        "earlier": [scenes[ref] for ref in case.get("earlier_refs", [])],
        "scene_text": case["scene"] if "scene" in case else scenes[case["scene_ref"]],
    }


def summarize(rows: list[dict[str, Any]]) -> G6Summary:
    out = G6Summary()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        out.total += 1
        expected, got = row["expected"], row["got"]
        confusion[expected][got] += 1
        if got == expected:
            out.correct += 1
            continue
        out.wrong.append({"id": row["id"], "expected": expected, "got": got})
        if got.startswith("error:"):
            out.errors += 1
            continue
        kind = Feasibility(row["feasibility"])
        should = needs_rewrite(kind, OverreachVerdict(expected))
        does = needs_rewrite(kind, OverreachVerdict(got))
        if should and not does:
            out.rewrite_missed.append(row["id"])
        elif does and not should:
            out.false_rewrite.append(row["id"])
    out.confusion = {k: dict(v) for k, v in confusion.items()}
    return out


async def score(doc: Mapping[str, Any], *, llm: LLMClient, config: AppConfig) -> G6Result:
    rows: list[dict[str, Any]] = []
    stopped = False
    for case in doc["cases"]:
        try:
            got = (await check_overreach(**case_inputs(case, doc), llm=llm, config=config)
                   ).verdict.value
        except WritoryError as e:
            if e.code in BUDGET_CODES:
                stopped = True
                break
            got = f"error:{e.code.value}"
        rows.append({"id": case["id"], "set": case.get("set", "original"),
                     "feasibility": case["feasibility"], "expected": case["expected"],
                     "got": got})
    by_set = {name: asdict(summarize([r for r in rows if r["set"] == name])) for name in SETS}
    return G6Result(**asdict(summarize(rows)), by_set=by_set, rows=rows, stopped_by_budget=stopped)


def _oracle(doc: Mapping[str, Any]) -> Callable[[list[Message]], str]:
    """Trả đúng kết luận của câu có cùng cảnh vừa viết (phần sau "Cảnh vừa viết:") và cùng các cảnh
    trước với lời gọi."""
    def key(inputs: Mapping[str, Any]) -> tuple[str, ...]:
        return (str(UserAuthored(inputs["scene_text"], "scene_text")),
                *(str(UserAuthored(t, "scene_text")) for t in inputs["earlier"]))

    def answer(messages: list[Message]) -> str:
        before, current = messages[-1].content.split("Cảnh vừa viết:", 1)
        found = [c for c in doc["cases"]
                 if (k := key(case_inputs(c, doc)))[0] in current
                 and all(e in before for e in k[1:])
                 and before.count('source="scene_text"') == len(k) - 1]
        [case] = found
        return json.dumps({"verdict": case["expected"], "reason": "chạy khô"})
    return answer


def _line(name: str, m: Mapping[str, Any]) -> str:
    return (f"{name}: đúng {m['correct']}/{m['total']}; bỏ sót (phải viết lại mà cho qua) "
            f"{len(m['rewrite_missed'])}, báo nhầm (được qua mà bắt viết lại) "
            f"{len(m['false_rewrite'])}, lỗi gọi {m['errors']}")


def _print(result: G6Result, cost_text: str) -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    for name in SETS:
        print(_line(name, result.by_set[name]))
    print(f"{_line('cả bộ', asdict(result))}; {cost_text}")
    if result.stopped_by_budget:
        print("DỪNG vì chạm trần chi phí: chưa đo hết bộ câu")


async def _main(args: argparse.Namespace) -> int:
    from writory.llm.cost import CostTracker, MeteredClient
    from writory.llm.provider import bench_llm

    config = load_config(args.config_dir)
    doc = load_set(args.cases)
    if args.dry_run:
        fake = DryRunClient(_oracle(doc), config=config)
        result = await score(doc, llm=MeteredClient(fake, unlimited_tracker()), config=config)
        _print(result, f"CHẠY KHÔ: {len(fake.calls)} lời gọi, ước tính ~{fake.estimated_usd:.4f} "
                       f"USD (token ra giả định {DRY_RUN_COMPLETION_TOKENS} mỗi lời gọi)")
        return 0
    cap = args.budget if args.budget is not None else config.limits.cost_usd.require("per_story")
    tracker = CostTracker(CostLimits(per_scene=cap, per_chapter=cap, per_story=cap))
    llm = bench_llm(config, args.env_file, models=[config.models.roles.overreach])
    result = await score(doc, llm=MeteredClient(llm, tracker), config=config)
    _print(result, f"chi phí {tracker.story_usd:.4f} USD")
    if args.out:
        meta = {
            **run_meta([*config_sources(args.config_dir, "models.yaml"),
                        *config_sources(args.config_dir, "limits.yaml")], args.cases,
                       config=config, models=[config.models.roles.overreach]),
            "model": config.models.roles.overreach,
            "reasoning": config.models.role_reasoning.overreach,
            "prompt": PROMPT_VERSION,
            "budget_usd": cap,
            "cost_usd": tracker.story_usd,
        }
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "result.json").write_text(
            json.dumps({"meta": meta, **asdict(result)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Đo vai overreach của G6 với model thật")
    parser.add_argument("--out", type=Path, help="thư mục kết quả (evals/results/<ngày>-g6)")
    parser.add_argument("--cases", type=Path, default=CASES_PATH,
                        help="bộ câu (mặc định evals/redteam/g6_overreach.yaml)")
    parser.add_argument("--budget", type=positive_float,
                        help="trần chi phí của lần chạy, USD (mặc định limits.cost_usd.per_story)")
    parser.add_argument("--config-dir", type=Path, default=REPO_CONFIG_DIR,
                        help="thư mục config (D-140: evals/config/meta dùng model Meta); mặc định config/")
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env",
                        help="file .env chứa key của chủ dự án (OPENROUTER_API_KEY hay META_API_KEY)")
    parser.add_argument("--dry-run", action="store_true",
                        help="không gọi model: đếm lời gọi và ước tính chi phí")
    return parser


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_main(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
