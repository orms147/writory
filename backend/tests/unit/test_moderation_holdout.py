"""Bộ câu G9 giữ riêng (evals/redteam/g9_moderation_holdout.yaml, D-71), chạy với model giả: kiểm cấu
trúc, độ phủ các nhóm, rằng nó không chép bộ cũ hay ví dụ trong config, rằng nội dung cấm chỉ ở dạng
mô tả, và đường đi từ câu tới kết luận. KHÔNG đo chất lượng model (việc đó: writory.safety.bench_g9)."""

import html
import re
from collections import Counter
from pathlib import Path

import pytest
import yaml

from tests.moderation_fixtures import CaseModerator
from writory.config import REPO_ROOT, load_config
from writory.safety.bench_g9 import CASES_PATH, load_cases, score
from writory.safety.categories import Category
from writory.safety.moderate import Finding, Source, Verdict, decide, moderate
from writory.safety.wrap import CLOSE_TAG

HOLDOUT_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation_holdout.yaml"
CFG = load_config()
CASES = load_cases(HOLDOUT_PATH)
OLD = load_cases(CASES_PATH)
IDS = [c["id"] for c in CASES]
OUTPUT = {Source.SCENE.value, Source.CHOICES.value}


def findings_of(case):
    return [(f["category"], f["intensity"]) for f in case["expected"]["findings"]]


# --- khai trước, định dạng -----------------------------------------------------------------------


def test_header_declares_the_set_before_use_and_versions_it():
    text = HOLDOUT_PATH.read_text(encoding="utf-8")
    head = text.split("guardrail:")[0]
    assert "21/10/2026" in head and "CHƯA dùng để chỉnh" in head and "tăng `version`" in head
    doc = yaml.safe_load(text)
    assert doc["guardrail"] == "G9" and doc["version"] == 1


def test_same_format_as_the_original_set():
    required = {"id", "lang", "source", "tags", "text", "expected"}
    for case in CASES:
        assert required <= set(case), case["id"]
        assert set(case) <= required | {"darkness_level"}, case["id"]
        assert set(case["expected"]) == {"verdict", "findings"}
        assert case["source"] in {s.value for s in Source}
        assert case["expected"]["verdict"] in {v.value for v in Verdict}
        for f in case["expected"]["findings"]:
            assert set(f) == {"category", "intensity"} and f["category"] in {c.value for c in Category}
    assert len(set(IDS)) == len(IDS) and all(i.startswith("h-") for i in IDS)
    assert not set(IDS) & {c["id"] for c in OLD}


# --- độ phủ ----------------------------------------------------------------------------------------


def test_covers_every_category_on_both_input_and_output():
    for category in Category:
        on_input = [c for c in CASES if c["source"] == "input"
                    and category.value in {f["category"] for f in c["expected"]["findings"]}]
        on_output = [c for c in CASES if c["source"] in OUTPUT
                     and category.value in {f["category"] for f in c["expected"]["findings"]}]
        assert on_input, f"{category.value}: thiếu câu đầu vào"
        assert on_output, f"{category.value}: thiếu câu đầu ra"


def test_covers_every_source_verdict_language_and_darkness_level():
    assert {c["source"] for c in CASES} == {s.value for s in Source}
    assert {c["expected"]["verdict"] for c in CASES} == {v.value for v in Verdict}
    assert {"vi", "vi-khong-dau", "vi-teencode", "en"} <= {c["lang"] for c in CASES}
    levels = Counter(c["darkness_level"] for c in CASES if "darkness_level" in c)
    assert set(levels) == set(CFG.moderation.darkness_levels)
    assert all(n >= 3 for n in levels.values()), levels
    # Chữ cảnh và lựa chọn kiểm ở cả ba mức; mức u tối chỉ có nghĩa với đầu ra.
    assert all(c["source"] in OUTPUT for c in CASES if "darkness_level" in c)


def test_covers_tags_the_original_set_has_plus_wrapped():
    tags = {t for c in CASES for t in c["tags"]}
    assert {"negation", "long", "attack", "wrapped", "legit", "violence", "politics", "child",
            "ambiguous"} <= tags
    long_ones = [c for c in CASES if "long" in c["tags"]]
    assert len(long_ones) >= 3 and all(len(c["text"]) >= 300 for c in long_ones)
    for lang in ("vi-khong-dau", "vi-teencode"):
        assert {c["source"] for c in CASES if c["lang"] == lang} >= {"input"}


def test_has_many_legit_dark_fiction_cases_in_every_source_and_they_all_expect_allow():
    """Nửa còn lại của bộ câu: chặn nhầm cũng là lỗi."""
    legit = [c for c in CASES if "legit" in c["tags"]]
    assert len(legit) >= 30
    assert {c["source"] for c in legit} == {s.value for s in Source}
    for case in legit:
        assert case["expected"]["verdict"] == "allow", case["id"]
    for case in CASES:
        if "negation" in case["tags"] and "legit" in case["tags"]:
            assert case["expected"]["verdict"] == "allow"
    assert len([c for c in legit if {"violence"} & set(c["tags"])]) >= 12


def test_every_block_level_verdict_has_a_matching_disguised_variant():
    """Câu đội lốt (bọc trong lời kể, giả làm hệ thống) có ở loại chặn cứng, chặn, và hợp lệ."""
    disguised = [c for c in CASES if {"attack", "wrapped"} & set(c["tags"])]
    assert {"hard_blocked", "blocked", "allow"} <= {c["expected"]["verdict"] for c in disguised}


def test_hard_cases_are_hard_blocked_in_every_source_and_level():
    hard = [c for c in CASES if c["expected"]["verdict"] == "hard_blocked"]
    assert len(hard) >= 10
    for case in hard:
        for source in Source:
            for level in CFG.moderation.darkness_levels:
                verdict, _ = decide(
                    [Finding(category=c, intensity=i) for c, i in findings_of(case)],
                    source=source, config=CFG.moderation, darkness_level=level)
                assert verdict is Verdict.HARD_BLOCKED, (case["id"], source, level)


# --- nội dung cấm chỉ ở dạng mô tả ------------------------------------------------------------------


def test_forbidden_content_is_only_ever_a_bracketed_description():
    """Mọi câu thuộc loại cấm (chặn cứng, hoặc chặn ở đầu ra) chỉ mang nội dung trong ngoặc vuông;
    phần ngoài ngoặc là bối cảnh hay lời dẫn, không phải nội dung cấm."""
    for case in CASES:
        if case["expected"]["verdict"] == "hard_blocked":
            assert re.search(r"\[[^\]]{15,}\]", case["text"]), case["id"]
        if case["expected"]["verdict"] == "blocked" and case["source"] != "input":
            assert re.search(r"\[[^\]]{15,}\]", case["text"]), case["id"]
        if case["expected"]["verdict"] == "over_darkness" and any(
                f["intensity"] == "extreme" or (f["category"] == "adult_sexual"
                                                and f["intensity"] == "strong")
                for f in case["expected"]["findings"]):
            assert re.search(r"\[[^\]]{15,}\]", case["text"]), case["id"]


# --- không chép bộ cũ, không chép ví dụ trong config ------------------------------------------------


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.casefold())).strip()


def _shingles(text: str, n: int = 4) -> set[tuple[str, ...]]:
    words = _norm(text).split()
    return {tuple(words[i:i + n]) for i in range(max(len(words) - n + 1, 0))}


def _config_examples() -> list[str]:
    """Các câu ví dụ trong ngoặc kép của thang mức độ (config/moderation.yaml)."""
    scale = yaml.safe_load((REPO_ROOT / "config" / "moderation.yaml").read_text(
        encoding="utf-8"))["intensity_scale"]
    return [m for text in scale.values() for m in re.findall(r'"([^"]+)"', text)]


def test_config_examples_were_found():
    assert len(_config_examples()) >= 6  # nếu config đổi cách viết ví dụ, test này báo để sửa


def test_no_case_copies_or_closely_paraphrases_the_original_set_or_config_examples():
    reference = [(c["id"], c["text"]) for c in OLD] + [("config", t) for t in _config_examples()]
    for case in CASES:
        mine = _norm(case["text"])
        for ref_id, ref in reference:
            assert _norm(ref) not in mine and mine not in _norm(ref), (case["id"], ref_id)
            theirs = _shingles(ref)
            overlap = _shingles(case["text"]) & theirs
            # Chung hơn một phần tư số cụm bốn từ của câu tham chiếu: coi là chép hoặc diễn đạt lại.
            assert len(overlap) <= max(1, len(theirs) // 4), (case["id"], ref_id, overlap)


def test_the_overlap_check_itself_catches_a_copy():
    old = OLD[0]["text"]
    assert _norm(old) in _norm("Mở đầu khác. " + old + " Kết thúc khác.")
    changed = old.replace("Tôi", "Ta")
    assert len(_shingles(changed) & _shingles(old)) > max(1, len(_shingles(old)) // 3)


# --- đường đi với model giả -------------------------------------------------------------------------


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


async def test_bench_scores_an_oracle_model_perfectly_on_the_holdout():
    result = await score(CASES, llm=CaseModerator(CASES), config=CFG)
    assert (result.correct, result.total, result.errors) == (len(CASES), len(CASES), 0)
    assert result.missed == [] and result.false_blocks == [] and result.wrong_kind == []


async def test_bench_scores_a_blind_model_as_missing_every_blocked_case():
    result = await score(CASES, llm=CaseModerator(constant=[]), config=CFG)
    assert result.missed == [c["id"] for c in CASES if c["expected"]["verdict"] != "allow"]
    assert result.false_blocks == []


def test_holdout_is_reachable_through_the_cli_option():
    from writory.safety.bench_g9 import build_parser

    assert build_parser().parse_args(["--cases", str(HOLDOUT_PATH)]).cases == Path(HOLDOUT_PATH)
