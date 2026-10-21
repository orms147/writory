import pytest

from writory.errors import MESSAGES, ErrorCode, WritoryError


def test_every_code_has_a_message():
    assert set(MESSAGES) == set(ErrorCode)


@pytest.mark.parametrize("code", list(ErrorCode))
def test_message_says_what_happened_and_what_next(code: ErrorCode):
    msg = MESSAGES[code]
    assert msg.what.strip()
    assert msg.next_step.strip()
    assert msg.what.strip() != msg.next_step.strip()


def test_player_payload_has_code_and_message_only():
    err = WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 502 from provider xyz")
    payload = err.player_payload()
    assert set(payload) == {"code", "message"}
    assert payload["code"] == "LLM_UNAVAILABLE"
    assert MESSAGES[ErrorCode.LLM_UNAVAILABLE].what in payload["message"]
    assert "provider xyz" not in payload["message"]


def test_detail_goes_to_log_text():
    err = WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 502 from provider xyz")
    assert "provider xyz" in str(err)
    assert "LLM_UNAVAILABLE" in str(err)


def test_log_text_redacts_key_like_strings():
    fake_key = "sk-or-v1-" + "a1" * 32
    err = WritoryError(ErrorCode.LLM_AUTH_FAILED, detail=f"rejected {fake_key}")
    assert fake_key not in str(err)
    assert fake_key not in repr(err)


def test_payload_lists_fields_only_when_given():
    """G12: lỗi đầu vào nói trường nào sai; lỗi khác giữ đúng hai khoá như trước."""
    assert set(WritoryError(ErrorCode.REQUEST_INVALID).player_payload()) == {"code", "message"}
    payload = WritoryError(ErrorCode.REQUEST_INVALID,
                           fields=["index", "tags.genre"]).player_payload()
    assert set(payload) == {"code", "message", "fields"}
    assert payload["fields"] == ["index", "tags.genre"]


@pytest.mark.parametrize("code", list(ErrorCode))
def test_no_message_offers_a_cheaper_writer_tier(code: ErrorCode):
    """Bản 1 chỉ có một mức model viết (D-33): không câu lỗi nào bảo người chơi đổi mức model
    (README bàn giao thiết kế, mục 8 điểm 2; D-67)."""
    text = MESSAGES[code].text().casefold()
    assert "mức model" not in text
    assert "rẻ hơn" not in text


@pytest.mark.parametrize("code", [ErrorCode.COST_LIMIT_SCENE, ErrorCode.COST_LIMIT_CHAPTER])
def test_cost_limit_messages_say_saved_work_is_kept_and_retry(code: ErrorCode):
    """G11: chạm trần thì không ghi nửa chừng, nên câu lỗi nói phần đã lưu vẫn còn; bước tiếp là
    thử lại (trần do hệ thống đặt, người chơi không nâng được)."""
    msg = MESSAGES[code]
    assert "trần chi phí" in msg.what
    assert "vẫn còn" in msg.what
    assert "thử lại" in msg.next_step.casefold()
