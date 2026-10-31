"""Client có trần chi phí cho các công cụ admin chạy bằng lệnh: bộ xuất kịch bản video (D-125) và bộ viết kịch
bản audio (D-151). Trần là `--budget` của lệnh, tiền là key của chủ dự án; người chơi không đi qua đây (đường của
người chơi dùng `MeteredClient`, trần G8 trong `limits.cost_usd`)."""

import json
import math
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel

from writory.config import ModelPrice
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import ChatResult, LLMClient, Message, StreamEvent, trace_call
from writory.llm.cost import maybe_billed
from writory.quality.bench_d import EST_CHARS_PER_TOKEN, Budget, BudgetExceeded


class CappedClient(LLMClient):
    """Giữ chỗ chi phí tối đa của lời gọi trong ngân sách của cả lần xuất trước khi gọi, gửi kèm
    `max_tokens`, và ghi mỗi lời gọi một dòng (vai, model, token, chi phí). Không ghi chữ của lời gọi hay
    của câu trả lời (chữ truyện là truth).

    Trần là trần của giữ chỗ, như D-10: một lời gọi chỉ bắt đầu khi đã tiêu + đang giữ + ước tính tối đa
    của nó không vượt trần. Ước tính dùng `max_tokens` nên chi phí thật thường thấp hơn; nếu nhà cung cấp
    tính cao hơn ước tính thì tổng có thể vượt trần một lời gọi, và lời gọi kế bị từ chối. Lời gọi lỗi tính
    theo `llm.cost.maybe_billed` (D-64)."""

    def __init__(self, inner: LLMClient, *, budget: Budget, prices: Mapping[str, ModelPrice],
                 max_tokens: int, record: Callable[[dict[str, Any]], None], roles: Mapping[str, str]) -> None:
        """`roles`: tên schema của câu trả lời -> tên vai ghi vào nhật ký lời gọi."""
        self._inner, self._budget, self._prices = inner, budget, prices
        self._max_tokens, self._record, self._roles = max_tokens, record, roles
        self.halted: str | None = None
        self._seq = 0

    @property
    def spent_usd(self) -> float:
        return self._budget.spent_usd

    def estimate(self, model: str, messages: Sequence[Message],
                 schema: type[BaseModel] | None) -> float:
        price = self._prices[model]
        chars = sum(len(m.content) for m in messages)
        if schema is not None:
            chars += len(json.dumps(schema.model_json_schema(), ensure_ascii=False))
        return (math.ceil(chars / EST_CHARS_PER_TOKEN) * price.input
                + self._max_tokens * price.output) / 1e6

    async def chat(self, model: str, messages: list[Message], *,
                   response_schema: type[BaseModel] | None = None,
                   extra: Mapping[str, Any] | None = None) -> ChatResult:
        if model not in self._prices:
            raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET,
                               detail=f"models.yaml không có giá cho {model}")
        estimate = self.estimate(model, messages, response_schema)
        try:
            held = self._budget.reserve(estimate)
        except BudgetExceeded as e:
            self.halted = str(e)
            raise WritoryError(ErrorCode.COST_LIMIT_STORY, detail=f"trần --budget: {e}") from None
        body = dict(extra or {})
        body["max_tokens"] = min(body.get("max_tokens", self._max_tokens), self._max_tokens)
        self._seq += 1
        row = {"seq": self._seq,
               "role": self._roles.get(response_schema.__name__ if response_schema else "", "?"),
               "model": model, "reserved_usd": round(estimate, 6)}
        with trace_call() as trace:
            try:
                result = await self._inner.chat(model, messages, response_schema=response_schema,
                                                extra=body)
            except WritoryError as e:
                billed = estimate if maybe_billed(e, trace) else 0.0
                self._budget.settle(held, billed)
                self._record(row | {"status": e.code.value, "cost_usd": None,
                                    "cost_estimated_usd": billed or None})
                raise
            except BaseException:
                self._budget.settle(held, estimate)  # có thể đã bị tính tiền: tính theo mức tối đa
                self._record(row | {"status": "INTERRUPTED", "cost_usd": None,
                                    "cost_estimated_usd": estimate})
                raise
        cost = result.usage.cost_usd
        self._budget.settle(held, estimate if cost is None else cost)
        self._record(row | {
            "status": "ok", "served_model": result.model, "cost_usd": cost,
            "cost_estimated_usd": estimate if cost is None else None,
            "prompt_tokens": result.usage.prompt_tokens,
            "completion_tokens": result.usage.completion_tokens})
        return result

    def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError("công cụ admin không dùng stream")
