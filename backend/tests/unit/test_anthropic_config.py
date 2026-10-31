"""Cấu hình bộ đo dùng Claude qua Anthropic API (D-145): tiền tố `anthropic-api/`, định tuyến, thư mục config bộ đo,
và sản phẩm từ chối model của bộ đo. Không mạng."""

from pathlib import Path

import httpx
import pytest
import yaml
from pydantic import SecretStr

from tests.pipeline_fixtures import make_config
from writory.api.app import create_app
from writory.config import (
    REPO_ROOT,
    ConfigError,
    ModelPrice,
    Settings,
    is_anthropic_model,
    is_bench_only_model,
    load_config,
    product_model_problems,
)
from writory.errors import ErrorCode, WritoryError
from writory.llm.anthropic_client import AnthropicClient
from writory.llm.base import Message
from writory.llm.openrouter import OpenRouterClient
from writory.llm.provider import RoutingClient, bench_llm, config_models, llm_identity, provider_of

DIR = REPO_ROOT / "evals" / "config" / "anthropic"
META_DIR = REPO_ROOT / "evals" / "config" / "meta"
MODEL = "anthropic-api/claude-haiku-5-5"


@pytest.fixture(autouse=True)
def no_keys_in_the_environment(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "META_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def env(tmp_path: Path, **keys: str) -> Path:
    path = tmp_path / ".env"
    path.write_text("".join(f"{k}={v}\n" for k, v in keys.items()), encoding="utf-8")
    return path


def test_the_prefix_cannot_clash_with_openrouters_own_anthropic_models():
    """OpenRouter đặt model Claude dưới `anthropic/...`: tiền tố của bộ đo phải khác để sản phẩm vẫn dùng được chúng."""
    assert is_anthropic_model(MODEL) and not is_anthropic_model("anthropic/claude-haiku-5-5")
    assert not is_anthropic_model("anthropic-apix/claude") and not is_anthropic_model(None)
    assert not is_anthropic_model("x-anthropic-api/claude")    # chỉ tiền tố, không phải chỗ nào trong chuỗi
    assert is_bench_only_model(MODEL) and is_bench_only_model("meta/muse-wonder-1.0")
    assert not is_bench_only_model("anthropic/claude-haiku-5-5") and not is_bench_only_model("openai/gpt-6-luna")
    assert provider_of(MODEL) == "anthropic" and provider_of("anthropic/claude-haiku-5-5") == "openrouter"


def test_a_price_can_carry_cache_write_and_long_prompt_rates():
    price = ModelPrice.model_validate({"in": 0.1, "out": 0.5, "cached_in": 0.01, "cache_write_in": 0.125,
                                       "long_prompt": {"over_tokens": 100000, "in": 0.5, "out": 2.5}})
    assert price.cache_write_in == 0.125 and price.long_prompt.over_tokens == 100000
    assert ModelPrice.model_validate({"in": 0.1, "out": 0.5}).long_prompt is None
    with pytest.raises(ValueError):
        ModelPrice.model_validate({"in": 0.1, "out": 0.5, "long_prompt": {"over_tokens": 0, "in": 1, "out": 1}})


# --- config bộ đo trong repo --------------------------------------------------------------------


def test_the_repo_anthropic_bench_config_uses_haiku_for_every_role_and_tier_and_prices_it():
    config = load_config(DIR)
    roles = config.models.roles.model_dump()
    assert roles and all(v is None or v == MODEL for v in roles.values()) and roles["setup"] == MODEL
    assert {t.model for t in config.models.writer_tiers} == {MODEL}
    price = config.models.prices[MODEL]
    assert price.input > 0 and price.output > 0 and price.cached_in and price.cache_write_in and price.long_prompt
    assert config.models.provider_ignore == []


def test_the_anthropic_bench_config_dir_holds_only_models_yaml_because_the_price_matches_luna():
    """Haiku 5.5 giá bằng Luna (cùng bảng giá cho prompt đến 100 nghìn token), nên trần chi phí của config/ dùng được
    nguyên: không có limits.yaml riêng."""
    assert sorted(p.name for p in DIR.glob("*.yaml")) == ["models.yaml"]
    config, base = load_config(DIR), load_config()
    luna = base.models.prices["openai/gpt-6-luna"]
    assert (config.models.prices[MODEL].input, config.models.prices[MODEL].output) == (luna.input, luna.output)
    assert config.limits == base.limits
    assert set(yaml.safe_load((DIR / "models.yaml").read_text(encoding="utf-8"))) == {"roles", "writer_tiers", "prices"}


def test_the_anthropic_models_file_keeps_the_roles_and_tiers_of_the_repo_one_apart_from_the_model_names():
    anth, base = load_config(DIR).models, load_config().models
    assert {r: m is None for r, m in anth.roles.model_dump().items()} == {
        r: m is None for r, m in base.roles.model_dump().items()}
    assert anth.role_reasoning == base.role_reasoning
    assert [t.model_copy(update={"model": ""}) for t in anth.writer_tiers] == [
        t.model_copy(update={"model": ""}) for t in base.writer_tiers]


# --- định tuyến ---------------------------------------------------------------------------------


def test_a_config_with_only_anthropic_models_gets_the_anthropic_client_and_needs_only_its_key(tmp_path):
    client = bench_llm(load_config(DIR), env(tmp_path, ANTHROPIC_API_KEY="a-key"))
    assert isinstance(client, AnthropicClient)
    with pytest.raises(ConfigError, match="ANTHROPIC_API_KEY"):
        bench_llm(load_config(DIR), env(tmp_path, OPENROUTER_API_KEY="o", META_API_KEY="m"))


def test_the_workspace_id_in_the_env_file_reaches_the_client(tmp_path):
    client = bench_llm(load_config(DIR), env(tmp_path, ANTHROPIC_API_KEY="a", ANTHROPIC_WORKSPACE_ID="wrk_1"))
    assert client._workspace_id.get_secret_value() == "wrk_1"


def test_three_providers_in_one_config_get_a_router_and_need_all_three_keys(tmp_path):
    config = load_config(META_DIR)
    roles = config.models.roles.model_copy(update={"moderate": "openai/gpt-6-luna", "summary": MODEL})
    mixed = config.model_copy(update={"models": config.models.model_copy(update={"roles": roles})})
    full = env(tmp_path, META_API_KEY="m", OPENROUTER_API_KEY="o", ANTHROPIC_API_KEY="a")
    assert isinstance(bench_llm(mixed, full), RoutingClient)
    anth = load_config(DIR)
    two = anth.model_copy(update={"models": anth.models.model_copy(update={"roles": anth.models.roles.model_copy(
        update={"summary": "openai/gpt-6-luna"})})})
    assert isinstance(bench_llm(two, env(tmp_path, OPENROUTER_API_KEY="o", ANTHROPIC_API_KEY="a")), RoutingClient)
    for missing in ("META_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"):
        keys = {k: "x" for k in ("META_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY") if k != missing}
        with pytest.raises(ConfigError, match=missing):
            bench_llm(mixed, env(tmp_path, **keys))
    assert llm_identity(mixed)["provider"] == "mixed"
    assert llm_identity(load_config(DIR)) == {"provider": "anthropic", "models": [MODEL]}
    assert config_models(load_config(DIR)) == [MODEL]


async def test_the_router_sends_each_model_to_its_provider():
    from tests.unit.test_llm_provider import Stub

    meta, anth, openrouter = Stub("meta"), Stub("anth"), Stub("or")
    router = RoutingClient(meta=meta, openrouter=openrouter, anthropic=anth)
    assert (await router.chat(MODEL, [Message(role="user", content="x")])).text == "anth"
    assert (await router.chat("meta/x", [Message(role="user", content="x")])).text == "meta"
    assert (await router.chat("anthropic/claude-x", [Message(role="user", content="x")])).text == "or"
    lonely = RoutingClient(meta=meta, openrouter=openrouter, anthropic=None)
    with pytest.raises(ConfigError, match="anthropic"):
        await lonely.chat(MODEL, [Message(role="user", content="x")])


# --- sản phẩm cho người chơi --------------------------------------------------------------------


def test_the_product_check_names_anthropic_api_models_too_but_not_openrouters_claude_models(tmp_path):
    problems = product_model_problems(load_config(DIR))
    assert any("roles.setup" in p for p in problems) and any("writer_tiers" in p for p in problems)
    assert all(MODEL in p for p in problems)
    clean = make_config(tmp_path, models={"roles": {"summary": "anthropic/claude-haiku-5-5"},
                                          "prices": {"anthropic/claude-haiku-5-5": {"in": 0.1, "out": 0.5}}})
    assert product_model_problems(clean) == []


def test_the_app_refuses_to_start_with_an_anthropic_api_model_in_its_config():
    settings = Settings(_env_file=None, neo4j_uri="bolt://x", neo4j_user="u", neo4j_password=SecretStr("p"),  # type: ignore[call-arg]
                        postgres_dsn=SecretStr("postgresql://u:p@h/d"), player_key_encryption_key=SecretStr("k"))
    with pytest.raises(ConfigError, match="anthropic-api/"):
        create_app(config=load_config(DIR), settings=settings, health_checks={}, storage_setup=lambda s: None)


async def test_the_openrouter_client_refuses_an_anthropic_api_model_but_accepts_openrouters_own_claude_id():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                                         "usage": {"cost": 0.0}})

    client = OpenRouterClient(SecretStr("k"), http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(WritoryError) as caught:
        await client.chat(MODEL, [Message(role="user", content="x")])
    assert caught.value.code is ErrorCode.CONFIG_MODEL_NOT_SET and seen == []
    assert (await client.chat("anthropic/claude-haiku-5-5", [Message(role="user", content="x")])).text == "ok"
