"""Đo vai `overreach` của G6 (D-138) trên bộ câu có nhãn evals/redteam/g6_overreach.yaml, với model thật.

Chạy:
    cd backend && uv run python -m writory.safety.bench_g6 --budget 0.05 --out ../evals/results/<ngày>-g6
    cd backend && uv run python -m writory.safety.bench_g6 --dry-run

Mỗi câu đi qua đúng `safety.overreach.check_overreach` như bước soát cảnh của sản phẩm: hành động,
loại vượt luật, văn các cảnh trước của chương (`earlier_refs`), cảnh vừa viết (`scene` hay
`scene_ref`). `--budget`, `--dry-run` như `safety.bench_g5`.

Cần: `models.roles.overreach`, trần chi phí và OPENROUTER_API_KEY (key của chủ dự án dành cho bộ đo).

Chỉ số, theo thứ tự quan trọng:
- `granted_missed`: mong đợi `granted` mà ra `failed`/`cost`: trang chiều theo mà không bị bắt (G6 hở).
- `false_granted`: mong đợi `failed`/`cost` mà ra `granted`: cảnh hợp lệ bị viết lại, hết lượt thì
  bị chặn.
- `correct`/`total`: đúng cả ba giá trị. Nhầm giữa `failed` và `cost` không đổi gì ở sản phẩm.
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

from writory.config import REPO_ROOT, AppConfig, CostLimits, Settings, load_config
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
from writory.safety.overreach import PROMPT_VERSION, OverreachVerdict, check_overreach
from writory.safety.wrap import UserAuthored

CASES_PATH = REPO_ROOT / "evals" / "redteam" / "g6_overreach.yaml"
GRANTED = OverreachVerdict.GRANTED.value


@dataclass
class G6Result:
    total: int = 0
    correct: int = 0
    errors: int = 0
    granted_missed: list[str] = field(default_factory=list)
    false_granted: list[str] = field(default_factory=list)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    wrong: list[dict] = field(default_factory=list)
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


async def score(doc: Mapping[str, Any], *, llm: LLMClient, config: AppConfig) -> G6Result:
    result = G6Result()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for case in doc["cases"]:
        expected = case["expected"]
        try:
            got = (await check_overreach(**case_inputs(case, doc), llm=llm, config=config)
                   ).verdict.value
        except WritoryError as e:
            if e.code in BUDGET_CODES:
                result.stopped_by_budget = True
                break
            result.errors += 1
            got = f"error:{e.code.value}"
        result.total += 1
        confusion[expected][got] += 1
        if got == expected:
            result.correct += 1
            continue
        result.wrong.append({"id": case["id"], "expected": expected, "got": got})
        if got.startswith("error:"):
            continue
        if expected == GRANTED:
            result.granted_missed.append(case["id"])
        elif got == GRANTED:
            result.false_granted.append(case["id"])
    result.confusion = {k: dict(v) for k, v in confusion.items()}
    return result


def _oracle(doc: Mapping[str, Any]) -> Callable[[list[Message]], str]:
    """Trả đúng kết luận của câu có cảnh vừa viết trong lời gọi (phần sau "Cảnh vừa viết:")."""
    def answer(messages: list[Message]) -> str:
        current = messages[-1].content.split("Cảnh vừa viết:", 1)[1]
        for case in doc["cases"]:
            inputs = case_inputs(case, doc)
            if (str(UserAuthored(inputs["scene_text"], "scene_text")) in current
                    and len(inputs["earlier"]) == messages[-1].content.count("scene_text") - 1):
                return json.dumps({"verdict": case["expected"], "reason": "chạy khô"})
        raise AssertionError("chạy khô: không tìm thấy câu của lời gọi")
    return answer


def _print(result: G6Result, cost_text: str) -> None:
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    print(f"đúng {result.correct}/{result.total}; granted bị bỏ sót {len(result.granted_missed)}, "
          f"granted báo nhầm {len(result.false_granted)}, lỗi gọi {result.errors}; {cost_text}")
    if result.stopped_by_budget:
        print("DỪNG vì chạm trần chi phí: chưa đo hết bộ câu")


async def _main(args: argparse.Namespace) -> int:
    from writory.llm.cost import CostTracker, MeteredClient
    from writory.llm.openrouter import OpenRouterClient

    config = load_config()
    doc = load_set(args.cases)
    if args.dry_run:
        fake = DryRunClient(_oracle(doc), config=config)
        result = await score(doc, llm=MeteredClient(fake, unlimited_tracker()), config=config)
        _print(result, f"CHẠY KHÔ: {len(fake.calls)} lời gọi, ước tính ~{fake.estimated_usd:.4f} "
                       f"USD (token ra giả định {DRY_RUN_COMPLETION_TOKENS} mỗi lời gọi)")
        return 0
    cap = args.budget if args.budget is not None else config.limits.cost_usd.require("per_story")
    key = Settings().openrouter_api_key
    if key is None:
        raise SystemExit("thiếu OPENROUTER_API_KEY (key của chủ dự án cho bộ đo)")
    tracker = CostTracker(CostLimits(per_scene=cap, per_chapter=cap, per_story=cap))
    result = await score(doc, llm=MeteredClient(OpenRouterClient(key), tracker), config=config)
    _print(result, f"chi phí {tracker.story_usd:.4f} USD")
    if args.out:
        meta = {
            **run_meta([REPO_ROOT / "config" / "models.yaml",
                        REPO_ROOT / "config" / "limits.yaml"], args.cases),
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
    parser.add_argument("--dry-run", action="store_true",
                        help="không gọi model: đếm lời gọi và ước tính chi phí")
    return parser


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_main(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
