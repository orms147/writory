"""Dùng chung cho test API (D-41, D-44): cấu hình app dev, kho key và nhật ký chi phí trong bộ nhớ
(cùng giao thức với bản Postgres trong `api/deps.py`), và nhà máy client model giả ghi lại key nhận
được (để test G7 chứng minh key giải mã đi tới client model, không đi đâu khác)."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from cryptography.fernet import Fernet
from pydantic import SecretStr

from writory.config import Settings
from writory.db import CostEntry
from writory.llm.base import LLMClient

FAKE_KEY = "sk-or-v1-" + "5eed1e55" * 8  # dạng key OpenRouter, không phải key thật
MASTER_KEY = Fernet.generate_key().decode()


def dev_settings(*, dev: bool = True, master_key: str = MASTER_KEY) -> Settings:
    return Settings(
        _env_file=None,
        neo4j_uri="bolt://neo4j.invalid:7687",
        neo4j_user="neo4j",
        neo4j_password="pw",
        postgres_dsn="postgresql://u:p@pg.invalid/db",
        player_key_encryption_key=master_key,
        enable_dev_routes=dev,
    )


class MemoryKeyStore:
    def __init__(self, token: bytes | None = None) -> None:
        self.token = token

    def load(self) -> bytes | None:
        return self.token

    def save(self, token: bytes) -> None:
        self.token = token

    def delete(self) -> bool:
        had, self.token = self.token is not None, None
        return had


class MemoryCostLedger:
    def __init__(self, *, story_spent: float = 0.0, setup_spent: float = 0.0) -> None:
        self.rows: list[tuple[CostEntry, str | None, str | None, int | None]] = []
        self._story_spent = story_spent
        self._setup_spent = setup_spent

    def record(self, entry: CostEntry, *, story_id: str | None = None,
               setup_id: str | None = None, chapter: int | None = None) -> None:
        self.rows.append((entry, story_id, setup_id, chapter))

    def story_spent(self, story_id: str) -> float:
        return self._story_spent + sum(e.cost_usd or 0 for e, s, _, _ in self.rows if s == story_id)

    def setup_spent(self, setup_id: str) -> float:
        return self._setup_spent + sum(e.cost_usd or 0 for e, _, s, _ in self.rows if s == setup_id)


class KeyedFactory:
    """Nhà máy client model: trả `llm` và ghi lại mọi key được đưa vào."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.keys: list[str] = []

    def __call__(self, api_key: SecretStr) -> LLMClient:
        self.keys.append(api_key.get_secret_value())
        return self.llm


class CaptureLogs(logging.Handler):
    """Gắn thẳng vào logger gốc của gói `writory` và vào root: không qua bộ lọc redaction, nên chỉ
    xanh khi chính code không ghi key (G7)."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())
        if record.exc_info:
            self.lines.append(logging.Formatter().formatException(record.exc_info))

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@contextmanager
def captured_logs() -> Iterator[CaptureLogs]:
    handler = CaptureLogs()
    loggers = [logging.getLogger(n) for n in ("", "writory", "uvicorn", "uvicorn.error")]
    old_levels = [lg.level for lg in loggers]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.DEBUG)
    try:
        yield handler
    finally:
        for lg, level in zip(loggers, old_levels, strict=True):
            lg.removeHandler(handler)
            lg.setLevel(level)
