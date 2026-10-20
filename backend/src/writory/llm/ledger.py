"""Ghi chi phí của mọi lời gọi model vào nhật ký (G8, D-44).

`RecordingClient` bọc client thật, nằm DƯỚI `MeteredClient`: mỗi phản hồi về tới là ghi một dòng
(vai, model, token, chi phí), kể cả khi thiếu `usage.cost`, trước khi `CostTracker` kiểm và có thể
dừng. Lời gọi lỗi không có `usage`, nên không có dòng (stream đứt giữa chừng: docs/security.md).

Vai không truyền qua lời gọi; nơi dựng client đưa vào `role_of` (đoán vai theo schema JSON, không
schema là model viết).
"""

from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any

from pydantic import BaseModel

from writory.llm.base import ChatResult, LLMClient, Message, StreamDone, StreamEvent, Usage

CostSink = Callable[[str, str, Usage], None]  # (vai, model, usage)
RoleOf = Callable[[type[BaseModel] | None], str]


class RecordingClient(LLMClient):
    def __init__(self, inner: LLMClient, sink: CostSink, *, role_of: RoleOf) -> None:
        self._inner = inner
        self._sink = sink
        self._role_of = role_of

    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        result = await self._inner.chat(
            model, messages, response_schema=response_schema, extra=extra
        )
        self._sink(self._role_of(response_schema), model, result.usage)
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        async for event in self._inner.stream(model, messages):
            if isinstance(event, StreamDone):
                self._sink(self._role_of(None), model, event.usage)
            yield event
