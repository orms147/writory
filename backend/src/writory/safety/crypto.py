"""Mã hoá key OpenRouter của người chơi khi lưu (G7). Khoá: PLAYER_KEY_ENCRYPTION_KEY (D-11)."""

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from writory.errors import ErrorCode, WritoryError
from writory.safety.redact import REDACTED, redact

KEY_PREFIX = "sk-or-"  # key OpenRouter
KEY_MAX_CHARS = 200


class KeyCipher:
    def __init__(self, master_key: SecretStr) -> None:
        try:
            self._fernet = Fernet(master_key.get_secret_value())
        except (ValueError, TypeError):
            raise ValueError(
                "PLAYER_KEY_ENCRYPTION_KEY không phải khoá Fernet hợp lệ "
                "(32 byte, base64 urlsafe); cách tạo: docs/runbook.md"
            ) from None

    def encrypt(self, api_key: SecretStr) -> bytes:
        return self._fernet.encrypt(api_key.get_secret_value().encode())

    def decrypt(self, token: bytes) -> SecretStr:
        try:
            return SecretStr(self._fernet.decrypt(token).decode())
        except InvalidToken:
            raise WritoryError(
                ErrorCode.PLAYER_KEY_UNREADABLE,
                detail="InvalidToken: sai khoá mã hoá hoặc dữ liệu hỏng",
            ) from None


def mask_key(api_key: SecretStr) -> str:
    """Chỉ hiện 4 ký tự cuối (G7)."""
    value = api_key.get_secret_value()
    return "…" + (value[-4:] if len(value) > 4 else "")


def key_last4(api_key: SecretStr) -> str:
    """4 ký tự cuối, cho giao diện hiện "•••• 7f3a" (G7). Chỉ dùng cho key đã qua
    `validate_player_key` (đủ dài, nên 4 ký tự không lộ gì đáng kể)."""
    return api_key.get_secret_value()[-4:]


def validate_player_key(api_key: SecretStr) -> SecretStr:
    """Kiểm dạng key người chơi dán vào (chỉ kiểm định dạng) và bỏ khoảng trắng hai đầu.

    Key phải bắt đầu bằng `sk-or-` và được bộ lọc log nhận ra trọn vẹn (`redact(key) == REDACTED`):
    nhờ vậy nếu key lọt vào một dòng log nào, bộ lọc vẫn xoá được (G7). Sai thì báo
    PLAYER_KEY_INVALID; chi tiết lỗi không chứa key.
    """
    value = api_key.get_secret_value().strip()
    if len(value) > KEY_MAX_CHARS or not value.startswith(KEY_PREFIX) or redact(value) != REDACTED:
        raise WritoryError(
            ErrorCode.PLAYER_KEY_INVALID, detail=f"key không đúng dạng (dài {len(value)} ký tự)"
        )
    return SecretStr(value)
