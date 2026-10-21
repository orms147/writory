"""Bộ đo G9 (safety/bench_g9.py): chọn bộ câu, chạy lặp, trần chi phí, ghi kết quả. Model giả."""

import hashlib
import json
from pathlib import Path

import pytest
import yaml

from tests.moderation_fixtures import moderation_reply
from writory.config import CostLimits, load_config
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM
from writory.safety import bench_g9
from writory.safety.bench_g9 import (
    CASES_PATH,
    build_parser,
    cases_info,
    load_cases,
    run_bench,
    score,
)

CFG = load_config()
ALLOW = moderation_reply()
HARD = moderation_reply(("sexual_minors", "strong"))


def case(cid: str, verdict: str) -> dict:
    findings = [{"category": "sexual_minors", "intensity": "strong"}] if verdict != "allow" else []
    return {"id": cid, "lang": "vi", "source": "input", "tags": [], "text": f"câu {cid}",
            "expected": {"verdict": verdict, "findings": findings}}


def write_cases(path: Path, cases: list[dict], version: int = 1) -> Path:
    path.write_text(yaml.safe_dump({"guardrail": "G9", "version": version, "cases": cases},
                                   allow_unicode=True), encoding="utf-8")
    return path


# --- chạy lặp -----------------------------------------------------------------------------------


async def test_repeat_runs_every_case_that_many_times_and_reports_unstable_ones():
    cases = [case("a", "hard_blocked"), case("b", "hard_blocked"), case("c", "allow")]
    # Ba lượt, mỗi lượt a, b, c. Câu b lượt 2 ra allow (bỏ sót), các lượt khác đúng.
    llm = FakeLLM.scripted([HARD, HARD, ALLOW,   HARD, ALLOW, ALLOW,   HARD, HARD, ALLOW])
    result = await score(cases, llm=llm, config=CFG, repeat=3)

    assert (result.total, result.correct, result.errors) == (9, 8, 0)
    assert len(llm.calls) == 9
    assert result.missed == ["b"] and result.false_blocks == [] and result.wrong_kind == []
    assert result.wrong == [{"id": "b", "run": 2, "expected": "hard_blocked", "got": "allow"}]
    assert result.repeat == 3
    assert result.unstable == [{"id": "b", "verdicts": {"hard_blocked": 2, "allow": 1}}]
    assert result.stable_rate == pytest.approx(2 / 3)
    assert result.confusion == {"hard_blocked": {"hard_blocked": 5, "allow": 1},
                                "allow": {"allow": 3}}


async def test_repeat_one_keeps_the_single_run_behaviour():
    cases = [case("a", "hard_blocked"), case("c", "allow")]
    result = await score(cases, llm=FakeLLM.scripted([HARD, ALLOW]), config=CFG)
    assert (result.total, result.correct, result.repeat) == (2, 2, 1)
    assert result.unstable == [] and result.stable_rate == 1.0


async def test_a_case_wrong_the_same_way_every_run_is_stable_but_still_wrong():
    result = await score([case("a", "hard_blocked")], llm=FakeLLM.scripted([ALLOW] * 3),
                         config=CFG, repeat=3)
    assert result.unstable == [] and result.missed == ["a"] and result.correct == 0


async def test_repeat_must_be_positive():
    with pytest.raises(ValueError, match="repeat"):
        await score([case("a", "allow")], llm=FakeLLM.scripted([]), config=CFG, repeat=0)


# --- trần chi phí -------------------------------------------------------------------------------


def metered(cost_usd: float, cap: float):
    tracker = CostTracker(CostLimits(per_scene=cap, per_chapter=cap, per_story=cap))
    return MeteredClient(FakeLLM.scripted([ALLOW] * 50, cost_usd=cost_usd), tracker), tracker


async def test_budget_stops_the_run_before_the_next_call():
    llm, tracker = metered(cost_usd=0.01, cap=0.025)  # kiểm trước mỗi lời gọi: 0, 0,01, 0,02 qua
    cases = [case(str(i), "allow") for i in range(4)]
    result = await score(cases, llm=llm, config=CFG, repeat=2)

    assert result.stopped_by_budget is True
    assert result.total == 3 and result.errors == 0  # hết trần không phải lỗi của model
    assert tracker.story_usd == pytest.approx(0.03)
    assert result.unstable == []  # chưa câu nào đủ hai lượt


async def test_run_within_budget_is_not_marked_stopped():
    llm, _ = metered(cost_usd=0.001, cap=1.0)
    result = await score([case("a", "allow")], llm=llm, config=CFG, repeat=2)
    assert result.stopped_by_budget is False and result.total == 2


# --- bộ câu và kết quả ----------------------------------------------------------------------------


def test_default_cases_file_is_the_original_set():
    assert CASES_PATH.name == "g9_moderation.yaml"
    assert build_parser().parse_args([]).cases == CASES_PATH
    assert load_cases() == load_cases(CASES_PATH)


def test_cli_options():
    args = build_parser().parse_args(["--cases", "x.yaml", "--repeat", "3", "--budget", "0.5"])
    assert (args.cases, args.repeat, args.budget) == (Path("x.yaml"), 3, 0.5)
    defaults = build_parser().parse_args([])
    assert (defaults.repeat, defaults.budget) == (1, None)
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--repeat", "0"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--budget", "0"])


def test_cases_info_names_the_file_and_hashes_its_bytes(tmp_path):
    path = write_cases(tmp_path / "bo-thu.yaml", [case("a", "allow"), case("b", "allow")],
                       version=4)
    info = cases_info(path)
    assert info == {"file": "bo-thu.yaml", "sha256_16": hashlib.sha256(
        path.read_bytes()).hexdigest()[:16], "version": 4, "count": 2}
    assert cases_info(CASES_PATH)["file"] == "evals/redteam/g9_moderation.yaml"


async def test_result_json_records_the_cases_file_hash_repeat_and_budget(tmp_path):
    path = write_cases(tmp_path / "bo-thu.yaml", [case("a", "hard_blocked"), case("b", "allow")])
    llm, tracker = metered(cost_usd=0.001, cap=1.0)
    llm = MeteredClient(FakeLLM.scripted([HARD, ALLOW] * 2, cost_usd=0.001), tracker)
    out = tmp_path / "ket-qua"
    result = await run_bench(path, repeat=2, budget=1.0, llm=llm, tracker=tracker, config=CFG,
                             out=out)

    saved = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert saved["meta"]["cases"] == cases_info(path)
    assert saved["meta"]["repeat"] == 2 and saved["meta"]["budget_usd"] == 1.0
    assert saved["meta"]["cost_usd"] == pytest.approx(0.004)
    assert saved["repeat"] == 2 and saved["stable_rate"] == 1.0
    assert (saved["total"], saved["correct"]) == (4, 4) == (result.total, result.correct)

    # Đổi nội dung bộ câu thì hash của bộ câu và hash đầu vào chung đều đổi.
    other = write_cases(tmp_path / "bo-khac.yaml", [case("a", "hard_blocked")])
    llm2 = MeteredClient(FakeLLM.scripted([HARD]), tracker)
    out2 = tmp_path / "ket-qua-2"
    await run_bench(other, repeat=1, budget=1.0, llm=llm2, tracker=tracker, config=CFG, out=out2)
    saved2 = json.loads((out2 / "result.json").read_text(encoding="utf-8"))
    assert saved2["meta"]["cases"]["sha256_16"] != saved["meta"]["cases"]["sha256_16"]
    assert saved2["meta"]["inputs_sha256_16"] != saved["meta"]["inputs_sha256_16"]


async def test_result_json_marks_a_budget_stop(tmp_path):
    path = write_cases(tmp_path / "bo.yaml", [case(str(i), "allow") for i in range(5)])
    llm, tracker = metered(cost_usd=0.02, cap=0.03)
    out = tmp_path / "kq"
    await run_bench(path, repeat=1, budget=0.03, llm=llm, tracker=tracker, config=CFG, out=out)
    saved = json.loads((out / "result.json").read_text(encoding="utf-8"))
    assert saved["stopped_by_budget"] is True and saved["total"] == 2
    assert saved["meta"]["budget_usd"] == 0.03


def test_module_still_exposes_main():
    assert callable(bench_g9.main)
