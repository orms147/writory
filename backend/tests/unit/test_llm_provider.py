"""Chọn client cho bộ đo theo config (D-140): một hàm tạo chung cho mọi bộ đo, nhà cung cấp theo tiền tố id model."""

from pathlib import Path

import httpx
import pytest

from tests.pipeline_fixtures import make_config
from writory.config import REPO_ROOT, ConfigError, load_config
from writory.llm.base import (
    ChatResult,
    GenerationCost,
    LLMClient,
    Message,
    StreamDone,
    TextDelta,
    Usage,
)
from writory.llm.meta import MetaClient
from writory.llm.openrouter import OpenRouterClient
from writory.llm.provider import RoutingClient, bench_llm, config_models, llm_identity, provider_of

META_DIR = REPO_ROOT / "evals" / "config" / "meta"
MSGS = [Message(role="user", content="x")]


@pytest.fixture(autouse=True)
def no_keys_in_the_environment(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "META_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def env(tmp_path: Path, **keys: str) -> Path:
    path = tmp_path / ".env"
    path.write_text("".join(f"{k}={v}\n" for k, v in keys.items()), encoding="utf-8")
    return path


def test_the_provider_is_the_prefix_of_the_model_id():
    assert provider_of("meta/muse-wonder-1.0") == "meta" and provider_of("openai/gpt-6-luna") == "openrouter"
    assert provider_of("meta-llama/llama-4") == "openrouter"


def test_config_models_lists_every_model_a_run_can_call_once():
    meta, repo = config_models(load_config(META_DIR)), config_models(load_config())
    assert meta == ["meta/muse-wonder-1.0"] and "openai/gpt-6-luna" in repo and len(set(repo)) == len(repo)


def test_a_config_with_only_openrouter_models_gets_the_openrouter_client_and_needs_only_its_key(tmp_path):
    client = bench_llm(load_config(), env(tmp_path, OPENROUTER_API_KEY="or-key"))
    assert isinstance(client, OpenRouterClient)
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        bench_llm(load_config(), env(tmp_path, META_API_KEY="m-key"))


def test_a_config_with_only_meta_models_gets_the_meta_client_and_needs_only_the_meta_key(tmp_path):
    client = bench_llm(load_config(META_DIR), env(tmp_path, META_API_KEY="m-key"))
    assert isinstance(client, MetaClient)
    with pytest.raises(ConfigError, match="META_API_KEY"):
        bench_llm(load_config(META_DIR), env(tmp_path, OPENROUTER_API_KEY="or-key"))


def test_a_mixed_config_gets_a_router_and_needs_both_keys(tmp_path):
    config = load_config(META_DIR)
    mixed = config.model_copy(update={"models": config.models.model_copy(update={
        "roles": config.models.roles.model_copy(update={"moderate": "openai/gpt-6-luna"})})})
    client = bench_llm(mixed, env(tmp_path, META_API_KEY="m", OPENROUTER_API_KEY="o"))
    assert isinstance(client, RoutingClient)
    with pytest.raises(ConfigError, match="META_API_KEY"):
        bench_llm(mixed, env(tmp_path, OPENROUTER_API_KEY="o"))


def test_the_http_client_and_deadline_reach_the_inner_client(tmp_path):
    http = httpx.AsyncClient()
    client = bench_llm(load_config(META_DIR), env(tmp_path, META_API_KEY="m"), http=http, deadline_s=42)
    assert client._http is http and client._deadline_s == 42


class Stub(LLMClient):
    def __init__(self, name):
        self.name, self.models = name, []

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        self.models.append(model)
        return ChatResult(text=self.name, usage=Usage(cost_usd=0.0))

    async def stream(self, model, messages):
        self.models.append(model)
        yield TextDelta(self.name)
        yield StreamDone(Usage(cost_usd=0.0))

    async def generation_cost(self, generation_id):
        return GenerationCost(cost_usd=1.0) if self.name == "or" else None


async def test_the_router_sends_each_model_to_its_own_client():
    meta, router = Stub("meta"), None
    openrouter = Stub("or")
    router = RoutingClient(meta=meta, openrouter=openrouter)
    assert (await router.chat("meta/muse-wonder-1.0", MSGS)).text == "meta"
    assert (await router.chat("openai/gpt-6-luna", MSGS)).text == "or"
    assert [e.text async for e in router.stream("meta/x", MSGS) if isinstance(e, TextDelta)] == ["meta"]
    assert meta.models == ["meta/muse-wonder-1.0", "meta/x"] and openrouter.models == ["openai/gpt-6-luna"]
    assert (await router.generation_cost("gen-1")).cost_usd == 1.0


async def test_the_router_without_a_client_for_a_model_says_so_instead_of_guessing():
    router = RoutingClient(meta=Stub("meta"), openrouter=None)
    with pytest.raises(ConfigError, match="openrouter"):
        await router.chat("openai/gpt-6-luna", MSGS)


def test_the_identity_for_meta_json_names_provider_and_models(tmp_path):
    assert llm_identity(load_config(META_DIR)) == {"provider": "meta", "models": ["meta/muse-wonder-1.0"]}
    repo = llm_identity(make_config(tmp_path))
    assert repo["provider"] == "openrouter" and repo["models"]
    mixed = load_config(META_DIR)
    mixed = mixed.model_copy(update={"models": mixed.models.model_copy(update={
        "roles": mixed.models.roles.model_copy(update={"moderate": "openai/gpt-6-luna"})})})
    assert llm_identity(mixed)["provider"] == "mixed"
