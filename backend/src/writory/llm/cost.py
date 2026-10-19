"""Theo dõi chi phí và trần (G8): cộng dồn theo cảnh, chương, truyện; chạm trần thì dừng.

Trần kiểm trước mỗi lời gọi, nên lời gọi cuối có thể vượt trần đúng bằng chi phí của chính nó
(D-10). Trần chưa đặt (null) là lỗi, không phải vô hạn.
"""

from collections.abc import AsyncIterator

from pydantic import BaseModel

from writory.config import CostLimits, LimitNotSetError
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import ChatResult, LLMClient, Message, StreamDone, StreamEvent


class CostTracker:
    def __init__(self, limits: CostLimits, *, story_spent_usd: float = 0.0) -> None:
        self._limits = limits
        self.story_usd = story_spent_usd
        self.chapter_usd = 0.0
        self.scene_usd = 0.0

    def start_chapter(self) -> None:
        self.chapter_usd = 0.0
        self.scene_usd = 0.0

    def start_scene(self) -> None:
        self.scene_usd = 0.0

    def ensure_budget(self) -> None:
        checks = (
            ("per_story", self.story_usd, ErrorCode.COST_LIMIT_STORY),
            ("per_chapter", self.chapter_usd, ErrorCode.COST_LIMIT_CHAPTER),
            ("per_scene", self.scene_usd, ErrorCode.COST_LIMIT_SCENE),
        )
        for name, spent, code in checks:
            try:
                cap = self._limits.require(name)
            except LimitNotSetError as e:
                raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None
            if spent >= cap:
                raise WritoryError(code, detail=f"đã tiêu {spent:.6f} USD, trần {name}={cap}")

    def record(self, cost_usd: float | None) -> None:
        if cost_usd is None:
            raise WritoryError(
                ErrorCode.LLM_COST_UNKNOWN, detail="phản hồi không có usage.cost"
            )
        if cost_usd < 0:
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail=f"usage.cost âm: {cost_usd}")
        self.scene_usd += cost_usd
        self.chapter_usd += cost_usd
        self.story_usd += cost_usd


class MeteredClient(LLMClient):
    """Bọc một client: kiểm trần trước mỗi lời gọi, ghi chi phí sau lời gọi."""

    def __init__(self, inner: LLMClient, tracker: CostTracker) -> None:
        self._inner = inner
        self.tracker = tracker

    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
    ) -> ChatResult:
        self.tracker.ensure_budget()
        result = await self._inner.chat(model, messages, response_schema=response_schema)
        self.tracker.record(result.usage.cost_usd)
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        self.tracker.ensure_budget()
        async for event in self._inner.stream(model, messages):
            if isinstance(event, StreamDone):
                self.tracker.record(event.usage.cost_usd)
            yield event
