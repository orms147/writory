"""Mã hoá key OpenRouter của người chơi khi lưu (G7). Khoá: PLAYER_KEY_ENCRYPTION_KEY (D-11)."""

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr

from writory.errors import ErrorCode, WritoryError


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
