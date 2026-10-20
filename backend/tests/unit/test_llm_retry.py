import pytest
from pydantic import BaseModel

from writory.config import load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message
from writory.llm.fake import FakeLLM
from writory.llm.retry import RETRY_SCHEMA, RETRY_TRANSIENT, with_retries

MSGS = [Message(role="user", content="trích JSON")]
RETRIES = load_config().limits.retries


class Change(BaseModel):
    who: str


def unavailable() -> WritoryError:
    return WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="giả lập")


async def test_always_failing_model_stops_after_configured_transient_retries():
    """G8: model giả luôn lỗi mạng → dừng sau đúng `retries.llm_transient` lần thử lại."""
    max_retries = RETRIES.llm_transient
    llm = FakeLLM.scripted([unavailable() for _ in range(max_retries + 5)])
    with pytest.raises(WritoryError) as exc:
        await with_retries(
            lambda: llm.chat("m", MSGS), max_retries=max_retries, retry_on=RETRY_TRANSIENT
        )
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == max_retries + 1


async def test_always_bad_json_stops_after_configured_schema_retries():
    """G11: JSON sai schema chỉ thử lại `retries.extract_schema_retry` lần."""
    max_retries = RETRIES.extract_schema_retry
    llm = FakeLLM.scripted(["không phải json"] * (max_retries + 5))
    with pytest.raises(WritoryError) as exc:
        await with_retries(
            lambda: llm.chat_json("m", MSGS, Change),
            max_retries=max_retries,
            retry_on=RETRY_SCHEMA,
        )
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == max_retries + 1


async def test_zero_retries_means_one_attempt():
    llm = FakeLLM.scripted([unavailable(), "không tới đây"])
    with pytest.raises(WritoryError):
        await with_retries(lambda: llm.chat("m", MSGS), max_retries=0, retry_on=RETRY_TRANSIENT)
    assert len(llm.calls) == 1


async def test_bad_json_then_good_json_succeeds():
    llm = FakeLLM.scripted(["không phải json", '{"who": "Lan"}'])
    value, _ = await with_retries(
        lambda: llm.chat_json("m", MSGS, Change), max_retries=1, retry_on=RETRY_SCHEMA
    )
    assert value == Change(who="Lan")
    assert len(llm.calls) == 2


@pytest.mark.parametrize(
    ("retry_on", "error"),
    [
        (RETRY_TRANSIENT, ErrorCode.LLM_BAD_RESPONSE),  # số lần của lỗi mạng không dùng cho JSON
        (RETRY_SCHEMA, ErrorCode.LLM_UNAVAILABLE),
    ],
)
async def test_error_outside_retry_on_is_raised_immediately(retry_on, error):
    llm = FakeLLM.scripted([WritoryError(error), "không tới đây"])
    with pytest.raises(WritoryError) as exc:
        await with_retries(lambda: llm.chat("m", MSGS), max_retries=3, retry_on=retry_on)
    assert exc.value.code is error
    assert len(llm.calls) == 1


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
        await with_retries(
            lambda: llm.chat("m", MSGS), max_retries=3, retry_on=RETRY_TRANSIENT | RETRY_SCHEMA
        )
    assert exc.value.code is code
    assert len(llm.calls) == 1


async def test_retry_on_is_required():
    with pytest.raises(TypeError):
        await with_retries(lambda: None, max_retries=1)


async def test_negative_retries_rejected():
    with pytest.raises(ValueError):
        await with_retries(lambda: None, max_retries=-1, retry_on=RETRY_TRANSIENT)


def test_require_model_returns_role_model_or_model_not_set():
    from writory.llm.base import require_model

    cfg = load_config()
    roles = cfg.models.roles.model_copy(update={"extract": "x/extract", "guard": None})
    assert require_model(roles, "extract") == "x/extract"
    with pytest.raises(WritoryError) as exc:
        require_model(roles, "guard")
    assert exc.value.code is ErrorCode.CONFIG_MODEL_NOT_SET
    assert "roles.guard" in str(exc.value)
