"""G12: lỗi ghi chương có mã riêng và câu tiếng Việt; chi tiết chỉ vào log, đã redact."""

import pytest

from writory.db import (
    ChapterCommitError,
    ChapterError,
    ChapterOrderError,
    ChapterPackageError,
    ChapterQuoteError,
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
    (ChapterQuoteError, ErrorCode.CHAPTER_QUOTE_NOT_IN_TEXT),
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


# --- G3 ở bước ghi (D-106): câu trích bịa thì không ghi gì, không cần Postgres hay Neo4j -----------


def _quote_package(quote: str):
    from writory.graph import ChangePackage

    return ChangePackage.model_validate({"commit_id": "c3", "edges": [
        {"type": "REVEALED_TO_PLAYER", "from": "f_x", "to": "ch3", "valid_from_chapter": 3,
         "quote": quote},
        {"type": "KNOWS", "from": "pc", "to": "f_x", "valid_from_chapter": 3, "how": "chứng kiến",
         "quote": quote},
    ]})


@pytest.fixture
def spy_writes(monkeypatch):
    import writory.db.chapters as chapters_mod

    writes: list[str] = []
    monkeypatch.setattr(chapters_mod, "protagonist_id", lambda _driver, _sid: "pc")
    monkeypatch.setattr(chapters_mod, "_record_pending", lambda *_a: writes.append("pending"))
    monkeypatch.setattr(chapters_mod, "_apply", lambda *_a: writes.append("apply"))
    monkeypatch.setattr(chapters_mod, "_mark_committed", lambda *_a: writes.append("committed"))
    return writes


def test_fabricated_quote_is_rejected_before_any_write(spy_writes, caplog):
    import logging

    from writory.db import commit_chapter

    with caplog.at_level(logging.WARNING, logger="writory.db.chapters"),             pytest.raises(ChapterQuoteError) as info:
        commit_chapter(None, None, "s1", 3, ["Trời mưa suốt đêm."], _quote_package("Lan là gián điệp."))
    assert spy_writes == []
    assert info.value.code is ErrorCode.CHAPTER_QUOTE_NOT_IN_TEXT
    assert "REVEALED_TO_PLAYER" in str(info.value) and "KNOWS" in str(info.value)
    assert "gián điệp" not in info.value.player_payload()["message"]
    assert "REVEALED_TO_PLAYER" in caplog.text  # chi tiết vào log máy chủ


def test_quote_found_in_a_scene_is_written(spy_writes):
    from writory.db import commit_chapter

    commit_chapter(None, None, "s1", 3, ["Mở đầu.", "Lan là gián điệp, ai cũng biết."],
                   _quote_package("Lan là gián điệp"))
    assert spy_writes == ["pending", "apply", "committed"]


def test_chapter_zero_quotes_come_from_the_story_brief(spy_writes):
    """D-74: câu trích ở chương 0 là dòng của thiết lập truyện, không có văn chương để đối chiếu."""
    from writory.db import commit_chapter
    from writory.graph import ChangePackage

    package = ChangePackage.model_validate({"commit_id": "c0", "edges": [
        {"type": "REVEALED_TO_PLAYER", "from": "pc", "to": "ch0", "valid_from_chapter": 0,
         "quote": "Nhân vật chính: Lục Thanh Vân", "known_as": "Lục Thanh Vân"}]})
    commit_chapter(None, None, "s1", 0, [], package)
    assert spy_writes == ["pending", "apply", "committed"]
