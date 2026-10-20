"""Kiểm văn bằng code (design §6.5 mục 5). Không gọi LLM.

Ngưỡng trong config/quality.yaml đang null (chưa đo). Test dùng NGƯỠNG THỬ bên dưới; số này
chỉ để test, không phải giá trị chốt.
"""

import unicodedata
from pathlib import Path

import pytest
import yaml

from writory.config import REPO_ROOT, load_config
from writory.errors import ErrorCode, WritoryError
from writory.quality import (
    IssueKind,
    check_cliches,
    check_dialogue,
    check_foreign_script,
    check_length,
    check_repetition,
    check_scene,
    normalize_dashes,
)

FIXTURES = Path(__file__).parents[1] / "fixtures" / "quality"
CASES = yaml.safe_load((FIXTURES / "cases.yaml").read_text(encoding="utf-8"))["cases"]
CLEAN = sorted((FIXTURES / "clean").glob("*.txt"))
SAMPLE_STORY = sorted((REPO_ROOT / "data" / "sample-story").glob("ch*.md"))

REPO = load_config()
TRIAL = REPO.quality.model_copy(
    update={
        "repetition": REPO.quality.repetition.model_copy(
            update={"ngram_words": 4, "max_repeats": 2}
        ),
        "foreign_script": REPO.quality.foreign_script.model_copy(
            update={"latin_run_min_words": 4}
        ),
        # Văn sạch trong fixtures/quality/clean/ kể ngôi thứ ba (D-51: ngôi theo config).
        "narration": REPO.quality.narration.model_copy(update={"person": "third"}),
    }
)


def all_but_length(text: str):
    return (
        check_repetition(text, TRIAL)
        + check_cliches(text, TRIAL)
        + check_foreign_script(text, TRIAL)
        + check_dialogue(text, TRIAL)
    )


# --- cấu hình ---------------------------------------------------------------------------


def test_repo_quality_config_loads():
    assert REPO.quality.dialogue_style == "dash"
    assert REPO.quality.cliches.phrases


def test_unset_threshold_is_config_error_not_skipped():
    unset = REPO.quality.repetition.model_copy(update={"max_repeats": None})
    quality = REPO.quality.model_copy(update={"repetition": unset})
    with pytest.raises(WritoryError) as exc:
        check_scene("Một cảnh.", scenes_in_chapter=2, quality=quality,
                    lengths=REPO.story_lengths)
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert "quality.yaml" in str(exc.value)


def test_quotes_style_is_not_supported_yet():
    cfg = TRIAL.model_copy(update={"dialogue_style": "quotes"})
    with pytest.raises(ValueError, match="chưa hỗ trợ"):
        check_dialogue("“Chào.”", cfg)


# --- từng ca cài lỗi / ca hợp lệ ---------------------------------------------------------


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_case_reports_exactly_expected_kinds(case):
    kinds = {issue.kind.value for issue in all_but_length(case["text"])}
    assert kinds == set(case["expect"])


def test_issue_points_at_offending_text():
    text = "Lão Gù đặt thanh kiếm xuống. The ancient sword glowed with a strange light. Minh lùi lại."
    [issue] = check_foreign_script(text, TRIAL)
    assert issue.kind is IssueKind.FOREIGN_SCRIPT
    assert issue.excerpt == text[issue.start : issue.end]
    assert "ancient" in issue.excerpt
    assert "Minh" not in issue.excerpt
    assert issue.detail


def test_overlapping_repeats_become_one_issue():
    text = next(c["text"] for c in CASES if c["id"] == "lap-cum")
    issues = check_repetition(text, TRIAL)
    assert len(issues) == 1
    assert "3" in issues[0].detail


# Lần chạy tu-tien-1 (notes.md mục 5): tên một đồ vật 4 từ nhắc 3 lần trong cảnh bị bắt viết lại.
ITEM = "Tín Vật Huyền Nguyệt"
NAMED_THRICE = ("Tôi siết Tín Vật Huyền Nguyệt trong tay. Gió lùa qua khe đá. Lục Hàn Sương nhìn "
                "Tín Vật Huyền Nguyệt rồi quay đi. Tới lúc trời sáng, tín vật huyền nguyệt vẫn lạnh.")


def test_entity_name_repeated_is_not_repetition():
    """Tên hay biệt danh của thực thể không phải cụm lặp (D-51): tên tính như một từ."""
    [issue] = check_repetition(NAMED_THRICE, TRIAL)  # không biết tên: bị đếm như trước
    assert "tín vật huyền nguyệt" in issue.detail
    assert check_repetition(NAMED_THRICE, TRIAL, names=[ITEM]) == []
    nfd = unicodedata.normalize("NFD", NAMED_THRICE)
    assert check_repetition(nfd, TRIAL, names=[unicodedata.normalize("NFD", ITEM)]) == []


def test_phrase_around_a_name_still_counts_as_repetition():
    """Tên tính như một từ, nên câu lặp quanh tên vẫn bị bắt: "đặt <tên> lên bàn" là 4 từ."""
    text = ("Tôi đặt Tín Vật Huyền Nguyệt lên bàn đá. Nàng bảo tôi đặt Tín Vật Huyền Nguyệt lên bàn "
            "gỗ. Lát sau tôi lại đặt Tín Vật Huyền Nguyệt lên bàn cũ.")
    [issue] = check_repetition(text, TRIAL, names=[ITEM])
    assert text[issue.start:issue.end].startswith("đặt Tín Vật Huyền Nguyệt lên bàn")


def test_repeated_phrase_that_is_not_a_name_still_counts():
    """"trận quanh linh mạch" (lần chạy tu-tien-1, chương 6) không phải tên thực thể nào."""
    text = ("Mỗi nhịp giữ thêm, trận quanh linh mạch yếu đi. Chàng biết trận quanh linh mạch sắp "
            "vỡ. Nàng nhắc rằng trận quanh linh mạch cần người giữ.")
    [issue] = check_repetition(text, TRIAL, names=["Động Linh Mạch", ITEM])
    assert "trận quanh linh mạch" in issue.detail


def test_check_scene_passes_names_to_the_repetition_check():
    kw = {"scenes_in_chapter": 2, "quality": TRIAL, "lengths": REPO.story_lengths}
    assert IssueKind.REPETITION in {i.kind for i in check_scene(NAMED_THRICE, **kw)}
    assert IssueKind.REPETITION not in {i.kind for i in check_scene(NAMED_THRICE, names=[ITEM],
                                                                     **kw)}


def test_each_cjk_run_is_one_issue():
    issues = check_foreign_script("Trà 好喝 lắm, còn bánh 很甜.", TRIAL)
    assert [i.excerpt for i in issues] == ["好喝", "很甜"]


def test_decomposed_unicode_is_normalised_before_matching():
    nfd = unicodedata.normalize("NFD", "Khi ấy, thời gian như ngừng trôi.")
    [issue] = check_cliches(nfd, TRIAL)
    assert issue.excerpt == "thời gian như ngừng trôi"


@pytest.mark.parametrize(("raw", "want"), [
    ("— Anh uống đi.", "- Anh uống đi."),
    ("– Anh uống đi.", "- Anh uống đi."),
    ("—Anh đi đâu?", "- Anh đi đâu?"),
    ("-Ai đó?", "- Ai đó?"),
    ("  — Thụt lề.", "  - Thụt lề."),
    ("Thanh Sương, — lão nói, không ngẩng lên.", "Thanh Sương, - lão nói, không ngẩng lên."),
    ("Anh chép sách phải không? — cô hỏi.", "Anh chép sách phải không? - cô hỏi."),
    ("Chiến tranh 1945–1954, số nhà 12-14.", "Chiến tranh 1945-1954, số nhà 12-14."),
    ("Minh im lặng.\n\n—\n\nLan quay đi.", "Minh im lặng.\n\n-\n\nLan quay đi."),
])
def test_normalize_dashes_turns_every_dash_into_hyphen(raw, want):
    """D-31: backend thay mọi " — " bằng " - "; dòng thoại thành "- "."""
    assert normalize_dashes(raw) == want
    assert normalize_dashes(want) == want  # chạy lại không đổi gì


def test_only_dash_line_is_still_an_error_after_normalising():
    [issue] = check_dialogue("—", TRIAL)
    assert issue.kind == "dialogue_format"


# --- độ dài -------------------------------------------------------------------------------


def test_length_range_follows_number_of_scenes():
    lengths = REPO.story_lengths
    n = lengths.scenes_per_chapter.max
    low = lengths.chapter_chars.min // n
    assert check_length("x" * (low + 10), n, lengths) == []
    [short] = check_length("x" * (low - 10), n, lengths)
    assert short.kind is IssueKind.LENGTH
    high = lengths.chapter_chars.max // n
    assert check_length("x" * (high + 10), n, lengths)[0].kind is IssueKind.LENGTH


def test_length_ignores_extra_whitespace():
    lengths = REPO.story_lengths
    n = lengths.scenes_per_chapter.max
    low = lengths.chapter_chars.min // n
    padded = "x" * (low - 10) + " \n\n   " * 50
    assert check_length(padded, n, lengths)


def test_scene_count_outside_config_is_rejected():
    with pytest.raises(ValueError):
        check_length("x", REPO.story_lengths.scenes_per_chapter.max + 1, REPO.story_lengths)


# --- báo nhầm trên văn sạch ----------------------------------------------------------------


@pytest.mark.parametrize("path", CLEAN, ids=[p.stem for p in CLEAN])
def test_clean_scene_has_no_issues(path: Path):
    text = path.read_text(encoding="utf-8")
    issues = check_scene(text, scenes_in_chapter=3, quality=TRIAL, lengths=REPO.story_lengths)
    assert issues == []


@pytest.mark.skipif(not SAMPLE_STORY, reason="chưa có data/sample-story/ trên nhánh này")
@pytest.mark.parametrize("path", SAMPLE_STORY, ids=[p.stem for p in SAMPLE_STORY])
def test_hand_written_sample_story_has_no_issues(path: Path):
    """Truyện mẫu viết tay: không được báo nhầm. Bỏ dòng tiêu đề markdown; không kiểm độ dài."""
    lines = path.read_text(encoding="utf-8").splitlines()
    text = "\n".join(line for line in lines if not line.startswith("#"))
    assert all_but_length(text) == []


def test_issues_are_sorted_by_position():
    # D-31: dấu gạch được chuẩn hoá nên không còn là lỗi; dòng mở bằng ngoặc kép thì vẫn lỗi.
    text = "他 thời gian như ngừng trôi.\n\n—Đi thôi.\n\n“Về thôi.”"
    issues = check_scene(text, scenes_in_chapter=2, quality=TRIAL, lengths=REPO.story_lengths)
    starts = [i.start for i in issues]
    assert starts == sorted(starts)
    assert {i.kind for i in issues} >= {
        IssueKind.FOREIGN_SCRIPT, IssueKind.CLICHE, IssueKind.DIALOGUE_FORMAT, IssueKind.LENGTH
    }
