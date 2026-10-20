"""Giới hạn số lời gọi model mỗi phút (G8, D-56): bọc client, kiểm trước mỗi lời gọi."""

import pytest

from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone, TextDelta
from writory.llm.fake import FakeLLM
from writory.llm.ratelimit import RateLimitedClient

MSGS = [Message(role="user", content="viết")]


class CountingQuota:
    """Cho `allowed` lượt rồi từ chối; ghi số lần được hỏi."""

    def __init__(self, allowed: int) -> None:
        self.allowed = allowed
        self.asked = 0

    async def take(self) -> bool:
        self.asked += 1
        return self.asked <= self.allowed


async def test_calls_within_quota_reach_the_model():
    inner = FakeLLM.scripted(["một", "hai"], cost_usd=0.01)
    client = RateLimitedClient(inner, CountingQuota(2))

    assert (await client.chat("m", MSGS)).text == "một"
    assert (await client.chat("m", MSGS, extra={"max_tokens": 5})).text == "hai"
    assert inner.extras[-1] == {"max_tokens": 5}


async def test_call_over_quota_is_refused_before_the_model_is_called():
    inner = FakeLLM.scripted(["một", "hai"])
    client = RateLimitedClient(inner, CountingQuota(1))
    await client.chat("m", MSGS)

    with pytest.raises(WritoryError) as exc:
        await client.chat("m", MSGS)
    assert exc.value.code is ErrorCode.WRITORY_RATE_LIMITED
    assert len(inner.calls) == 1  # lời gọi bị từ chối không tới model


async def test_stream_is_counted_and_refused_like_chat():
    inner = FakeLLM.scripted(["chữ chảy", "không tới"])
    client = RateLimitedClient(inner, CountingQuota(1))

    events = [e async for e in client.stream("m", MSGS)]
    assert "".join(e.text for e in events if isinstance(e, TextDelta)) == "chữ chảy"
    assert isinstance(events[-1], StreamDone)
    with pytest.raises(WritoryError) as exc:
        [e async for e in client.stream("m", MSGS)]
    assert exc.value.code is ErrorCode.WRITORY_RATE_LIMITED
    assert len(inner.calls) == 1


async def test_chat_json_goes_through_the_same_quota():
    from pydantic import BaseModel

    class Out(BaseModel):
        x: int

    quota = CountingQuota(0)
    client = RateLimitedClient(FakeLLM.scripted(['{"x": 1}']), quota)
    with pytest.raises(WritoryError) as exc:
        await client.chat_json("m", MSGS, Out)
    assert exc.value.code is ErrorCode.WRITORY_RATE_LIMITED and quota.asked == 1


async def test_error_text_for_the_player_is_fixed_vietnamese():
    payload = WritoryError(ErrorCode.WRITORY_RATE_LIMITED).player_payload()
    assert payload["code"] == "WRITORY_RATE_LIMITED" and "Đợi" in payload["message"]
