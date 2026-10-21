"""Ghi chi phí mọi lời gọi model theo vai (G8, D-44): `RecordingClient` và bảng vai theo schema.
Lời gọi không có usage (bị huỷ, đứt, thiếu usage.cost) ghi chi phí tối đa, đánh dấu ước tính, rồi
tra lại theo id generation (D-64)."""

import asyncio

import pytest

from writory.api.deps import ROLE_OF_SCHEMA, role_of_schema
from writory.config import CostLimits, ModelPrice
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import (
    ChatResult,
    GenerationCost,
    LLMClient,
    Message,
    StreamDone,
    Usage,
    current_trace,
)
from writory.llm.cost import CostEstimator, CostTracker, MeteredClient
from writory.llm.fake import FakeLLM
from writory.llm.ledger import CallCost, PendingEstimate, RecordingClient, settle_estimates
from writory.pipeline.choices import ChoicesOutput
from writory.pipeline.extract import ExtractOutput
from writory.pipeline.narrator import NarratorOutput
from writory.pipeline.scene import SceneOutline
from writory.pipeline.setup import BuildOutput, CharactersOutput, PlotsOutput, SettingsOutput
from writory.safety.classify import Classification
from writory.safety.moderate import ChoicesModerationOutput, ModerationOutput

MSG = [Message(role="user", content="xin chào")]
CAP = CostLimits(per_scene=1.0, per_chapter=1.0, per_story=1.0)


def recorder():
    rows: list[tuple[str, str, CallCost]] = []
    return rows, lambda cost: rows.append((cost.role, cost.model, cost))


async def test_records_role_model_and_usage_of_each_call():
    rows, sink = recorder()
    narrator_json = '{"known": false, "answer": null, "entry_ids": []}'
    llm = RecordingClient(FakeLLM.scripted(["a", narrator_json], cost_usd=0.002),
                          sink, role_of=role_of_schema)
    await llm.chat("m/writer", MSG)
    await llm.chat_json("m/narrator", MSG, NarratorOutput)
    assert [(r, m, u.cost_usd) for r, m, u in rows] == [
        ("writer", "m/writer", 0.002), ("narrator", "m/narrator", 0.002)]


async def test_call_without_cost_is_still_recorded_then_metering_stops():
    """Phản hồi thiếu usage.cost: vẫn có dòng nhật ký (cost NULL), rồi MeteredClient dừng (D-10)."""
    rows, sink = recorder()
    llm = MeteredClient(RecordingClient(FakeLLM.scripted(["a"], cost_usd=None), sink,
                                        role_of=role_of_schema), CostTracker(CAP))
    with pytest.raises(WritoryError) as exc:
        await llm.chat("m", MSG)
    assert exc.value.code is ErrorCode.LLM_COST_UNKNOWN
    assert [(r, u.cost_usd) for r, _, u in rows] == [("writer", None)]


async def test_failed_call_records_nothing():
    rows, sink = recorder()
    llm = RecordingClient(FakeLLM.scripted([WritoryError(ErrorCode.LLM_UNAVAILABLE)]), sink,
                          role_of=role_of_schema)
    with pytest.raises(WritoryError):
        await llm.chat("m", MSG)
    assert rows == []


async def test_stream_records_once_at_the_end():
    rows, sink = recorder()
    llm = RecordingClient(FakeLLM.scripted(["x" * 40], cost_usd=0.01), sink,
                          role_of=role_of_schema)
    events = [e async for e in llm.stream("m", MSG)]
    assert isinstance(events[-1], StreamDone)
    assert [(r, u.cost_usd) for r, _, u in rows] == [("writer", 0.01)]


@pytest.mark.parametrize(("schema", "role"), [
    (None, "writer"),
    (SceneOutline, "outline"),
    (ExtractOutput, "extract"),
    (ChoicesOutput, "choices"),
    (NarratorOutput, "narrator"),
    (Classification, "classify"),
    (SettingsOutput, "setup"),
    (PlotsOutput, "setup"),
    (CharactersOutput, "setup"),
    (BuildOutput, "setup"),
    (ModerationOutput, "moderate"),  # G9, D-57
    (ChoicesModerationOutput, "moderate"),  # bộ lựa chọn theo dòng, D-79
])
def test_role_of_schema(schema, role):
    assert role_of_schema(schema) == role


def test_every_mapped_role_is_a_config_role():
    from writory.config import RoleModels

    assert set(ROLE_OF_SCHEMA.values()) <= set(RoleModels.model_fields)


# --- lời gọi không có usage: chi phí tối đa, đánh dấu ước tính (D-64) -----------------------

GEN = "gen-1761000000-AbC"
CAP_TOKENS = 1000
ESTIMATOR = CostEstimator({"m": ModelPrice(input=0.10, output=0.50)},
                          max_output_tokens=CAP_TOKENS)
CEILING = ESTIMATOR.max_cost("m", MSG, None)


class ReportingLLM(LLMClient):
    """Model giả báo `CallTrace` như client OpenRouter (đã gửi, id generation), rồi làm `then`:
    "hang" (chờ tới khi bị huỷ), một lỗi để ném, hay một ChatResult để trả."""

    def __init__(self, then, *, sent=True, generation_id=GEN) -> None:
        self.then, self.sent, self.generation_id = then, sent, generation_id
        self.entered = asyncio.Event()

    async def chat(self, model, messages, *, response_schema=None, extra=None):
        trace = current_trace()
        trace.sent = self.sent
        if self.generation_id is not None:
            trace.generation_id = self.generation_id
        self.entered.set()
        if self.then == "hang":
            await asyncio.Event().wait()
        if isinstance(self.then, BaseException):
            raise self.then
        return self.then

    async def stream(self, model, messages):  # pragma: no cover
        raise NotImplementedError
        yield


def estimating(inner, sink, **kw) -> RecordingClient:
    return RecordingClient(inner, sink, role_of=role_of_schema, estimator=ESTIMATOR, **kw)


async def test_every_call_is_sent_with_the_output_cap():
    rows, sink = recorder()
    inner = FakeLLM.scripted(["a", "b"], cost_usd=0.001)
    llm = estimating(inner, sink)
    await llm.chat("m", MSG)
    await llm.chat("m", MSG, extra={"max_tokens": 50, "reasoning": {"effort": "low"}})
    assert inner.extras == [{"max_tokens": CAP_TOKENS},
                            {"max_tokens": 50, "reasoning": {"effort": "low"}}]
    assert [(c.cost_usd, c.estimated) for _, _, c in rows] == [(0.001, False)] * 2


async def test_model_without_price_is_refused_before_the_call():
    rows, sink = recorder()
    inner = FakeLLM.scripted(["a"])
    with pytest.raises(WritoryError) as exc:
        await estimating(inner, sink).chat("m/khong-gia", MSG)
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert inner.calls == [] and rows == []


async def test_result_with_cost_keeps_the_generation_id():
    rows, sink = recorder()
    result = ChatResult(text="a", usage=Usage(prompt_tokens=3, completion_tokens=4,
                                              cost_usd=0.002), generation_id=GEN)
    await estimating(ReportingLLM(result), sink).chat("m", MSG)
    [(_, _, cost)] = rows
    assert cost == CallCost("writer", "m", 3, 4, 0.002, estimated=False, generation_id=GEN)


async def test_result_without_cost_records_the_ceiling_as_an_estimate():
    """Trước D-64 dòng này mang cost NULL, không cộng vào trần mỗi truyện. MeteredClient vẫn dừng
    ở lời gọi đó như D-10."""
    rows, sink = recorder()
    result = ChatResult(text="a", usage=Usage(prompt_tokens=3, completion_tokens=4,
                                              cost_usd=None), generation_id=GEN)
    llm = MeteredClient(estimating(ReportingLLM(result), sink), CostTracker(CAP))
    with pytest.raises(WritoryError) as exc:
        await llm.chat("m", MSG)
    assert exc.value.code is ErrorCode.LLM_COST_UNKNOWN
    [(_, _, cost)] = rows
    assert cost == CallCost("writer", "m", 3, 4, CEILING, estimated=True, generation_id=GEN)


async def test_cancelled_call_records_the_ceiling_with_its_generation_id():
    rows, sink = recorder()
    inner = ReportingLLM("hang")
    task = asyncio.create_task(estimating(inner, sink).chat("m", MSG))
    await asyncio.wait_for(inner.entered.wait(), timeout=30)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    [(_, _, cost)] = rows
    assert cost == CallCost("writer", "m", 0, 0, CEILING, estimated=True, generation_id=GEN)


async def test_cancelled_call_of_a_client_that_reports_nothing_is_still_estimated():
    """Model giả, client khác: không báo đã gửi hay chưa, coi như có thể đã gửi (fail closed)."""
    rows, sink = recorder()

    class Silent(FakeLLM):
        async def chat(self, model, messages, *, response_schema=None, extra=None):
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await estimating(Silent([]), sink).chat("m", MSG)
    assert [(c.cost_usd, c.estimated, c.generation_id) for _, _, c in rows] == [
        (CEILING, True, None)]


@pytest.mark.parametrize(("exc", "sent", "gen", "recorded"), [
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="ReadError"), True, None, True),
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 200, error.code=server_error: x"),
     True, GEN, True),
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="ConnectError"), False, None, False),
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 503, error.code=503: x"), True, None,
     False),
    (WritoryError(ErrorCode.WRITORY_RATE_LIMITED), None, None, False),
])
async def test_failed_call_is_estimated_only_if_it_may_have_been_billed(exc, sent, gen,
                                                                        recorded):
    rows, sink = recorder()
    with pytest.raises(WritoryError):
        await estimating(ReportingLLM(exc, sent=sent, generation_id=gen), sink).chat("m", MSG)
    assert [(c.cost_usd, c.estimated, c.generation_id) for _, _, c in rows] == (
        [(CEILING, True, gen)] if recorded else [])


async def test_ledger_failure_on_the_error_path_keeps_the_original_error(caplog):
    def broken_sink(cost):
        raise RuntimeError("Postgres mất kết nối")

    with pytest.raises(WritoryError) as exc:
        await estimating(ReportingLLM(WritoryError(ErrorCode.LLM_UNAVAILABLE, "ReadError")),
                         broken_sink).chat("m", MSG)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE
    assert "ước tính" in caplog.text


# --- tra lại theo id generation (D-64) --------------------------------------------------------


class MemoryBook:
    def __init__(self, pending: list[PendingEstimate]) -> None:
        self.rows = list(pending)
        self.settled: dict[int, GenerationCost] = {}
        self.asked: list[int] = []

    def pending(self, limit: int) -> list[PendingEstimate]:
        self.asked.append(limit)
        return [r for r in self.rows if r.row_id not in self.settled][:limit]

    def settle(self, row_id: int, cost: GenerationCost) -> None:
        self.settled[row_id] = cost


async def test_settle_replaces_estimates_that_have_a_generation_and_keeps_the_rest():
    book = MemoryBook([PendingEstimate(1, "gen-a"), PendingEstimate(2, "gen-b"),
                       PendingEstimate(3, "gen-c")])
    actual = GenerationCost(cost_usd=0.0012, prompt_tokens=900, completion_tokens=400)
    answers = {"gen-a": actual, "gen-b": None, "gen-c": actual}  # gen-b chưa có (404)

    async def lookup(gen_id):
        return answers[gen_id]

    assert await settle_estimates(book, lookup, limit=5) == 2
    assert book.settled == {1: actual, 3: actual} and book.asked == [5]


async def test_settle_stops_at_a_lookup_error_and_keeps_estimates():
    book = MemoryBook([PendingEstimate(1, "gen-a"), PendingEstimate(2, "gen-b")])
    seen = []

    async def lookup(gen_id):
        seen.append(gen_id)
        raise WritoryError(ErrorCode.LLM_AUTH_FAILED, detail="HTTP 401")

    assert await settle_estimates(book, lookup, limit=5) == 0
    assert book.settled == {} and seen == ["gen-a"]


async def test_recording_client_settles_once_before_its_first_call_and_never_blocks_it():
    rows, sink = recorder()
    runs = []

    async def settle():
        runs.append(1)
        raise RuntimeError("tra lại lỗi")  # không được chặn lời gọi

    llm = estimating(FakeLLM.scripted(["a", "b"], cost_usd=0.001), sink, settle=settle)
    await llm.chat("m", MSG)
    await llm.chat("m", MSG)
    assert runs == [1] and len(rows) == 2
