import pytest
from pydantic import BaseModel

from writory.config import load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message
from writory.llm.fake import FakeLLM
from writory.llm.retry import with_retries

MSGS = [Message(role="user", content="trích JSON")]


class Change(BaseModel):
    who: str


def unavailable() -> WritoryError:
    return WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="giả lập")


async def test_always_failing_model_stops_after_configured_retries():
    """G8: model giả luôn lỗi → dừng sau đúng số lần thử trong config/limits.yaml."""
    max_retries = load_config().limits.retries.extract_schema_retry
    llm = FakeLLM.scripted([unavailable() for _ in range(max_retries + 5)])
    with pytest.raises(WritoryError) as exc:
        await with_retries(lambda: llm.chat("m", MSGS), max_retries=max_retries)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == max_retries + 1


async def test_zero_retries_means_one_attempt():
    llm = FakeLLM.scripted([unavailable(), "không tới đây"])
    with pytest.raises(WritoryError):
        await with_retries(lambda: llm.chat("m", MSGS), max_retries=0)
    assert len(llm.calls) == 1


async def test_bad_json_then_good_json_succeeds():
    llm = FakeLLM.scripted(["không phải json", '{"who": "Lan"}'])
    value, _ = await with_retries(lambda: llm.chat_json("m", MSGS, Change), max_retries=1)
    assert value == Change(who="Lan")
    assert len(llm.calls) == 2


@pytest.mark.parametrize(
    "code",
    [
        ErrorCode.LLM_AUTH_FAILED,
        ErrorCode.LLM_INSUFFICIENT_CREDITS,
        ErrorCode.COST_LIMIT_SCENE,
        ErrorCode.LLM_COST_UNKNOWN,
    ],
)
async def test_non_retryable_errors_are_not_retried(code):
    llm = FakeLLM.scripted([WritoryError(code), "không tới đây"])
    with pytest.raises(WritoryError) as exc:
        await with_retries(lambda: llm.chat("m", MSGS), max_retries=3)
    assert exc.value.code is code
    assert len(llm.calls) == 1


async def test_negative_retries_rejected():
    with pytest.raises(ValueError):
        await with_retries(lambda: None, max_retries=-1)
