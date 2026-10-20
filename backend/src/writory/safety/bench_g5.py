"""Đo bộ phân loại G5 trên bộ câu có nhãn evals/redteam/g5_classify.yaml, với model thật.

Chạy (CHƯA chạy lần nào; cần model rẻ từ bài D):
    cd backend && uv run python -m writory.safety.bench_g5 --out ../evals/results/<ngày>-g5

Cần: `models.roles.classify`, `limits.input.custom_action_max_chars` và
`limits.cost_usd.per_story` trong config (trần chi phí của cả lần đo), cùng OPENROUTER_API_KEY
(key của chủ dự án dành cho bộ đo). Trần chưa đặt thì từ chối chạy, không gọi model.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

from writory.config import REPO_ROOT, AppConfig, CostLimits, Settings, load_config
from writory.errors import WritoryError
from writory.llm.base import LLMClient
from writory.safety.classify import classify_action

CASES_PATH = REPO_ROOT / "evals" / "redteam" / "g5_classify.yaml"


@dataclass
class G5Result:
    total: int = 0
    correct: int = 0
    errors: int = 0  # lời gọi lỗi (fail closed): tính là sai
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    wrong: list[dict] = field(default_factory=list)


async def score(cases: list[dict], *, llm: LLMClient, config: AppConfig) -> G5Result:
    result = G5Result()
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for case in cases:
        result.total += 1
        try:
            got = (await classify_action(case["text"], llm=llm, config=config)).label.value
        except WritoryError as e:
            result.errors += 1
            got = f"error:{e.code.value}"
        confusion[case["expected"]][got] += 1
        if got == case["expected"]:
            result.correct += 1
        else:
            result.wrong.append({"id": case["id"], "expected": case["expected"], "got": got})
    result.confusion = {k: dict(v) for k, v in confusion.items()}
    return result


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


async def _main(out: Path | None) -> int:
    from writory.llm.cost import CostTracker, MeteredClient
    from writory.llm.openrouter import OpenRouterClient

    config = load_config()
    cap = config.limits.cost_usd.require("per_story")
    key = Settings().openrouter_api_key
    if key is None:
        raise SystemExit("thiếu OPENROUTER_API_KEY (key của chủ dự án cho bộ đo)")
    tracker = CostTracker(CostLimits(per_scene=cap, per_chapter=cap, per_story=cap))
    llm = MeteredClient(OpenRouterClient(key), tracker)
    cases = yaml.safe_load(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    result = await score(cases, llm=llm, config=config)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"đúng {result.correct}/{result.total}, lỗi gọi {result.errors}, "
          f"chi phí {tracker.story_usd:.4f} USD")
    if out:
        inputs = [CASES_PATH, REPO_ROOT / "config" / "models.yaml",
                  REPO_ROOT / "config" / "limits.yaml"]
        meta = {
            "date": date.today().isoformat(),
            "commit": _git("rev-parse", "HEAD"),
            "worktree_dirty": bool(_git("status", "--porcelain")),
            "inputs_sha256_16": hashlib.sha256(
                b"".join(p.read_bytes() for p in inputs)).hexdigest()[:16],
            "model": config.models.roles.classify,
            "cost_usd": tracker.story_usd,
        }
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(
            json.dumps({"meta": meta, **asdict(result)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Đo bộ phân loại G5 với model thật")
    parser.add_argument("--out", type=Path, help="thư mục kết quả (evals/results/<ngày>-g5)")
    args = parser.parse_args(argv)
    return asyncio.run(_main(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
