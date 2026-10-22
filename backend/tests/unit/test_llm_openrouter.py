"""OpenRouter client qua httpx.MockTransport: không mạng.

Hình dạng phản hồi lấy theo docs openrouter.ai (api-reference/overview, errors, streaming,
use-cases/usage-accounting), tra ngày 19/10/2026; header `X-Generation-Id` và GET /generation
(api-reference/get-a-generation) tra ngày 21/10/2026 (D-64). Chưa đối chiếu với lời gọi thật.
"""

import asyncio
import json
import ssl

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import GenerationCost, Message, StreamDone, TextDelta, trace_call
from writory.llm.openrouter import OpenRouterClient
from writory.llm.retry import RETRY_TRANSIENT, with_retries

FAKE_KEY = "sk-or-v1-" + "0123456789abcdef" * 4
MSGS = [Message(role="system", content="luật"), Message(role="user", content="viết")]


def completion(text="Xin chào", cost=0.0012, **extra) -> dict:
    usage = {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    if cost is not None:
        usage["cost"] = cost
    return {
        "id": "gen-1",
        "model": "x/y",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                     "finish_reason": "stop"}],
        "usage": usage,
        **extra,
    }


def client_with(handler) -> tuple[OpenRouterClient, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(recording))
    return OpenRouterClient(SecretStr(FAKE_KEY), http=http), seen


async def test_chat_sends_request_and_reads_usage_cost():
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    result = await client.chat("x/y", MSGS)
    assert result.text == "Xin chào"
    assert result.usage.cost_usd == pytest.approx(0.0012)
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 5
    req = seen[0]
    assert req.method == "POST"
    assert req.url.path.endswith("/chat/completions")
    assert req.headers["authorization"] == f"Bearer {FAKE_KEY}"
    body = json.loads(req.content)
    assert body["model"] == "x/y"
    assert body["messages"] == [{"role": "system", "content": "luật"},
                                {"role": "user", "content": "viết"}]
    assert "response_format" not in body


async def test_chat_reads_served_model_and_finish_reason():
    client, _ = client_with(lambda r: httpx.Response(200, json=completion()))
    result = await client.chat("x/y", MSGS)
    assert result.model == "x/y"
    assert result.finish_reason == "stop"


async def test_chat_extra_params_go_into_body():
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    extra = {"max_tokens": 900, "reasoning": {"effort": "none"}}
    await client.chat("x/y", MSGS, extra=extra)
    body = json.loads(seen[0].content)
    assert body["max_tokens"] == 900
    assert body["reasoning"] == {"effort": "none"}
    assert body["model"] == "x/y"


@pytest.mark.parametrize("key", ["model", "messages", "stream", "response_format"])
async def test_chat_extra_cannot_override_core_fields(key):
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    with pytest.raises(ValueError, match=key):
        await client.chat("x/y", MSGS, extra={key: "khác"})
    assert seen == []


async def test_missing_cost_is_reported_as_unknown():
    client, _ = client_with(lambda r: httpx.Response(200, json=completion(cost=None)))
    assert (await client.chat("x/y", MSGS)).usage.cost_usd is None


async def test_chat_json_sends_json_schema_response_format():
    class Out(BaseModel):
        name: str

    client, seen = client_with(lambda r: httpx.Response(200, json=completion('{"name": "Lan"}')))
    value, _ = await client.chat_json("x/y", MSGS, Out)
    assert value == Out(name="Lan")
    fmt = json.loads(seen[0].content)["response_format"]
    assert fmt["type"] == "json_schema"
    assert fmt["json_schema"]["name"] == "Out"
    assert fmt["json_schema"]["schema"]["properties"]["name"]["type"] == "string"


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, ErrorCode.LLM_REQUEST_INVALID),
        (401, ErrorCode.LLM_AUTH_FAILED),
        (402, ErrorCode.LLM_INSUFFICIENT_CREDITS),
        (403, ErrorCode.LLM_CONTENT_BLOCKED),
        (408, ErrorCode.LLM_UNAVAILABLE),
        (409, ErrorCode.LLM_UNAVAILABLE),  # không có trong docs; hồi quy ky-ao-vua-ab-tat (D-94)
        (429, ErrorCode.LLM_RATE_LIMITED),
        (500, ErrorCode.LLM_UNAVAILABLE),
        (502, ErrorCode.LLM_UNAVAILABLE),
        (503, ErrorCode.LLM_UNAVAILABLE),
    ],
)
async def test_http_status_maps_to_error_code(status, code):
    body = {"error": {"code": status, "message": "boom"}}
    client, _ = client_with(lambda r: httpx.Response(status, json=body))
    with pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert exc.value.code is code
    assert str(status) in str(exc.value)


async def test_error_body_on_http_200_is_an_error():
    body = {"error": {"code": 402, "message": "Insufficient credits"}}
    client, _ = client_with(lambda r: httpx.Response(200, json=body))
    with pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert exc.value.code is ErrorCode.LLM_INSUFFICIENT_CREDITS


async def test_non_json_body_is_bad_response():
    client, _ = client_with(lambda r: httpx.Response(200, text="<html>oops</html>"))
    with pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert exc.value.code is ErrorCode.LLM_BAD_RESPONSE


async def test_network_error_is_unavailable():
    def boom(request):
        raise httpx.ConnectError("connection refused", request=request)

    client, _ = client_with(boom)
    with pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_key_never_appears_in_error_even_if_server_echoes_it():
    body = {"error": {"code": 401, "message": f"Invalid key {FAKE_KEY}"}}
    client, _ = client_with(lambda r: httpx.Response(401, json=body))
    with pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert FAKE_KEY not in str(exc.value)
    assert FAKE_KEY not in repr(exc.value)
    assert FAKE_KEY not in json.dumps(exc.value.player_payload())


def sse(*events: str) -> bytes:
    return "".join(f"{e}\n\n" for e in events).encode()


def chunk(content: str | None = None, usage: dict | None = None, **extra) -> str:
    data = {"id": "gen-1", "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": content or ""}}], **extra}
    if usage is not None:
        data["usage"] = usage
    return "data: " + json.dumps(data)


async def test_stream_yields_text_then_usage():
    payload = sse(
        ": OPENROUTER PROCESSING",
        chunk("Mưa "),
        chunk("rơi."),
        chunk("", usage={"prompt_tokens": 3, "completion_tokens": 2, "cost": 0.0005}),
        "data: [DONE]",
    )
    client, seen = client_with(lambda r: httpx.Response(200, content=payload))
    events = [e async for e in client.stream("x/y", MSGS)]
    assert [e.text for e in events if isinstance(e, TextDelta)] == ["Mưa ", "rơi."]
    assert isinstance(events[-1], StreamDone)
    assert events[-1].usage.cost_usd == pytest.approx(0.0005)
    assert json.loads(seen[0].content)["stream"] is True


async def test_stream_without_usage_reports_unknown_cost():
    payload = sse(chunk("a"), "data: [DONE]")
    client, _ = client_with(lambda r: httpx.Response(200, content=payload))
    events = [e async for e in client.stream("x/y", MSGS)]
    assert events[-1].usage.cost_usd is None


async def test_mid_stream_error_raises():
    err = chunk("", error={"code": "server_error", "message": "Provider disconnected"})
    payload = sse(chunk("a"), err)
    client, _ = client_with(lambda r: httpx.Response(200, content=payload))
    with pytest.raises(WritoryError) as exc:
        [e async for e in client.stream("x/y", MSGS)]
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_stream_http_error_before_start_maps_status():
    body = {"error": {"code": 401, "message": "No auth"}}
    client, _ = client_with(lambda r: httpx.Response(401, json=body))
    with pytest.raises(WritoryError) as exc:
        [e async for e in client.stream("x/y", MSGS)]
    assert exc.value.code is ErrorCode.LLM_AUTH_FAILED


# --- id generation và tra chi phí theo id (D-64) ----------------------------------------------

GEN_ID = "gen-1761000000-AbCdEf123"


async def test_chat_reads_generation_id_from_header_then_body():
    with_header = completion() | {"id": "gen-from-body"}
    client, _ = client_with(lambda r: httpx.Response(200, json=with_header,
                                                     headers={"X-Generation-Id": GEN_ID}))
    assert (await client.chat("x/y", MSGS)).generation_id == GEN_ID
    client, _ = client_with(lambda r: httpx.Response(200, json=completion() | {"id": GEN_ID}))
    assert (await client.chat("x/y", MSGS)).generation_id == GEN_ID


@pytest.mark.parametrize("bad", ["chatcmpl-1", "gen-" + "a" * 200, "gen-a/../b", ""])
async def test_malformed_generation_id_is_ignored(bad):
    client, _ = client_with(lambda r: httpx.Response(200, json=completion() | {"id": bad},
                                                     headers={"X-Generation-Id": bad}))
    with trace_call() as trace:
        result = await client.chat("x/y", MSGS)
    assert result.generation_id is None and trace.generation_id is None


class BrokenBody(httpx.AsyncByteStream):
    """Thân phản hồi đứt sau phần đầu (mạng rớt giữa chừng)."""

    async def __aiter__(self):
        yield b'{"id": "gen-'
        raise httpx.ReadError("connection reset")


class EndlessBody(httpx.AsyncByteStream):
    """Thân phản hồi không bao giờ tới: model đang sinh chữ (không stream)."""

    def __init__(self) -> None:
        self.started = asyncio.Event()

    async def __aiter__(self):
        self.started.set()
        await asyncio.Event().wait()
        yield b""  # pragma: no cover


async def test_body_broken_after_headers_keeps_generation_id_for_the_ledger():
    client, _ = client_with(lambda r: httpx.Response(200, headers={"X-Generation-Id": GEN_ID},
                                                     stream=BrokenBody()))
    with trace_call() as trace, pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE
    assert (trace.sent, trace.generation_id) == (True, GEN_ID)


async def test_cancelled_while_waiting_for_the_body_keeps_generation_id():
    """Header tới khi nhà cung cấp nhận yêu cầu (docs: errors), trước thân phản hồi; nên lời gọi bị
    huỷ lúc đang chờ thân vẫn biết id để tra lại chi phí."""
    body = EndlessBody()
    client, _ = client_with(lambda r: httpx.Response(200, headers={"X-Generation-Id": GEN_ID},
                                                     stream=body))

    async def call():
        with trace_call() as trace:
            try:
                await client.chat("x/y", MSGS)
            finally:
                seen.append(trace)

    seen = []
    task = asyncio.create_task(call())
    await asyncio.wait_for(body.started.wait(), timeout=30)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert (seen[0].sent, seen[0].generation_id) == (True, GEN_ID)


async def test_connect_error_means_not_sent():
    def boom(request):
        raise httpx.ConnectError("connection refused", request=request)

    client, _ = client_with(boom)
    with trace_call() as trace, pytest.raises(WritoryError):
        await client.chat("x/y", MSGS)
    assert trace.sent is False and trace.generation_id is None


async def test_stream_reports_generation_id():
    payload = sse(chunk("a", id=GEN_ID),
                  chunk("", usage={"prompt_tokens": 3, "completion_tokens": 2, "cost": 0.0005}),
                  "data: [DONE]")
    client, _ = client_with(lambda r: httpx.Response(200, content=payload))
    with trace_call() as trace:
        events = [e async for e in client.stream("x/y", MSGS)]
    assert events[-1].generation_id == GEN_ID == trace.generation_id


def generation(**data) -> dict:
    base = {"id": GEN_ID, "total_cost": 0.00421, "usage": 0.00421, "tokens_prompt": 1200,
            "tokens_completion": 800, "cancelled": True, "model": "x/y", "is_byok": False,
            "upstream_id": None, "created_at": "2026-10-21T00:00:00Z", "origin": "",
            "data_region": "global"}
    return {"data": base | data}


async def test_generation_cost_reads_total_cost_by_id():
    client, seen = client_with(lambda r: httpx.Response(200, json=generation()))
    cost = await client.generation_cost(GEN_ID)
    assert cost == GenerationCost(cost_usd=0.00421, prompt_tokens=1200, completion_tokens=800)
    req = seen[0]
    assert req.method == "GET" and req.url.path.endswith("/api/v1/generation")
    assert req.url.params["id"] == GEN_ID
    assert req.headers["authorization"] == f"Bearer {FAKE_KEY}"


async def test_generation_not_ready_or_unknown_is_none():
    body = {"error": {"code": 404, "message": "Generation not found"}}
    client, _ = client_with(lambda r: httpx.Response(404, json=body))
    assert await client.generation_cost(GEN_ID) is None


@pytest.mark.parametrize("data", [{"total_cost": None}, {"total_cost": "0.1"},
                                  {"total_cost": -1.0}])
async def test_generation_without_a_usable_cost_is_bad_response(data):
    client, _ = client_with(lambda r: httpx.Response(200, json=generation(**data)))
    with pytest.raises(WritoryError) as exc:
        await client.generation_cost(GEN_ID)
    assert exc.value.code is ErrorCode.LLM_BAD_RESPONSE


async def test_generation_lookup_errors_never_carry_the_key():
    body = {"error": {"code": 401, "message": f"Invalid key {FAKE_KEY}"}}
    client, _ = client_with(lambda r: httpx.Response(401, json=body))
    with pytest.raises(WritoryError) as exc:
        await client.generation_cost(GEN_ID)
    assert exc.value.code is ErrorCode.LLM_AUTH_FAILED
    assert FAKE_KEY not in str(exc.value) and FAKE_KEY not in repr(exc.value)


async def test_generation_lookup_rejects_malformed_id_without_a_request():
    client, seen = client_with(lambda r: httpx.Response(200, json=generation()))
    with pytest.raises(ValueError):
        await client.generation_cost("gen-a&id=gen-b")
    assert seen == []


# --- HTTP 409 (D-94) --------------------------------------------------------------------------------
# Lần chạy ky-ao-vua-ab-tat dừng ở chương 8: OpenRouter trả 409, thân `{"error": {"code": 409,
# "message": ""}}`, sau 0,08 giây. Trang lỗi của OpenRouter không có 409; xử như lỗi tạm.


def _conflict(_request: httpx.Request) -> httpx.Response:
    return httpx.Response(409, json={"error": {"code": 409, "message": ""}})


async def test_one_409_is_retried_and_the_second_answer_is_used():
    answers = iter([_conflict(None), httpx.Response(200, json=completion("Qua rồi"))])
    client, seen = client_with(lambda r: next(answers))
    result = await with_retries(lambda: client.chat("x/y", MSGS), max_retries=1,
                                retry_on=RETRY_TRANSIENT)
    assert result.text == "Qua rồi" and len(seen) == 2


async def test_409_that_never_clears_stops_at_the_retry_limit():
    client, seen = client_with(_conflict)
    with pytest.raises(WritoryError) as exc:
        await with_retries(lambda: client.chat("x/y", MSGS), max_retries=2,
                           retry_on=RETRY_TRANSIENT)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(seen) == 3  # 1 lần đầu + 2 lần thử lại, không hơn (G8)
    assert "409" in str(exc.value)


async def test_409_in_a_stream_before_it_starts_maps_the_same_way():
    client, _ = client_with(_conflict)
    with pytest.raises(WritoryError) as exc:
        async for _ in client.stream("x/y", MSGS):
            pass
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


# --- lỗi TLS và socket httpx không bọc (D-97) -------------------------------------------------------
# Lần chạy long-tu-tien-1 chết ở chương 16: `ssl.SSLError` (SSLV3_ALERT_BAD_RECORD_MAC) đi qua anyio,
# httpx không bọc thành `httpx.HTTPError`, nên rơi xuống INTERNAL_ERROR và không được thử lại.

_LOW_LEVEL_ERRORS = [
    ssl.SSLError(1, "[SSL: SSLV3_ALERT_BAD_RECORD_MAC] sslv3 alert bad record mac"),
    ConnectionResetError(10054, "connection reset by peer"),
    BrokenPipeError(32, "broken pipe"),
    TimeoutError("timed out"),
]


def _raises(error: BaseException):
    def boom(_request):
        raise error

    return boom


@pytest.mark.parametrize("error", _LOW_LEVEL_ERRORS, ids=lambda e: type(e).__name__)
async def test_low_level_network_error_is_unavailable_and_carries_only_its_type(error):
    client, _ = client_with(_raises(error))
    with pytest.raises(WritoryError) as exc:
        await client.chat("x/y", MSGS)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE
    assert type(error).__name__ in str(exc.value) and "bad record mac" not in str(exc.value)


async def test_one_tls_error_is_retried_and_the_second_answer_is_used():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise _LOW_LEVEL_ERRORS[0]
        return httpx.Response(200, json=completion("Qua rồi"))

    client, _ = client_with(handler)
    result = await with_retries(lambda: client.chat("x/y", MSGS), max_retries=1,
                                retry_on=RETRY_TRANSIENT)
    assert result.text == "Qua rồi" and len(calls) == 2


async def test_tls_error_that_never_clears_stops_at_the_retry_limit():
    client, seen = client_with(_raises(_LOW_LEVEL_ERRORS[0]))
    with pytest.raises(WritoryError) as exc:
        await with_retries(lambda: client.chat("x/y", MSGS), max_retries=2,
                           retry_on=RETRY_TRANSIENT)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED and len(seen) == 3  # G8


async def test_tls_error_before_a_stream_starts_is_unavailable():
    client, _ = client_with(_raises(_LOW_LEVEL_ERRORS[0]))
    with pytest.raises(WritoryError) as exc:
        [e async for e in client.stream("x/y", MSGS)]
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_tls_error_after_part_of_a_stream_is_unavailable_too():
    """Đã nhận một phần: luật hiện có cho lỗi httpx cũng là LLM_UNAVAILABLE (người gọi quyết có dùng
    phần đã nhận không); lỗi TLS theo đúng luật đó."""

    class Broken(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield sse(chunk("Xin "))
            raise _LOW_LEVEL_ERRORS[0]

    client, _ = client_with(lambda r: httpx.Response(200, stream=Broken()))
    got = []
    with pytest.raises(WritoryError) as exc:
        async for event in client.stream("x/y", MSGS):
            got.append(event)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE
    assert got and isinstance(got[0], TextDelta) and got[0].text == "Xin "


async def test_tls_error_in_generation_lookup_is_unavailable():
    client, _ = client_with(_raises(_LOW_LEVEL_ERRORS[0]))
    with pytest.raises(WritoryError) as exc:
        await client.generation_cost("gen-1761000000-AbCdEf123")
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_programming_errors_are_not_swallowed_as_network_errors():
    """Chỉ lỗi mạng (OSError) được coi là tạm; lỗi lập trình vẫn nổi lên."""
    client, _ = client_with(_raises(ValueError("lỗi lập trình")))
    with pytest.raises(ValueError):
        await client.chat("x/y", MSGS)
