"""Interface tối giản cho mọi client LLM: chat, chat theo schema JSON, stream, tra chi phí theo id
generation. Kèm `CallTrace`: điều client thật biết về một lời gọi khi nó chưa xong (D-64)."""

import re
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from writory.config import LimitNotSetError, ModelsConfig, RoleModels
from writory.errors import ErrorCode, WritoryError


def require_model(roles: RoleModels, role: str) -> str:
    """Model của một vai trong config/models.yaml. Vai chưa chọn model (null) thì báo
    CONFIG_MODEL_NOT_SET, không đoán model nào."""
    try:
        return roles.require(role)
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_MODEL_NOT_SET, detail=str(e)) from None


def reasoning_extra(effort: str | None) -> dict[str, Any] | None:
    """`extra` cho một mức suy luận (tham số `reasoning` của OpenRouter). null thì không gửi gì."""
    return {"reasoning": {"effort": effort}} if effort is not None else None


def role_extra(models: ModelsConfig, role: str) -> dict[str, Any] | None:
    """Tham số riêng của một vai cho `chat`/`chat_json` (`extra`): mức suy luận trong
    `role_reasoning` (tham số `reasoning` của OpenRouter, như bài C) và nhà cung cấp bị loại
    (`provider_ignore`, D-100). Không có gì thì trả None."""
    extra = reasoning_extra(getattr(models.role_reasoning, role)) or {}
    extra.update(provider_extra(models) or {})
    return extra or None


def provider_extra(models: ModelsConfig) -> dict[str, Any] | None:
    """Chỉ phần nhà cung cấp của `extra` (D-100): `provider_ignore` trong config/models.yaml, kèm
    `require_parameters`. Mọi vai lấy phần này qua `role_extra` (D-106)."""
    if not models.provider_ignore:
        return None
    return {"provider": {"require_parameters": True, "ignore": list(models.provider_ignore)}}


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: Literal["system", "user", "assistant"]
    content: str


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # None = phản hồi không cho biết chi phí. CostTracker coi đó là lỗi (D-10).
    cost_usd: float | None
    # Số token vào được đọc từ cache prompt của nhà cung cấp (usage.prompt_tokens_details.
    # cached_tokens, D-96). None = phản hồi không báo (khác 0 = đã báo, không có cache).
    cached_tokens: int | None = None


class ChatResult(BaseModel):
    text: str
    usage: Usage
    # Model thật sự trả lời (theo phản hồi) và lý do dừng ("length" = chạm max_tokens).
    model: str | None = None
    finish_reason: str | None = None
    # Id generation của OpenRouter (`gen-...`), để tra lại chi phí sau (D-64). None: không biết.
    generation_id: str | None = None


class GenerationCost(BaseModel):
    """Chi phí thật của một generation, tra lại theo id sau khi lời gọi đã xong (D-64)."""

    cost_usd: float
    prompt_tokens: int = 0
    completion_tokens: int = 0


# Id generation hợp lệ theo docs OpenRouter (GET /generation): "gen-" rồi chữ, số, gạch ngang;
# tối đa 128 ký tự. Id lạ từ header hay thân phản hồi bị bỏ qua, không đưa vào URL hay nhật ký.
_GENERATION_ID = re.compile(r"gen-[A-Za-z0-9-]{1,124}")


def valid_generation_id(value: object) -> str | None:
    return value if isinstance(value, str) and _GENERATION_ID.fullmatch(value) else None


@dataclass
class CallTrace:
    """Điều client thật báo về một lời gọi đang chạy, để nơi ghi chi phí còn biết khi lời gọi lỗi
    hay bị huỷ (lúc đó không có `usage`; D-64).

    `sent`: None = client không báo (model giả, client khác), coi như có thể đã gửi; False = chắc
    chắn chưa tới nhà cung cấp (lỗi kết nối, chưa bắt đầu); True = yêu cầu đã đi.
    `generation_id`: id generation, biết ngay khi có header phản hồi."""

    sent: bool | None = None
    generation_id: str | None = None


_CALL_TRACE: ContextVar[CallTrace | None] = ContextVar("writory_llm_call_trace", default=None)


@contextmanager
def trace_call() -> Iterator[CallTrace]:
    """Mở một `CallTrace` cho lời gọi chạy trong khối này (cùng task asyncio)."""
    trace = CallTrace()
    token = _CALL_TRACE.set(trace)
    try:
        yield trace
    finally:
        _CALL_TRACE.reset(token)


def current_trace() -> CallTrace | None:
    """`CallTrace` của lời gọi đang chạy; None khi không ai mở (client thật vẫn chạy bình thường)."""
    return _CALL_TRACE.get()


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class StreamDone:
    usage: Usage
    generation_id: str | None = None


type StreamEvent = TextDelta | StreamDone


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        """`extra`: tham số riêng theo model (ví dụ max_tokens, reasoning), thêm vào thân yêu cầu."""

    @abstractmethod
    def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        """Trả các TextDelta, rồi đúng một StreamDone ở cuối."""

    async def generation_cost(self, generation_id: str) -> GenerationCost | None:
        """Chi phí thật của một generation đã xong. None: chưa có (thử lại sau) hoặc client này
        không tra được. Mặc định: không tra được."""
        return None

    async def chat_json[T: BaseModel](
        self, model: str, messages: list[Message], schema: type[T],
        *, extra: Mapping[str, Any] | None = None,
    ) -> tuple[T, ChatResult]:
        """Gọi chat với schema JSON rồi kiểm bằng pydantic (G11). Không tự thử lại."""
        result = await self.chat(model, messages, response_schema=schema, extra=extra)
        try:
            return schema.model_validate_json(result.text), result
        except ValidationError as e:
            # Không ghi chữ model trả về vào log: có thể chứa bí mật truyện.
            problems = "; ".join(
                f"{'.'.join(str(p) for p in err['loc']) or '(gốc)'}: {err['type']}"
                for err in e.errors(include_input=False, include_url=False)
            )
            raise WritoryError(
                ErrorCode.LLM_BAD_RESPONSE, detail=f"{schema.__name__}: {problems}"
            ) from None
