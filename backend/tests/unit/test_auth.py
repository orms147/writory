"""Đăng nhập bằng mã mời (D-89), phần không cần Postgres: dạng mã, lọc log, chế độ `AUTH_MODE`,
phiên thiếu hay sai → 401, chống CSRF cho route ghi. Luồng đủ trên Postgres:
tests/graph/test_auth_api.py."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Annotated

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient

from tests.api_fixtures import MemoryKeyStore, dev_settings
from writory.api import create_app, deps
from writory.config import Settings, load_config
from writory.db.auth import (
    SESSION_COOKIE,
    SessionInfo,
    new_invite_code,
    new_session_token,
    parse_invite_code,
)
from writory.errors import MESSAGES, ErrorCode, WritoryError
from writory.safety.redact import RedactSecretsFilter, redact

CFG = load_config()


async def ok() -> bool:
    return True


# --- mã mời và token ---------------------------------------------------------------------------


def test_invite_code_has_prefix_groups_and_enough_entropy():
    codes = {new_invite_code() for _ in range(200)}
    assert len(codes) == 200
    for code in list(codes)[:20]:
        assert code.startswith("wt-")
        groups = code.removeprefix("wt-").split("-")
        assert [len(g) for g in groups] == [4] * 8  # 32 ký tự base32: 160 bit
        assert parse_invite_code(code) is not None


@pytest.mark.parametrize("typed", [
    lambda c: c, lambda c: c.upper(), lambda c: f"  {c}\n", lambda c: c.replace("-", ""),
    lambda c: c.removeprefix("wt-"), lambda c: c.replace("-", " "),
])
def test_invite_code_is_read_however_the_friend_pastes_it(typed):
    code = new_invite_code()
    assert parse_invite_code(typed(code)) == parse_invite_code(code)


@pytest.mark.parametrize("bad", ["", "wt-", "wt-abcd", "wt-" + "1" * 32, "x" * 500,
                                 "wt-" + "a" * 33])
def test_malformed_invite_code_is_rejected_without_lookup(bad):
    assert parse_invite_code(bad) is None


def test_session_token_is_long_random_and_prefixed():
    tokens = {new_session_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(t.startswith("wts_") and len(t) >= 40 for t in tokens)


def test_codes_and_tokens_are_redacted_from_logs():
    code, token = new_invite_code(), new_session_token()
    for text in (f"mã {code} sai", f"mã {code.upper()}", f"cookie {SESSION_COOKIE}={token}",
                 f"token {token}"):
        cleaned = redact(text)
        assert code not in cleaned and code.upper() not in cleaned and token not in cleaned
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "login %s", (code,), None)
    RedactSecretsFilter().filter(record)
    assert code not in record.getMessage()


# --- chế độ ------------------------------------------------------------------------------------


def settings(*, mode: str, dev: bool = False) -> Settings:
    return dev_settings(dev=dev).model_copy(update={"auth_mode": mode})


def test_auth_mode_defaults_to_dev_and_rejects_unknown(monkeypatch):
    for name, value in (("NEO4J_URI", "bolt://x"), ("NEO4J_USER", "n"), ("NEO4J_PASSWORD", "p"),
                        ("POSTGRES_DSN", "postgresql://u:p@h/d"),
                        ("PLAYER_KEY_ENCRYPTION_KEY", "k")):
        monkeypatch.setenv(name, value)
    assert Settings(_env_file=None).auth_mode == "dev"
    monkeypatch.setenv("AUTH_MODE", "invite")
    assert Settings(_env_file=None).auth_mode == "invite"
    monkeypatch.setenv("AUTH_MODE", "open")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_auth_limits_live_in_config():
    auth = CFG.limits.auth
    assert auth.require("session_ttl_hours") > 0
    assert auth.require("login_attempts_per_window") > 0
    assert auth.require("login_window_seconds") > 0


class FixedSessions:
    """Phiên trong bộ nhớ: token → chủ. Ghi lại các lần tra."""

    def __init__(self, sessions: dict[str, SessionInfo] | None = None) -> None:
        self.sessions = sessions or {}
        self.asked: list[tuple[str, datetime]] = []

    def owner_of(self, token: str, *, now: datetime) -> SessionInfo | None:
        self.asked.append((token, now))
        info = self.sessions.get(token)
        return info if info is not None and info.expires_at > now else None


NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)


def make_app(mode: str, *, dev: bool = False, sessions: FixedSessions | None = None):
    app = create_app(settings(mode=mode, dev=dev), health_checks={"neo4j": ok}, config=CFG)
    app.dependency_overrides[deps.get_pg_conn] = lambda: None
    app.dependency_overrides[deps.get_clock] = lambda: (lambda: NOW.timestamp())
    seen: list[str] = []

    def keys(owner: Annotated[str, Depends(deps.get_owner_id)]) -> MemoryKeyStore:
        seen.append(owner)
        return MemoryKeyStore()

    app.dependency_overrides[deps.get_key_store] = keys
    app.dependency_overrides[deps.get_session_lookup] = lambda: sessions or FixedSessions()
    return app, seen


def test_dev_mode_is_unchanged_everyone_is_dev_and_routes_need_the_dev_flag():
    app, seen = make_app("dev", dev=True)
    with TestClient(app) as c:
        assert c.get("/player/key").status_code == 200
        assert c.get("/auth/session").json() == {"mode": "dev", "logged_in": True, "name": None}
        assert c.delete("/player/key", headers=JSON).status_code == 200
    assert seen == [deps.DEV_OWNER_ID, deps.DEV_OWNER_ID]
    off, _ = make_app("dev", dev=False)
    assert not any(p.startswith(("/player", "/auth", "/stories")) for p in off.openapi()["paths"])


def test_invite_mode_mounts_player_routes_without_the_dev_flag():
    app, _ = make_app("invite", dev=False)
    paths = app.openapi()["paths"]
    assert {"/player/key", "/stories", "/auth/login", "/auth/logout", "/auth/session",
            "/config/public"} <= set(paths)


def test_public_config_and_session_need_no_login():
    app, _ = make_app("invite")
    with TestClient(app) as c:
        assert c.get("/config/public").status_code == 200
        assert c.get("/auth/session").json() == {"mode": "invite", "logged_in": False,
                                                 "name": None}


def assert_auth_required(resp) -> None:
    assert resp.status_code == 401
    assert resp.json() == WritoryError(ErrorCode.AUTH_REQUIRED).player_payload()


def test_invite_mode_without_cookie_is_401_and_never_reaches_the_route():
    app, seen = make_app("invite")
    with TestClient(app) as c:
        assert_auth_required(c.get("/player/key"))
        assert_auth_required(c.get("/stories"))
        assert_auth_required(c.get("/stories/s1/notebook"))
    assert seen == []


def test_invite_mode_unknown_or_expired_session_is_401():
    sessions = FixedSessions({"wts_old": SessionInfo("u-a", "Lan", NOW - timedelta(seconds=1))})
    app, seen = make_app("invite", sessions=sessions)
    with TestClient(app) as c:
        for token in ("wts_nope", "wts_old"):
            c.cookies.set(SESSION_COOKIE, token)
            assert_auth_required(c.get("/player/key"))
    assert seen == []
    assert [now for _, now in sessions.asked] == [NOW, NOW]  # giờ lấy từ đồng hồ giả


def test_invite_mode_valid_session_gives_the_invite_owner():
    sessions = FixedSessions({"wts_ok": SessionInfo("u-a", "Lan", NOW + timedelta(hours=1))})
    app, seen = make_app("invite", sessions=sessions)
    with TestClient(app) as c:
        c.cookies.set(SESSION_COOKIE, "wts_ok")
        assert c.get("/player/key").status_code == 200
        assert c.get("/auth/session").json() == {"mode": "invite", "logged_in": True,
                                                 "name": "Lan"}
    assert seen == ["u-a"]


def test_auth_messages_are_vietnamese_and_say_what_next():
    for code in (ErrorCode.AUTH_REQUIRED, ErrorCode.INVITE_CODE_INVALID,
                 ErrorCode.LOGIN_RATE_LIMITED, ErrorCode.REQUEST_ORIGIN_INVALID):
        msg = MESSAGES[code]
        assert msg.what and msg.next_step
    assert "đăng nhập" in MESSAGES[ErrorCode.AUTH_REQUIRED].text().lower()


# --- CSRF (D-89): route ghi ở chế độ invite ------------------------------------------------------


def assert_origin_rejected(resp) -> None:
    assert resp.status_code == 403
    assert resp.json() == WritoryError(ErrorCode.REQUEST_ORIGIN_INVALID).player_payload()


JSON = {"content-type": "application/json"}


@pytest.mark.parametrize(("method", "path"), [
    ("PUT", "/player/key"), ("DELETE", "/player/key"), ("POST", "/stories/s1/choices"),
    ("POST", "/stories/s1/chapters/next"), ("POST", "/setup"), ("POST", "/auth/login"),
    ("POST", "/auth/logout"),
])
@pytest.mark.parametrize("headers", [
    {},  # form của trang khác không gửi được JSON
    {"content-type": "text/plain"},
    {"content-type": "application/x-www-form-urlencoded"},
    {**JSON, "sec-fetch-site": "cross-site"},
    {**JSON, "sec-fetch-site": "same-site"},
    {**JSON, "origin": "https://evil.example"},
    {**JSON, "origin": "null"},
])
@pytest.mark.parametrize("mode", ["invite", "dev"])
def test_write_routes_refuse_requests_that_may_come_from_another_site(mode, method, path, headers):
    """Cả ở `dev` (D-89, điều phối quyết): trang lạ trong trình duyệt của máy dev gửi được yêu cầu
    ghi tới localhost và tiêu key đã lưu, dù không có cookie đăng nhập."""
    sessions = FixedSessions({"wts_ok": SessionInfo("u-a", "Lan", NOW + timedelta(hours=1))})
    app, seen = make_app(mode, dev=True, sessions=sessions)
    with TestClient(app) as c:
        c.cookies.set(SESSION_COOKIE, "wts_ok")
        assert_origin_rejected(c.request(method, path, headers=headers))
    assert seen == [] and sessions.asked == []  # bị chặn trước khi đọc phiên


@pytest.mark.parametrize("headers", [
    JSON, {"content-type": "application/json; charset=utf-8"},
    {**JSON, "sec-fetch-site": "same-origin"},
    {**JSON, "origin": "http://testserver"},
    # Qua proxy của Vite: Origin là cổng giao diện, nhưng trình duyệt báo cùng origin.
    {**JSON, "origin": "http://localhost:5173", "sec-fetch-site": "same-origin"},
])
@pytest.mark.parametrize("mode", ["invite", "dev"])
def test_same_origin_json_write_passes_the_check(mode, headers):
    sessions = FixedSessions({"wts_ok": SessionInfo("u-a", "Lan", NOW + timedelta(hours=1))})
    app, seen = make_app(mode, dev=True, sessions=sessions)
    with TestClient(app) as c:
        c.cookies.set(SESSION_COOKIE, "wts_ok")
        assert c.delete("/player/key", headers=headers).status_code == 200
    assert seen == ["u-a" if mode == "invite" else deps.DEV_OWNER_ID]


@pytest.mark.parametrize("mode", ["invite", "dev"])
def test_reads_are_not_checked_for_origin(mode):
    sessions = FixedSessions({"wts_ok": SessionInfo("u-a", "Lan", NOW + timedelta(hours=1))})
    app, _ = make_app(mode, dev=True, sessions=sessions)
    with TestClient(app) as c:
        c.cookies.set(SESSION_COOKIE, "wts_ok")
        assert c.get("/player/key", headers={"sec-fetch-site": "cross-site"}).status_code == 200
