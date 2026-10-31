"""Truyện audio: thoại liền nhau quá nhiều lượt thì giọng đọc máy không cho người nghe biết ai nói (D-156)."""

from writory.config import load_config
from writory.quality.checks import IssueKind, check_dialogue_attribution


def test_more_than_n_dialogue_lines_in_a_row_is_one_issue_per_run():
    text = "Tôi bước vào.\n- Một.\n- Hai.\n- Ba.\nCô ta cười.\n- Bốn.\n- Năm.\n- Sáu.\n- Bảy."
    issues = check_dialogue_attribution(text, max_run=2)
    assert [i.kind for i in issues] == [IssueKind.DIALOGUE_UNATTRIBUTED] * 2
    assert text[issues[0].start:issues[0].end].startswith("- Một.") and "3 lượt" in issues[0].detail
    assert "4 lượt" in issues[1].detail


def test_a_narration_line_between_turns_starts_the_count_again():
    assert check_dialogue_attribution("- A.\n- B.\nTôi đáp.\n- C.\n- D.", max_run=2) == []


def test_a_blank_line_does_not_tell_the_listener_who_speaks():
    # Giọng đọc máy đọc liền: dòng trống không phải câu dẫn, nên không cắt chuỗi thoại.
    assert len(check_dialogue_attribution("- C.\n- D.\n\n- E.", max_run=2)) == 1


def test_other_dash_kinds_count_as_dialogue_after_normalising():
    assert len(check_dialogue_attribution("— Một.\n– Hai.\n- Ba.", max_run=2)) == 1


def test_the_run_limit_comes_from_quality_config():
    assert load_config().quality.audio_dialogue_max_run == 2
