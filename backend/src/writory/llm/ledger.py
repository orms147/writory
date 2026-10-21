"""Ghi chi phí của mọi lời gọi model vào nhật ký (G8, D-44, D-64).

`RecordingClient` bọc client thật, nằm DƯỚI `MeteredClient`: mỗi phản hồi về tới là ghi một dòng
(vai, model, token, chi phí), trước khi `CostTracker` kiểm và có thể dừng.

Lời gọi không có `usage` (D-64): bị huỷ (người chơi ngắt kết nối SSE), đứt giữa chừng, hay phản
hồi thiếu `usage.cost`. Có `estimator` thì dòng đó mang chi phí tối đa của lời gọi, đánh dấu
`estimated`, kèm id generation nếu client thật đã biết (`CallTrace`); trần mỗi truyện cộng cả
số ước tính, nên không còn hụt. Lời gọi lỗi chỉ được ghi khi có thể đã bị tính tiền
(`llm.cost.maybe_billed`). Mọi lời gọi gửi kèm `max_tokens` của `estimator`, để số tối đa là thật
ở phần ra. `settle_estimates` tra lại theo id và thay số ước tính bằng số thật; `RecordingClient`
chạy nó một lần, trước lời gọi đầu.

Vai không truyền qua lời gọi; nơi dựng client đưa vào `role_of` (đoán vai theo schema JSON, không
schema là model viết).
"""

import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from writory.errors import WritoryError
from writory.llm.base import (
    CallTrace,
    ChatResult,
    GenerationCost,
    LLMClient,
    Message,
    StreamDone,
    StreamEvent,
    Usage,
    trace_call,
)
from writory.llm.cost import CostEstimator, maybe_billed

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class CallCost:
    """Một dòng nhật ký chi phí. `estimated`: `cost_usd` là chi phí tối đa, chưa phải số thật."""

    role: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float | None
    estimated: bool = False
    generation_id: str | None = None


CostSink = Callable[[CallCost], None]
RoleOf = Callable[[type[BaseModel] | None], str]
Settle = Callable[[], Awaitable[object]]


class RecordingClient(LLMClient):
    def __init__(self, inner: LLMClient, sink: CostSink, *, role_of: RoleOf,
                 estimator: CostEstimator | None = None, settle: Settle | None = None) -> None:
        self._inner = inner
        self._sink = sink
        self._role_of = role_of
        self._estimator = estimator
        self._settle = settle

    async def _settle_once(self) -> None:
        settle, self._settle = self._settle, None
        if settle is None:
            return
        try:
            await settle()
        except Exception as e:  # noqa: BLE001 — tra lại chỉ làm số chính xác hơn; không chặn lời gọi
            log.warning("tra lại chi phí ước tính lỗi (%s); giữ số ước tính", type(e).__name__)

    def _record_failure(self, role: str, model: str, ceiling: float | None, trace: CallTrace,
                        exc: BaseException) -> None:
        if ceiling is None or not maybe_billed(exc, trace):
            return
        try:
            self._sink(CallCost(role, model, 0, 0, ceiling, estimated=True,
                                generation_id=trace.generation_id))
        except Exception as e:  # noqa: BLE001 — giữ lỗi gốc của lời gọi
            log.error("không ghi được chi phí ước tính của lời gọi %s lỗi (%s)", role,
                      type(e).__name__)

    def _record(self, role: str, model: str, usage: Usage, ceiling: float | None,
                generation_id: str | None) -> None:
        estimated = usage.cost_usd is None and ceiling is not None
        self._sink(CallCost(role, model, usage.prompt_tokens, usage.completion_tokens,
                            ceiling if estimated else usage.cost_usd, estimated=estimated,
                            generation_id=generation_id))

    async def chat(
        self,
        model: str,
        messages: list[Message],
        *,
        response_schema: type[BaseModel] | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> ChatResult:
        await self._settle_once()
        role = self._role_of(response_schema)
        ceiling: float | None = None
        if self._estimator is not None:
            ceiling = self._estimator.max_cost(model, messages, response_schema)  # trước khi gửi
            extra = self._estimator.bound(extra)
        with trace_call() as trace:
            try:
                result = await self._inner.chat(
                    model, messages, response_schema=response_schema, extra=extra
                )
            except BaseException as e:
                self._record_failure(role, model, ceiling, trace, e)
                raise
        self._record(role, model, result.usage, ceiling,
                     result.generation_id or trace.generation_id)
        return result

    async def stream(self, model: str, messages: list[Message]) -> AsyncIterator[StreamEvent]:
        """Không có `extra` nên không gửi được `max_tokens`: số ước tính của stream không phải
        chặn trên. Chưa đường nào của app dùng stream (D-64)."""
        await self._settle_once()
        role = self._role_of(None)
        ceiling = (self._estimator.max_cost(model, messages, None)
                   if self._estimator is not None else None)
        try:
            async for event in self._inner.stream(model, messages):
                if isinstance(event, StreamDone):
                    self._record(role, model, event.usage, ceiling, event.generation_id)
                yield event
        except BaseException as e:
            self._record_failure(role, model, ceiling, CallTrace(), e)
            raise


# --- tra lại theo id generation ------------------------------------------------------------------


@dataclass(frozen=True)
class PendingEstimate:
    row_id: int
    generation_id: str


class EstimateBook(Protocol):
    """Các dòng ước tính có id generation của một phạm vi (truyện hoặc phiên khởi tạo)."""

    def pending(self, limit: int) -> list[PendingEstimate]: ...
    def settle(self, row_id: int, cost: GenerationCost) -> None: ...


Lookup = Callable[[str], Awaitable[GenerationCost | None]]


async def settle_estimates(book: EstimateBook, lookup: Lookup, *, limit: int) -> int:
    """Thay số ước tính bằng chi phí thật tra theo id generation, tối đa `limit` dòng (D-64).
    Chưa có (None, ví dụ 404 khi generation chưa xong) thì giữ ước tính, lần sau tra tiếp. Lỗi
    tra (key, mạng) thì dừng: các dòng sau cũng sẽ lỗi. Trả số dòng đã thay."""
    settled = 0
    for row in book.pending(limit):
        try:
            cost = await lookup(row.generation_id)
        except WritoryError as e:
            log.warning("tra chi phí theo id generation lỗi (%s); giữ số ước tính", e.code.value)
            break
        if cost is not None:
            book.settle(row.row_id, cost)
            settled += 1
    return settled
