"""G7: key người chơi mã hoá khi lưu; log và phản hồi lỗi không chứa key."""

import io
import json
import logging

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from writory.errors import ErrorCode, WritoryError
from writory.safety.crypto import KeyCipher, mask_key
from writory.safety.redact import REDACTED, RedactSecretsFilter, install_log_redaction, redact

FAKE_KEY = "sk-or-v1-" + "fedcba9876543210" * 4


@pytest.fixture
def cipher() -> KeyCipher:
    return KeyCipher(SecretStr(Fernet.generate_key().decode()))


def test_encrypt_then_decrypt_roundtrip(cipher: KeyCipher):
    token = cipher.encrypt(SecretStr(FAKE_KEY))
    assert FAKE_KEY.encode() not in token
    assert cipher.decrypt(token).get_secret_value() == FAKE_KEY


def test_decrypt_with_other_master_key_is_player_error(cipher: KeyCipher):
    token = cipher.encrypt(SecretStr(FAKE_KEY))
    other = KeyCipher(SecretStr(Fernet.generate_key().decode()))
    with pytest.raises(WritoryError) as exc:
        other.decrypt(token)
    assert exc.value.code is ErrorCode.PLAYER_KEY_UNREADABLE


def test_decrypt_garbage_is_player_error(cipher: KeyCipher):
    with pytest.raises(WritoryError) as exc:
        cipher.decrypt(b"not-a-token")
    assert exc.value.code is ErrorCode.PLAYER_KEY_UNREADABLE


def test_bad_master_key_fails_at_startup_without_echoing_it():
    with pytest.raises(ValueError) as exc:
        KeyCipher(SecretStr("too-short-master-key"))
    assert "too-short-master-key" not in str(exc.value)


def test_mask_shows_only_last_four():
    masked = mask_key(SecretStr(FAKE_KEY))
    assert masked.endswith(FAKE_KEY[-4:])
    assert FAKE_KEY[:-4] not in masked
    assert sum(ch.isalnum() for ch in masked) == 4


@pytest.mark.parametrize(
    "text",
    [
        f"calling openrouter with {FAKE_KEY}",
        f"headers={{'Authorization': 'Bearer {FAKE_KEY}'}}",
        "key=sk-proj-" + "x" * 40,
        "authorization: bearer abcdefghijklmnop1234",
    ],
)
def test_redact_removes_key_like_strings(text: str):
    out = redact(text)
    assert REDACTED in out
    assert FAKE_KEY not in out
    assert "abcdefghijklmnop1234" not in out


def test_redact_keeps_normal_vietnamese_text():
    text = "Lan rút thanh kiếm sk-ra khỏi vỏ; Minh đứng im."
    assert redact(text) == text


def _capture_logger(name: str) -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger(name)
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.DEBUG)
    install_log_redaction(logger)
    return logger, stream


def test_log_message_and_args_are_redacted():
    logger, stream = _capture_logger("writory.test.args")
    logger.info("dùng key %s cho truyện %s", FAKE_KEY, "abc")
    logger.warning(f"thử lại với Bearer {FAKE_KEY}")
    out = stream.getvalue()
    assert FAKE_KEY not in out
    assert "truyện abc" in out


def test_logged_exception_traceback_is_redacted():
    logger, stream = _capture_logger("writory.test.exc")
    try:
        raise RuntimeError(f"upstream said: invalid key {FAKE_KEY}")
    except RuntimeError:
        logger.exception("gọi model lỗi")
    out = stream.getvalue()
    assert "RuntimeError" in out
    assert FAKE_KEY not in out


def test_child_logger_records_are_redacted_by_handler_filter():
    parent, stream = _capture_logger("writory.test.parent")
    child = logging.getLogger("writory.test.parent.child")
    child.propagate = True
    child.error("key=%s", FAKE_KEY)
    assert FAKE_KEY not in stream.getvalue()
    assert any(isinstance(f, RedactSecretsFilter) for f in parent.handlers[0].filters)


def test_install_is_idempotent():
    logger, _ = _capture_logger("writory.test.idem")
    install_log_redaction(logger)
    assert sum(isinstance(f, RedactSecretsFilter) for f in logger.handlers[0].filters) == 1


def test_error_payload_and_log_text_never_contain_key():
    err = WritoryError(ErrorCode.LLM_AUTH_FAILED, detail=f"401 for key {FAKE_KEY}")
    assert FAKE_KEY not in json.dumps(err.player_payload(), ensure_ascii=False)
    logger, stream = _capture_logger("writory.test.err")
    logger.error("lỗi: %s", err)
    assert FAKE_KEY not in stream.getvalue()


def test_filter_keeps_args_for_formatters_that_read_them():
    """Hồi quy: AccessFormatter của uvicorn đọc record.args (client, method, path, version,
    status). Bộ lọc không được gộp args thành None; vẫn phải xoá key trong args."""
    from uvicorn.logging import AccessFormatter

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(AccessFormatter('%(client_addr)s - "%(request_line)s" %(status_code)s',
                                         use_colors=False))
    logger = logging.getLogger("writory.test.access")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    install_log_redaction(logger)
    logger.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:5", "GET", f"/x?key={FAKE_KEY}", "1.1", 404)
    out = stream.getvalue()
    assert "127.0.0.1:5" in out and "404" in out and "GET /x?key=" in out
    assert FAKE_KEY not in out


def test_key_split_between_message_and_arg_is_redacted():
    """Hồi quy (review bảo mật): redact từng mảnh thì bỏ sót key bị cắt giữa msg và arg."""
    logger, stream = _capture_logger("writory.test.split")
    logger.info("key=sk-or-v1-%s", FAKE_KEY.removeprefix("sk-or-v1-"))
    assert FAKE_KEY not in stream.getvalue()
    assert REDACTED in stream.getvalue()


def test_key_only_in_repr_is_redacted():
    class Holder:
        def __str__(self) -> str:
            return "Holder"

        def __repr__(self) -> str:
            return f"Holder(key={FAKE_KEY!r})"

    logger, stream = _capture_logger("writory.test.repr")
    logger.info("obj=%r", Holder())
    assert FAKE_KEY not in stream.getvalue()
