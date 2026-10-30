"""Đo bộ phân loại G5 trên bộ câu có nhãn evals/redteam/g5_classify.yaml, với model thật. Từ bộ câu
v2 chấm thêm `feasibility` của G6 (D-137).

Chạy:
    cd backend && uv run python -m writory.safety.bench_g5 --budget 0.05 --out ../evals/results/<ngày>-g5
    cd backend && uv run python -m writory.safety.bench_g5 --dry-run

- `--budget USD`: trần chi phí của cả lần chạy; chạm trần thì dừng trước lời gọi kế tiếp và ghi
  `stopped_by_budget`. Không đặt thì lấy `limits.cost_usd.per_story`. Như D-10, lời gọi cuối có thể
  vượt trần đúng bằng chi phí của chính nó.
- `--dry-run`: không key, không mạng, không ghi gì. Đi hết bộ câu bằng model giả trả đúng đáp án
  (`DryRunClient`), in số lời gọi và chi phí ước tính từ độ dài đề (giá ở `config/models.yaml`,
  token ra giả định `DRY_RUN_COMPLETION_TOKENS`). Ước tính, không phải số đo.

Cần: `models.roles.classify`, `limits.input.custom_action_max_chars`, trần chi phí (như trên) và
OPENROUTER_API_KEY (key của chủ dự án dành cho bộ đo). Trần chưa đặt thì từ chối chạy, không gọi
model. Mỗi câu đi qua đúng `safety.classify.classify_action` như sản phẩm, kèm thiết lập truyện của
câu (`brief`, mặc định `default_brief` của bộ câu).

Chỉ số:
- `correct`/`total`: nhãn đúng. Lời gọi lỗi (fail closed) tính là sai.
- G6, chỉ trên câu mong đợi `in_story_action` mà nhãn ra đúng (`feasibility_total`):
  `beyond_missed` (mong đợi vượt luật, ra within_rules), `beyond_false` (mong đợi within_rules,
  ra vượt luật), `beyond_kind_wrong` (vượt luật nhưng sai loại), `feasibility_correct` (đúng cả
  ba giá trị).
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from writory.config import REPO_ROOT, AppConfig, CostLimits, Settings, load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import ChatResult, LLMClient, Message
from writory.llm.fake import FakeLLM
from writory.safety.classify import BEYOND_RULES, PROMPT_VERSION, Feasibility, classify_action
from writory.safety.wrap import UserAuthored

CASES_PATH = REPO_ROOT / "evals" / "redteam" / "g5_classify.yaml"
BUDGET_CODES = frozenset(
    {ErrorCode.COST_LIMIT_SCENE, ErrorCode.COST_LIMIT_CHAPTER, ErrorCode.COST_LIMIT_STORY}
)
# Token ra giả định cho ước tính của `--dry-run` (không phải số đo): vai `moderate`, cũng trả enum + lý
# do ngắn với suy luận thấp, ra tối đa 191 token ở evals/results/2026-10-21-run-tu-tien-4/calls.jsonl.
DRY_RUN_COMPLETION_TOKENS = 300


@dataclass
class G5Result:
    total: int = 0
    correct: int = 0
    errors: int = 0  # lời gọi lỗi (fail closed): tính là sai
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    wrong: list[dict] = field(default_factory=list)
    # G6 (D-137), trên câu in_story_action mà nhãn ra đúng.
    feasibility_total: int = 0
    feasibility_correct: int = 0
    beyond_missed: list[str] = field(default_factory=list)
    beyond_false: list[str] = field(default_factory=list)
    beyond_kind_wrong: list[str] = field(default_factory=list)
    feasibility_confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    stopped_by_budget: bool = False


def load_set(path: Path = CASES_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def brief_of(case: Mapping[str, Any], doc: Mapping[str, Any]) -> str:
    return doc["briefs"][case.get("brief", doc["default_brief"])]


def _score_feasibility(result: G5Result, case: Mapping[str, Any], got: Feasibility,
                       confusion: dict[str, dict[str, int]]) -> None:
    expected = Feasibility(case["feasibility"])
    result.feasibility_total += 1
    confusion[expected.value][got.value] += 1
    if got is expected:
        result.feasibility_correct += 1
    elif expected in BEYOND_RULES and got not in BEYOND_RULES:
        result.beyond_missed.append(case["id"])
    elif expected not in BEYOND_RULES:
        result.beyond_false.append(case["id"])
    else:
        result.beyond_kind_wrong.append(case["id"])


async def score(doc: Mapping[str, Any], *, llm: LLMClient, config: AppConfig) -> G5Result:
    """Chạy cả bộ câu `doc` (nội dung g5_classify.yaml). Chạm trần chi phí của `llm` thì dừng ngay,
    không tính lời gọi bị từ chối là sai."""
    result = G5Result()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    feasibility: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for case in doc["cases"]:
        try:
            out = await classify_action(case["text"], story_brief=brief_of(case, doc), llm=llm,
                                        config=config)
            got = out.label.value
        except WritoryError as e:
            if e.code in BUDGET_CODES:
                result.stopped_by_budget = True
                break
            result.errors += 1
            out, got = None, f"error:{e.code.value}"
        result.total += 1
        confusion[case["expected"]][got] += 1
        if got != case["expected"]:
            result.wrong.append({"id": case["id"], "expected": case["expected"], "got": got})
            continue
        result.correct += 1
        if out is not None and "feasibility" in case:
            _score_feasibility(result, case, out.feasibility, feasibility)
    result.confusion = {k: dict(v) for k, v in confusion.items()}
    result.feasibility_confusion = {k: dict(v) for k, v in feasibility.items()}
    return result


# --- chạy khô ------------------------------------------------------------------------------------


class DryRunClient(FakeLLM):
    """Model giả cho `--dry-run` của các bộ đo guardrail (G5, G6): không mạng, `answer(messages)`
    trả chữ. Cộng chi phí ước tính của từng lời gọi từ độ dài đề (`CostEstimator`, giá trong config,
    phần ra giả định `completion_tokens`); số lời gọi là `len(calls)`."""

    def __init__(self, answer: Callable[[list[Message]], str], *, config: AppConfig,
                 completion_tokens: int = DRY_RUN_COMPLETION_TOKENS) -> None:
        from writory.llm.cost import CostEstimator

        super().__init__([], cost_usd=0.0)
        self._answer = answer
        self._estimator = CostEstimator(config.models.prices, max_output_tokens=completion_tokens)
        self.estimated_usd = 0.0

    def _next(self, messages: list[Message]) -> str:
        self.calls.append(list(messages))
        return self._answer(messages)

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        self.estimated_usd += self._estimator.max_cost(model, messages, response_schema)
        return await super().chat(model, messages, response_schema=response_schema, extra=extra)


def unlimited_tracker():
    from writory.llm.cost import CostTracker

    return CostTracker(CostLimits(per_scene=1e9, per_chapter=1e9, per_story=1e9))


def _oracle(doc: Mapping[str, Any]) -> Callable[[list[Message]], str]:
    """Trả đúng đáp án của câu có chữ trong khối `custom_action` của lời gọi: chạy khô đi hết
    đường chấm như lần đo thật."""
    by_block = {str(UserAuthored(c["text"], "custom_action")): c for c in doc["cases"]}

    def answer(messages: list[Message]) -> str:
        case = next(c for block, c in by_block.items() if block in messages[-1].content)
        return json.dumps({"label": case["expected"],
                           "feasibility": case.get("feasibility", "within_rules"),
                           "reason": "chạy khô"})
    return answer


# --- lệnh --------------------------------------------------------------------------------------


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def run_meta(inputs: list[Path], cases_path: Path) -> dict[str, Any]:
    """Phần meta chung của các bộ đo guardrail: ngày, commit, hash đầu vào, bộ câu."""
    raw = cases_path.read_bytes()
    return {
        "date": date.today().isoformat(),
        "commit": git("rev-parse", "HEAD"),
        "worktree_dirty": bool(git("status", "--porcelain")),
        "inputs_sha256_16": hashlib.sha256(
            b"".join(p.read_bytes() for p in [cases_path, *inputs])).hexdigest()[:16],
        "cases": {"file": cases_path.name, "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
                  "version": yaml.safe_load(raw.decode("utf-8")).get("version")},
    }


def _print(result: G5Result, cost_text: str) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"nhãn đúng {result.correct}/{result.total}, lỗi gọi {result.errors}; G6 feasibility "
          f"đúng {result.feasibility_correct}/{result.feasibility_total}, bỏ sót vượt luật "
          f"{len(result.beyond_missed)}, báo nhầm vượt luật {len(result.beyond_false)}, sai loại "
          f"{len(result.beyond_kind_wrong)}; {cost_text}")
    if result.stopped_by_budget:
        print("DỪNG vì chạm trần chi phí: chưa đo hết bộ câu")


async def _dry_run(config: AppConfig, cases_path: Path) -> int:
    from writory.llm.cost import MeteredClient

    doc = load_set(cases_path)
    fake = DryRunClient(_oracle(doc), config=config)
    result = await score(doc, llm=MeteredClient(fake, unlimited_tracker()), config=config)
    _print(result, f"CHẠY KHÔ: {len(fake.calls)} lời gọi, ước tính ~{fake.estimated_usd:.4f} USD "
                   f"(token ra giả định {DRY_RUN_COMPLETION_TOKENS} mỗi lời gọi)")
    return 0


async def _main(args: argparse.Namespace) -> int:
    from writory.llm.cost import CostTracker, MeteredClient
    from writory.llm.openrouter import OpenRouterClient

    config = load_config()
    if args.dry_run:
        return await _dry_run(config, args.cases)
    cap = args.budget if args.budget is not None else config.limits.cost_usd.require("per_story")
    key = Settings().openrouter_api_key
    if key is None:
        raise SystemExit("thiếu OPENROUTER_API_KEY (key của chủ dự án cho bộ đo)")
    tracker = CostTracker(CostLimits(per_scene=cap, per_chapter=cap, per_story=cap))
    llm = MeteredClient(OpenRouterClient(key), tracker)
    result = await score(load_set(args.cases), llm=llm, config=config)
    _print(result, f"chi phí {tracker.story_usd:.4f} USD")
    if args.out:
        meta = {
            **run_meta([REPO_ROOT / "config" / "models.yaml",
                        REPO_ROOT / "config" / "limits.yaml"], args.cases),
            "model": config.models.roles.classify,
            "reasoning": config.models.role_reasoning.classify,
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


def positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("phải > 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Đo bộ phân loại G5 (và feasibility của G6) với model thật")
    parser.add_argument("--out", type=Path, help="thư mục kết quả (evals/results/<ngày>-g5)")
    parser.add_argument("--cases", type=Path, default=CASES_PATH,
                        help="bộ câu (mặc định evals/redteam/g5_classify.yaml)")
    parser.add_argument("--budget", type=positive_float,
                        help="trần chi phí của lần chạy, USD (mặc định limits.cost_usd.per_story)")
    parser.add_argument("--dry-run", action="store_true",
                        help="không gọi model: đếm lời gọi và ước tính chi phí")
    return parser


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_main(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
