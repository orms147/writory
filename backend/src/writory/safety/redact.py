"""Xoá chuỗi trông giống key/bí mật xác thực khỏi văn bản sắp ghi log (G7).

Regex ở đây chỉ kiểm định dạng chuỗi, không đọc ý định người dùng (G5).
"""

import logging
import re

REDACTED = "[REDACTED]"

_PATTERNS = [
    (re.compile(r"sk-or-[A-Za-z0-9_-]{8,}"), REDACTED),  # key OpenRouter: sk-or-v1-<hex>
    (re.compile(r"sk-[A-Za-z0-9_-]{20,}"), REDACTED),  # key kiểu OpenAI/Anthropic
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]{8,}"), r"\g<1>" + REDACTED),
    (re.compile(r"gAAAAA[A-Za-z0-9_=-]{20,}"), REDACTED),  # token Fernet (key đã mã hoá)
    # Mã mời và token phiên đăng nhập (D-89): `db.auth.new_invite_code`, `new_session_token`.
    (re.compile(r"(?i)\bwt-[a-z2-7]{4}(?:[-\s]?[a-z2-7]{4}){7}"), REDACTED),
    (re.compile(r"wts_[A-Za-z0-9_-]{20,}"), REDACTED),
    (re.compile(r"(writory_session=)[^;\s]+"), r"\g<1>" + REDACTED),
]


def redact(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def _redact_arg(arg):
    """Giữ nguyên kiểu (formatter như AccessFormatter của uvicorn đọc từng arg); chỉ thay khi
    chữ của arg có chuỗi giống key."""
    if isinstance(arg, str):
        return redact(arg)
    for text in (str(arg), repr(arg)):  # repr cho trường hợp %r
        cleaned = redact(text)
        if cleaned != text:
            return cleaned
    return arg


class RedactSecretsFilter(logging.Filter):
    """Gắn vào handler: xoá chuỗi giống key trong message, từng arg, traceback và stack.

    Redact từng mảnh trước để giữ `record.args` cho formatter đọc args (AccessFormatter của
    uvicorn). Sau đó kiểm câu đã ghép: còn sót (key bị cắt giữa msg và arg) thì gộp thành câu
    đã redact, bỏ args. Trường hợp hiếm đó, formatter đọc args mất định dạng nhưng không lộ key.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        else:
            record.msg = _redact_arg(record.msg)
        if isinstance(record.args, dict):
            record.args = {k: _redact_arg(v) for k, v in record.args.items()}
        elif record.args:
            record.args = tuple(_redact_arg(a) for a in record.args)
        if record.args:
            try:
                full = record.getMessage()
            except (TypeError, ValueError):  # msg và args không khớp: để logging tự báo lỗi
                full = None
            if full is not None and redact(full) != full:
                record.msg, record.args = redact(full), None
        if record.exc_info:
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        if record.stack_info:
            record.stack_info = redact(record.stack_info)
        return True


def install_log_redaction(logger: logging.Logger | None = None) -> None:
    """Gắn bộ lọc vào mọi handler của logger (mặc định: root).

    Gắn vào handler chứ không vào logger, vì filter của logger không chạy với record
    truyền lên từ logger con.
    """
    target = logger or logging.getLogger()
    for handler in target.handlers:
        if not any(isinstance(f, RedactSecretsFilter) for f in handler.filters):
            handler.addFilter(RedactSecretsFilter())
