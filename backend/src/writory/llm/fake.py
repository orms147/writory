"""Model giả cho test. Không mạng.

Hai chế độ:
- `scripted` / `from_fixture`: trả lần lượt các câu ghi sẵn (hoặc ném lỗi ghi sẵn).
- `echo`: trả lại nguyên context nhận được, để test G1 đỏ ngay khi lọc `player_view` sai.
"""

import json
from collections import deque
from collections.abc import AsyncIterator, Iterable
from pathlib import Path

from pydantic import BaseModel

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import (
    ChatResult,
    LLMClient,
    Message,
    StreamDone,
    StreamEvent,
    TextDelta,
    Usage,
)

_STREAM_CHUNK_CHARS = 16


def render_context(messages: list[Message]) -> str:
    return "\n\n".join(f"[{m.role}]\n{m.content}" for m in messages)


class FakeLLM(LLMClient):
    def __init__(
        self,
        responses: Iterable[str | Exception] | None,
        *,
        cost_usd: float | None = 0.0,
    ) -> None:
        self._responses = deque(responses) if responses is not None else None
        self._cost_usd = cost_usd
        self.calls: list[list[Message]] = []
        self.schemas: list[type[BaseModel]] = []

    @classmethod
    def scripted(
        cls, responses: Iterable[str | Exception], *, cost_usd: float | None = 0.0
    ) -> "FakeLLM":
        return cls(responses, cost_usd=cost_usd)

    @classmethod
    def echo(cls, *, cost_usd: float | None = 0.0) -> "FakeLLM":
        return cls(None, cost_usd=cost_usd)

    @classmethod
    def from_fixture(cls, path: Path, *, cost_usd: float | None = 0.0) -> "FakeLLM":
        """File JSON: {"responses": [chuỗi | {"error": "<ErrorCode>"}]}."""
        data = json.loads(path.read_text(encoding="utf-8"))
        responses: list[str | Exception] = [
            item if isinstance(item, str) else WritoryError(ErrorCode(item["error"]), "fixture")
            for item in data["responses"]
        ]
        return cls(responses, cost_usd=cost_usd)

    def _next(self, messages: list[Message]) -> str:
        self.calls.append(list(messages))
        if self._responses is None:
            return render_context(messages)
        if not self._responses:
            raise AssertionError("FakeLLM: hết câu trả lời ghi sẵn")
        item = self._responses.popleft()
        if isinstance(item, Exception):
            raise item
        return item

    def _usage(self) -> Usage:
        return Usage(cost_usd=self._cost_usd)

    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
    ) -> ChatResult:
        if response_schema is not None:
            self.schemas.append(response_schema)
        return ChatResult(text=self._next(messages), usage=self._usage())

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        text = self._next(messages)
        for i in range(0, len(text), _STREAM_CHUNK_CHARS):
            yield TextDelta(text[i : i + _STREAM_CHUNK_CHARS])
        yield StreamDone(self._usage())
