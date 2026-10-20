from pathlib import Path

import pytest
from pydantic import BaseModel

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone, TextDelta
from writory.llm.fake import FakeLLM

FIXTURES = Path(__file__).parents[1] / "fixtures"


class Point(BaseModel):
    x: int


MSGS = [Message(role="system", content="luật chung"), Message(role="user", content="xin chào")]


async def test_scripted_returns_in_order_and_records_calls():
    llm = FakeLLM.scripted(["một", "hai"])
    assert (await llm.chat("m", MSGS)).text == "một"
    assert (await llm.chat("m", MSGS)).text == "hai"
    assert llm.calls == [MSGS, MSGS]


async def test_chat_reports_requested_model_and_records_extra():
    llm = FakeLLM.scripted(["một"])
    result = await llm.chat("m/x", MSGS, extra={"max_tokens": 10})
    assert result.model == "m/x"
    assert result.finish_reason == "stop"
    assert llm.extras == [{"max_tokens": 10}]


async def test_scripted_exhausted_fails_loudly():
    llm = FakeLLM.scripted([])
    with pytest.raises(AssertionError, match="hết câu"):
        await llm.chat("m", MSGS)


async def test_scripted_error_entry_is_raised():
    llm = FakeLLM.scripted([WritoryError(ErrorCode.LLM_UNAVAILABLE)])
    with pytest.raises(WritoryError) as exc:
        await llm.chat("m", MSGS)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_echo_returns_whole_context():
    llm = FakeLLM.echo()
    text = (await llm.chat("m", MSGS)).text
    assert "luật chung" in text
    assert "xin chào" in text


async def test_echo_stream_yields_whole_context_then_done():
    llm = FakeLLM.echo(cost_usd=0.01)
    events = [e async for e in llm.stream("m", MSGS)]
    assert isinstance(events[-1], StreamDone)
    assert events[-1].usage.cost_usd == 0.01
    streamed = "".join(e.text for e in events if isinstance(e, TextDelta))
    assert streamed == (await llm.chat("m", MSGS)).text


async def test_from_fixture_loads_text_and_errors():
    llm = FakeLLM.from_fixture(FIXTURES / "llm" / "example_scripted.json")
    assert (await llm.chat("m", MSGS)).text
    with pytest.raises(WritoryError) as exc:
        await llm.chat("m", MSGS)
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


async def test_chat_json_validates_with_pydantic():
    llm = FakeLLM.scripted(['{"x": 3}'])
    value, result = await llm.chat_json("m", MSGS, Point)
    assert value == Point(x=3)
    assert result.text == '{"x": 3}'


async def test_chat_json_wrong_schema_is_bad_response():
    llm = FakeLLM.scripted(['{"y": 3}'])
    with pytest.raises(WritoryError) as exc:
        await llm.chat_json("m", MSGS, Point)
    assert exc.value.code is ErrorCode.LLM_BAD_RESPONSE


async def test_chat_json_passes_schema_to_client():
    llm = FakeLLM.scripted(['{"x": 1}'])
    await llm.chat_json("m", MSGS, Point)
    assert llm.schemas == [Point]
