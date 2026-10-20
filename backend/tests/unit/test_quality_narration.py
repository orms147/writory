"""Kiểm ngôi kể bằng code (design §6.5 mục 5; D-51). Không gọi model.

Lời kể (không tính dòng thoại "- " và chữ trong ngoặc kép) phải đúng ngôi đã chốt của truyện
(`quality.narration.person`). Đo bằng số lần "tôi" trên 100 từ lời kể: đếm đại từ trong văn là kiểm
văn bằng code, không phải đọc ý định người dùng (G5).

Fixture: cảnh 1 của chương 1 và chương 6 trong lần chạy thật `evals/results/2026-10-20-run-tu-tien-1/`
(chương 1–5 kể "tôi", chương 6 chuyển sang ngôi thứ ba).
"""

from pathlib import Path

import pytest

from writory.config import REPO_ROOT, load_config
from writory.errors import ErrorCode, WritoryError
from writory.quality import IssueKind, check_narration, check_scene, narration_instruction

FIXTURES = Path(__file__).parents[1] / "fixtures" / "quality" / "narration"
CH01 = (FIXTURES / "run-tu-tien-1-ch01-scene1.txt").read_text(encoding="utf-8")
CH06 = (FIXTURES / "run-tu-tien-1-ch06-scene1.txt").read_text(encoding="utf-8")
SAMPLE_CH04 = (REPO_ROOT / "data" / "sample-story" / "ch04.md").read_text(encoding="utf-8")

REPO = load_config()
FIRST = REPO.quality
THIRD = REPO.quality.model_copy(update={
    "narration": REPO.quality.narration.model_copy(update={"person": "third"})})


def _with(**changes):
    return REPO.quality.model_copy(update={
        "narration": REPO.quality.narration.model_copy(update=changes)})


def test_repo_story_is_told_in_first_person():
    """Ngôi đã chốt hiện hành: ngôi thứ nhất, người kể xưng "tôi" (D-51)."""
    assert REPO.quality.narration.person == "first"


def test_run_chapter_6_switched_to_third_person_is_caught():
    [issue] = check_narration(CH06, FIRST)
    assert issue.kind is IssueKind.NARRATION_PERSON
    assert '"tôi"' in issue.detail  # góp ý cho lượt viết lại nói rõ phải xưng gì


def test_run_chapter_1_in_first_person_passes():
    assert check_narration(CH01, FIRST) == []


def test_check_scene_runs_the_narration_check():
    issues = check_scene(CH06, scenes_in_chapter=2, quality=FIRST, lengths=REPO.story_lengths)
    assert IssueKind.NARRATION_PERSON in {i.kind for i in issues}
    issues = check_scene(CH01, scenes_in_chapter=2, quality=FIRST, lengths=REPO.story_lengths)
    assert IssueKind.NARRATION_PERSON not in {i.kind for i in issues}


def test_first_person_only_in_dialogue_does_not_count():
    """Dòng thoại "- " không phải lời kể: "tôi" trong thoại không cứu được lời kể ngôi thứ ba."""
    third = "\n\n".join(line for line in CH06.split("\n\n") if not line.startswith("-"))
    talk = "\n\n".join(f"- Tôi biết, tôi sẽ giữ chốt, tôi hứa. ({i})" for i in range(12))
    assert check_narration(f"{third}\n\n{talk}", FIRST)


def test_first_person_inside_quotes_does_not_count():
    third = "\n\n".join(line for line in CH06.split("\n\n") if not line.startswith("-"))
    quoted = "Trên vách đá có khắc: “Tôi ở đây, tôi chờ, tôi không đi, tôi còn sống.”"
    assert check_narration(f"{quoted}\n\n{third}", FIRST)


def test_short_narration_is_not_judged():
    """Lời kể ngắn hơn `min_words` từ (cảnh gần như toàn thoại): không đủ để kết luận."""
    text = "Kỷ Trầm Uyên gật đầu.\n\n- Đi thôi.\n\n- Ừ."
    assert check_narration(text, FIRST) == []


def test_third_person_story_flags_first_person_narration():
    assert check_narration(CH01, THIRD)
    assert check_narration(CH06, THIRD) == []


def test_hand_written_sample_story_is_third_person():
    """Truyện mẫu (data/sample-story/) kể ngôi thứ ba: không báo nhầm ở chế độ ngôi thứ ba."""
    body = "\n".join(line for line in SAMPLE_CH04.splitlines() if not line.startswith("#"))
    assert check_narration(body, THIRD) == []


@pytest.mark.parametrize("key", ["min_words", "first_person_min_per_100_words"])
def test_unset_threshold_is_config_error(key):
    with pytest.raises(WritoryError) as exc:
        check_narration(CH06, _with(**{key: None}))
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert "quality.yaml" in str(exc.value)


@pytest.mark.parametrize(("person", "word"), [("first", '"tôi"'), ("third", "ngôi thứ ba")])
def test_writer_instruction_comes_from_the_same_config(person, word):
    """Đề viết nói đúng ngôi mà phép kiểm đòi (một nguồn: `quality.narration.person`)."""
    assert word in narration_instruction(_with(person=person))
