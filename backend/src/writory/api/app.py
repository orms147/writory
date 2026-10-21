"""App FastAPI (D-29). Chạy dev: docs/runbook.md.

Tạo app bằng factory `create_app`, không tạo lúc import, để import không cần biến môi trường.
Router chưa có đăng nhập (`DEV_ROUTERS`: truyện, khởi tạo, key và chi phí người chơi, cấu hình
công khai cho giao diện) chỉ mount khi `enable_dev_routes` bật (D-41, D-66). Không bật CORS: giao
diện dev gọi API qua proxy của Vite, cùng origin (D-66, docs/runbook.md).
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from neo4j import GraphDatabase

from writory.api.errors import install_error_handlers
from writory.api.keys import router as keys_router
from writory.api.play import router as play_router
from writory.api.public_config import router as public_config_router
from writory.api.setup import router as setup_router
from writory.api.stories import router as stories_router
from writory.config import AppConfig, Settings, load_config
from writory.llm.openrouter import DEFAULT_TIMEOUT
from writory.safety.crypto import KeyCipher
from writory.safety.redact import install_log_redaction, redact

log = logging.getLogger(__name__)

# Router chưa có đăng nhập (D-41): chỉ mount khi bật ENABLE_DEV_ROUTES.
DEV_ROUTERS = (stories_router, play_router, setup_router, keys_router, public_config_router)

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
        if app.state.dev_routes_enabled:
            # Một httpx client cho mọi client OpenRouter (mỗi client mang key một người chơi).
            app.state.openrouter_http = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT)
        try:
            yield
        finally:
            driver = getattr(app.state, "neo4j_driver", None)
            if driver is not None:
                driver.close()
            http = getattr(app.state, "openrouter_http", None)
            if http is not None:
                await http.aclose()

    app = FastAPI(title="WriTory", lifespan=lifespan)
    install_error_handlers(app)
    app.state.settings = settings
    app.state.config = config
    # D-41: router chưa có đăng nhập chỉ mount khi bật cờ dev; mặc định tắt (fail closed).
    app.state.dev_routes_enabled = settings.enable_dev_routes is True
    if app.state.dev_routes_enabled:
        # D-11: khoá mã hoá key sai thì app không khởi động (lỗi không chép lại khoá).
        app.state.key_cipher = KeyCipher(settings.player_key_encryption_key)
        for router in DEV_ROUTERS:
            app.include_router(router)

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
