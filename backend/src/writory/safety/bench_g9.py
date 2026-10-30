"""Đo bộ kiểm duyệt G9 (D-57) trên bộ câu có nhãn, với model thật.

Chạy:
    cd backend && uv run python -m writory.safety.bench_g9 --out ../evals/results/<ngày>-g9
    ... --cases ../evals/redteam/g9_moderation_holdout.yaml --repeat 3 --budget 0.05 --out ...

- `--cases`: bộ câu, mặc định evals/redteam/g9_moderation.yaml. Bộ giữ riêng (D-71) là
  evals/redteam/g9_moderation_holdout.yaml; tên file và hash của bộ câu được ghi vào result.json.
- `--repeat N`: chạy mỗi câu N lần (mỗi lượt đi hết bộ câu một lần), báo câu nào ra kết luận khác
  nhau giữa các lượt (`unstable`) và tỉ lệ ổn định (`stable_rate`).
- `--budget USD`: trần chi phí của cả lần chạy; chạm trần thì dừng trước lời gọi kế tiếp và ghi
  `stopped_by_budget`. Không đặt thì lấy `limits.cost_usd.per_story`. Như D-10, lời gọi cuối có
  thể vượt trần đúng bằng chi phí của chính nó.

Cần: `models.roles.moderate`, trần chi phí (như trên) và OPENROUTER_API_KEY (key của chủ dự án
dành cho bộ đo). Trần chưa đặt thì từ chối chạy, không gọi model. Mỗi câu đi qua đúng
`safety.moderate.moderate` như sản phẩm (D-79): câu đầu vào tới `moderation.input_votes` lời gọi
mỗi lượt (dừng ở lần báo chặn), câu cảnh và bộ lựa chọn một lời gọi. `result.json` ghi `prompt` và
`input_votes`.

Chỉ số chính, theo thứ tự quan trọng:
- `missed`: câu mong đợi bị chặn (hard_blocked, blocked, over_darkness) mà ra `allow`.
- `false_blocks`: câu mong đợi `allow` (truyện u tối hợp lệ) mà bị chặn.
- `wrong_kind`: bị chặn nhưng sai mức (ví dụ mong đợi blocked, ra hard_blocked).
Lời gọi lỗi (fail closed) tính là sai, không tính vào missed hay false_blocks. Khi chạy lặp, ba danh
sách này liệt kê câu sai ở ít nhất một lượt; `total` và `correct` đếm theo lượt.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

from writory.config import (
    REPO_CONFIG_DIR,
    REPO_ROOT,
    AppConfig,
    CostLimits,
    config_sources,
    load_config,
)
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import LLMClient
from writory.llm.provider import llm_identity
from writory.safety.moderate import PROMPT_VERSION, Source, Verdict, moderate

CASES_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation.yaml"
_BUDGET_CODES = frozenset(
    {ErrorCode.COST_LIMIT_SCENE, ErrorCode.COST_LIMIT_CHAPTER, ErrorCode.COST_LIMIT_STORY}
)


@dataclass
class G9Result:
    total: int = 0
    correct: int = 0
    errors: int = 0
    missed: list[str] = field(default_factory=list)
    false_blocks: list[str] = field(default_factory=list)
    wrong_kind: list[str] = field(default_factory=list)
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)
    wrong: list[dict] = field(default_factory=list)
    repeat: int = 1
    # Câu có kết luận khác nhau giữa các lượt: {"id", "verdicts": {kết luận: số lượt}}.
    unstable: list[dict] = field(default_factory=list)
    stable_rate: float = 1.0  # tính trên các câu đã chạy ít nhất hai lượt
    stopped_by_budget: bool = False


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))["cases"]


async def score(
    cases: list[dict], *, llm: LLMClient, config: AppConfig, repeat: int = 1
) -> G9Result:
    """Chạy `repeat` lượt, mỗi lượt đi hết `cases`. Chạm trần chi phí của `llm` thì dừng ngay, không
    tính lời gọi bị từ chối là một lượt và không tính là lỗi của model."""
    if repeat < 1:
        raise ValueError(f"repeat phải >= 1, nhận {repeat}")
    result = G9Result(repeat=repeat)
    confusion: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    seen: dict[str, Counter[str]] = {c["id"]: Counter() for c in cases}
    missed: dict[str, None] = {}
    false_blocks: dict[str, None] = {}
    wrong_kind: dict[str, None] = {}
    for run in range(1, repeat + 1):
        for case in cases:
            expected = case["expected"]["verdict"]
            try:
                got = (await moderate(case["text"], source=Source(case["source"]), llm=llm,
                                      config=config, darkness_level=case.get("darkness_level"))
                       ).verdict.value
            except WritoryError as e:
                if e.code in _BUDGET_CODES:
                    result.stopped_by_budget = True
                    break
                result.errors += 1
                got = f"error:{e.code.value}"
            result.total += 1
            seen[case["id"]][got] += 1
            confusion[expected][got] += 1
            if got == expected:
                result.correct += 1
                continue
            result.wrong.append({"id": case["id"], "run": run, "expected": expected, "got": got})
            if got.startswith("error:"):
                continue
            if got == Verdict.ALLOW.value:
                missed[case["id"]] = None
            elif expected == Verdict.ALLOW.value:
                false_blocks[case["id"]] = None
            else:
                wrong_kind[case["id"]] = None
        if result.stopped_by_budget:
            break
    result.missed, result.false_blocks = list(missed), list(false_blocks)
    result.wrong_kind = list(wrong_kind)
    result.confusion = {k: dict(v) for k, v in confusion.items()}
    repeated = [cid for cid, c in seen.items() if sum(c.values()) >= 2]
    result.unstable = [{"id": cid, "verdicts": dict(seen[cid])}
                       for cid in repeated if len(seen[cid]) > 1]
    if repeated:
        result.stable_rate = 1 - len(result.unstable) / len(repeated)
    return result


def cases_info(path: Path) -> dict:
    """Tên, hash, phiên bản và số câu của một bộ câu, để ghi vào kết quả."""
    raw = path.read_bytes()
    try:
        name = path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        name = path.name
    doc = yaml.safe_load(raw.decode("utf-8"))
    return {"file": name, "sha256_16": hashlib.sha256(raw).hexdigest()[:16],
            "version": doc.get("version"), "count": len(doc["cases"])}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


async def run_bench(
    cases_path: Path, *, repeat: int, budget: float, llm: LLMClient, tracker, config: AppConfig,
    out: Path | None, config_dir: Path = REPO_CONFIG_DIR,
) -> G9Result:
    """Chạy bộ câu và ghi `result.json` (nếu có `out`). `llm` phải là client đã bọc `tracker`;
    `budget` chỉ để ghi lại (trần do `tracker` thi hành)."""
    result = await score(load_cases(cases_path), llm=llm, config=config, repeat=repeat)
    if out:
        inputs = [cases_path, *(p for n in ("models.yaml", "moderation.yaml", "limits.yaml")
                                for p in config_sources(config_dir, n))]
        meta = {
            "date": date.today().isoformat(),
            "commit": _git("rev-parse", "HEAD"),
            "worktree_dirty": bool(_git("status", "--porcelain")),
            "inputs_sha256_16": hashlib.sha256(
                b"".join(p.read_bytes() for p in inputs)).hexdigest()[:16],
            "cases": cases_info(cases_path),
            "repeat": repeat,
            "budget_usd": budget,
            "provider": llm_identity(config, [config.models.roles.moderate])["provider"],  # D-140
            "model": config.models.roles.moderate,
            "reasoning": config.models.role_reasoning.moderate,
            # Cách gọi (D-79): đầu vào kiểm `input_votes` lần, bộ lựa chọn chấm từng dòng.
            "prompt": PROMPT_VERSION,
            "input_votes": config.moderation.input_votes,
            "catalogue_draft": config.moderation.draft,
            "cost_usd": tracker.story_usd,
        }
        out.mkdir(parents=True, exist_ok=True)
        (out / "result.json").write_text(
            json.dumps({"meta": meta, **asdict(result)}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8", newline="\n",
        )
    return result


async def _main(args: argparse.Namespace) -> int:
    from writory.llm.cost import CostTracker, MeteredClient
    from writory.llm.provider import bench_llm

    config = load_config(args.config_dir)
    cap = args.budget if args.budget is not None else config.limits.cost_usd.require("per_story")
    tracker = CostTracker(CostLimits(per_scene=cap, per_chapter=cap, per_story=cap))
    llm = MeteredClient(bench_llm(config, args.env_file, models=[config.models.roles.moderate]), tracker)
    result = await run_bench(args.cases, repeat=args.repeat, budget=cap, llm=llm,
                             tracker=tracker, config=config, out=args.out, config_dir=args.config_dir)
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"đúng {result.correct}/{result.total}; bỏ sót {len(result.missed)}, chặn nhầm "
          f"{len(result.false_blocks)}, sai mức {len(result.wrong_kind)}, lỗi gọi {result.errors}; "
          f"chi phí {tracker.story_usd:.4f} USD")
    if args.repeat > 1:
        print(f"ổn định {result.stable_rate:.1%}: {len(result.unstable)} câu ra kết luận khác nhau "
              f"giữa {args.repeat} lượt")
    if result.stopped_by_budget:
        print(f"DỪNG vì chạm trần {cap} USD: chưa đo hết bộ câu")
    return 0


def _positive_int(text: str) -> int:
    value = int(text)
    if value < 1:
        raise argparse.ArgumentTypeError("phải >= 1")
    return value


def _positive_float(text: str) -> float:
    value = float(text)
    if value <= 0:
        raise argparse.ArgumentTypeError("phải > 0")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Đo bộ kiểm duyệt G9 với model thật")
    parser.add_argument("--out", type=Path, help="thư mục kết quả (evals/results/<ngày>-g9)")
    parser.add_argument("--cases", type=Path, default=CASES_PATH,
                        help="bộ câu (mặc định evals/redteam/g9_moderation.yaml)")
    parser.add_argument("--config-dir", type=Path, default=REPO_CONFIG_DIR,
                        help="thư mục config (D-140: evals/config/meta dùng model Meta); mặc định config/")
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env",
                        help="file .env chứa key của chủ dự án (OPENROUTER_API_KEY hay META_API_KEY)")
    parser.add_argument("--repeat", type=_positive_int, default=1,
                        help="số lượt: mỗi câu chạy lại từng ấy lần, báo độ ổn định")
    parser.add_argument("--budget", type=_positive_float,
                        help="trần chi phí của lần chạy, USD (mặc định limits.cost_usd.per_story)")
    return parser


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_main(build_parser().parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
