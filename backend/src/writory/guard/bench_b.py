"""Bài B (design §9, docs/eval.md): người canh, phần kiểm bằng code, trên lỗi cài sẵn.

Chạy: `cd backend && uv run python -m writory.guard.bench_b [--out ../evals/results/<ngày>-guard-b]`
Dữ liệu khai trước: evals/scenarios/guard-b/cases.yaml. Không gọi model, không cần Neo4j:
nền là truyện mẫu dựng bằng OverlayState (khớp Neo4j: tests/graph/test_guard_state_parity.py).
"""

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

import yaml

from writory.config import REPO_ROOT, GuardConfig
from writory.graph import ChangePackage, read_sample
from writory.graph.sample import DEFAULT_SAMPLE_DIR, SampleStory
from writory.guard.rules import GuardIssue, GuardKind, check_scene_package
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.story_plan import StoryPlan

SCENARIOS = REPO_ROOT / "evals" / "scenarios" / "guard-b" / "cases.yaml"


@dataclass
class Scenarios:
    plan: StoryPlan
    config: GuardConfig
    cases: list[dict]


@dataclass
class KindRow:
    error_cases: int = 0
    detected: int = 0
    clean_cases: int = 0
    false_positive_cases: int = 0


@dataclass
class BenchResult:
    by_kind: dict[str, KindRow] = field(default_factory=dict)
    unexpected: int = 0
    failures: list[dict] = field(default_factory=list)


def load_scenarios(path: Path) -> Scenarios:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenarios(
        StoryPlan.model_validate(raw["plan"]),
        GuardConfig.model_validate(raw["trial_config"]),
        raw["cases"],
    )


def _package(data: dict, commit_id: str) -> ChangePackage:
    return ChangePackage.model_validate({"commit_id": commit_id, **data})


def run_case(case: dict, scen: Scenarios, sample: SampleStory) -> list[GuardIssue]:
    committed = OverlayState(
        EmptyState(), [c.package for c in sample.chapters if c.number <= case["committed_through"]]
    )
    earlier = [
        _package(p, f"{case['id']}-earlier-{i}") for i, p in enumerate(case.get("earlier", []))
    ]
    if "current_sample" in case:
        [current] = [c.package for c in sample.chapters if c.number == case["current_sample"]]
    else:
        current = _package(case["current"], f"{case['id']}-current")
    return check_scene_package(
        chapter=case["chapter"], current=current, earlier=earlier,
        committed=committed, plan=scen.plan, config=scen.config,
    )


def run(path: Path = SCENARIOS, sample: SampleStory | None = None) -> BenchResult:
    scen = load_scenarios(path)
    sample = sample or read_sample()
    result = BenchResult(by_kind={k.value: KindRow() for k in GuardKind})
    for case in scen.cases:
        found = {i.kind.value for i in run_case(case, scen, sample)}
        expect = set(case["expect"])
        for kind in case["targets"]:
            row = result.by_kind[kind]
            if kind in expect:
                row.error_cases += 1
                row.detected += kind in found
            else:
                row.clean_cases += 1
                row.false_positive_cases += kind in found
        result.unexpected += len(found - expect)
        if found != expect:
            result.failures.append(
                {"id": case["id"], "expect": sorted(expect), "found": sorted(found)}
            )
    return result


def _table(result: BenchResult) -> str:
    lines = [
        "| Phép kiểm | Ca lỗi | Bắt được | Recall | Ca sạch | Báo nhầm |",
        "|---|---|---|---|---|---|",
    ]
    for kind, r in result.by_kind.items():
        recall = f"{r.detected / r.error_cases:.0%}" if r.error_cases else "—"
        lines.append(f"| {kind} | {r.error_cases} | {r.detected} | {recall} | "
                     f"{r.clean_cases} | {r.false_positive_cases} |")
    lines.append(f"\nLoại lỗi báo ngoài `expect` (mọi ca): {result.unexpected}")
    for f in result.failures:
        lines.append(f"- SAI {f['id']}: expect {f['expect']}, found {f['found']}")
    return "\n".join(lines)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def _write_results(out: Path, result: BenchResult, table: str) -> None:
    inputs = [SCENARIOS, REPO_ROOT / "config" / "guard.yaml", DEFAULT_SAMPLE_DIR / "graph.yaml"]
    digest = hashlib.sha256(b"".join(p.read_bytes() for p in inputs)).hexdigest()[:16]
    meta = {
        "date": date.today().isoformat(),
        "commit": _git("rev-parse", "HEAD"),
        "worktree_dirty": bool(_git("status", "--porcelain")),
        "inputs_sha256_16": digest,
        "inputs": [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in inputs],
        "model": "không dùng model (phần kiểm bằng code)",
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps({"meta": meta, **asdict(result)}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (out / "README.md").write_text(
        "# Bài B: người canh, phần kiểm bằng code\n\n"
        f"- Ngày: {meta['date']}\n- Commit: `{meta['commit']}`"
        f"{' (worktree có thay đổi chưa commit)' if meta['worktree_dirty'] else ''}\n"
        f"- Hash đầu vào (sha256, 16 ký tự đầu): `{digest}` của {', '.join(meta['inputs'])}\n"
        f"- Model: {meta['model']}\n"
        "- Lệnh: `cd backend && uv run python -m writory.guard.bench_b --out <thư mục này>`\n\n"
        + table + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bài B: người canh, phần kiểm bằng code")
    parser.add_argument("--out", type=Path, help="thư mục ghi kết quả (evals/results/<ngày>-guard-b)")
    args = parser.parse_args(argv)
    result = run()
    table = _table(result)
    sys.stdout.reconfigure(encoding="utf-8")
    print(table)
    if args.out:
        _write_results(args.out, result, table)
    return 0 if not result.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
