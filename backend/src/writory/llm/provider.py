"""Chọn client cho BỘ ĐO theo config (D-140): một hàm tạo chung thay cho `OpenRouterClient(...)` rải ở từng bộ đo.

Nhà cung cấp của một lời gọi là tiền tố id model (`meta/...` đi Meta, còn lại OpenRouter). Config chỉ có model
OpenRouter thì client là `OpenRouterClient` và chỉ cần `OPENROUTER_API_KEY`; chỉ có model Meta thì là `MetaClient`
và chỉ cần `META_API_KEY`; trộn cả hai thì `RoutingClient`. Muốn đổi nhà cung cấp của bộ đo là đổi config
(`--config-dir`), không có cờ riêng. Sản phẩm cho người chơi không đi qua đây (D-2, `product_model_problems`)."""

from collections.abc import AsyncIterator, Iterable, Mapping
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

from writory.config import AppConfig, ConfigError, is_meta_model
from writory.llm.base import ChatResult, GenerationCost, LLMClient, Message, StreamEvent
from writory.llm.meta import MetaClient
from writory.llm.openrouter import OpenRouterClient

OPENROUTER, META = "openrouter", "meta"


def provider_of(model: str) -> str:
    return META if is_meta_model(model) else OPENROUTER


def config_models(config: AppConfig) -> list[str]:
    """Mọi model một lần chạy có thể gọi theo config: các vai đã chọn, rồi các mức model viết."""
    found = [m for m in config.models.roles.model_dump().values() if m]
    found += [t.model for t in config.models.writer_tiers]
    return list(dict.fromkeys(found))


def llm_identity(config: AppConfig, models: Iterable[str] | None = None) -> dict[str, Any]:
    """Nhà cung cấp và model để ghi vào `meta.json` của bộ đo: `openrouter`, `meta` hay `mixed`."""
    used = sorted(set(config_models(config) if models is None else models))
    providers = {provider_of(m) for m in used}
    return {"provider": providers.pop() if len(providers) == 1 else ("mixed" if providers else None),
            "models": used}


class RoutingClient(LLMClient):
    """Gửi mỗi lời gọi tới client của nhà cung cấp theo tiền tố id model."""

    def __init__(self, *, meta: LLMClient | None, openrouter: LLMClient | None) -> None:
        self._clients: Mapping[str, LLMClient | None] = {META: meta, OPENROUTER: openrouter}

    def _for(self, model: str) -> LLMClient:
        provider = provider_of(model)
        client = self._clients[provider]
        if client is None:
            raise ConfigError(f"model {model} cần nhà cung cấp {provider} mà lần chạy này không dựng client cho nó")
        return client

    async def chat(self, model: str, messages: list[Message], *, response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        return await self._for(model).chat(model, messages, response_schema=response_schema, extra=extra)

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        async for event in self._for(model).stream(model, messages):
            yield event

    async def generation_cost(self, generation_id: str) -> GenerationCost | None:
        client = self._clients[OPENROUTER]  # id generation `gen-...` là của OpenRouter
        return None if client is None else await client.generation_cost(generation_id)


def bench_llm(config: AppConfig, env_file: Path, *, http: httpx.AsyncClient | None = None,
              deadline_s: float | None = None, models: Iterable[str] | None = None) -> LLMClient:
    """Client của bộ đo cho các model của `config` (hay `models`): key của chủ dự án từ `env_file` hay biến môi
    trường, chỉ key các nhà cung cấp thật sự cần. Không in, không ghi key (G7)."""
    from writory.quality.bench_d import load_keys  # trì hoãn: bench_d nặng và import lại lớp llm

    wanted = {provider_of(m) for m in (config_models(config) if models is None else models)}
    keys = load_keys(env_file, sorted(wanted))
    openrouter = meta = None
    if OPENROUTER in wanted:
        assert keys.openrouter_api_key is not None
        openrouter = OpenRouterClient(keys.openrouter_api_key, http=http, deadline_s=deadline_s)
    if META in wanted:
        assert keys.meta_api_key is not None
        meta = MetaClient(keys.meta_api_key, config.models.prices, http=http, deadline_s=deadline_s)
    if openrouter is not None and meta is not None:
        return RoutingClient(meta=meta, openrouter=openrouter)
    return meta or openrouter or _no_models()


def _no_models() -> LLMClient:
    raise ConfigError("config không chọn model nào: không biết dựng client của nhà cung cấp nào")
