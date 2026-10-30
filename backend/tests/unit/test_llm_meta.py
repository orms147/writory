"""MetaClient (llm/meta.py, D-140): client của bộ đo cho model Meta qua httpx.MockTransport, không mạng.
Hình dạng yêu cầu và phản hồi theo MetaProvider của bài F (D-108) và tài liệu Meta Model API
(dev.meta.ai/docs/features/chat-completion, tra 30/10/2026): endpoint kiểu OpenAI, bearer, `reasoning_effort`,
`usage` chỉ có token (không có chi phí). Chưa đối chiếu với lời gọi thật."""

import json

import httpx
import pytest
from pydantic import BaseModel, SecretStr

from writory.config import ModelPrice
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone, TextDelta, trace_call
from writory.llm.meta import META_BASE_URL, MetaClient, strict_schema

KEY = "meta-key-" + "0123456789abcdef" * 3
MODEL = "meta/muse-wonder-1.0"
PRICES = {MODEL: ModelPrice.model_validate({"in": 4.0, "cached_in": 0.2, "out": 20.0})}
MSGS = [Message(role="system", content="luật"), Message(role="user", content="viết")]


def completion(text="Xin chào", *, prompt=10, completion_tokens=5, cached=None, usage=True, **message) -> dict:
    body: dict = {
        "id": "x", "model": "muse-wonder-1.0",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": text, **message}}],
    }
    if usage:
        body["usage"] = {"prompt_tokens": prompt, "completion_tokens": completion_tokens,
                         "total_tokens": prompt + completion_tokens,
                         **({"prompt_tokens_details": {"cached_tokens": cached}} if cached is not None else {})}
    return body


def client_with(handler, prices=PRICES, **kw):
    seen: list[httpx.Request] = []

    def recording(request):
        seen.append(request)
        return handler(request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(recording))
    return MetaClient(SecretStr(KEY), prices, http=http, **kw), seen


def sent(seen) -> dict:
    return json.loads(seen[-1].content)


async def test_the_request_goes_to_meta_with_the_key_only_in_the_header_and_the_bare_model_id():
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    result = await client.chat(MODEL, MSGS, extra={"max_tokens": 777})
    req = seen[0]
    assert str(req.url) == f"{META_BASE_URL}/chat/completions" and req.method == "POST"
    assert req.headers["authorization"] == f"Bearer {KEY}"
    assert KEY not in req.content.decode() and KEY not in str(req.url)
    body = sent(seen)
    assert body["model"] == "muse-wonder-1.0" and body["max_tokens"] == 777
    assert body["messages"] == [{"role": "system", "content": "luật"}, {"role": "user", "content": "viết"}]
    assert "provider" not in body and not body.get("stream") and "response_format" not in body
    assert result.text == "Xin chào" and result.finish_reason == "stop" and result.model == "muse-wonder-1.0"


@pytest.mark.parametrize("effort, sent_effort", [
    ("minimal", "minimal"), ("low", "low"), ("medium", "medium"), ("high", "high"),
    ("none", "minimal"),   # Meta không nhận `none` (HTTP 400): mức thấp nhất của nó là `minimal`
])
async def test_the_role_reasoning_is_mapped_to_reasoning_effort(effort, sent_effort):
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    await client.chat(MODEL, MSGS, extra={"reasoning": {"effort": effort}})
    assert sent(seen)["reasoning_effort"] == sent_effort and "reasoning" not in sent(seen)


async def test_no_reasoning_setting_sends_no_effort_and_the_openrouter_provider_field_is_dropped():
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    await client.chat(MODEL, MSGS, extra={"provider": {"require_parameters": True, "ignore": ["x"]}})
    assert "reasoning_effort" not in sent(seen) and "provider" not in sent(seen)


async def test_an_unknown_extra_is_refused_instead_of_silently_lost():
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    with pytest.raises(ValueError, match="mirostat"):
        await client.chat(MODEL, MSGS, extra={"mirostat": 2})
    with pytest.raises(ValueError, match="model"):
        await client.chat(MODEL, MSGS, extra={"model": "x"})
    assert seen == []


async def test_a_model_that_is_not_meta_or_has_no_price_is_refused_before_anything_is_sent():
    client, seen = client_with(lambda r: httpx.Response(200, json=completion()))
    with pytest.raises(WritoryError) as wrong:
        await client.chat("openai/gpt-6-luna", MSGS)
    assert wrong.value.code is ErrorCode.CONFIG_MODEL_NOT_SET
    with pytest.raises(WritoryError) as unpriced:
        await client.chat("meta/muse-other", MSGS)
    assert unpriced.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET and "meta/muse-other" in unpriced.value.detail
    assert seen == []


# --- chi phí tính từ token ----------------------------------------------------------------------


async def test_the_cost_is_tokens_times_the_configured_price_with_cached_tokens_priced_apart():
    client, _ = client_with(lambda r: httpx.Response(200, json=completion(prompt=1000, completion_tokens=500,
                                                                           cached=400)))
    result = await client.chat(MODEL, MSGS)
    assert result.usage.cost_usd == pytest.approx((600 * 4.0 + 400 * 0.2 + 500 * 20.0) / 1e6)
    assert (result.usage.prompt_tokens, result.usage.completion_tokens, result.usage.cached_tokens) == (1000, 500, 400)


async def test_without_a_cached_price_the_cached_tokens_cost_the_normal_input_price():
    prices = {MODEL: ModelPrice.model_validate({"in": 4.0, "out": 20.0})}
    client, _ = client_with(lambda r: httpx.Response(200, json=completion(prompt=1000, completion_tokens=500,
                                                                           cached=400)), prices)
    assert (await client.chat(MODEL, MSGS)).usage.cost_usd == pytest.approx((1000 * 4.0 + 500 * 20.0) / 1e6)


async def test_a_response_without_usage_has_no_cost_so_the_caller_stops_instead_of_guessing():
    client, _ = client_with(lambda r: httpx.Response(200, json=completion(usage=False)))
    assert (await client.chat(MODEL, MSGS)).usage.cost_usd is None


# --- JSON theo schema ---------------------------------------------------------------------------


class Inner(BaseModel):
    note: str


class Out(BaseModel):
    title: str
    count: int
    inner: Inner
    maybe: str | None = None
    tags: list[str] = []


async def test_a_schema_goes_as_a_strict_json_schema_and_the_answer_is_validated_by_pydantic():
    reply = json.dumps({"title": "t", "count": 2, "inner": {"note": "n"}, "maybe": None, "tags": []})
    client, seen = client_with(lambda r: httpx.Response(200, json=completion(reply)))
    value, result = await client.chat_json(MODEL, MSGS, Out)
    assert value.count == 2 and result.text == reply
    fmt = sent(seen)["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["name"] == "Out" and fmt["json_schema"]["strict"] is True


def test_the_strict_schema_closes_every_object_requires_every_property_and_drops_unchecked_keywords():
    schema = strict_schema(Out)

    def objects(node):
        if isinstance(node, dict):
            if "properties" in node:
                yield node
            for v in node.values():
                yield from objects(v)
        elif isinstance(node, list):
            for v in node:
                yield from objects(v)

    found = list(objects(schema))
    assert len(found) == 2    # Out và Inner (trong $defs)
    for obj in found:
        assert obj["additionalProperties"] is False and obj["required"] == list(obj["properties"])
    text = json.dumps(schema)
    for banned in ('"default"', '"minLength"', '"minItems"', '"maxLength"', '"minimum"'):
        assert banned not in text


# --- lỗi ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("status, code", [
    (400, ErrorCode.LLM_REQUEST_INVALID), (401, ErrorCode.LLM_AUTH_FAILED), (402, ErrorCode.LLM_INSUFFICIENT_CREDITS),
    (403, ErrorCode.LLM_AUTH_FAILED), (429, ErrorCode.LLM_RATE_LIMITED), (500, ErrorCode.LLM_UNAVAILABLE),
    (503, ErrorCode.LLM_UNAVAILABLE), (504, ErrorCode.LLM_UNAVAILABLE),
])
async def test_http_errors_become_codes_and_the_key_never_reaches_the_message(status, code):
    client, _ = client_with(lambda r: httpx.Response(status, json={"error": {"message": f"bad key {KEY}"}}))
    with pytest.raises(WritoryError) as caught:
        await client.chat(MODEL, MSGS)
    assert caught.value.code is code
    assert KEY not in caught.value.detail and KEY not in str(caught.value) and f"HTTP {status}" in caught.value.detail


async def test_a_dropped_connection_is_unavailable_and_says_whether_the_request_left_the_machine():
    def refuse(request):
        raise httpx.ConnectError("no route", request=request)

    client, _ = client_with(refuse)
    with trace_call() as trace, pytest.raises(WritoryError) as caught:
        await client.chat(MODEL, MSGS)
    assert caught.value.code is ErrorCode.LLM_UNAVAILABLE and trace.sent is False

    def cut(request):
        raise httpx.ReadError("cut", request=request)

    client2, _ = client_with(cut)
    with trace_call() as trace2, pytest.raises(WritoryError):
        await client2.chat(MODEL, MSGS)
    assert trace2.sent is True    # đã gửi: có thể đã bị tính tiền


async def test_a_refusal_is_content_blocked_and_a_bodyless_answer_is_a_bad_response():
    refused, _ = client_with(lambda r: httpx.Response(200, json=completion(None, refusal="không thể")))
    with pytest.raises(WritoryError) as blocked:
        await refused.chat(MODEL, MSGS)
    assert blocked.value.code is ErrorCode.LLM_CONTENT_BLOCKED
    empty, _ = client_with(lambda r: httpx.Response(200, json={"choices": []}))
    with pytest.raises(WritoryError) as bad:
        await empty.chat(MODEL, MSGS)
    assert bad.value.code is ErrorCode.LLM_BAD_RESPONSE


# --- stream -------------------------------------------------------------------------------------


async def test_stream_is_one_call_without_streaming_because_the_stream_usage_is_not_documented():
    """Docs Meta không nói chunk SSE có `usage` hay không: không có token thì không tính được chi phí. Nên
    `stream` gọi một lần không stream rồi trả một TextDelta và StreamDone (ghi trong D-140)."""
    client, seen = client_with(lambda r: httpx.Response(200, json=completion("Một mạch", prompt=100,
                                                                              completion_tokens=50)))
    events = [e async for e in client.stream(MODEL, MSGS)]
    assert [type(e) for e in events] == [TextDelta, StreamDone] and events[0].text == "Một mạch"
    assert events[1].usage.cost_usd == pytest.approx((100 * 4.0 + 50 * 20.0) / 1e6)
    assert not sent(seen).get("stream")
