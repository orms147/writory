"""Chạy prod sau reverse proxy (D-103): `APP_ENV=prod` từ chối cấu hình nguy hiểm, chuẩn bị kho lúc
khởi động, chỉ tin header địa chỉ máy từ proxy tin cậy, cookie `Secure` đúng sau proxy, và file
compose prod không mở cổng của Neo4j, Postgres. Không cần Docker: phần chạy thật ở
tests/graph/test_deploy_storage.py và docs/runbook.md, mục Deploy."""

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tests.api_fixtures import dev_settings
from writory.api import auth as auth_api
from writory.api import create_app, deps
from writory.config import (
    MIN_PROD_SECRET_CHARS,
    REPO_ROOT,
    ConfigError,
    Settings,
    load_config,
    parse_trusted_proxies,
    prod_problems,
)
from writory.db.auth import SESSION_COOKIE, LoginResult, SessionInfo

CFG = load_config()
JSON = {"content-type": "application/json"}
PROXY = "172.30.80.10"
FRIEND = "203.0.113.7"  # địa chỉ tài liệu (RFC 5737)
NEO4J_PW = "n" * MIN_PROD_SECRET_CHARS
PG_PW = "p" * MIN_PROD_SECRET_CHARS


async def ok() -> bool:
    return True


def prod_settings(**update) -> Settings:
    base = dev_settings(dev=False).model_copy(update={
        "app_env": "prod", "auth_mode": "invite",
        "neo4j_password": SecretStr(NEO4J_PW),
        "postgres_dsn": SecretStr(f"postgresql://writory:{PG_PW}@postgres:5432/writory"),
        "trusted_proxies": PROXY,
    })
    return base.model_copy(update=update)


# --- APP_ENV=prod từ chối cấu hình nguy hiểm -----------------------------------------------------


def test_app_env_defaults_to_dev_and_rejects_unknown(monkeypatch):
    for name, value in (("NEO4J_URI", "bolt://x"), ("NEO4J_USER", "n"), ("NEO4J_PASSWORD", "p"),
                        ("POSTGRES_DSN", "postgresql://u:p@h/d"),
                        ("PLAYER_KEY_ENCRYPTION_KEY", "k")):
        monkeypatch.setenv(name, value)
    assert Settings(_env_file=None).app_env == "dev"
    monkeypatch.setenv("APP_ENV", "prod")
    assert Settings(_env_file=None).app_env == "prod"
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_good_prod_settings_have_no_problem():
    assert prod_problems(prod_settings()) == []


def test_prod_refuses_dev_auth_mode():
    problems = prod_problems(prod_settings(auth_mode="dev"))
    assert any("AUTH_MODE" in p for p in problems)
    with pytest.raises(ConfigError, match="AUTH_MODE"):
        create_app(prod_settings(auth_mode="dev"), health_checks={"neo4j": ok}, config=CFG)


@pytest.mark.parametrize("weak", ["change-me-local", "pw", "x" * (MIN_PROD_SECRET_CHARS - 1),
                                  "change-me-local-but-much-longer"])
def test_prod_refuses_weak_or_example_passwords_and_never_echoes_them(weak):
    for update, name in (
        ({"neo4j_password": SecretStr(weak)}, "NEO4J_PASSWORD"),
        ({"postgres_dsn": SecretStr(f"postgresql://writory:{weak}@postgres:5432/writory")},
         "POSTGRES_DSN"),
    ):
        problems = prod_problems(prod_settings(**update))
        assert any(name in p for p in problems), (name, problems)
        with pytest.raises(ConfigError) as err:
            create_app(prod_settings(**update), health_checks={"neo4j": ok}, config=CFG)
        assert weak not in str(err.value)


def test_prod_refuses_a_dsn_without_password():
    problems = prod_problems(prod_settings(
        postgres_dsn=SecretStr("postgresql://writory@postgres:5432/writory")))
    assert any("POSTGRES_DSN" in p for p in problems)


def test_dev_mode_keeps_the_example_passwords_working():
    settings = dev_settings(dev=True)  # mật khẩu "pw" như máy dev
    assert settings.app_env == "dev"
    create_app(settings, health_checks={"neo4j": ok}, config=CFG)  # không lỗi


def test_prod_hides_the_openapi_pages_and_dev_keeps_them():
    with TestClient(create_app(prod_settings(), health_checks={"neo4j": ok}, config=CFG,
                               storage_setup=lambda s: None)) as c:
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert c.get(path).status_code == 404
    with TestClient(create_app(dev_settings(dev=True), health_checks={"neo4j": ok},
                               config=CFG)) as c:
        assert c.get("/openapi.json").status_code == 200


def test_prod_prepares_storage_at_startup_and_dev_does_not():
    calls: list[Settings] = []
    settings = prod_settings()
    with TestClient(create_app(settings, health_checks={"neo4j": ok}, config=CFG,
                               storage_setup=calls.append)) as c:
        assert calls == [settings]  # trước khi nhận yêu cầu đầu
        assert c.get("/health").status_code == 200
    dev_calls: list[Settings] = []
    with TestClient(create_app(dev_settings(dev=True), health_checks={"neo4j": ok}, config=CFG,
                               storage_setup=dev_calls.append)):
        pass
    assert dev_calls == []


def test_prod_does_not_start_when_storage_setup_fails():
    def broken(_settings: Settings) -> None:
        raise RuntimeError("Neo4j chưa lên")

    app = create_app(prod_settings(), health_checks={"neo4j": ok}, config=CFG,
                     storage_setup=broken)
    with pytest.raises(RuntimeError, match="Neo4j"), TestClient(app):
        pass


# --- proxy tin cậy ---------------------------------------------------------------------------------


def test_trusted_proxies_parse_ips_and_networks():
    nets = parse_trusted_proxies(" 172.30.80.10, 10.0.0.0/8 ,::1 ")
    assert [str(n) for n in nets] == ["172.30.80.10/32", "10.0.0.0/8", "::1/128"]
    assert parse_trusted_proxies("") == ()


@pytest.mark.parametrize("bad", ["proxy", "10.0.0.0/33", "*", "172.30.80.10/24"])
def test_trusted_proxies_reject_names_wildcards_and_bad_networks(bad):
    with pytest.raises(ValueError):
        parse_trusted_proxies(bad)


def test_trusted_proxies_env_is_checked_at_settings(monkeypatch):
    for name, value in (("NEO4J_URI", "bolt://x"), ("NEO4J_USER", "n"), ("NEO4J_PASSWORD", "p"),
                        ("POSTGRES_DSN", "postgresql://u:p@h/d"),
                        ("PLAYER_KEY_ENCRYPTION_KEY", "k"), ("TRUSTED_PROXIES", "*")):
        monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def login_app(settings: Settings, monkeypatch, *, succeed: bool = False):
    """App invite có đăng nhập thật tới chỗ đếm và kiểm mã; Postgres thay bằng bộ ghi."""
    seen: list[str] = []

    def take(conn, client, limit, *, window_seconds, now):
        seen.append(client)
        return True

    def login_with_code(conn, typed, *, ttl, now):
        if not succeed:
            return None
        return LoginResult("wts_" + "t" * 43, SessionInfo("u-a", "Lan", now + ttl))

    monkeypatch.setattr(auth_api, "take_login_attempt", take)
    monkeypatch.setattr(auth_api, "login_with_code", login_with_code)
    app = create_app(settings, health_checks={"neo4j": ok}, config=CFG,
                     storage_setup=lambda s: None)
    app.dependency_overrides[deps.get_pg_conn] = lambda: None
    return app, seen


def post_login(client: TestClient, headers: dict[str, str] | None = None):
    return client.post("/auth/login", json={"code": "wt-" + "a" * 32},
                       headers={**JSON, **(headers or {})})


def test_login_counter_reads_the_real_client_from_the_trusted_proxy(monkeypatch):
    app, seen = login_app(prod_settings(), monkeypatch)
    with TestClient(app, client=(PROXY, 40000), raise_server_exceptions=False) as c:
        post_login(c, {"x-real-ip": FRIEND, "x-forwarded-for": "198.51.100.1, " + FRIEND})
        post_login(c, {"x-forwarded-for": "198.51.100.1, " + FRIEND})  # phần tử proxy tự thêm
        post_login(c, {"x-real-ip": "not-an-ip", "x-forwarded-for": "also bad"})
        post_login(c)
    assert seen == [FRIEND, FRIEND, PROXY, PROXY]


def test_forwarded_headers_from_an_untrusted_client_are_ignored(monkeypatch):
    app, seen = login_app(prod_settings(), monkeypatch)
    with TestClient(app, client=(FRIEND, 40000), raise_server_exceptions=False) as c:
        post_login(c, {"x-real-ip": "198.51.100.9", "x-forwarded-for": "198.51.100.9"})
    assert seen == [FRIEND]


def test_no_trusted_proxy_means_every_header_is_ignored(monkeypatch):
    app, seen = login_app(prod_settings(trusted_proxies=""), monkeypatch)
    with TestClient(app, client=(PROXY, 40000), raise_server_exceptions=False) as c:
        post_login(c, {"x-real-ip": FRIEND})
    assert seen == [PROXY]


def test_trusted_network_covers_every_address_in_it(monkeypatch):
    app, seen = login_app(prod_settings(trusted_proxies="172.30.80.0/24"), monkeypatch)
    with TestClient(app, client=("172.30.80.99", 40000), raise_server_exceptions=False) as c:
        post_login(c, {"x-real-ip": FRIEND})
    with TestClient(app, client=("172.30.81.1", 40000), raise_server_exceptions=False) as c:
        post_login(c, {"x-real-ip": FRIEND})
    assert seen == [FRIEND, "172.30.81.1"]


TUNNEL = "10.89.103.20"


def test_cf_connecting_ip_sent_straight_to_the_backend_is_ignored(monkeypatch):
    app, seen = login_app(prod_settings(), monkeypatch)
    with TestClient(app, client=(FRIEND, 40000), raise_server_exceptions=False) as c:
        post_login(c, {"cf-connecting-ip": "198.51.100.9"})
    with TestClient(app, client=(PROXY, 40000), raise_server_exceptions=False) as c:
        post_login(c, {"cf-connecting-ip": "198.51.100.9"})  # backend chỉ đọc chữ proxy đặt
    assert seen == [FRIEND, PROXY]


def tunnel_headers() -> dict[str, str]:
    """Header backend nhận ở chuỗi Cloudflare → cloudflared → Caddy (cloudflared là proxy tin cậy
    của Caddy): Caddy đặt X-Real-IP từ CF-Connecting-IP, nối IP cloudflared vào cuối
    X-Forwarded-For, giữ X-Forwarded-Proto của Cloudflare."""
    return {"x-real-ip": FRIEND, "x-forwarded-for": f"{FRIEND}, {TUNNEL}",
            "x-forwarded-proto": "https", "cf-connecting-ip": FRIEND,
            "origin": "https://writory.example"}


def test_tunnel_chain_counts_the_friend_not_cloudflared(monkeypatch):
    app, seen = login_app(prod_settings(), monkeypatch)
    with TestClient(app, base_url="http://writory.example", client=(PROXY, 40000),
                    raise_server_exceptions=False) as c:
        post_login(c, tunnel_headers())
    assert seen == [FRIEND]


# --- cookie sau proxy HTTPS ------------------------------------------------------------------------


def cookie_of(resp) -> str:
    header = resp.headers["set-cookie"]
    assert header.startswith(SESSION_COOKIE + "=")
    return header.lower()


def test_cookie_is_secure_behind_the_https_proxy_on_the_public_host(monkeypatch):
    app, _ = login_app(prod_settings(), monkeypatch, succeed=True)
    # Proxy giữ Host của trình duyệt và nói chuyện với backend bằng http.
    with TestClient(app, base_url="http://writory.example", client=(PROXY, 40000)) as c:
        resp = post_login(c, {"x-real-ip": FRIEND, "x-forwarded-proto": "https",
                              "origin": "https://writory.example"})
    assert resp.status_code == 200
    cookie = cookie_of(resp)
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie


def test_cookie_is_secure_after_the_tunnel_chain(monkeypatch):
    app, _ = login_app(prod_settings(), monkeypatch, succeed=True)
    with TestClient(app, base_url="http://writory.example", client=(PROXY, 40000)) as c:
        resp = post_login(c, tunnel_headers())
    assert resp.status_code == 200
    assert "secure" in cookie_of(resp)


def test_spoofed_forwarded_proto_cannot_drop_secure_on_a_public_host(monkeypatch):
    app, _ = login_app(prod_settings(), monkeypatch, succeed=True)
    with TestClient(app, base_url="http://writory.example", client=(PROXY, 40000)) as c:
        resp = post_login(c, {"x-forwarded-proto": "http"})
    assert "secure" in cookie_of(resp)


def test_https_proxy_on_localhost_makes_the_cookie_secure_only_if_trusted(monkeypatch):
    app, _ = login_app(prod_settings(), monkeypatch, succeed=True)
    with TestClient(app, base_url="http://localhost:8443", client=(PROXY, 40000)) as c:
        assert "secure" in cookie_of(post_login(c, {"x-forwarded-proto": "https"}))
    with TestClient(app, base_url="http://localhost:8443", client=(FRIEND, 40000)) as c:
        assert "secure" not in cookie_of(post_login(c, {"x-forwarded-proto": "https"}))
    with TestClient(app, base_url="http://localhost:8080", client=(PROXY, 40000)) as c:
        assert "secure" not in cookie_of(post_login(c))  # thử chồng prod bằng http trên máy


def test_same_origin_check_passes_behind_a_proxy_that_keeps_host(monkeypatch):
    app, _ = login_app(prod_settings(), monkeypatch, succeed=True)
    with TestClient(app, base_url="http://writory.example", client=(PROXY, 40000),
                    raise_server_exceptions=False) as c:
        assert post_login(c, {"origin": "https://writory.example"}).status_code == 200
        bad = post_login(c, {"origin": "https://evil.example"})
        assert bad.status_code == 403 and bad.json()["code"] == "REQUEST_ORIGIN_INVALID"
        form = c.post("/auth/login", data={"code": "x"})
        assert form.status_code == 403


# --- compose prod ----------------------------------------------------------------------------------

COMPOSE = REPO_ROOT / "docker-compose.prod.yml"


def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


DEV_PORTS = {"8000", "5173", "7474", "7687", "5432"}  # chồng dev chạy cùng máy (D-103)
SECRETS = ("NEO4J_PASSWORD", "POSTGRES_PASSWORD", "PLAYER_KEY_ENCRYPTION_KEY",
           "CLOUDFLARE_TUNNEL_TOKEN")


def test_prod_compose_publishes_no_port_the_tunnel_is_the_only_way_in():
    data = compose()
    assert data["name"] == "writory-prod"  # không trùng project của chồng dev
    services = data["services"]
    assert {"cloudflared", "proxy", "backend", "neo4j", "postgres"} <= set(services)
    assert {name for name, s in services.items() if s.get("ports")} == set()


def test_localtest_override_binds_only_loopback_away_from_dev_ports():
    data = yaml.safe_load((REPO_ROOT / "deploy" / "docker-compose.localtest.yml")
                          .read_text(encoding="utf-8"))
    assert data["services"]["cloudflared"]["profiles"]  # không chạy tunnel khi thử
    for name, service in data["services"].items():
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:"), (name, port)
            host_port = port.split(":")[1].split("-")[-1].rstrip("}")
            assert host_port not in DEV_PORTS, (name, port)


def test_prod_compose_services_restart_have_healthchecks_and_durable_volumes():
    data = compose()
    for name, service in data["services"].items():
        assert service.get("restart") == "unless-stopped", name
    for name in ("proxy", "backend", "neo4j", "postgres"):
        assert "healthcheck" in data["services"][name], name
    for name, mount in (("neo4j", "/data"), ("postgres", "/var/lib/postgresql/data"),
                        ("proxy", "/data")):
        volumes = data["services"][name]["volumes"]
        named = [v.split(":")[0] for v in volumes if v.endswith(":" + mount)]
        assert named and named[0] in data["volumes"], name  # volume có tên, không phải thư mục


def test_prod_compose_trust_chain_is_tunnel_then_proxy_then_backend():
    data = compose()
    services = data["services"]
    env = services["backend"]["environment"]
    assert env["APP_ENV"] == "prod"
    assert env["AUTH_MODE"] == "invite"
    assert "ENABLE_DEV_ROUTES" not in env
    # backend chỉ tin proxy; proxy chỉ tin cloudflared
    assert env["TRUSTED_PROXIES"] == services["proxy"]["networks"]["edge"]["ipv4_address"]
    assert (services["proxy"]["environment"]["CADDY_TRUSTED_PROXIES"]
            == services["cloudflared"]["networks"]["edge"]["ipv4_address"])
    for name in ("neo4j", "postgres"):  # kho chỉ ở mạng nội bộ, proxy và tunnel không tới được
        assert set(services[name]["networks"]) == {"data"}
    assert data["networks"]["data"].get("internal") is True
    for name in ("proxy", "cloudflared"):
        assert "data" not in services[name]["networks"], name


def test_prod_compose_requires_every_secret():
    text = COMPOSE.read_text(encoding="utf-8")
    for name in SECRETS:
        assert "${" + name + ":?" in text, name  # compose dừng khi thiếu, không có mặc định
    assert "change-me" not in text


def test_env_prod_example_lists_names_without_values():
    example = REPO_ROOT / ".env.prod.example"
    names = {}
    for line in example.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, _, value = line.partition("=")
            names[key.strip()] = value.strip()
    assert set(SECRETS) <= set(names)
    assert all(value == "" for value in names.values()), names
    readers = [COMPOSE, REPO_ROOT / "deploy" / "docker-compose.localtest.yml",
               *sorted((REPO_ROOT / "deploy").glob("*.ps1"))]
    text = "".join(path.read_text(encoding="utf-8-sig") for path in readers)
    for key in names:  # không có tên thừa mà compose hay script không đọc
        assert "${" + key in text or f"'{key}'" in text, key


def test_proxy_keeps_the_api_prefix_like_vite_and_does_not_buffer_sse():
    caddy = (REPO_ROOT / "deploy" / "Caddyfile").read_text(encoding="utf-8")
    assert "handle_path /api/*" in caddy  # bỏ tiền tố /api như proxy Vite (frontend/vite.config.ts)
    assert "flush_interval -1" in caddy
    assert "header_up X-Real-IP {client_ip}" in caddy
    assert "client_ip_headers Cf-Connecting-Ip" in caddy  # IP thật sau Cloudflare Tunnel
    assert "trusted_proxies static {$CADDY_TRUSTED_PROXIES}" in caddy


def test_backend_image_carries_every_file_the_app_reads_at_runtime():
    dockerfile = (REPO_ROOT / "deploy" / "backend.Dockerfile").read_text(encoding="utf-8")
    from writory.pipeline.scene import STYLE_GUIDE_PATH
    for path in (Path("config"), STYLE_GUIDE_PATH.relative_to(REPO_ROOT)):
        assert path.as_posix() in dockerfile, path
    lines = [ln for ln in dockerfile.splitlines() if not ln.lstrip().startswith("#")]
    assert any(ln.startswith("USER ") and "root" not in ln for ln in lines)
    assert not any("--reload" in ln for ln in lines)
