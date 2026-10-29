"""Hạn tổng mỗi lời gọi model (D-113): lời gọi treo thì ra LLM_TIMEOUT, không treo vô hạn.

Hồi quy long-tu-tien-3: MỘT lời gọi dàn ý ở ch18 treo 13121 giây rồi mới ConnectError, trong khi
mọi lời gọi khác ≤ 111 giây. `httpx.Timeout(120)` là hạn từng lần đọc/ghi, không phải hạn tổng.

Không chờ thời gian thật (CLAUDE.md §6): đồng hồ của vòng lặp asyncio được nhảy tới sau hạn, nên
`asyncio.timeout` thật chạy trên đồng hồ giả. Cầu chì của `run` chạy theo thời gian THẬT, trong
luồng riêng, chỉ để test hỏng thì đỏ thay vì treo cả bộ test.
"""

import asyncio
import threading
from contextlib import contextmanager
from types import SimpleNamespace

import httpx
import pytest
from pydantic import SecretStr

from writory.config import ModelPrice, load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone, TextDelta, trace_call
from writory.llm.cost import CostEstimator, maybe_billed
from writory.llm.ledger import CallCost, RecordingClient
from writory.llm.openrouter import OpenRouterClient, call_deadline
from writory.llm.retry import RETRY_TRANSIENT, with_json_retries, with_retries

FAKE_KEY = "sk-or-v1-" + "0123456789abcdef" * 4
MSGS = [Message(role="system", content="luật"), Message(role="user", content="viết")]
DEADLINE = 300
PAST_DEADLINE = 10_000


@contextmanager
def fake_clock():
    """Đồng hồ của vòng lặp nhảy được: `advance(s)` cộng s giây ở lần chạy kế tiếp của vòng lặp."""
    loop = asyncio.get_running_loop()
    real = loop.time
    offset = [0.0]
    loop.time = lambda: real() + offset[0]  # type: ignore[method-assign]

    def advance(seconds: float) -> None:
        loop.call_soon(lambda: offset.__setitem__(0, offset[0] + seconds))

    try:
        yield advance
    finally:
        del loop.time


async def run(awaitable, *, advance=None, seconds: float = 30.0):
    """Chạy một lời gọi như một task riêng. `advance`: sau khi lời gọi đã chạy tới chỗ chờ đầu tiên
    (hạn đã đăng ký) thì nhảy đồng hồ quá hạn."""
    loop = asyncio.get_running_loop()
    task = asyncio.ensure_future(awaitable)
    fuse = threading.Timer(seconds, lambda: loop.call_soon_threadsafe(task.cancel))
    fuse.start()
    try:
        if advance is not None:
            await asyncio.sleep(0)
            advance(PAST_DEADLINE)
        return await task
    finally:
        fuse.cancel()


async def never(request: httpx.Request) -> httpx.Response:
    await asyncio.Event().wait()
    raise AssertionError("không tới đây")


def client_with(handler, **kw) -> OpenRouterClient:
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return OpenRouterClient(SecretStr(FAKE_KEY), http=http, **kw)


def completion() -> dict:
    return {"id": "gen-1", "model": "x/y", "usage": {"prompt_tokens": 1, "completion_tokens": 1,
                                                       "cost": 0.001},
            "choices": [{"message": {"role": "assistant", "content": "Xin chào"},
                         "finish_reason": "stop"}]}


# --- chat -------------------------------------------------------------------------------------


async def test_a_chat_that_never_answers_ends_at_the_deadline():
    client = client_with(never, deadline_s=DEADLINE)
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(client.chat("x/y", MSGS), advance=advance)
    assert exc.value.code is ErrorCode.LLM_TIMEOUT
    assert str(DEADLINE) in exc.value.detail and "sk-or" not in exc.value.detail


async def test_a_chat_that_answers_in_time_is_untouched():
    client = client_with(lambda r: httpx.Response(200, json=completion()), deadline_s=DEADLINE)
    result = await run(client.chat("x/y", MSGS))
    assert result.text == "Xin chào"


async def test_the_deadline_covers_the_whole_call_even_if_bytes_keep_arriving():
    """Nguyên nhân khả dĩ: máy chủ nhỏ giọt byte giữ kết nối thì hạn từng lần đọc không bao giờ hết."""
    async def trickle():
        while True:
            yield b" "
            await asyncio.sleep(0)

    client = client_with(lambda r: httpx.Response(200, content=trickle()), deadline_s=DEADLINE)
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(client.chat("x/y", MSGS), advance=advance)
    assert exc.value.code is ErrorCode.LLM_TIMEOUT


async def test_no_deadline_means_the_old_behaviour():
    async def slow(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        return httpx.Response(200, json=completion())

    client = client_with(slow)  # deadline_s=None
    with fake_clock() as advance:
        result = await run(client.chat("x/y", MSGS), advance=advance)
    assert result.text == "Xin chào"


async def test_a_socket_level_timeout_is_still_a_network_error_not_the_deadline():
    """`TimeoutError` là lớp con của `OSError`: không được nhầm hạn tổng với lỗi socket."""
    def boom(request: httpx.Request) -> httpx.Response:
        raise TimeoutError("socket")

    client = client_with(boom, deadline_s=DEADLINE)
    with pytest.raises(WritoryError) as exc:
        await run(client.chat("x/y", MSGS))
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_the_deadline_error_says_nothing_about_the_request_body():
    client = client_with(never, deadline_s=DEADLINE)
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(client.chat("x/y", [Message(role="user", content="BÍ MẬT-CỦA-TRUYỆN")]),
                  advance=advance)
    assert "BÍ MẬT" not in exc.value.detail and "BÍ MẬT" not in str(exc.value)


# --- stream -----------------------------------------------------------------------------------


def stalled_stream(request: httpx.Request) -> httpx.Response:
    async def body():
        yield b'data: {"id":"gen-1","choices":[{"delta":{"content":"Xin"}}]}\n\n'
        await asyncio.Event().wait()

    return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body())


async def test_a_stream_that_stalls_after_some_text_ends_at_the_deadline():
    client = client_with(stalled_stream, deadline_s=DEADLINE)
    got: list = []

    async def consume(advance):
        async for event in client.stream("x/y", MSGS):
            got.append(event)
            advance(PAST_DEADLINE)  # đã nhận chữ đầu rồi mới tới hạn

    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(consume(advance))
    assert exc.value.code is ErrorCode.LLM_TIMEOUT
    assert got == [TextDelta("Xin")]


async def test_a_stream_that_never_starts_ends_at_the_deadline():
    client = client_with(never, deadline_s=DEADLINE)
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(anext(client.stream("x/y", MSGS)), advance=advance)
    assert exc.value.code is ErrorCode.LLM_TIMEOUT


async def test_a_stream_that_finishes_in_time_yields_everything():
    def ok(request: httpx.Request) -> httpx.Response:
        text = ('data: {"id":"gen-1","choices":[{"delta":{"content":"Xin"}}]}\n\n'
                'data: {"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1,"cost":0.1}}\n\n'
                "data: [DONE]\n\n")
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=text)

    client = client_with(ok, deadline_s=DEADLINE)
    events = [e async for e in client.stream("x/y", MSGS)]
    assert events[0] == TextDelta("Xin") and isinstance(events[-1], StreamDone)


# --- tra chi phí theo id ------------------------------------------------------------------------


async def test_the_cost_lookup_is_bounded_too():
    client = client_with(never, deadline_s=DEADLINE)
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(client.generation_cost("gen-1"), advance=advance)
    assert exc.value.code is ErrorCode.LLM_TIMEOUT


# --- mã lỗi, thử lại, chi phí ---------------------------------------------------------------------


def test_the_timeout_is_a_transient_error_the_retry_layer_handles():
    assert ErrorCode.LLM_TIMEOUT in RETRY_TRANSIENT


async def test_a_timeout_is_retried_then_succeeds():
    calls = []

    async def op():
        calls.append(1)
        if len(calls) == 1:
            raise WritoryError(ErrorCode.LLM_TIMEOUT, detail="quá 300 giây")
        return "ok"

    assert await with_json_retries(op, schema_retries=0, transient_retries=2) == "ok"
    assert len(calls) == 2


async def test_timeouts_every_time_stop_at_the_retry_limit():
    async def op():
        raise WritoryError(ErrorCode.LLM_TIMEOUT, detail="quá 300 giây")

    with pytest.raises(WritoryError) as exc:
        await with_retries(op, max_retries=2, retry_on=RETRY_TRANSIENT)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED


def test_a_call_that_timed_out_after_sending_may_have_been_billed_like_a_cancelled_one():
    err = WritoryError(ErrorCode.LLM_TIMEOUT, detail="quá 300 giây")
    with trace_call() as trace:
        trace.sent = True
        assert maybe_billed(err, trace)
    with trace_call() as trace:
        trace.sent = True
        trace.generation_id = "gen-1"
        assert maybe_billed(err, trace)
    with trace_call() as trace:
        trace.sent = False
        assert not maybe_billed(err, trace)


async def test_a_timed_out_call_is_logged_with_its_estimated_maximum_cost():
    """Như lời gọi bị huỷ (D-64): lời gọi không stream vẫn bị tính tiền đủ."""
    client = client_with(never, deadline_s=DEADLINE)
    rows: list[CallCost] = []
    estimator = CostEstimator({"x/y": ModelPrice(**{"in": 1.0, "out": 2.0})},
                              max_output_tokens=1000)
    recording = RecordingClient(client, rows.append, role_of=lambda s: "outline",
                                estimator=estimator)
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(recording.chat("x/y", MSGS), advance=advance)
    assert exc.value.code is ErrorCode.LLM_TIMEOUT
    [row] = rows
    assert row.estimated and row.cost_usd == pytest.approx(estimator.max_cost("x/y", MSGS, None))


# --- config và nối dây ------------------------------------------------------------------------


def test_the_deadline_is_a_number_in_limits_yaml():
    config = load_config()
    assert call_deadline(config) == config.limits.llm_call.require("deadline_seconds") > 0


def test_a_missing_deadline_is_a_config_error_not_infinity():
    config = load_config()
    llm_call = config.limits.llm_call.model_copy(update={"deadline_seconds": None})
    bare = config.model_copy(update={"limits": config.limits.model_copy(
        update={"llm_call": llm_call})})
    with pytest.raises(WritoryError) as exc:
        call_deadline(bare)
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET


async def test_the_apps_client_factory_carries_the_configured_deadline():
    from writory.api import deps

    http = httpx.AsyncClient(transport=httpx.MockTransport(never))
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        openrouter_http=http, config=load_config())))
    client = deps.get_llm_factory(request)(SecretStr(FAKE_KEY))
    with fake_clock() as advance, pytest.raises(WritoryError) as exc:
        await run(client.chat("x/y", MSGS), advance=advance)
    assert exc.value.code is ErrorCode.LLM_TIMEOUT
