"""AnthropicClient (llm/anthropic_client.py, D-145): client của bộ đo cho Claude qua SDK `anthropic`, HTTP thay bằng
transport giả, không mạng. Hình dạng yêu cầu theo skill claude-api (Messages API: `output_config.format`,
`output_config.effort`, `thinking`, `usage`), tra 30/10/2026; chưa đối chiếu với lời gọi thật."""

import json

import anthropic
import httpx
import httpx2
import pytest
from pydantic import BaseModel, SecretStr

from writory.config import ModelPrice
from writory.errors import ErrorCode, WritoryError
from writory.llm.anthropic_client import AnthropicClient
from writory.llm.base import Message, StreamDone, TextDelta, trace_call
from writory.llm.meta import strict_schema

# Dạng không khớp mẫu key nào của bộ che chung (WritoryError tự che `sk-...`), để thấy phép bỏ key của chính client.
KEY = "plain-secret-" + "0123456789abcdef" * 3
MODEL = "anthropic-api/claude-haiku-5-5"
PRICE = {
    "in": 0.10, "out": 0.50, "cached_in": 0.01, "cache_write_in": 0.125,
    "long_prompt": {"over_tokens": 100_000, "in": 0.50, "out": 2.50, "cached_in": 0.05, "cache_write_in": 0.625},
}
PRICES = {MODEL: ModelPrice.model_validate(PRICE)}
MSGS = [Message(role="system", content="luật"), Message(role="user", content="viết")]


def reply(text="Xin chào", *, stop="end_turn", usage=None, content=None) -> dict:
    return {
        "id": "msg_x", "type": "message", "role": "assistant", "model": "claude-haiku-5-5",
        "content": content if content is not None else [{"type": "text", "text": text}],
        "stop_reason": stop, "stop_sequence": None, "stop_details": None,
        "usage": usage or {"input_tokens": 10, "output_tokens": 5, "cache_creation_input_tokens": 0,
                           "cache_read_input_tokens": 0},
    }


def client_with(handler, prices=PRICES, **kw):
    seen: list = []

    def transport(request):
        seen.append(request)
        out = handler(request)
        status, payload = out if isinstance(out, tuple) else (200, out)
        if isinstance(payload, bytes):
            return httpx2.Response(status, content=payload, headers={"content-type": "text/event-stream"})
        return httpx2.Response(status, json=payload)

    sdk = anthropic.AsyncAnthropic(api_key=KEY, max_retries=0, base_url="https://api.anthropic.com",
                                   http_client=anthropic.DefaultAsyncHttpxClient(transport=httpx2.MockTransport(transport)))
    return AnthropicClient(SecretStr(KEY), prices, sdk=sdk, **kw), seen


def body(seen) -> dict:
    return json.loads(seen[-1].content)


async def test_the_request_goes_to_the_messages_api_with_the_key_in_the_header_only():
    client, seen = client_with(lambda r: reply())
    result = await client.chat(MODEL, MSGS, extra={"max_tokens": 777})
    req = seen[0]
    assert str(req.url) == "https://api.anthropic.com/v1/messages" and req.method == "POST"
    assert req.headers["x-api-key"] == KEY and "authorization" not in req.headers
    assert KEY not in req.content.decode() and KEY not in str(req.url)
    b = body(seen)
    assert b["model"] == "claude-haiku-5-5" and b["max_tokens"] == 777 and b["system"] == "luật"
    assert b["messages"] == [{"role": "user", "content": "viết"}]
    for absent in ("temperature", "top_p", "top_k", "thinking", "output_config", "provider", "stream"):
        assert absent not in b, absent
    assert result.text == "Xin chào" and result.finish_reason == "stop" and result.model == "claude-haiku-5-5"


async def test_without_a_max_tokens_the_configured_default_is_sent_because_the_api_requires_one():
    client, seen = client_with(lambda r: reply(), default_max_tokens=4321)
    await client.chat(MODEL, MSGS)
    assert body(seen)["max_tokens"] == 4321


async def test_every_system_message_goes_to_the_system_field_and_a_final_assistant_turn_is_refused():
    msgs = [Message(role="system", content="a"), Message(role="user", content="u"),
            Message(role="system", content="b")]
    client, seen = client_with(lambda r: reply())
    await client.chat(MODEL, msgs)
    assert body(seen)["system"] == "a\n\nb" and [m["role"] for m in body(seen)["messages"]] == ["user"]
    with pytest.raises(ValueError, match="prefill"):
        await client.chat(MODEL, [Message(role="user", content="u"), Message(role="assistant", content="a")])
    assert len(seen) == 1


@pytest.mark.parametrize("effort, expected", [("minimal", "low"), ("low", "low"), ("medium", "medium"),
                                              ("high", "high")])
async def test_the_role_reasoning_is_mapped_to_output_config_effort(effort, expected):
    client, seen = client_with(lambda r: reply())
    await client.chat(MODEL, MSGS, extra={"reasoning": {"effort": effort}})
    assert body(seen)["output_config"] == {"effort": expected} and "thinking" not in body(seen)


async def test_none_turns_thinking_off_and_no_setting_leaves_the_model_default():
    client, seen = client_with(lambda r: reply())
    await client.chat(MODEL, MSGS, extra={"reasoning": {"effort": "none"}})
    assert body(seen)["thinking"] == {"type": "disabled"} and "output_config" not in body(seen)
    await client.chat(MODEL, MSGS, extra={"provider": {"require_parameters": True}})
    assert "thinking" not in body(seen) and "output_config" not in body(seen) and "provider" not in body(seen)


async def test_sampling_parameters_and_unknown_extras_are_refused_instead_of_sent():
    client, seen = client_with(lambda r: reply())
    for bad in ("temperature", "top_p", "top_k"):
        with pytest.raises(ValueError, match=f"{bad}.*từ chối"):
            await client.chat(MODEL, MSGS, extra={bad: 1})
    with pytest.raises(ValueError, match="mirostat"):
        await client.chat(MODEL, MSGS, extra={"mirostat": 1})
    with pytest.raises(ValueError, match="model"):
        await client.chat(MODEL, MSGS, extra={"model": "x"})
    assert seen == []


async def test_a_model_without_the_prefix_or_without_a_price_is_refused_before_anything_is_sent():
    client, seen = client_with(lambda r: reply())
    with pytest.raises(WritoryError) as wrong:
        await client.chat("openai/gpt-6-luna", MSGS)
    assert wrong.value.code is ErrorCode.CONFIG_MODEL_NOT_SET
    with pytest.raises(WritoryError) as unpriced:
        await client.chat("anthropic-api/claude-other", MSGS)
    assert unpriced.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET and "claude-other" in unpriced.value.detail
    assert seen == []


# --- chi phí từ token -------------------------------------------------------------------------------


def usage(**kw):
    return {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, **kw}


async def test_the_cost_prices_fresh_cached_and_cache_written_tokens_apart():
    client, _ = client_with(lambda r: reply(usage=usage(input_tokens=600, cache_read_input_tokens=400,
                                                        cache_creation_input_tokens=200, output_tokens=500)))
    result = await client.chat(MODEL, MSGS)
    assert result.usage.cost_usd == pytest.approx((600 * 0.10 + 400 * 0.01 + 200 * 0.125 + 500 * 0.50) / 1e6)
    assert (result.usage.prompt_tokens, result.usage.completion_tokens, result.usage.cached_tokens) == (1200, 500, 400)
    assert result.usage.reasoning_tokens is None   # Anthropic không tách token suy luận khỏi output_tokens


async def test_a_prompt_over_the_threshold_is_priced_on_the_long_rate_card():
    client, _ = client_with(lambda r: reply(usage=usage(input_tokens=90_000, cache_read_input_tokens=20_000,
                                                        output_tokens=1000)))
    result = await client.chat(MODEL, MSGS)    # 110 nghìn token vào: bảng giá dài cho CẢ lời gọi
    assert result.usage.cost_usd == pytest.approx((90_000 * 0.50 + 20_000 * 0.05 + 1000 * 2.50) / 1e6)
    short, _ = client_with(lambda r: reply(usage=usage(input_tokens=100_000, output_tokens=10)))
    assert (await short.chat(MODEL, MSGS)).usage.cost_usd == pytest.approx((100_000 * 0.10 + 10 * 0.50) / 1e6)


async def test_a_price_without_cache_rates_falls_back_to_the_input_price():
    prices = {MODEL: ModelPrice.model_validate({"in": 0.10, "out": 0.50})}
    client, _ = client_with(lambda r: reply(usage=usage(input_tokens=100, cache_read_input_tokens=100,
                                                        cache_creation_input_tokens=100, output_tokens=10)), prices)
    assert (await client.chat(MODEL, MSGS)).usage.cost_usd == pytest.approx((300 * 0.10 + 10 * 0.50) / 1e6)


# --- JSON theo schema, nội dung -----------------------------------------------------------------


class Inner(BaseModel):
    note: str


class Out(BaseModel):
    title: str
    count: int
    inner: Inner
    tags: list[str] = []


async def test_a_schema_goes_as_output_config_format_and_the_answer_is_validated_by_pydantic():
    text = json.dumps({"title": "t", "count": 2, "inner": {"note": "n"}, "tags": []})
    client, seen = client_with(lambda r: reply(text))
    value, _ = await client.chat_json(MODEL, MSGS, Out, extra={"reasoning": {"effort": "low"}})
    assert value.count == 2
    assert body(seen)["output_config"] == {"effort": "low", "format": {"type": "json_schema",
                                                                     "schema": strict_schema(Out)}}


async def test_thinking_blocks_before_the_answer_are_skipped_and_stop_reasons_are_translated():
    blocks = [{"type": "thinking", "thinking": "", "signature": "sig"}, {"type": "text", "text": "đáp án"}]
    client, _ = client_with(lambda r: reply(content=blocks, stop="max_tokens"))
    result = await client.chat(MODEL, MSGS)
    assert result.text == "đáp án" and result.finish_reason == "length"


async def test_a_refusal_is_content_blocked_and_an_answer_without_text_is_a_bad_response():
    refused, _ = client_with(lambda r: reply(content=[], stop="refusal"))
    with pytest.raises(WritoryError) as blocked:
        await refused.chat(MODEL, MSGS)
    assert blocked.value.code is ErrorCode.LLM_CONTENT_BLOCKED
    only_thinking = [{"type": "thinking", "thinking": "", "signature": "s"}]
    empty, _ = client_with(lambda r: reply(content=only_thinking, stop="max_tokens"))
    with pytest.raises(WritoryError) as bad:
        await empty.chat(MODEL, MSGS)
    assert bad.value.code is ErrorCode.LLM_BAD_RESPONSE


async def test_the_workspace_id_is_sent_when_the_key_needs_one():
    client, seen = client_with(lambda r: reply(), workspace_id=SecretStr("wrkspc_123"))
    await client.chat(MODEL, MSGS)
    assert "wrkspc_123" in {v for v in seen[0].headers.values()} | {seen[0].content.decode()}


# --- lỗi ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("status, code", [
    (400, ErrorCode.LLM_REQUEST_INVALID), (401, ErrorCode.LLM_AUTH_FAILED), (402, ErrorCode.LLM_INSUFFICIENT_CREDITS),
    (403, ErrorCode.LLM_AUTH_FAILED), (413, ErrorCode.LLM_REQUEST_INVALID), (429, ErrorCode.LLM_RATE_LIMITED),
    (500, ErrorCode.LLM_UNAVAILABLE), (529, ErrorCode.LLM_UNAVAILABLE),
])
async def test_http_errors_become_codes_and_the_key_never_reaches_the_message(status, code):
    err = {"type": "error", "error": {"type": "x", "message": f"bad key {KEY}"}}
    client, _ = client_with(lambda r: (status, err))
    with pytest.raises(WritoryError) as caught:
        await client.chat(MODEL, MSGS)
    assert caught.value.code is code
    assert KEY not in caught.value.detail and KEY not in str(caught.value) and f"HTTP {status}" in caught.value.detail


async def test_a_dropped_connection_is_unavailable_and_says_whether_the_request_left_the_machine():
    def refuse(request):
        raise httpx2.ConnectError("no route", request=request)

    client, _ = client_with(refuse)
    with trace_call() as trace, pytest.raises(WritoryError) as caught:
        await client.chat(MODEL, MSGS)
    assert caught.value.code is ErrorCode.LLM_UNAVAILABLE and trace.sent is False

    def cut(request):
        raise httpx2.ReadError("cut", request=request)

    client2, _ = client_with(cut)
    with trace_call() as trace2, pytest.raises(WritoryError):
        await client2.chat(MODEL, MSGS)
    assert trace2.sent is True      # đã gửi: có thể đã bị tính tiền
    assert httpx.ConnectError  # httpx (OpenRouter/Meta) và httpx2 (SDK) là hai thư viện khác nhau


# --- stream -------------------------------------------------------------------------------------


def sse(*events: tuple[str, dict]) -> bytes:
    return "".join(f"event: {name}\ndata: {json.dumps(data)}\n\n" for name, data in events).encode()


async def test_stream_yields_the_text_then_one_done_with_the_usage_priced():
    start = {"type": "message_start", "message": {
        "id": "msg_x", "type": "message", "role": "assistant", "model": "claude-haiku-5-5", "content": [],
        "stop_reason": None, "stop_sequence": None, "stop_details": None,
        "usage": usage(input_tokens=100, output_tokens=1)}}
    events = sse(
        ("message_start", start),
        ("content_block_start", {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Một "}}),
        ("content_block_delta", {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "mạch"}}),
        ("content_block_stop", {"type": "content_block_stop", "index": 0}),
        ("message_delta", {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                           "usage": {"output_tokens": 50}}),
        ("message_stop", {"type": "message_stop"}),
    )
    client, seen = client_with(lambda r: events)
    got = [e async for e in client.stream(MODEL, MSGS)]
    assert [type(e) for e in got] == [TextDelta, TextDelta, StreamDone]
    assert "".join(e.text for e in got[:2]) == "Một mạch" and body(seen)["stream"] is True
    assert got[2].usage.cost_usd == pytest.approx((100 * 0.10 + 50 * 0.50) / 1e6)


# --- schema quá lớn cho structured output: lùi về schema trong prompt ----------------------------------

GRAMMAR_ERROR = {"type": "error", "error": {"type": "invalid_request_error", "message": (
    "The compiled grammar is too large, which would cause performance issues. Simplify your tool schemas or "
    "reduce the number of strict tools.")}}
GOOD = json.dumps({"title": "t", "count": 2, "inner": {"note": "n"}, "tags": []})


async def test_a_schema_too_large_for_structured_output_falls_back_to_the_schema_in_the_prompt():
    """Lượt thử thật (D-145): BuildOutput bị 400 `compiled grammar is too large`. Lời gọi 400 không bị tính tiền; client
    thử lại không có `output_config.format`, đưa schema vào `system`, pydantic vẫn kiểm câu trả lời (G11)."""
    def handler(request):
        return (400, GRAMMAR_ERROR) if "format" in (json.loads(request.content).get("output_config") or {}) else reply(GOOD)

    client, seen = client_with(handler)
    value, _ = await client.chat_json(MODEL, MSGS, Out, extra={"reasoning": {"effort": "low"}})
    assert value.count == 2 and len(seen) == 2
    first, second = json.loads(seen[0].content), json.loads(seen[1].content)
    assert "format" in first["output_config"]
    assert second["output_config"] == {"effort": "low"} and "format" not in second["output_config"]
    assert second["system"].startswith("luật") and '"count"' in second["system"] and "JSON" in second["system"]
    # Schema đã biết là quá lớn thì lần sau đi thẳng, không tốn thêm một lời gọi 400.
    await client.chat_json(MODEL, MSGS, Out)
    assert len(seen) == 3 and "format" not in (json.loads(seen[2].content).get("output_config") or {})


async def test_other_bad_requests_do_not_trigger_the_fallback_and_a_plain_chat_never_does():
    other = {"type": "error", "error": {"type": "invalid_request_error", "message": "max_tokens too large"}}
    client, seen = client_with(lambda r: (400, other))
    with pytest.raises(WritoryError) as caught:
        await client.chat_json(MODEL, MSGS, Out)
    assert caught.value.code is ErrorCode.LLM_REQUEST_INVALID and len(seen) == 1
    client2, seen2 = client_with(lambda r: (400, GRAMMAR_ERROR))
    with pytest.raises(WritoryError):
        await client2.chat(MODEL, MSGS)      # không có schema: không có gì để lùi
    assert len(seen2) == 1
