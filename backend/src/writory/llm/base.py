"""Interface tối giản cho mọi client LLM: chat, chat theo schema JSON, stream."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Mapping
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


def role_extra(models: ModelsConfig, role: str) -> dict[str, Any] | None:
    """Tham số riêng của một vai cho `chat`/`chat_json` (`extra`): mức suy luận trong
    `role_reasoning` (tham số `reasoning` của OpenRouter, như bài C). null thì không gửi gì."""
    effort = getattr(models.role_reasoning, role)
    return {"reasoning": {"effort": effort}} if effort is not None else None


class Message(BaseModel):
    model_config = ConfigDict(frozen=True)
    role: Literal["system", "user", "assistant"]
    content: str


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    # None = phản hồi không cho biết chi phí. CostTracker coi đó là lỗi (D-10).
    cost_usd: float | None


class ChatResult(BaseModel):
    text: str
    usage: Usage
    # Model thật sự trả lời (theo phản hồi) và lý do dừng ("length" = chạm max_tokens).
    model: str | None = None
    finish_reason: str | None = None


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class StreamDone:
    usage: Usage


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
