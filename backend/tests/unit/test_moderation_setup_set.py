"""Bộ câu G9 cho nguồn `setup` (evals/redteam/g9_moderation_setup.yaml, D-137, D-141), chạy với model
giả: kiểm cấu trúc, độ phủ, nhãn khớp `decide`, nội dung loại cấm chỉ ở dạng mô tả, không chép bộ khác,
và đường chấm TỪNG DÒNG của bộ đo (`bench_g9`). KHÔNG đo chất lượng model (việc đó: lệnh
`python -m writory.safety.bench_g9 --cases …g9_moderation_setup.yaml`, docs/eval.md)."""

import json
import re
from pathlib import Path

import yaml

from writory.config import REPO_ROOT, load_config
from writory.llm.fake import FakeLLM
from writory.safety import bench_g9
from writory.safety.bench_g9 import CASES_PATH, load_cases, score
from writory.safety.categories import Category
from writory.safety.moderate import Finding, Source, Verdict, decide

SETUP_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation_setup.yaml"
HOLDOUT_V1_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation_holdout.yaml"
HOLDOUT_V2_PATH = REPO_ROOT / "evals" / "redteam" / "g9_moderation_holdout_v2.yaml"
CFG = load_config()
RAW = yaml.safe_load(SETUP_PATH.read_text(encoding="utf-8"))
RAW_CASES = RAW["cases"]
LINES = [(c, i, line) for c in RAW_CASES for i, line in enumerate(c["lines"], 1)]
BRACKET = re.compile(r"\[[^\]]{15,}\]")
SEVERITY = {"allow": 0, "over_darkness": 1, "blocked": 2, "hard_blocked": 3}


def decided(case, line) -> str:
    verdict, _ = decide(
        [Finding(category=f["category"], intensity=f["intensity"]) for f in line["findings"]],
        source=Source.SETUP, config=CFG.moderation, darkness_level=case.get("darkness_level"))
    return verdict.value


# --- khai trước, định dạng ----------------------------------------------------------------------


def test_header_declares_the_set_before_use_and_names_its_limits():
    text = SETUP_PATH.read_text(encoding="utf-8")
    head = text.split("guardrail:")[0]
    assert "30/10/2026" in head and "CHƯA dùng để chỉnh" in head and "tăng `version`" in head
    assert "GIỚI HẠN ĐÃ BIẾT" in head and "chấm TỪNG DÒNG" in head
    assert RAW["guardrail"] == "G9" and RAW["version"] == 1


def test_format_every_case_is_a_step_with_labelled_lines():
    for case in RAW_CASES:
        assert set(case) <= {"id", "step", "darkness_level", "tags", "lines"}, case["id"]
        assert {"id", "step", "tags", "lines"} <= set(case), case["id"]
        assert case["step"] in {"settings", "plots", "characters"}
        assert 3 <= len(case["lines"]) <= 4, case["id"]
        if "darkness_level" in case:
            assert case["darkness_level"] in CFG.moderation.darkness_levels
        for line in case["lines"]:
            assert set(line) == {"text", "verdict", "findings"}, case["id"]
            assert line["text"].strip() and "\n" not in line["text"], case["id"]
            assert line["verdict"] in {v.value for v in Verdict}
            for f in line["findings"]:
                assert set(f) == {"category", "intensity"}
                assert f["category"] in {c.value for c in Category}
    ids = [c["id"] for c in RAW_CASES]
    assert len(set(ids)) == len(ids) and all(i.startswith("setup-") for i in ids)


def test_size_and_coverage_of_steps_verdicts_and_darkness_levels():
    assert 30 <= len(LINES) <= 40
    assert {c["step"] for c in RAW_CASES} == {"settings", "plots", "characters"}
    assert {line["verdict"] for _, _, line in LINES} == {v.value for v in Verdict}
    assert {c.get("darkness_level") for c in RAW_CASES} >= set(CFG.moderation.darkness_levels)
    assert {t for c in RAW_CASES for t in c["tags"]} >= {
        "legit", "dark-ok", "over", "blocked", "hard", "mixed", "child", "tricky-word", "attack"}
    # Trọng tâm là chặn nhầm: phần lớn dòng hợp lệ (cho qua), loại cấm là nhóm nhỏ.
    allowed = [1 for _, _, line in LINES if line["verdict"] == "allow"]
    blocked = [1 for _, _, line in LINES if line["verdict"] in {"hard_blocked", "blocked"}]
    assert len(allowed) > len(LINES) / 2 and 4 <= len(blocked) < len(allowed)
    assert len([1 for _, _, line in LINES if line["verdict"] == "hard_blocked"]) >= 2


def test_each_darkness_level_has_dark_but_allowed_lines_and_over_lines_in_order():
    """Cùng loại nội dung có thể cho qua ở mức này và vượt ở mức khác: có dòng u tối cho qua ở
    `moderate` và `dark`, dòng vượt mức ở `light`, `moderate` và `dark`."""
    for level in ("moderate", "dark"):
        assert any(c.get("darkness_level") == level and line["verdict"] == "allow" and line["findings"]
                   for c, _, line in LINES), level
    for level in ("light", "moderate", "dark"):
        assert any(c.get("darkness_level") == level and line["verdict"] == "over_darkness"
                   for c, _, line in LINES), level


def test_there_is_a_mixed_step_where_only_some_lines_must_be_dropped():
    mixed = [c for c in RAW_CASES if "mixed" in c["tags"]]
    assert mixed
    for case in mixed:
        verdicts = {line["verdict"] for line in case["lines"]}
        assert "allow" in verdicts and len(verdicts) >= 3, case["id"]


def test_line_verdict_is_what_decide_gives_from_its_findings_on_the_setup_source():
    for case, i, line in LINES:
        assert decided(case, line) == line["verdict"], (case["id"], i)


def test_hard_lines_are_hard_blocked_at_every_darkness_level():
    for case, i, line in LINES:
        if line["verdict"] != "hard_blocked":
            continue
        for level in CFG.moderation.darkness_levels:
            verdict, _ = decide(
                [Finding(category=f["category"], intensity=f["intensity"]) for f in line["findings"]],
                source=Source.SETUP, config=CFG.moderation, darkness_level=level)
            assert verdict is Verdict.HARD_BLOCKED, (case["id"], i, level)


# --- nội dung loại cấm chỉ ở dạng mô tả -----------------------------------------------------------


def test_forbidden_and_extreme_content_is_only_ever_a_bracketed_description():
    """D-80, D-141: loại chặn cứng, loại chặn và mức nặng vượt u tối chỉ viết dạng mô tả trong ngoặc
    vuông. Chữ ngoài ngoặc của dòng chặn là tên hay đề mục, không phải nội dung cấm."""
    for case, i, line in LINES:
        extreme = any(f["intensity"] == "extreme"
                      or (f["category"] == "adult_sexual" and f["intensity"] == "strong")
                      for f in line["findings"])
        if line["verdict"] in {"hard_blocked", "blocked"} or (line["verdict"] == "over_darkness"
                                                              and extreme):
            assert BRACKET.search(line["text"]), (case["id"], i)
    for case, i, line in LINES:
        if line["verdict"] in {"hard_blocked", "blocked"}:
            outside = BRACKET.sub("", line["text"])
            assert len(outside.split()) <= 12, (case["id"], i)  # tên hay lời dẫn ngắn, không văn bản


def test_no_line_asks_the_system_to_skip_rules_with_real_attack_text():
    """Dòng `attack` là chữ ra lệnh cho bộ kiểm duyệt nằm GIỮA nội dung hợp lệ (tấm biển, bia đá);
    không có dòng nào vừa ra lệnh vừa mang nội dung loại cấm."""
    attack = [(c, i, line) for c, i, line in LINES if "attack" in c["tags"]]
    assert attack and all(line["verdict"] == "allow" for _, _, line in attack)


# --- không chép các bộ khác ---------------------------------------------------------------------------


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.casefold())).strip()


def _shingles(text: str, n: int = 4) -> set[tuple[str, ...]]:
    words = _norm(text).split()
    return {tuple(words[i:i + n]) for i in range(max(len(words) - n + 1, 0))}


def _reference_texts() -> list[tuple[str, str]]:
    refs = []
    for name, path in (("tuning", CASES_PATH), ("v1", HOLDOUT_V1_PATH), ("v2", HOLDOUT_V2_PATH)):
        refs += [(f"{name}:{c['id']}", c["text"]) for c in yaml.safe_load(
            path.read_text(encoding="utf-8"))["cases"]]
    scale = yaml.safe_load((REPO_ROOT / "config" / "moderation.yaml").read_text(
        encoding="utf-8"))["intensity_scale"]
    refs += [("config", m) for text in scale.values() for m in re.findall(r'"([^"]+)"', text)]
    return refs


def test_no_line_copies_or_closely_paraphrases_another_g9_set_or_the_config_examples():
    reference = _reference_texts()
    assert len(reference) > 100
    for case, i, line in LINES:
        mine = _norm(line["text"])
        for ref_id, ref in reference:
            assert _norm(ref) not in mine and mine not in _norm(ref), (case["id"], i, ref_id)
            theirs = _shingles(ref)
            overlap = _shingles(line["text"]) & theirs
            assert len(overlap) <= max(1, len(theirs) // 4), (case["id"], i, ref_id, overlap)


# --- bộ đo chấm từng dòng -----------------------------------------------------------------------------


def test_load_cases_turns_lines_into_one_numbered_block_with_worst_line_as_the_case_verdict():
    cases = load_cases(SETUP_PATH)
    assert len(cases) == len(RAW_CASES)
    for raw, case in zip(RAW_CASES, cases, strict=True):
        assert case["source"] == "setup" and case["id"] == raw["id"]
        assert case["text"].split("\n") == [line["text"] for line in raw["lines"]]
        verdicts = [line["verdict"] for line in raw["lines"]]
        assert case["expected"]["lines"] == verdicts
        assert case["expected"]["verdict"] == max(verdicts, key=SEVERITY.__getitem__)
        assert case.get("darkness_level") == raw.get("darkness_level")


async def test_an_oracle_scores_every_case_and_every_line_correct():
    cases = load_cases(SETUP_PATH)
    llm = bench_g9.OracleClient(cases, config=CFG)
    result = await score(cases, llm=llm, config=CFG)
    assert result.correct == result.total == len(cases) and result.errors == 0
    assert result.line_total == result.line_correct == len(LINES)
    assert result.line_missed == result.line_false_blocks == result.line_wrong_kind == []
    assert len(llm.calls) == len(cases)  # một lời gọi cho cả bước (D-137)


async def test_line_metrics_name_the_line_that_was_missed_blocked_by_mistake_or_the_wrong_kind():
    """Một lời gọi chấm sai ba dòng khác nhau của ba bước: bỏ sót (cho qua dòng phải bị chặn), chặn
    nhầm (chặn dòng hợp lệ), sai mức. Bộ đo gọi tên đúng dòng, và bước vẫn đúng ở các dòng còn lại."""
    cases = load_cases(SETUP_PATH)
    mixed = next(c for c in cases if c["id"] == "setup-mixed-characters")
    over = next(c for c in cases if c["id"] == "setup-over-settings-light")
    hard = next(c for c in cases if c["id"] == "setup-blocked-categories-a")
    chosen = [mixed, over, hard]
    flips = {
        # Dòng 2 của bước hỗn hợp phải bị chặn: model cho qua.
        (mixed["id"], 2): [],
        # Dòng 2 của bước vượt mức nhẹ là dòng hợp lệ: model báo gore strong.
        (over["id"], 2): [("gore", "strong")],
        # Dòng 3 của bước chặn cứng: model báo loại chặn thường thay vì chặn cứng.
        (hard["id"], 3): [("real_world_harm", "strong")],
    }
    llm = bench_g9.OracleClient(chosen, config=CFG, overrides=flips)
    result = await score(chosen, llm=llm, config=CFG)
    assert result.line_total == sum(len(c["expected"]["lines"]) for c in chosen)
    assert result.line_correct == result.line_total - 3
    assert result.line_missed == [f"{mixed['id']}#2"]
    assert result.line_false_blocks == [f"{over['id']}#2"]
    assert result.line_wrong_kind == [f"{hard['id']}#3"]


async def test_an_error_call_counts_every_line_of_the_step_as_wrong_not_as_missed():
    cases = [c for c in load_cases(SETUP_PATH) if c["id"] == "setup-mixed-characters"]
    llm = FakeLLM.scripted([json.dumps({"lines": [], "reason": "x"})] * 3)
    result = await score(cases, llm=llm, config=CFG)
    assert result.errors == 1 and result.correct == 0
    assert result.line_total == 4 and result.line_correct == 0
    assert result.line_missed == [] and result.line_false_blocks == []


def test_dry_run_walks_the_whole_set_with_an_oracle_and_prints_calls_cost_and_line_counts(capsys):
    assert bench_g9.main(["--dry-run", "--cases", str(SETUP_PATH)]) == 0
    out = capsys.readouterr().out
    assert f"{len(RAW_CASES)} lời gọi" in out and "USD" in out
    assert f"dòng đúng {len(LINES)}/{len(LINES)}" in out


def test_default_set_path_is_unchanged_and_other_sets_still_load():
    assert CASES_PATH.name == "g9_moderation.yaml"
    assert load_cases(HOLDOUT_V2_PATH)[0]["expected"]["verdict"] in {v.value for v in Verdict}
    assert Path(SETUP_PATH).exists()
