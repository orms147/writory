"""Interface tối giản cho mọi client LLM: chat, chat theo schema JSON, stream."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from writory.errors import ErrorCode, WritoryError


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
    ) -> ChatResult: ...

    @abstractmethod
    def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        """Trả các TextDelta, rồi đúng một StreamDone ở cuối."""

    async def chat_json[T: BaseModel](
        self, model: str, messages: list[Message], schema: type[T]
    ) -> tuple[T, ChatResult]:
        """Gọi chat với schema JSON rồi kiểm bằng pydantic (G11). Không tự thử lại."""
        result = await self.chat(model, messages, response_schema=schema)
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
