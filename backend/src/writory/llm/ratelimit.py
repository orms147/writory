"""Giới hạn tần suất lời gọi model (G8, D-56): mỗi lời gọi xin một lượt trước khi tới model.

Hết lượt thì `WRITORY_RATE_LIMITED`, trước khi gọi, nên không tốn tiền và không có dòng nhật ký chi
phí. `RateLimitedClient` nằm DƯỚI `RecordingClient` và `MeteredClient`, sát client thật: mọi lời
gọi tới model, kể cả lần thử lại vì lỗi mạng, đều được đếm vì đều là lời gọi thật. Lỗi này không
nằm trong `RETRY_TRANSIENT` nên không bị thử lại.
"""

from collections.abc import AsyncIterator, Mapping
from typing import Any, Protocol

from pydantic import BaseModel

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent


class CallQuota(Protocol):
    """Lượt gọi model của một người chơi. `take` trả False khi hết lượt trong phút này."""

    async def take(self) -> bool: ...


class RateLimitedClient(LLMClient):
    def __init__(self, inner: LLMClient, quota: CallQuota) -> None:
        self._inner = inner
        self._quota = quota

    async def _take(self) -> None:
        if not await self._quota.take():
            raise WritoryError(ErrorCode.WRITORY_RATE_LIMITED, detail="hết lượt gọi model trong phút")

    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        await self._take()
        return await self._inner.chat(model, messages, response_schema=response_schema, extra=extra)

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        await self._take()
        async for event in self._inner.stream(model, messages):
            yield event
