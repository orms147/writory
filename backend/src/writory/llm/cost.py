"""Theo dõi chi phí và trần (G8): cộng dồn theo cảnh, chương, truyện; chạm trần thì dừng.

Trần kiểm trước mỗi lời gọi, nên lời gọi cuối có thể vượt trần đúng bằng chi phí của chính nó
(D-10). Trần chưa đặt (null) là lỗi, không phải vô hạn.

Lời gọi không có usage (bị huỷ, đứt giữa chừng, thiếu usage.cost) được tính bằng chi phí tối đa
của nó (`CostEstimator`, D-64); `maybe_billed` nói lời gọi lỗi nào có thể đã bị tính tiền.
"""

import asyncio
import json
import math
import statistics
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel

from writory.config import AppConfig, CostLimits, LimitNotSetError, ModelPrice
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import (
    CallTrace,
    ChatResult,
    LLMClient,
    Message,
    StreamDone,
    StreamEvent,
)

# Ước tính thô số token vào từ số ký tự; chỉ để giữ chỗ ngân sách và ước tính tối đa, chi phí thật
# lấy từ usage. Chưa đo với tokenizer thật: chưa chắc là chặn trên của phần vào.
EST_CHARS_PER_TOKEN = 2.0


class CostEstimator:
    """Chi phí tối đa của một lời gọi: token vào ước tính (ký tự đề + schema JSON, chia
    `EST_CHARS_PER_TOKEN`) × giá vào + `max_output_tokens` × giá ra, như bench_run (D-43).

    Phần ra chỉ là chặn trên thật khi lời gọi gửi kèm `max_tokens` không quá `max_output_tokens`:
    nơi dùng số này phải gửi `bound(extra)` (D-64). Model không có giá: fail closed, trước khi
    gọi."""

    def __init__(self, prices: Mapping[str, ModelPrice], *, max_output_tokens: int) -> None:
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens phải > 0")
        self._prices = dict(prices)
        self.max_output_tokens = max_output_tokens

    @classmethod
    def from_config(cls, config: AppConfig) -> "CostEstimator":
        try:
            cap = config.limits.llm_call.require("max_output_tokens")
        except LimitNotSetError as e:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None
        return cls(config.models.prices, max_output_tokens=cap)

    def bound(self, extra: Mapping[str, Any] | None) -> dict[str, Any]:
        """`extra` của lời gọi, với `max_tokens` không quá trần (vai nào đặt thấp hơn thì giữ)."""
        out = dict(extra or {})
        out["max_tokens"] = min(out.get("max_tokens", self.max_output_tokens),
                                self.max_output_tokens)
        return out

    def max_cost(self, model: str, messages: Sequence[Message],
                 schema: type[BaseModel] | None) -> float:
        price = self._prices.get(model)
        if price is None:
            raise WritoryError(
                ErrorCode.CONFIG_LIMIT_NOT_SET,
                detail=f"config/models.yaml: prices chưa có giá cho model {model}",
            )
        chars = sum(len(m.content) for m in messages)
        if schema is not None:
            chars += len(json.dumps(schema.model_json_schema(), ensure_ascii=False))
        tokens_in = math.ceil(chars / EST_CHARS_PER_TOKEN)
        return (tokens_in * price.input + self.max_output_tokens * price.output) / 1e6


def maybe_billed(exc: BaseException, trace: CallTrace) -> bool:
    """Lời gọi kết thúc bằng `exc` có thể đã bị tính tiền không (D-64).

    - Đã có id generation: nhà cung cấp đã nhận yêu cầu; tra lại theo id ra số thật (có thể 0).
    - Client báo chắc chưa gửi (lỗi kết nối): không.
    - Bị huỷ khi có thể đã gửi: có (lời gọi không stream bị huỷ vẫn bị tính đủ, docs OpenRouter).
    - Lỗi mạng sau khi gửi (LLM_UNAVAILABLE không kèm HTTP status): có.
    - Quá hạn tổng sau khi gửi (LLM_TIMEOUT, D-113): có, như lời gọi bị huỷ.
    - Lỗi có HTTP status mà không có generation, và mọi lỗi khác (WRITORY_RATE_LIMITED chặn trước
      khi gọi, extra sai): không."""
    if trace.generation_id is not None:
        return True
    if trace.sent is False:
        return False
    if isinstance(exc, asyncio.CancelledError):
        return True
    if isinstance(exc, WritoryError) and exc.code is ErrorCode.LLM_TIMEOUT:
        return True
    return (isinstance(exc, WritoryError) and exc.code is ErrorCode.LLM_UNAVAILABLE
            and not exc.detail.startswith("HTTP "))


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
        extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        self.tracker.ensure_budget()
        result = await self._inner.chat(
            model, messages, response_schema=response_schema, extra=extra
        )
        self.tracker.record(result.usage.cost_usd)
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        self.tracker.ensure_budget()
        async for event in self._inner.stream(model, messages):
            if isinstance(event, StreamDone):
                self.tracker.record(event.usage.cost_usd)
            yield event


@dataclass(frozen=True)
class ChapterEstimate:
    """Ước tính chi phí chương tới (D-87). `usd` None: không có số nào để nói (không chương nào
    đo được và config chưa đặt số mặc định). `chapters_used`: số chương đo được dùng để ước."""

    usd: float | None
    source: Literal["story_median", "default"]
    chapters_used: int


def estimate_chapter_cost(chapter_costs: Sequence[float], *,
                          default_usd: float | None) -> ChapterEstimate:
    """Trung vị chi phí thật mỗi chương đã ghi của chính truyện. Trung vị, không phải trung bình:
    một chương phải viết lại nhiều lần không kéo cả ước tính. Chưa có chương nào thì số mặc định."""
    if chapter_costs:
        return ChapterEstimate(float(statistics.median(chapter_costs)), "story_median",
                               len(chapter_costs))
    return ChapterEstimate(default_usd, "default", 0)
