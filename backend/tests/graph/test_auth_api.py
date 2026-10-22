"""Đăng nhập bằng mã mời trên Postgres thật (D-89): mã mời chỉ lưu băm, phiên trong cookie,
hết hạn theo đồng hồ giả, thu hồi, đăng xuất, giới hạn số lần nhập mã, lệnh dòng lệnh, và kiểm chủ
sở hữu ở API ("G10 ở API", docs/security.md): người chơi B không đọc, ghi được truyện, phiên khởi
tạo, key, chi phí của A, trên MỌI route có `story_id` hay `session_id`."""

import io
import logging
import uuid
from contextlib import redirect_stdout

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.api_fixtures import FAKE_KEY, AllowAllQuota, KeyedFactory, dev_settings
from tests.graph.test_play_api import FakeClock
from tests.pipeline_fixtures import make_config
from tests.unit.test_narrator import PLAN
from writory.api import create_app, deps
from writory.db import (
    CostEntry,
    commit_chapter,
    create_setup,
    create_story_with_plan,
    delete_player_key,
    record_cost,
    save_player_key,
)
from writory.db import invites as invites_cli
from writory.db.auth import (
    SESSION_COOKIE,
    PostgresSessionLookup,
    create_invite,
    list_invites,
    revoke_invite,
)
from writory.graph import read_sample
from writory.llm.fake import FakeLLM

pytestmark = pytest.mark.graph

SAMPLE = read_sample()
LOCAL = "http://localhost"  # không Secure trên localhost, để TestClient gửi lại cookie qua http
JSON = {"content-type": "application/json"}
ATTEMPTS = 4


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def auth_db(pg):
    """Dọn mã mời, phiên và bộ đếm lần nhập mã của test (bảng dùng chung giữa các test)."""
    made: list[str] = []

    def clean() -> None:
        pg.execute("DELETE FROM login_attempt_windows")
        for invite_id in made:
            pg.execute("DELETE FROM invites WHERE id = %s", (invite_id,))

    clean()

    def invite(name: str):
        record, code = create_invite(pg, name, now=_dt(FakeClock()()))
        made.append(record.id)
        return record, code

    yield invite
    clean()


def _dt(ts: float):
    from datetime import UTC, datetime
    return datetime.fromtimestamp(ts, UTC)


def make_app(pg, driver, tmp_path, clock, *, llm=None):
    settings = dev_settings(dev=False).model_copy(update={"auth_mode": "invite"})
    config = make_config(tmp_path, limits={"auth": {"login_attempts_per_window": ATTEMPTS}})
    app = create_app(settings, health_checks={}, config=config)
    app.dependency_overrides[deps.get_pg_conn] = lambda: pg
    app.dependency_overrides[deps.get_neo4j_driver] = lambda: driver
    app.dependency_overrides[deps.get_clock] = lambda: clock
    app.dependency_overrides[deps.get_session_lookup] = lambda: PostgresSessionLookup(lambda: pg)
    factory = KeyedFactory(llm or FakeLLM.scripted([]))
    app.dependency_overrides[deps.get_llm_factory] = lambda: factory
    app.dependency_overrides[deps.get_call_quota] = AllowAllQuota
    return app, factory


def login(client, code):
    return client.post("/auth/login", json={"code": code}, headers=JSON)


# --- lưu trữ -----------------------------------------------------------------------------------


def test_invite_code_is_never_stored_only_its_hash(pg, auth_db):
    record, code = auth_db("Lan")
    rows = pg.execute("SELECT i::text FROM invites i WHERE id = %s", (record.id,)).fetchall()
    stored = rows[0][0].lower()
    plain = code.removeprefix("wt-").replace("-", "")
    assert plain[8:] not in stored and code not in stored  # phần bí mật của mã không nằm đâu
    assert record.owner_id.startswith("u-") and record.name == "Lan"
    assert all(code not in repr(r) and plain[8:] not in repr(r) for r in list_invites(pg))


def test_each_invite_has_its_own_owner(pg, auth_db):
    a, _ = auth_db("A")
    b, _ = auth_db("B")
    assert a.owner_id != b.owner_id


# --- đăng nhập, phiên, đăng xuất ---------------------------------------------------------------


def test_login_sets_httponly_lax_cookie_and_stores_only_the_token_hash(pg, driver, tmp_path,
                                                                     clock, auth_db, caplog):
    _, code = auth_db("Lan")
    app, _ = make_app(pg, driver, tmp_path, clock)
    caplog.set_level(logging.DEBUG)
    with TestClient(app, base_url=LOCAL) as client:
        resp = login(client, code)
        assert resp.status_code == 200
        assert resp.json() == {"mode": "invite", "logged_in": True, "name": "Lan"}
        cookie = resp.headers["set-cookie"]
        token = client.cookies.get(SESSION_COOKIE)
        assert token and token not in resp.text
        assert "httponly" in cookie.lower() and "samesite=lax" in cookie.lower()
        assert "secure" not in cookie.lower()  # localhost
        assert "max-age=" in cookie.lower() and "path=/" in cookie.lower()
        assert client.get("/auth/session").json()["logged_in"] is True
    stored = " ".join(r[0] for r in pg.execute("SELECT s::text FROM auth_sessions s").fetchall())
    assert token not in stored
    assert code not in caplog.text and token not in caplog.text


def test_cookie_is_secure_when_not_on_localhost(pg, driver, tmp_path, clock, auth_db):
    _, code = auth_db("Lan")
    app, _ = make_app(pg, driver, tmp_path, clock)
    with TestClient(app, base_url="https://writory.example") as client:
        resp = login(client, code)
    assert resp.status_code == 200
    assert "secure" in resp.headers["set-cookie"].lower()


def test_wrong_code_is_401_with_its_own_code_and_never_echoed(pg, driver, tmp_path, clock,
                                                              auth_db, caplog):
    _, code = auth_db("Lan")
    wrong = code[:-4] + ("aaaa" if not code.endswith("aaaa") else "bbbb")
    app, _ = make_app(pg, driver, tmp_path, clock)
    caplog.set_level(logging.DEBUG)
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        for typed in (wrong, "không phải mã", "wt-" + "2" * 32):
            resp = login(client, typed)
            assert resp.status_code == 401 and resp.json()["code"] == "INVITE_CODE_INVALID"
            assert typed not in resp.text
        assert client.cookies.get(SESSION_COOKIE) is None
    assert wrong not in caplog.text


def test_session_expires_on_the_fake_clock(pg, driver, tmp_path, clock, auth_db):
    _, code = auth_db("Lan")
    app, _ = make_app(pg, driver, tmp_path, clock)
    ttl = app.state.config.limits.auth.require("session_ttl_hours") * 3600
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        assert login(client, code).status_code == 200
        clock.now += ttl - 1
        assert client.get("/player/key").status_code == 200
        clock.now += 1
        resp = client.get("/player/key")
        assert (resp.status_code, resp.json()["code"]) == (401, "AUTH_REQUIRED")
        assert client.get("/auth/session").json()["logged_in"] is False


def test_logout_ends_the_session_on_the_server(pg, driver, tmp_path, clock, auth_db):
    _, code = auth_db("Lan")
    app, _ = make_app(pg, driver, tmp_path, clock)
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        assert login(client, code).status_code == 200
        token = client.cookies.get(SESSION_COOKIE)
        resp = client.post("/auth/logout", headers=JSON)
        assert resp.json() == {"mode": "invite", "logged_in": False, "name": None}
        assert client.cookies.get(SESSION_COOKIE) is None
        client.cookies.set(SESSION_COOKIE, token)  # cookie cũ bị chép lại cũng không dùng được
        assert client.get("/player/key").status_code == 401


def test_revoked_invite_cannot_log_in_and_its_sessions_stop(pg, driver, tmp_path, clock, auth_db):
    record, code = auth_db("Lan")
    app, _ = make_app(pg, driver, tmp_path, clock)
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        assert login(client, code).status_code == 200
        assert revoke_invite(pg, record.id, now=_dt(clock())) is True
        assert client.get("/player/key").status_code == 401
        assert login(client, code).json()["code"] == "INVITE_CODE_INVALID"
    assert revoke_invite(pg, "inv-khong-co", now=_dt(clock())) is False


def test_login_attempts_are_limited_per_client_then_reopen_next_window(pg, driver, tmp_path,
                                                                      clock, auth_db):
    _, code = auth_db("Lan")
    app, _ = make_app(pg, driver, tmp_path, clock)
    window = app.state.config.limits.auth.require("login_window_seconds")
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        for _ in range(ATTEMPTS):
            assert login(client, "wt-" + "a" * 32).status_code == 401
        blocked = login(client, code)  # đúng mã cũng bị chặn: không thử mã khi đã hết lượt
        assert (blocked.status_code, blocked.json()["code"]) == (429, "LOGIN_RATE_LIMITED")
        assert client.cookies.get(SESSION_COOKIE) is None
        clock.now += window
        assert login(client, code).status_code == 200
    stored = " ".join(r[0] for r in pg.execute(
        "SELECT client FROM login_attempt_windows").fetchall())
    assert "testclient" not in stored  # chỉ lưu băm của địa chỉ máy


# --- lệnh dòng lệnh ------------------------------------------------------------------------------


def test_cli_prints_the_code_once_and_list_never_shows_it(pg, auth_db):
    out = io.StringIO()
    with redirect_stdout(out):
        assert invites_cli.main(["create", "--name", "Bạn Lan"], conn=pg) == 0
    created = out.getvalue()
    code = next(w for w in created.split() if w.startswith("wt-"))
    invite_id = next(w for w in created.split() if w.startswith("inv-"))
    pg_ids = [r.id for r in list_invites(pg)]
    assert invite_id in pg_ids
    listed = io.StringIO()
    with redirect_stdout(listed):
        assert invites_cli.main(["list"], conn=pg) == 0
    assert "Bạn Lan" in listed.getvalue() and invite_id in listed.getvalue()
    assert code not in listed.getvalue()
    with redirect_stdout(io.StringIO()):
        assert invites_cli.main(["revoke", invite_id], conn=pg) == 0
        assert invites_cli.main(["revoke", invite_id], conn=pg) == 1  # đã thu hồi rồi
    pg.execute("DELETE FROM invites WHERE id = %s", (invite_id,))


# --- kiểm chủ sở hữu ở API ---------------------------------------------------------------------


@pytest.fixture
def two_players(pg, driver, new_db_story_id, auth_db):
    """A có truyện (chương 0–3, kế hoạch, lựa chọn chưa có), phiên khởi tạo, key, chi phí. B chỉ có
    key."""
    a, a_code = auth_db("A")
    b, b_code = auth_db("B")
    sid = new_db_story_id()
    create_story_with_plan(pg, sid, owner_id=a.owner_id, length_level="short", brief="b",
                           plan=PLAN)
    for ch in SAMPLE.chapters[:4]:
        commit_chapter(pg, driver, sid, ch.number, [ch.text] if ch.text else [], ch.package)
    setup_id = f"setup-{uuid.uuid4().hex[:16]}"
    create_setup(pg, setup_id, owner_id=a.owner_id, choices={
        "tags": {"genre": "kiếm hiệp"}, "length_level": "short", "pov": "protagonist",
        "naming": {"names": "han_viet", "places": "hu_cau"}})
    record_cost(pg, owner_id=a.owner_id, story_id=sid, chapter=1,
                entry=CostEntry("writer", "m", 1, 1, 0.042))
    yield a, a_code, b, b_code, sid, setup_id
    pg.execute("DELETE FROM setup_sessions WHERE id = %s", (setup_id,))
    for owner in (a.owner_id, b.owner_id):
        delete_player_key(pg, owner)


def owned_routes(app, param: str) -> list[tuple[str, str]]:
    """Mọi (method, path) có tham số `param`, đọc từ OpenAPI của chính app: route mới tự vào."""
    return sorted((m.upper(), path) for path, ops in app.openapi()["paths"].items()
                  if "{" + param + "}" in path for m in ops)


def test_player_b_gets_404_on_every_route_of_player_a_story(pg, driver, tmp_path, clock,
                                                            two_players):
    a, _, b, b_code, sid, _ = two_players
    app, factory = make_app(pg, driver, tmp_path, clock)
    for owner, last4 in ((a.owner_id, "aaaa"), (b.owner_id, "bbbb")):
        save_player_key(pg, owner, app.state.key_cipher.encrypt(SecretStr(FAKE_KEY[:-4] + last4)))
    routes = owned_routes(app, "story_id")
    # Mọi route có story_id hiện có, kể cả SSE và ước tính chi phí (D-87); route mới tự vào đây.
    assert {("GET", "/stories/{story_id}"), ("POST", "/stories/{story_id}/chapters/next"),
            ("GET", "/stories/{story_id}/estimate")} <= set(routes)
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        assert login(client, b_code).status_code == 200
        for method, path in routes:
            url = path.replace("{story_id}", sid).replace("{number}", "1")
            resp = client.request(method, url, headers=JSON,
                                  json={} if method != "GET" else None)
            assert (resp.status_code, resp.json()["code"]) == (404, "STORY_NOT_FOUND"), (
                method, path, resp.text)
            assert sid not in resp.text
        assert sid not in client.get("/stories").text
        assert client.get("/player/key").json()["last4"] == "bbbb"
        costs = client.get("/player/costs").json()
        assert costs["total_usd"] == 0 and costs["stories"] == []
    assert factory.keys == []  # không route nào tới được model


def test_player_b_gets_404_on_every_route_of_player_a_setup_session(pg, driver, tmp_path, clock,
                                                                    two_players):
    _, _, _, b_code, _, setup_id = two_players
    app, factory = make_app(pg, driver, tmp_path, clock)
    routes = owned_routes(app, "session_id")
    assert len(routes) >= 8
    with TestClient(app, base_url=LOCAL, raise_server_exceptions=False) as client:
        assert login(client, b_code).status_code == 200
        for method, path in routes:
            resp = client.request(method, path.replace("{session_id}", setup_id), headers=JSON,
                                  json={"index": 0} if method == "PUT" else None)
            assert (resp.status_code, resp.json()["code"]) == (404, "SETUP_NOT_FOUND"), (
                method, path, resp.text)
    assert factory.keys == []


def test_player_a_still_sees_own_story(pg, driver, tmp_path, clock, two_players):
    """Đối chứng cho hai test trên: cùng app, đúng chủ thì đọc được."""
    _, a_code, _, _, sid, setup_id = two_players
    app, _ = make_app(pg, driver, tmp_path, clock)
    with TestClient(app, base_url=LOCAL) as client:
        assert login(client, a_code).status_code == 200
        assert client.get(f"/setup/{setup_id}").status_code == 200
        assert client.get(f"/stories/{sid}").status_code == 200
        assert sid in client.get("/stories").text
        assert client.get("/player/costs").json()["total_usd"] == pytest.approx(0.042)
