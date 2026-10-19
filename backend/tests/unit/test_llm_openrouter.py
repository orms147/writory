"""OpenRouter client qua httpx.MockTransport: không mạng.

Hình dạng phản hồi lấy theo docs openrouter.ai (api-reference/overview, errors, streaming,
use-cases/usage-accounting), tra ngày 19/10/2026. Chưa đối chiếu với lời gọi thật.
"""

import json

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone, TextDelta
from writory.llm.openrouter import OpenRouterClient

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
