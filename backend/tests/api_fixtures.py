"""Dùng chung cho test API (D-41, D-44): cấu hình app dev, kho key và nhật ký chi phí trong bộ nhớ
(cùng giao thức với bản Postgres trong `api/deps.py`), và nhà máy client model giả ghi lại key nhận
được (để test G7 chứng minh key giải mã đi tới client model, không đi đâu khác)."""

import asyncio
import json
import logging
import os
import socket
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime

import psycopg
import uvicorn
from cryptography.fernet import Fernet
from pydantic import SecretStr

from writory.config import Settings
from writory.db import CostEntry, OwnerCosts
from writory.llm.base import GenerationCost, LLMClient
from writory.llm.ledger import PendingEstimate

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
        self.asked_now: list[datetime] = []
        self._story_spent = story_spent
        self._setup_spent = setup_spent

    def record(self, entry: CostEntry, *, story_id: str | None = None,
               setup_id: str | None = None, chapter: int | None = None) -> None:
        self.rows.append((entry, story_id, setup_id, chapter))

    def story_spent(self, story_id: str) -> float:
        return self._story_spent + sum(e.cost_usd or 0 for e, s, _, _ in self.rows if s == story_id)

    def setup_spent(self, setup_id: str) -> float:
        return self._setup_spent + sum(e.cost_usd or 0 for e, _, s, _ in self.rows if s == setup_id)

    def pending_estimates(self, *, story_id: str | None = None, setup_id: str | None = None,
                          limit: int) -> list[PendingEstimate]:
        """Id dòng là vị trí trong `rows` (D-64)."""
        return [PendingEstimate(i, e.generation_id) for i, (e, s, u, _) in enumerate(self.rows)
                if e.estimated and e.generation_id is not None
                and (s, u) == (story_id, setup_id)][:limit]

    def settle_estimate(self, row_id: int, cost: GenerationCost) -> None:
        entry, *where = self.rows[row_id]
        if entry.estimated:
            self.rows[row_id] = (replace(entry, cost_usd=cost.cost_usd, estimated=False,
                                         prompt_tokens=cost.prompt_tokens,
                                         completion_tokens=cost.completion_tokens), *where)

    def owner_costs(self, now: datetime) -> OwnerCosts:
        """Như bản Postgres, trừ tháng: dòng trong bộ nhớ không có giờ, nên mọi dòng tính vào tháng
        của `now`. Truyện tiêu gần nhất đứng trước."""
        self.asked_now.append(now)
        total = sum(e.cost_usd or 0 for e, *_ in self.rows)
        by_story: dict[str, float] = {}
        for e, story_id, _, _ in reversed(self.rows):
            if story_id is not None:
                by_story[story_id] = by_story.get(story_id, 0.0) + (e.cost_usd or 0)
        return OwnerCosts(total, total, tuple(by_story.items()))


class KeyedFactory:
    """Nhà máy client model: trả `llm` và ghi lại mọi key được đưa vào."""

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm
        self.keys: list[str] = []

    def __call__(self, api_key: SecretStr) -> LLMClient:
        self.keys.append(api_key.get_secret_value())
        return self.llm


class AllowAllQuota:
    """Bộ đếm tần suất luôn cho qua, cho test không có Postgres (cùng giao thức `CallQuota`)."""

    async def take(self) -> bool:
        return True


def offline(app) -> None:
    """Test không Docker: kết nối Postgres giả (None) nên khoá chống chạy đôi và bộ đếm tần suất
    (cả hai cần Postgres thật) được thay bằng bản không làm gì. Hành vi thật của chúng nằm ở test
    graph (tests/graph/test_play_api.py, test_rate_limit.py)."""
    from contextlib import nullcontext

    from writory.api import deps
    from writory.api.setup import lock_setup

    def no_lock():
        with nullcontext():
            yield

    for dep in (deps.lock_story, deps.lock_narrator, lock_setup):
        app.dependency_overrides[dep] = no_lock
    app.dependency_overrides[deps.get_call_quota] = AllowAllQuota


def own_connections() -> Iterator[psycopg.Connection]:
    """Thay `deps.get_pg_conn` trong test graph: mỗi yêu cầu một kết nối Postgres riêng, như app
    thật. Cần cho test khoá chống chạy đôi, vì advisory lock lồng được trên cùng một kết nối."""
    conn = psycopg.connect(os.environ.get(
        "POSTGRES_DSN", "postgresql://writory:change-me-local@localhost:5432/writory"),
        autocommit=True)
    try:
        yield conn
    finally:
        conn.close()


class CountedConnections:
    """Như `own_connections`, và đếm số kết nối đã đóng. Kết nối đóng sau mọi dependency khác của
    yêu cầu (kể cả nhả khoá của truyện), nên số đếm = số yêu cầu đã chạy xong hẳn phía máy chủ:
    test chờ điều kiện này thay vì sleep."""

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self.closed = 0

    def connection(self) -> Iterator[psycopg.Connection]:
        try:
            yield from own_connections()
        finally:
            with self._cond:
                self.closed += 1
                self._cond.notify_all()

    def wait_closed(self, count: int, *, timeout: float) -> bool:
        with self._cond:
            return self._cond.wait_for(lambda: self.closed >= count, timeout=timeout)


class _ReadyServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config) -> None:
        super().__init__(config)
        self.ready = threading.Event()

    async def startup(self, sockets=None) -> None:
        try:
            await super().startup(sockets=sockets)
        finally:
            self.ready.set()


@contextmanager
def live_server(app, *, timeout: float) -> Iterator[str]:
    """Chạy `app` bằng uvicorn thật trong một thread, trên cổng do hệ điều hành chọn; trả URL gốc.
    Chờ uvicorn khởi động xong bằng sự kiện, không sleep. `log_config=None`: không đổi cấu hình
    logging của tiến trình test."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host, port = sock.getsockname()
    server = _ReadyServer(uvicorn.Config(app, log_config=None, lifespan="on",
                                         timeout_graceful_shutdown=5))

    def run() -> None:
        try:
            server.run(sockets=[sock])
        finally:
            server.ready.set()  # khởi động hỏng thì người chờ không treo

    thread = threading.Thread(target=run, name="uvicorn-test", daemon=True)
    thread.start()
    try:
        if not server.ready.wait(timeout) or not server.started:
            raise RuntimeError("uvicorn không khởi động được")
        yield f"http://{host}:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout)
        sock.close()


async def asgi_request(app, method: str, path: str, body: dict | None = None,
                       *, on_send=None, disconnect: asyncio.Event | None = None
                       ) -> tuple[int, bytes]:
    """Gọi app ASGI trực tiếp trên event loop của test, để chạy nhiều yêu cầu song song (TestClient
    chạy tuần tự). `disconnect` được đặt thì yêu cầu báo ngắt kết nối ngay sau đó; không đặt thì
    không bao giờ ngắt."""
    raw = b"" if body is None else json.dumps(body).encode()
    sent_request = False
    messages: list[dict] = []

    async def receive():
        nonlocal sent_request
        if not sent_request:
            sent_request = True
            return {"type": "http.request", "body": raw, "more_body": False}
        await (disconnect or asyncio.Event()).wait()
        return {"type": "http.disconnect"}

    async def send(message):
        messages.append(message)
        if on_send is not None:
            on_send(message)

    headers = [(b"host", b"testserver"), (b"content-type", b"application/json")]
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
             "method": method, "scheme": "http", "path": path, "raw_path": path.encode(),
             "query_string": b"", "root_path": "", "headers": headers,
             "client": ("testclient", 50000), "server": ("testserver", 80), "state": {}}
    await app(scope, receive, send)
    status = next(m["status"] for m in messages if m["type"] == "http.response.start")
    data = b"".join(m.get("body", b"") for m in messages if m["type"] == "http.response.body")
    return status, data


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
