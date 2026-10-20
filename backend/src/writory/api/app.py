"""App FastAPI (D-29). Chạy dev: docs/runbook.md.

Tạo app bằng factory `create_app`, không tạo lúc import, để import không cần biến môi trường.
Router `stories` (sổ tay, hỏi người kể) chỉ mount khi `enable_dev_routes` bật (D-41).
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase

from writory.api.errors import install_error_handlers
from writory.api.stories import router as stories_router
from writory.config import AppConfig, Settings, load_config
from writory.safety.redact import install_log_redaction, redact

log = logging.getLogger(__name__)

# Logger của uvicorn có handler riêng và không truyền record lên root, nên phải gắn riêng (G7).
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")
_HEALTH_TIMEOUT_S = 3.0

HealthCheck = Callable[[], Awaitable[bool]]


def _default_health_checks(app: FastAPI, settings: Settings) -> dict[str, HealthCheck]:
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        connection_timeout=_HEALTH_TIMEOUT_S,
    )
    app.state.neo4j_driver = driver

    async def neo4j() -> bool:
        await asyncio.to_thread(driver.verify_connectivity)
        return True

    def postgres_sync() -> bool:
        # psycopg đồng bộ trong thread: bản async không chạy được trên ProactorEventLoop (Windows).
        with psycopg.connect(
            settings.postgres_dsn.get_secret_value(), connect_timeout=int(_HEALTH_TIMEOUT_S)
        ) as conn:
            conn.execute("SELECT 1")
        return True

    async def postgres() -> bool:
        return await asyncio.to_thread(postgres_sync)

    return {"neo4j": neo4j, "postgres": postgres}


def create_app(
    settings: Settings | None = None,
    *,
    health_checks: dict[str, HealthCheck] | None = None,
    config: AppConfig | None = None,
) -> FastAPI:
    # Đọc biến môi trường và config/ lúc gọi factory (uvicorn --factory), không lúc import.
    settings = settings if settings is not None else Settings()
    config = config if config is not None else load_config()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        for name in ("", *UVICORN_LOGGERS):
            install_log_redaction(logging.getLogger(name or None))
        # TODO(D-6, docs/graph-schema.md "Ghi theo commit_id"): gọi reconcile_pending lúc khởi
        # động. writory.db đã có hàm này; chưa nối vì chưa có quyết định.
        app.state.health_checks = (
            health_checks
            if health_checks is not None
            else _default_health_checks(app, settings)
        )
        try:
            yield
        finally:
            driver = getattr(app.state, "neo4j_driver", None)
            if driver is not None:
                driver.close()

    app = FastAPI(title="WriTory", lifespan=lifespan)
    install_error_handlers(app)
    app.state.settings = settings
    app.state.config = config
    # D-41: router chưa có đăng nhập chỉ mount khi bật cờ dev; mặc định tắt (fail closed).
    app.state.dev_routes_enabled = settings.enable_dev_routes is True
    if app.state.dev_routes_enabled:
        app.include_router(stories_router)

    @app.get("/health")
    async def health() -> JSONResponse:
        """Chỉ "ok"/"down" cho từng phần; không chuỗi kết nối, không thông điệp lỗi."""
        status: dict[str, str] = {}
        for name, check in app.state.health_checks.items():
            try:
                ok = await asyncio.wait_for(check(), timeout=_HEALTH_TIMEOUT_S)
            except Exception as exc:  # noqa: BLE001 — mọi lỗi của một phần đều là "down"
                log.warning("health %s down: %s", name, redact(f"{type(exc).__name__}: {exc}"))
                ok = False
            status[name] = "ok" if ok else "down"
        all_ok = all(v == "ok" for v in status.values())
        return JSONResponse(status, status_code=200 if all_ok else 503)

    return app
