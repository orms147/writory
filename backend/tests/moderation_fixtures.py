"""Model giả cho lời gọi kiểm duyệt (G9, D-57), dùng chung cho test pipeline và API.

Lời gọi kiểm duyệt (schema `ModerationOutput`) có hàng đợi riêng: không lẫn vào kịch bản của các vai
khác (thứ tự dàn ý → viết → trích …) và không nằm trong `calls` của model bọc. Hết hàng đợi thì cho
qua (findings rỗng). Test về kiểm duyệt đặt hàng đợi riêng và đọc `moderation_calls`.
"""

import json
from collections import deque
from collections.abc import AsyncIterator, Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, Usage
from writory.safety.moderate import ModerationOutput


def moderation_reply(*findings: tuple[str, str], reason: str = "lý do ngắn") -> str:
    """`findings`: (category, intensity), ví dụ ("gore", "extreme")."""
    return json.dumps(
        {"findings": [{"category": c, "intensity": i} for c, i in findings], "reason": reason},
        ensure_ascii=False,
    )


ALLOW = moderation_reply()


class ModerationScript:
    """Hàng đợi câu trả lời kiểm duyệt + nhật ký lời gọi. Dùng trong model giả bất kỳ."""

    def __init__(self, replies: Iterable[str | Exception] = (), *,
                 cost_usd: float | None = 0.0) -> None:
        self.replies = deque(replies)
        self.cost_usd = cost_usd
        self.moderation_calls: list[list[Message]] = []
        self.moderation_extras: list[Mapping[str, Any] | None] = []

    def answer(self, model: str, messages: list[Message], extra) -> ChatResult:
        self.moderation_calls.append(list(messages))
        self.moderation_extras.append(extra)
        item = self.replies.popleft() if self.replies else ALLOW
        if isinstance(item, Exception):
            raise item
        return ChatResult(text=item, usage=Usage(cost_usd=self.cost_usd), model=model,
                          finish_reason="stop")


class ModeratedLLM(LLMClient):
    """Bọc một model giả: lời gọi kiểm duyệt do `ModerationScript` trả lời, mọi lời gọi khác chuyển
    nguyên cho model bọc. Thuộc tính khác (calls, schemas, …) đọc thẳng từ model bọc."""

    def __init__(self, inner: LLMClient, replies: Iterable[str | Exception] = (), *,
                 cost_usd: float | None = 0.0) -> None:
        self.inner = inner
        self.script = ModerationScript(replies, cost_usd=cost_usd)

    @property
    def moderation_calls(self) -> list[list[Message]]:
        return self.script.moderation_calls

    def __getattr__(self, name: str):
        return getattr(self.inner, name)

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        if response_schema is ModerationOutput:
            return self.script.answer(model, messages, extra)
        return await self.inner.chat(model, messages, response_schema=response_schema, extra=extra)

    def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        return self.inner.stream(model, messages)
