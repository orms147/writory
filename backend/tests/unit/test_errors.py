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
