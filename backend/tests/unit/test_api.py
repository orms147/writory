"""Khung API (D-29): lỗi theo G12, redaction log (G7), /health. TestClient, không cần Docker."""

import logging

import pytest
from fastapi.testclient import TestClient

from writory.api import create_app
from writory.api.errors import HTTP_STATUS
from writory.config import Settings
from writory.errors import MESSAGES, ErrorCode, WritoryError
from writory.safety.redact import REDACTED, RedactSecretsFilter

FAKE_KEY = "sk-or-v1-" + "c0ffee12" * 8
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def settings() -> Settings:
    return Settings(
        _env_file=None,
        neo4j_uri="bolt://neo4j.invalid:7687",
        neo4j_user="neo4j",
        neo4j_password="pw-not-in-response",
        postgres_dsn="postgresql://u:dsn-secret@pg.invalid/db",
        player_key_encryption_key="enc-not-in-response",
    )


async def ok() -> bool:
    return True


def build(checks=None):
    app = create_app(settings(), health_checks=checks or {"neo4j": ok, "postgres": ok})

    @app.get("/test/boom")
    async def boom():
        raise RuntimeError(f"upstream rejected key {FAKE_KEY}")

    @app.get("/test/rate-limited")
    async def rate_limited():
        raise WritoryError(ErrorCode.LLM_RATE_LIMITED, detail=f"429 for {FAKE_KEY}")

    return app


def test_every_error_code_has_one_http_status():
    assert set(HTTP_STATUS) == set(ErrorCode)
    assert all(400 <= s < 600 for s in HTTP_STATUS.values())


def test_writory_error_returns_player_payload_and_status():
    with TestClient(build(), raise_server_exceptions=False) as client:
        resp = client.get("/test/rate-limited")
    assert resp.status_code == HTTP_STATUS[ErrorCode.LLM_RATE_LIMITED] == 429
    assert resp.json() == WritoryError(ErrorCode.LLM_RATE_LIMITED).player_payload()
    assert FAKE_KEY not in resp.text


class _Capture(logging.Handler):
    """Gắn thẳng vào logger của module: chạy trước handler của root, không có bộ lọc redaction,
    nên chỉ xanh khi chính code đã redact (không nhờ install_log_redaction)."""

    def __init__(self) -> None:
        super().__init__()
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.lines.append(record.getMessage())


def test_unexpected_error_is_generic_and_leaks_nothing():
    capture = _Capture()
    logger = logging.getLogger("writory.api.errors")
    logger.addHandler(capture)
    try:
        with TestClient(build(), raise_server_exceptions=False) as c:
            resp = c.get("/test/boom")
    finally:
        logger.removeHandler(capture)
    logged = "\n".join(capture.lines)
    assert resp.status_code == 500
    assert resp.json() == {
        "code": "INTERNAL_ERROR",
        "message": MESSAGES[ErrorCode.INTERNAL_ERROR].text(),
    }
    for leaked in (FAKE_KEY, "Traceback", "RuntimeError", "upstream rejected"):
        assert leaked not in resp.text
    assert "RuntimeError" in logged  # chi tiết có trong log...
    assert REDACTED in logged
    assert FAKE_KEY not in logged  # ...nhưng đã redact


@pytest.fixture
def uvicorn_handlers():
    """Giả lập cấu hình log của uvicorn: mỗi logger có handler riêng, không truyền lên root."""
    added = []
    for name in (*UVICORN_LOGGERS, ""):
        handler = logging.StreamHandler()
        logging.getLogger(name or None).addHandler(handler)
        added.append((name, handler))
    yield {name: handler for name, handler in added}
    for name, handler in added:
        logging.getLogger(name or None).removeHandler(handler)


def test_startup_installs_redaction_on_root_and_uvicorn_loggers(uvicorn_handlers):
    with TestClient(build()):
        for name, handler in uvicorn_handlers.items():
            assert any(isinstance(f, RedactSecretsFilter) for f in handler.filters), name or "root"


def test_health_reports_ok_or_down_only():
    async def down() -> bool:
        raise ConnectionError(f"cannot reach postgresql://u:dsn-secret@pg.invalid/db {FAKE_KEY}")

    with TestClient(build({"neo4j": ok, "postgres": down})) as client:
        resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json() == {"neo4j": "ok", "postgres": "down"}
    for leaked in ("dsn-secret", "pg.invalid", FAKE_KEY, "ConnectionError"):
        assert leaked not in resp.text


def test_health_all_ok():
    with TestClient(build()) as client:
        resp = client.get("/health")
    assert (resp.status_code, resp.json()) == (200, {"neo4j": "ok", "postgres": "ok"})


def test_settings_secrets_never_in_any_response():
    with TestClient(build(), raise_server_exceptions=False) as client:
        bodies = [client.get(p).text for p in ("/health", "/test/boom", "/test/rate-limited",
                                                 "/khong-co")]
    for secret in ("pw-not-in-response", "dsn-secret", "enc-not-in-response"):
        assert all(secret not in b for b in bodies)


async def test_default_postgres_check_works_on_any_event_loop():
    """Hồi quy: psycopg async không chạy trên ProactorEventLoop (mặc định của Windows), nên
    /health luôn báo postgres down. Gọi tới cổng đóng trên máy: phải là lỗi kết nối, không phải
    lỗi event loop. Không cần mạng ngoài."""
    import psycopg
    from fastapi import FastAPI

    from writory.api.app import _default_health_checks

    s = settings().model_copy(update={
        "postgres_dsn": settings().postgres_dsn.__class__("postgresql://u:p@127.0.0.1:1/db"),
    })
    app = FastAPI()
    checks = _default_health_checks(app, s)
    try:
        with pytest.raises(psycopg.OperationalError):
            await checks["postgres"]()
    finally:
        app.state.neo4j_driver.close()


def test_chapter_errors_from_db_layer_get_their_status():
    """Lỗi ghi chương (db/chapters.py) là lớp con WritoryError: handler trả đúng status, không detail."""
    from writory.db.chapters import PendingChapterError, StoryNotFoundError

    app = build()

    @app.get("/test/no-story")
    async def no_story():
        raise StoryNotFoundError("story test-123 của user khác")

    @app.get("/test/pending")
    async def pending():
        raise PendingChapterError("chương 4 pending")

    with TestClient(app, raise_server_exceptions=False) as client:
        a, b = client.get("/test/no-story"), client.get("/test/pending")
    assert (a.status_code, a.json()["code"]) == (404, "STORY_NOT_FOUND")
    assert (b.status_code, b.json()["code"]) == (409, "CHAPTER_PENDING")
    assert "test-123" not in a.text and "pending" not in b.json()["message"]


@pytest.mark.parametrize(("loc", "kind", "path"), [
    (("body", "tags", "genre"), "string_too_short", "tags.genre"),
    (("body", "index"), "int_type", "index"),
    (("body", "items", 0, "name"), "missing", "items.0.name"),
    (("path", "number"), "int_parsing", "number"),
    (("body",), "missing", "body"),
    (("body", 17), "json_invalid", "body"),
    # Tên trường lạ do người gửi đặt (ở đây là key) không bao giờ được chép lại (G7).
    (("body", FAKE_KEY), "extra_forbidden", "?"),
    (("body", "ghi chú"), "extra_forbidden", "?"),
    (("body", "a" * 65), "extra_forbidden", "?"),
])
def test_field_path_keeps_only_schema_names(loc, kind, path):
    from writory.api.errors import field_path

    assert field_path(loc, kind) == path
