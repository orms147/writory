"""Bộ câu và bộ chấm của vai `overreach` (G6, D-138). Model giả: kiểm cấu trúc và đường chấm, không đo
model. Đo với model thật: `writory.safety.bench_g6` (docs/eval.md, mục Red-team)."""

import json

import yaml

from writory.config import REPO_ROOT, load_config
from writory.llm.fake import FakeLLM
from writory.safety.bench_g6 import case_inputs, score
from writory.safety.classify import BEYOND_RULES, Feasibility
from writory.safety.overreach import OverreachVerdict
from writory.safety.wrap import CLOSE_TAG

DOC = yaml.safe_load((REPO_ROOT / "evals" / "redteam" / "g6_overreach.yaml").read_text(
    encoding="utf-8"))
CASES = DOC["cases"]
CFG = load_config()


def reply(verdict: str) -> str:
    return json.dumps({"verdict": verdict, "reason": "thử"})


def test_set_is_complete_and_every_reference_resolves():
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert {c["expected"] for c in CASES} == {v.value for v in OverreachVerdict}
    granted = [c for c in CASES if c["expected"] == "granted"]
    passed = [c for c in CASES if c["expected"] != "granted"]
    assert len(granted) >= 5 and len(passed) >= 5
    assert {Feasibility(c["feasibility"]) for c in CASES} == set(BEYOND_RULES)
    for case in CASES:
        inputs = case_inputs(case, DOC)  # tham chiếu lạ thì KeyError
        assert inputs["action"].strip() and inputs["scene_text"].strip(), case["id"]
        assert ("scene" in case) != ("scene_ref" in case), case["id"]
    earlier = [c for c in CASES if "earlier" in c["tags"]]
    assert {c["expected"] for c in earlier} >= {"granted", "failed"}
    assert all(c["expected"] == "granted" for c in CASES
               if {"attack", "mentioned-cost"} & set(c["tags"]))
    assert all(c["expected"] == "failed" for c in CASES if "dream" in c["tags"])


async def test_an_oracle_scores_perfectly():
    llm = FakeLLM.scripted([reply(c["expected"]) for c in CASES])
    result = await score(DOC, llm=llm, config=CFG)
    assert result.correct == result.total == len(CASES)
    assert (result.granted_missed, result.false_granted, result.errors) == ([], [], 0)


async def test_missed_and_false_granted_are_counted_apart_from_failed_cost_mixups():
    granted = next(c for c in CASES if c["expected"] == "granted")
    failed = next(c for c in CASES if c["expected"] == "failed")
    cost = next(c for c in CASES if c["expected"] == "cost")
    flip = {granted["id"]: "cost", failed["id"]: "granted", cost["id"]: "failed"}
    llm = FakeLLM.scripted([reply(flip.get(c["id"], c["expected"])) for c in CASES])
    result = await score(DOC, llm=llm, config=CFG)
    assert result.correct == len(CASES) - 3
    assert result.granted_missed == [granted["id"]]
    assert result.false_granted == [failed["id"]]
    assert result.confusion["cost"]["failed"] == 1


async def test_failed_calls_count_as_wrong_not_as_misses():
    llm = FakeLLM.scripted(["không phải json"] * 50)
    result = await score({**DOC, "cases": CASES[:1]}, llm=llm, config=CFG)
    assert result.errors == 1 and result.correct == 0
    assert result.granted_missed == [] and result.false_granted == []


async def test_each_call_carries_its_earlier_scenes_and_wraps_the_action():
    llm = FakeLLM.scripted([reply(c["expected"]) for c in CASES])
    await score(DOC, llm=llm, config=CFG)
    for case, call in zip(CASES, llm.calls, strict=True):
        user = call[-1].content
        inputs = case_inputs(case, DOC)
        assert user.count('<player_data source="scene_text">') == 1 + len(inputs["earlier"])
        start = user.index('<player_data source="player_action">')
        assert inputs["action"] in user[start:user.index(CLOSE_TAG, start)], case["id"]


def test_dry_run_makes_no_paid_call(capsys, monkeypatch):
    from writory.safety import bench_g6

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert bench_g6.main(["--dry-run"]) == 0
    out = capsys.readouterr().out
    assert f"đúng {len(CASES)}/{len(CASES)}" in out and f"{len(CASES)} lời gọi" in out
