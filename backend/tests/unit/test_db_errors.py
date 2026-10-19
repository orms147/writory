"""G12: lỗi ghi chương có mã riêng và câu tiếng Việt; chi tiết chỉ vào log, đã redact."""

import pytest

from writory.db import (
    ChapterCommitError,
    ChapterError,
    ChapterOrderError,
    ChapterPackageError,
    PendingChapterError,
    StoryNotFoundError,
)
from writory.errors import MESSAGES, ErrorCode, WritoryError

CASES = [
    (ChapterCommitError, ErrorCode.CHAPTER_SAVE_FAILED),
    (ChapterError, ErrorCode.CHAPTER_SAVE_FAILED),
    (PendingChapterError, ErrorCode.CHAPTER_PENDING),
    (ChapterOrderError, ErrorCode.CHAPTER_OUT_OF_ORDER),
    (ChapterPackageError, ErrorCode.CHAPTER_PACKAGE_INVALID),
    (StoryNotFoundError, ErrorCode.STORY_NOT_FOUND),
]


@pytest.mark.parametrize(("exc_type", "code"), CASES)
def test_db_errors_carry_player_code(exc_type, code):
    err = exc_type("commit c7: id không có trong truyện: ['ghost_item']")
    assert isinstance(err, WritoryError)
    assert err.code == code
    payload = err.player_payload()
    assert payload == {"code": code.value, "message": MESSAGES[code].text()}
    assert "ghost_item" not in payload["message"]
    assert "ghost_item" in str(err)


def test_db_error_detail_is_redacted():
    fake_key = "sk-or-v1-" + "b2" * 32
    err = ChapterCommitError(f"neo4j said {fake_key}")
    assert fake_key not in str(err)
