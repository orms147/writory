import pytest
from pydantic import BaseModel

from writory.config import load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message
from writory.llm.fake import FakeLLM
from writory.llm.retry import (
    RETRY_SCHEMA,
    RETRY_TRANSIENT,
    watch_rejections,
    with_json_retries,
    with_retries,
)

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


async def test_json_retries_layer_schema_inside_transient():
    """D-14: JSON hỏng thử lại theo số lần schema; lỗi mạng theo số lần mạng, mỗi lần lỗi mạng
    lại được đủ số lần schema."""
    from writory.llm.retry import with_json_retries

    llm = FakeLLM.scripted(["hỏng", unavailable(), "hỏng", '{"who": "Lan"}'])
    value, _ = await with_json_retries(
        lambda: llm.chat_json("m", MSGS, Change), schema_retries=1, transient_retries=1
    )
    assert value == Change(who="Lan") and len(llm.calls) == 4

    llm = FakeLLM.scripted(["hỏng"] * 5)
    with pytest.raises(WritoryError) as exc:
        await with_json_retries(lambda: llm.chat_json("m", MSGS, Change),
                                schema_retries=1, transient_retries=2)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == 2  # hết lượt schema: không dùng lượt của lỗi mạng


async def test_retry_on_is_required():
    with pytest.raises(TypeError):
        await with_retries(lambda: None, max_retries=1)


async def test_negative_retries_rejected():
    with pytest.raises(ValueError):
        await with_retries(lambda: None, max_retries=-1, retry_on=RETRY_TRANSIENT)


def test_require_model_returns_role_model_or_model_not_set():
    from writory.llm.base import require_model

    cfg = load_config()
    roles = cfg.models.roles.model_copy(update={"extract": "x/extract", "narrator": None})
    assert require_model(roles, "extract") == "x/extract"
    with pytest.raises(WritoryError) as exc:
        require_model(roles, "narrator")
    assert exc.value.code is ErrorCode.CONFIG_MODEL_NOT_SET
    assert "roles.narrator" in str(exc.value)


def test_role_extra_carries_reasoning_effort_from_config():
    """`role_reasoning.<vai>` (config/models.yaml) đi vào `extra` của lời gọi; null thì không gửi gì."""
    from writory.llm.base import role_extra

    models = load_config().models
    models = models.model_copy(update={
        "role_reasoning": models.role_reasoning.model_copy(update={"extract": "low", "setup": None}),
        "provider_ignore": [],
    })
    assert role_extra(models, "extract") == {"reasoning": {"effort": "low"}}
    assert role_extra(models, "setup") is None


def test_role_extra_carries_the_provider_blacklist_from_config():
    """D-100: nhà cung cấp trả JSON hỏng dù nhận structured_outputs bị loại bằng config; đi cùng
    `require_parameters`, kể cả khi vai không đặt mức suy luận."""
    from writory.llm.base import role_extra

    # Config thật (Luna, D-102) không loại nhà cung cấp nào: đặt một tên để thử cơ chế.
    models = load_config().models.model_copy(update={"provider_ignore": ["NhaCungCapHong"]})
    got = role_extra(models, "setup")
    assert got["provider"] == {"require_parameters": True, "ignore": ["NhaCungCapHong"]}
    assert role_extra(models, "extract")["reasoning"] == {"effort": "low"}
    assert role_extra(models, "extract")["provider"] == got["provider"]


def test_role_extra_has_no_provider_part_when_nothing_is_ignored():
    """D-102: Luna không cần loại nhà cung cấp nào; danh sách rỗng thì không gửi `provider`."""
    from writory.llm.base import provider_extra, role_extra

    models = load_config().models
    assert models.provider_ignore == []
    assert provider_extra(models) is None
    assert "provider" not in role_extra(models, "extract")


# --- móc báo thân trả lời bị từ chối, chỉ bộ đo cài (D-115) ---------------------------------------


def bad(detail="Schema: sai") -> WritoryError:
    return WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail=detail)


async def test_the_rejection_hook_hears_every_schema_failure_and_nothing_else():
    heard: list[WritoryError] = []
    calls = []

    async def op():
        calls.append(1)
        if len(calls) == 1:
            raise unavailable()
        if len(calls) < 4:
            raise bad(f"lần {len(calls)}")
        return "ok"

    with watch_rejections(heard.append):
        assert await with_json_retries(op, schema_retries=2, transient_retries=1) == "ok"
    assert [e.detail for e in heard] == ["lần 2", "lần 3"]  # lỗi mạng không phải thân bị từ chối


async def test_the_last_rejection_is_heard_too_before_the_retry_limit_error():
    heard: list[WritoryError] = []

    async def op():
        raise bad()

    with watch_rejections(heard.append), pytest.raises(WritoryError) as exc:
        await with_retries(op, max_retries=1, retry_on=RETRY_SCHEMA)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED and len(heard) == 2


async def test_without_a_hook_nothing_changes_and_the_hook_is_scoped():
    async def op():
        raise bad()

    with pytest.raises(WritoryError):
        await with_retries(op, max_retries=0, retry_on=RETRY_SCHEMA)
    heard: list[WritoryError] = []
    with watch_rejections(heard.append):
        pass
    with pytest.raises(WritoryError):
        await with_retries(op, max_retries=0, retry_on=RETRY_SCHEMA)
    assert heard == []  # ra khỏi khối là gỡ móc


async def test_a_failing_hook_never_changes_the_outcome():
    def broken(_: WritoryError) -> None:
        raise RuntimeError("móc hỏng")

    calls = []

    async def op():
        calls.append(1)
        if len(calls) == 1:
            raise bad()
        return "ok"

    with watch_rejections(broken):
        assert await with_retries(op, max_retries=1, retry_on=RETRY_SCHEMA) == "ok"


# --- thử lại có chờ lùi cho lỗi tạm (D-123) ------------------------------------------------------


def timeout() -> WritoryError:
    return WritoryError(ErrorCode.LLM_TIMEOUT, detail="quá hạn")


async def test_transient_errors_wait_longer_before_each_retry_using_the_schedule():
    waits: list[float] = []

    async def fake(seconds: float) -> None:
        waits.append(seconds)

    calls = []

    async def op():
        calls.append(1)
        if len(calls) < 4:
            raise unavailable() if len(calls) % 2 else timeout()
        return "ok"

    got = await with_retries(op, max_retries=3, retry_on=RETRY_TRANSIENT,
                             backoff=(2, 8, 30), sleep=fake)
    assert got == "ok" and waits == [2, 8, 30]


async def test_a_schedule_shorter_than_the_retries_repeats_its_last_wait():
    waits: list[float] = []

    async def fake(seconds: float) -> None:
        waits.append(seconds)

    async def op():
        raise unavailable()

    with pytest.raises(WritoryError):
        await with_retries(op, max_retries=3, retry_on=RETRY_TRANSIENT, backoff=(2, 8), sleep=fake)
    assert waits == [2, 8, 8]  # không chờ sau lần thử cuối, vì không còn lần nào


async def test_no_wait_for_schema_errors_rate_limits_or_without_a_schedule():
    waits: list[float] = []

    async def fake(seconds: float) -> None:
        waits.append(seconds)

    async def bad():
        raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="sai schema")

    with pytest.raises(WritoryError):
        await with_retries(bad, max_retries=2, retry_on=RETRY_SCHEMA, backoff=(2, 8), sleep=fake)

    async def limited():
        raise WritoryError(ErrorCode.LLM_RATE_LIMITED, detail="429")

    with pytest.raises(WritoryError) as exc:
        await with_retries(limited, max_retries=2, retry_on=RETRY_TRANSIENT, backoff=(2, 8),
                           sleep=fake)
    assert exc.value.code is ErrorCode.LLM_RATE_LIMITED  # không thử lại, không chờ

    async def down():
        raise unavailable()

    with pytest.raises(WritoryError):
        await with_retries(down, max_retries=2, retry_on=RETRY_TRANSIENT, sleep=fake)  # không lịch
    assert waits == []


async def test_json_retries_wait_only_in_the_transient_layer():
    waits: list[float] = []

    async def fake(seconds: float) -> None:
        waits.append(seconds)

    calls = []

    async def op():
        calls.append(1)
        n = len(calls)
        if n == 1:
            raise WritoryError(ErrorCode.LLM_BAD_RESPONSE, detail="sai schema")
        if n == 2:
            raise unavailable()
        return "ok"

    got = await with_json_retries(op, schema_retries=1, transient_retries=2, backoff=(2, 8),
                                  sleep=fake)
    assert got == "ok" and waits == [2]  # schema lần 1 không chờ; lỗi mạng chờ 2 giây


async def test_production_waits_through_the_replaceable_sleep_and_tests_replace_it(slept):
    """conftest thay `retry._sleep`: test không bao giờ chờ thật (§6), vẫn thấy số giây định chờ."""
    calls = []

    async def op():
        calls.append(1)
        if len(calls) < 3:
            raise unavailable()
        return "ok"

    assert await with_retries(op, max_retries=2, retry_on=RETRY_TRANSIENT, backoff=(2, 8)) == "ok"
    assert slept == [2, 8]


def test_the_repo_schedule_covers_every_transient_retry():
    """limits.yaml: mỗi lần thử lại lỗi tạm có một lần chờ riêng (D-123)."""
    r = RETRIES
    assert len(r.transient_backoff_seconds) == r.llm_transient >= 1
    assert list(r.transient_backoff_seconds) == sorted(r.transient_backoff_seconds)  # lùi dần


def test_the_worst_case_wait_fits_inside_what_a_player_will_sit_through():
    """Xấu nhất một lời gọi: (1 + lần thử lại) hạn tổng (D-113) cộng các lần chờ lùi; ghi ở D-123."""
    cfg = load_config()
    worst = (1 + cfg.limits.retries.llm_transient) * cfg.limits.llm_call.require(
        "deadline_seconds") + sum(cfg.limits.retries.transient_backoff_seconds)
    assert worst <= 30 * 60  # nửa giờ
