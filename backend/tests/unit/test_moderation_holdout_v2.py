"""Bộ câu G9 giữ riêng thế hệ hai (evals/redteam/g9_moderation_holdout_v2.yaml, D-80), chạy với model
giả: kiểm cấu trúc, độ phủ các nhóm và thể loại, rằng nó không chép bộ chỉnh, bộ giữ riêng v1 hay ví
dụ trong config, rằng nội dung loại cấm chỉ ở dạng mô tả, và đường đi từ câu tới kết luận. KHÔNG đo
chất lượng model (việc đó: writory.safety.bench_g9).

Khác bộ v1 (D-80): loại chặn cứng và loại chặn chỉ ở dạng mô tả trong ngoặc vuông, kể cả ở đầu vào,
vì v2 soạn phần đo được mà không viết nội dung tấn công; và test chống trùng so với CẢ bộ chỉnh lẫn
bộ giữ riêng v1."""

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

HOLDOUT_V2_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation_holdout_v2.yaml"
HOLDOUT_V1_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation_holdout.yaml"
CFG = load_config()
CASES = load_cases(HOLDOUT_V2_PATH)
TUNING = load_cases(CASES_PATH)  # bộ chỉnh g9_moderation.yaml
V1 = load_cases(HOLDOUT_V1_PATH)  # bộ giữ riêng v1, nay là bộ chỉnh (D-79)
IDS = [c["id"] for c in CASES]
OUTPUT = {Source.SCENE.value, Source.CHOICES.value}
GENRES = {"tu-tien", "kiem-hiep", "trinh-tham", "hau-tan-the", "co-trang", "kinh-di"}


def findings_of(case):
    return [(f["category"], f["intensity"]) for f in case["expected"]["findings"]]


# --- khai trước, định dạng -----------------------------------------------------------------------


def test_header_declares_the_set_before_use_and_versions_it():
    text = HOLDOUT_V2_PATH.read_text(encoding="utf-8")
    head = text.split("guardrail:")[0]
    assert "21/10/2026" in head and "CHƯA dùng để chỉnh" in head and "tăng `version`" in head
    assert "GIỚI HẠN ĐÃ BIẾT" in head  # ghi rõ loại nặng chỉ đo trên câu mô tả (D-80)
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
    assert len(set(IDS)) == len(IDS) and all(i.startswith("v2-") for i in IDS)
    assert not set(IDS) & {c["id"] for c in TUNING}
    assert not set(IDS) & {c["id"] for c in V1}


def test_expected_verdict_matches_decide_from_findings():
    """`expected.verdict` phải đúng là kết luận code rút từ `expected.findings` (không cần model)."""
    for case in CASES:
        verdict, _ = decide(
            [Finding(category=c, intensity=i) for c, i in findings_of(case)],
            source=Source(case["source"]), config=CFG.moderation,
            darkness_level=case.get("darkness_level"))
        assert verdict.value == case["expected"]["verdict"], case["id"]


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
    assert all(c["source"] in OUTPUT for c in CASES if "darkness_level" in c)


def test_covers_the_six_genres_across_input_and_output():
    tags = [t for c in CASES for t in c["tags"]]
    assert GENRES <= set(tags), GENRES - set(tags)
    # Mỗi thể loại có ít nhất một câu hợp lệ (đo chặn nhầm là mục đích chính của v2).
    for genre in GENRES:
        assert any(genre in c["tags"] and "legit" in c["tags"] for c in CASES), genre


def test_covers_tags_the_original_set_has_plus_wrapped_and_tricky_words():
    tags = {t for c in CASES for t in c["tags"]}
    assert {"negation", "long", "attack", "wrapped", "legit", "violence", "politics", "child",
            "ambiguous", "tricky-word"} <= tags
    long_ones = [c for c in CASES if "long" in c["tags"]]
    assert len(long_ones) >= 3 and all(len(c["text"]) >= 300 for c in long_ones)
    # Từ dễ gây nhầm mà vô hại: nhiều câu, mọi câu đều hợp lệ.
    tricky = [c for c in CASES if "tricky-word" in c["tags"]]
    assert len(tricky) >= 6 and all(c["expected"]["verdict"] == "allow" for c in tricky)
    for lang in ("vi-khong-dau", "vi-teencode"):
        assert {c["source"] for c in CASES if c["lang"] == lang} >= {"input"}


def test_legit_dark_fiction_is_the_majority_and_all_expect_allow():
    """Trọng tâm của v2: truyện u tối hợp lệ. Chặn nhầm cũng là lỗi."""
    legit = [c for c in CASES if "legit" in c["tags"]]
    assert len(legit) >= 30
    assert len(legit) > len(CASES) / 2  # phần lớn bộ câu
    assert {c["source"] for c in legit} == {s.value for s in Source}
    for case in legit:
        assert case["expected"]["verdict"] == "allow", case["id"]
    for case in CASES:
        if "negation" in case["tags"] and "legit" in case["tags"]:
            assert case["expected"]["verdict"] == "allow"
    assert len([c for c in legit if {"violence"} & set(c["tags"])]) >= 12


def test_over_darkness_only_uses_darkness_limited_categories_and_many_are_choice_lines():
    over = [c for c in CASES if c["expected"]["verdict"] == "over_darkness"]
    assert len(over) >= 10
    darkness_limited = {"violence", "gore", "adult_sexual"}
    for case in over:
        cats = {f["category"] for f in case["expected"]["findings"]}
        assert cats and cats <= darkness_limited, case["id"]  # chỉ loại theo mức u tối
    # Nhóm v1 bỏ sót nhiều: phần lớn câu vượt mức là dòng lựa chọn (D-79).
    assert len([c for c in over if c["source"] == "choices"]) >= len(over) / 2


def test_block_level_group_is_modest_and_covers_disguise():
    hard = [c for c in CASES if c["expected"]["verdict"] == "hard_blocked"]
    blocked = [c for c in CASES if c["expected"]["verdict"] == "blocked"]
    assert len(hard) >= 4
    assert 4 <= len(blocked)
    # "Số câu của nhóm này để vừa phải": ít hơn nhóm hợp lệ.
    assert len(hard) + len(blocked) < len([c for c in CASES if "legit" in c["tags"]])
    disguised = [c for c in CASES if {"attack", "wrapped"} & set(c["tags"])]
    assert {"hard_blocked", "blocked", "allow"} <= {c["expected"]["verdict"] for c in disguised}


def test_hard_cases_are_hard_blocked_in_every_source_and_level():
    hard = [c for c in CASES if c["expected"]["verdict"] == "hard_blocked"]
    for case in hard:
        for source in Source:
            for level in CFG.moderation.darkness_levels:
                verdict, _ = decide(
                    [Finding(category=c, intensity=i) for c, i in findings_of(case)],
                    source=source, config=CFG.moderation, darkness_level=level)
                assert verdict is Verdict.HARD_BLOCKED, (case["id"], source, level)


# --- nội dung loại cấm chỉ ở dạng mô tả (v2: kể cả chặn ở đầu vào) ----------------------------------


def test_forbidden_content_is_only_ever_a_bracketed_description():
    """v2: mọi câu chặn cứng và mọi câu chặn (ở BẤT KỲ nguồn nào, kể cả đầu vào) chỉ mang nội dung
    trong ngoặc vuông; nội dung nặng vượt mức (extreme, hoặc tình cảm người lớn mức strong) cũng
    viết dạng mô tả. Phần ngoài ngoặc là bối cảnh hay lời dẫn, không phải nội dung cấm."""
    bracket = re.compile(r"\[[^\]]{15,}\]")
    for case in CASES:
        verdict = case["expected"]["verdict"]
        if verdict in {"hard_blocked", "blocked"}:
            assert bracket.search(case["text"]), case["id"]
        if verdict == "over_darkness" and any(
                f["intensity"] == "extreme" or (f["category"] == "adult_sexual"
                                                and f["intensity"] == "strong")
                for f in case["expected"]["findings"]):
            assert bracket.search(case["text"]), case["id"]


def test_no_real_attack_text_at_input_for_blocked_categories():
    """Khác v1: ở đầu vào, câu thuộc loại chặn cứng / chặn KHÔNG viết yêu cầu tấn công thật, chỉ mô
    tả trong ngoặc. Toàn bộ chữ ngoài ngoặc không được là một câu mệnh lệnh gây hại."""
    bracket = re.compile(r"\[[^\]]{15,}\]")
    for case in CASES:
        if case["source"] == "input" and case["expected"]["verdict"] in {"hard_blocked", "blocked"}:
            outside = bracket.sub("", case["text"]).strip()
            assert outside == "", (case["id"], outside)  # không có chữ thật ngoài phần mô tả


# --- không chép bộ chỉnh, bộ v1, hay ví dụ trong config --------------------------------------------


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


def test_no_case_copies_or_closely_paraphrases_the_tuning_set_v1_or_config_examples():
    reference = ([(f"tuning:{c['id']}", c["text"]) for c in TUNING]
                 + [(f"v1:{c['id']}", c["text"]) for c in V1]
                 + [("config", t) for t in _config_examples()])
    for case in CASES:
        mine = _norm(case["text"])
        for ref_id, ref in reference:
            assert _norm(ref) not in mine and mine not in _norm(ref), (case["id"], ref_id)
            theirs = _shingles(ref)
            overlap = _shingles(case["text"]) & theirs
            # Chung hơn một phần tư số cụm bốn từ của câu tham chiếu: coi là chép hoặc diễn đạt lại.
            assert len(overlap) <= max(1, len(theirs) // 4), (case["id"], ref_id, overlap)


def test_the_overlap_check_itself_catches_a_copy():
    some = V1[0]["text"]
    assert _norm(some) in _norm("Mở khác. " + some + " Kết khác.")
    changed = some.replace("Tống", "Lục").replace("Dạ", "Vân")
    assert len(_shingles(changed) & _shingles(some)) > max(1, len(_shingles(some)) // 3)


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


def test_holdout_v2_is_reachable_through_the_cli_option():
    from writory.safety.bench_g9 import build_parser

    assert build_parser().parse_args(["--cases", str(HOLDOUT_V2_PATH)]).cases == Path(HOLDOUT_V2_PATH)
