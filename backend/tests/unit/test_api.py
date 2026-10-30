"""Khung API (D-29): lỗi theo G12, redaction log (G7), /health. TestClient, không cần Docker."""

import os
import subprocess
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from tests.api_fixtures import captured_logs
from writory.api import create_app
from writory.api.errors import HTTP_STATUS
from writory.config import Settings
from writory.errors import MESSAGES, ErrorCode, WritoryError
from writory.safety.redact import REDACTED

FAKE_KEY = "sk-or-v1-" + "c0ffee12" * 8


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


def test_unexpected_error_is_generic_and_leaks_nothing():
    # `captured_logs` bắt record lúc tạo, dưới lớp redaction của app: chỉ xanh khi chính
    # `api/errors.py` đã redact, không nhờ lớp đó.
    with captured_logs() as logs, TestClient(build(), raise_server_exceptions=False) as c:
        resp = c.get("/test/boom")
    logged = logs.text
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


# Tiến trình riêng chạy app như `uvicorn writory.api:create_app --factory` của
# deploy/backend.Dockerfile: `uvicorn.Config` dựng cấu hình log mặc định của uvicorn
# (`LOGGING_CONFIG`: handler chỉ ở logger `uvicorn*`, root không có handler) TRƯỚC khi gọi factory.
_UVICORN_DEFAULT_LOGGING = r'''
import logging, sys
import uvicorn
from fastapi.testclient import TestClient
from writory.api import create_app
from writory.config import Settings

key = sys.argv[1]
uvicorn.Config("writory.api:create_app", factory=True)
assert logging.getLogger().handlers == [], logging.getLogger().handlers

async def ok():
    return True

app = create_app(Settings(_env_file=None, neo4j_uri="bolt://neo4j.invalid:7687", neo4j_user="neo4j",
                          neo4j_password="pw", postgres_dsn="postgresql://u:p@pg.invalid/db",
                          player_key_encryption_key="enc"), health_checks={"neo4j": ok})

@app.get("/test/log")
async def emit():
    logging.getLogger("writory.api.errors").info("app info %s", key)
    logging.getLogger("writory.pipeline.chapter").warning("app warning %s", key)
    try:
        raise RuntimeError(f"model failed {key}")
    except RuntimeError:
        logging.getLogger("writory.llm.openrouter").exception("app exception")
    logging.getLogger("httpx").warning("library warning %s", key)
    logging.getLogger("uvicorn.error").warning("uvicorn warning %s", key)
    return {}

with TestClient(app) as client:
    assert client.get("/test/log").status_code == 200
'''


def test_app_logs_reach_output_redacted_under_uvicorn_default_logging():
    """Hồi quy (rà soát 30/10/2026, G7): bộ lọc chỉ gắn vào handler có sẵn lúc khởi động, mà cấu
    hình log mặc định của uvicorn không cho root handler nào, nên log `writory.*` rơi vào
    `logging.lastResort` không qua redact (key hiện nguyên) và dòng INFO bị bỏ. Chạy tiến trình
    riêng để có đúng cấu hình đó, không có handler nào của pytest ở root."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run([sys.executable, "-c", _UVICORN_DEFAULT_LOGGING, FAKE_KEY],
                          capture_output=True, env=env, timeout=300, check=False)
    out = proc.stdout.decode("utf-8") + proc.stderr.decode("utf-8")
    assert proc.returncode == 0, out
    assert FAKE_KEY not in out
    for line in (f"INFO writory.api.errors: app info {REDACTED}",
                 f"WARNING writory.pipeline.chapter: app warning {REDACTED}",
                 "ERROR writory.llm.openrouter: app exception",
                 f"RuntimeError: model failed {REDACTED}",
                 f"WARNING httpx: library warning {REDACTED}",
                 f"uvicorn warning {REDACTED}"):
        assert line in out, out


def test_backend_image_runs_uvicorn_with_its_default_logging():
    """Test trên dựng cấu hình log mặc định của uvicorn vì image prod chạy uvicorn không có
    `--log-config` (deploy/backend.Dockerfile); đổi lệnh đó thì test trên phải đổi theo."""
    from writory.config import REPO_ROOT

    dockerfile = (REPO_ROOT / "deploy" / "backend.Dockerfile").read_text(encoding="utf-8")
    [cmd] = [ln for ln in dockerfile.splitlines() if ln.startswith("CMD ")]
    assert '"uvicorn", "writory.api:create_app", "--factory"' in cmd
    assert "--log-config" not in dockerfile


# --- lỗi của router: route không có, sai phương thức, router chưa bật (G12) ----------------------


def test_unknown_route_and_wrong_method_get_their_own_code():
    with TestClient(build(), raise_server_exceptions=False) as client:
        unknown = client.get("/khong-co")
        wrong = client.delete("/health")
        closed = client.get("/stories")  # router người chơi không mount khi cờ dev tắt (D-41)
    for resp in (unknown, closed):
        assert resp.status_code == 404 == HTTP_STATUS[ErrorCode.ROUTE_NOT_FOUND]
        assert resp.json() == WritoryError(ErrorCode.ROUTE_NOT_FOUND).player_payload()
    assert wrong.status_code == 405 == HTTP_STATUS[ErrorCode.METHOD_NOT_ALLOWED]
    assert wrong.json() == WritoryError(ErrorCode.METHOD_NOT_ALLOWED).player_payload()
    assert wrong.headers["allow"] == "GET"


def test_router_refused_by_api_guard_gets_route_not_found():
    """`deps.api_guard`: router đã mount nhưng chưa bật cho app này thì 404 như route không có."""
    from tests.api_fixtures import dev_settings

    app = create_app(dev_settings(dev=True), health_checks={"neo4j": ok})
    app.state.player_routes_enabled = False
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/stories")
    assert (resp.status_code, resp.json()) == (
        404, WritoryError(ErrorCode.ROUTE_NOT_FOUND).player_payload())


@pytest.mark.parametrize(("status", "code"), [(400, ErrorCode.REQUEST_INVALID),
                                              (413, ErrorCode.REQUEST_INVALID),
                                              (503, ErrorCode.INTERNAL_ERROR)])
def test_other_http_errors_get_a_code_and_never_echo_their_detail(status, code):
    app = build()

    @app.get("/test/http")
    async def http_error():
        raise HTTPException(status_code=status, detail=f"parse error near {FAKE_KEY}")

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get("/test/http")
    assert (resp.status_code, resp.json()) == (HTTP_STATUS[code],
                                               WritoryError(code).player_payload())
    assert FAKE_KEY not in resp.text and "parse error" not in resp.text


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
