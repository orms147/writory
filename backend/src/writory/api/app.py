"""App FastAPI (D-29). Chạy dev: docs/runbook.md.

Tạo app bằng factory `create_app`, không tạo lúc import, để import không cần biến môi trường.
Router của người chơi (`PLAYER_ROUTERS`: truyện, khởi tạo, key và chi phí người chơi, cấu hình
công khai cho giao diện, đăng nhập) mount khi `AUTH_MODE=invite` (có đăng nhập bằng mã mời, D-89),
hoặc khi `enable_dev_routes` bật ở chế độ `dev` (mọi người là người chơi dev, D-41, D-66). Không
bật CORS: giao diện gọi API qua proxy của Vite, cùng origin (D-66, docs/runbook.md); chống CSRF
dựa vào điều đó (`deps.api_guard`).

`APP_ENV=prod` (máy chủ cho người chơi thật, D-103): cấu hình nguy hiểm thì không tạo app
(`config.prod_problems`); lúc khởi động chạy migration Postgres, tạo ràng buộc Neo4j, đọc thử
file app cần và áp lại chương kẹt `pending` (`prepare_storage`, D-105) trước khi nhận yêu cầu đầu;
không có trang OpenAPI. Sau reverse
proxy, chỉ tin header địa chỉ máy và scheme từ `TRUSTED_PROXIES` (`deps.client_address`).
"""

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from neo4j import Driver, GraphDatabase

from writory.api.auth import router as auth_router
from writory.api.errors import install_error_handlers
from writory.api.keys import router as keys_router
from writory.api.play import router as play_router
from writory.api.public_config import router as public_config_router
from writory.api.setup import router as setup_router
from writory.api.stories import router as stories_router
from writory.config import (
    AppConfig,
    ConfigError,
    Settings,
    load_config,
    parse_trusted_proxies,
    prod_problems,
)
from writory.llm.openrouter import DEFAULT_TIMEOUT
from writory.safety.crypto import KeyCipher
from writory.safety.redact import install_log_redaction, redact

log = logging.getLogger(__name__)

# Router của người chơi (D-41, D-89): mount theo `player_routes_enabled`.
PLAYER_ROUTERS = (stories_router, play_router, setup_router, keys_router, public_config_router,
                  auth_router)

# Logger của uvicorn có handler riêng và không truyền record lên root, nên phải gắn riêng (G7).
UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")
_HEALTH_TIMEOUT_S = 3.0

HealthCheck = Callable[[], Awaitable[bool]]
StorageSetup = Callable[[Settings], None]


def prepare_storage(settings: Settings) -> None:
    """Chuẩn bị kho lúc khởi động ở prod (D-103): migration Postgres (D-20, có khoá advisory),
    ràng buộc và index Neo4j (`graph.ensure_schema`, chạy lại an toàn), và đọc thử hướng dẫn văn
    phong (system prompt của model viết), để thiếu file thì app không lên thay vì hỏng ở chương
    đầu. Lỗi ở các bước đó làm app không khởi động; compose khởi động lại sau.

    Cuối cùng áp lại chương kẹt `pending` (`reconcile_at_startup`, D-6, D-105). Bước này không
    làm app chết: lỗi chỉ vào log."""
    from writory.db import connect, migrate
    from writory.graph import ensure_schema
    from writory.pipeline.scene import load_style_guide

    load_style_guide()
    with connect(settings) as conn:
        applied = migrate(conn)
        log.info("migration Postgres: %s", ", ".join(applied) if applied else "đã đủ")
        driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password.get_secret_value()),
        )
        try:
            ensure_schema(driver)
            log.info("ràng buộc Neo4j: đã đủ")
            reconcile_at_startup(conn, driver)
        finally:
            driver.close()


def reconcile_at_startup(conn: psycopg.Connection, driver: Driver) -> None:
    """Áp lại chương kẹt `pending` của truyện không có việc đang chạy (`db.reconcile_idle_stories`,
    D-105). Không ném lỗi: kho đã qua migration và ràng buộc, nên lỗi ở đây chỉ để các truyện đó
    còn kẹt (`CHAPTER_PENDING`), không đáng chặn mọi người chơi khác; lệnh chạy tay ở
    docs/runbook.md."""
    from writory.db import reconcile_idle_stories

    try:
        results = reconcile_idle_stories(conn, driver)
    except Exception as exc:  # noqa: BLE001 — xem docstring
        log.error("áp lại chương pending lúc khởi động không được: %s",
                  redact(f"{type(exc).__name__}: {exc}"))
        return
    for r in results:
        level = logging.INFO if r.status in ("committed", "busy") else logging.WARNING
        log.log(level, "áp lại chương pending: truyện %s chương %d (%s): %s%s", r.story_id,
                r.number, r.commit_id, r.status, f" ({redact(r.error)})" if r.error else "")
    if not results:
        log.info("áp lại chương pending: không có")


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
    storage_setup: StorageSetup = prepare_storage,
) -> FastAPI:
    # Đọc biến môi trường và config/ lúc gọi factory (uvicorn --factory), không lúc import.
    settings = settings if settings is not None else Settings()
    config = config if config is not None else load_config()
    prod = settings.app_env == "prod"
    if prod:
        problems = prod_problems(settings)
        if problems:
            raise ConfigError("APP_ENV=prod nhưng cấu hình chưa an toàn: " + "; ".join(problems)
                              + ". Xem docs/runbook.md, mục Deploy.")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        for name in ("", *UVICORN_LOGGERS):
            install_log_redaction(logging.getLogger(name or None))
        if prod:
            await asyncio.to_thread(storage_setup, settings)
        app.state.health_checks = (
            health_checks
            if health_checks is not None
            else _default_health_checks(app, settings)
        )
        if app.state.player_routes_enabled:
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

    # Prod không có trang OpenAPI (D-103): repo công khai, nhưng không cần mở thêm cửa.
    docs = {"docs_url": None, "redoc_url": None, "openapi_url": None} if prod else {}
    app = FastAPI(title="WriTory", lifespan=lifespan, **docs)
    install_error_handlers(app)
    app.state.settings = settings
    app.state.config = config
    app.state.trusted_proxies = parse_trusted_proxies(settings.trusted_proxies)
    # D-41, D-89: chế độ `dev` (không đăng nhập) chỉ mount khi bật cờ dev, mặc định tắt (fail
    # closed); chế độ `invite` luôn mount, vì mọi route đọc người chơi từ phiên đăng nhập.
    app.state.player_routes_enabled = (settings.auth_mode == "invite"
                                       or settings.enable_dev_routes is True)
    if app.state.player_routes_enabled:
        # D-11: khoá mã hoá key sai thì app không khởi động (lỗi không chép lại khoá).
        app.state.key_cipher = KeyCipher(settings.player_key_encryption_key)
        for router in PLAYER_ROUTERS:
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
