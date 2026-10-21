"""Bộ red-team G9 (evals/redteam/g9_moderation.yaml, D-57) chạy với model giả: kiểm cấu trúc bộ câu,
nhãn khớp danh mục hiện hành, và đường đi từ câu tới kết luận. KHÔNG đo chất lượng model kiểm duyệt
(việc đó cần model thật: writory.safety.bench_g9)."""

import html
import json

import pytest

from tests.moderation_fixtures import CaseModerator
from writory.config import load_config
from writory.llm.fake import FakeLLM
from writory.safety.bench_g9 import load_cases, score
from writory.safety.moderate import Finding, Source, Verdict, decide, moderate
from writory.safety.wrap import CLOSE_TAG

CFG = load_config()
CASES = load_cases()
IDS = [c["id"] for c in CASES]


def findings_of(case):
    return [(f["category"], f["intensity"]) for f in case["expected"]["findings"]]


# --- cấu trúc bộ câu -------------------------------------------------------------------------------


def test_set_covers_languages_sources_and_every_verdict():
    assert len(CASES) >= 40 and len(set(IDS)) == len(IDS)
    assert {"vi", "vi-khong-dau", "vi-teencode", "en"} <= {c["lang"] for c in CASES}
    assert {c["source"] for c in CASES} == {s.value for s in Source}
    assert {c["expected"]["verdict"] for c in CASES} == {v.value for v in Verdict}
    tags = {t for c in CASES for t in c["tags"]}
    assert {"negation", "long", "attack", "legit", "violence", "politics", "child"} <= tags
    assert {c["darkness_level"] for c in CASES if "darkness_level" in c} \
        == set(CFG.moderation.darkness_levels)


def test_legit_dark_fiction_and_negations_are_expected_allow():
    """Nửa còn lại của bộ câu: chặn nhầm cũng là lỗi. Mọi câu hợp lệ phải mong đợi `allow`."""
    for case in CASES:
        if {"legit", "negation"} & set(case["tags"]):
            assert case["expected"]["verdict"] == "allow", case["id"]
    legit_violent = [c for c in CASES if {"legit", "violence"} <= set(c["tags"])]
    assert len(legit_violent) >= 4
    assert sum(c["expected"]["verdict"] == "allow" for c in CASES) >= 20


def test_every_hard_case_is_hard_blocked_in_every_source_and_level():
    hard = [c for c in CASES if c["expected"]["verdict"] == "hard_blocked"]
    assert len(hard) >= 6
    for case in hard:
        for source in Source:
            for level in CFG.moderation.darkness_levels:
                verdict, _ = decide(
                    [Finding(category=c, intensity=i) for c, i in findings_of(case)],
                    source=source, config=CFG.moderation, darkness_level=level)
                assert verdict is Verdict.HARD_BLOCKED, (case["id"], source, level)


# --- đường đi với model giả ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=IDS)
async def test_case_reaches_its_expected_verdict(case):
    llm = CaseModerator([case])
    result = await moderate(case["text"], source=Source(case["source"]), llm=llm, config=CFG,
                            darkness_level=case.get("darkness_level"))
    assert result.verdict.value == case["expected"]["verdict"]
    assert llm.calls  # đầu vào: tới `input_votes` lời gọi; cảnh, bộ lựa chọn: một (D-79)
    # G4: chữ của câu chỉ nằm trong khối dữ liệu của vai user, kể cả câu đội lốt ra lệnh.
    for messages in llm.calls:
        system = " ".join(m.content for m in messages if m.role == "system")
        assert case["text"] not in system and "<player_data" not in system
        [content] = [m.content for m in messages if m.role == "user"]
        assert content.count("<player_data") == 1 and content.rstrip().endswith(CLOSE_TAG)
        data = html.unescape(content.split("<player_data", 1)[1])
        if case["source"] == Source.CHOICES.value:  # mỗi dòng một số thứ tự (D-79)
            assert all(line.strip() in data for line in case["text"].splitlines())
        else:
            assert case["text"] in data


async def test_bench_scores_an_oracle_model_perfectly():
    result = await score(CASES, llm=CaseModerator(CASES), config=CFG)
    assert (result.correct, result.total, result.errors) == (len(CASES), len(CASES), 0)
    assert result.missed == [] and result.false_blocks == [] and result.wrong_kind == []


async def test_bench_counts_a_blind_model_as_missing_every_blocked_case():
    result = await score(CASES, llm=CaseModerator(constant=[]), config=CFG)
    expected_blocked = [c["id"] for c in CASES if c["expected"]["verdict"] != "allow"]
    assert result.missed == expected_blocked and result.false_blocks == []
    assert result.correct == len(CASES) - len(expected_blocked)


async def test_bench_counts_a_paranoid_model_as_blocking_legit_cases():
    paranoid = CaseModerator(constant=[("sexual_minors", "strong")])
    result = await score(CASES, llm=paranoid, config=CFG)
    expected_allow = [c["id"] for c in CASES if c["expected"]["verdict"] == "allow"]
    assert result.false_blocks == expected_allow and result.missed == []
    # Đúng loại nhưng sai mức: câu mong đợi `blocked` hay `over_darkness` mà ra `hard_blocked`.
    assert set(result.wrong_kind) == {
        c["id"] for c in CASES if c["expected"]["verdict"] in ("blocked", "over_darkness")}


async def test_bench_counts_failed_calls_as_wrong_not_as_misses():
    llm = FakeLLM.scripted(["không phải json"] * (len(CASES) * 4))
    result = await score(CASES[:3], llm=llm, config=CFG)
    assert result.errors == 3 and result.correct == 0
    assert result.missed == [] and result.false_blocks == []
    assert json.dumps(result.wrong, ensure_ascii=False)  # ghi được ra file kết quả
