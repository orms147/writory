import asyncio

import pytest

from writory.config import AppConfig, CostLimits, ModelPrice, load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import CallTrace, Message, StreamDone
from writory.llm.cost import (
    EST_CHARS_PER_TOKEN,
    CostEstimator,
    CostTracker,
    MeteredClient,
    maybe_billed,
)
from writory.llm.fake import FakeLLM

MSGS = [Message(role="user", content="viết cảnh")]


def limits(scene=1.0, chapter=10.0, story=100.0) -> CostLimits:
    return CostLimits(per_scene=scene, per_chapter=chapter, per_story=story)


def code_of(exc_info) -> ErrorCode:
    return exc_info.value.code


def test_unset_cap_is_an_error_not_infinite():
    tracker = CostTracker(CostLimits(per_scene=None, per_chapter=1.0, per_story=1.0))
    with pytest.raises(WritoryError) as exc:
        tracker.ensure_budget()
    assert code_of(exc) is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert "per_scene" in str(exc.value)


def test_costs_accumulate_per_scene_chapter_story():
    tracker = CostTracker(limits(), story_spent_usd=5.0)
    tracker.record(0.25)
    tracker.record(0.5)
    assert tracker.scene_usd == pytest.approx(0.75)
    assert tracker.chapter_usd == pytest.approx(0.75)
    assert tracker.story_usd == pytest.approx(5.75)


def test_start_scene_resets_scene_only():
    tracker = CostTracker(limits())
    tracker.record(0.5)
    tracker.start_scene()
    assert tracker.scene_usd == 0
    assert tracker.chapter_usd == pytest.approx(0.5)


def test_start_chapter_resets_chapter_and_scene():
    tracker = CostTracker(limits())
    tracker.record(0.5)
    tracker.start_chapter()
    assert tracker.scene_usd == 0
    assert tracker.chapter_usd == 0
    assert tracker.story_usd == pytest.approx(0.5)


@pytest.mark.parametrize(
    ("caps", "expected"),
    [
        ({"scene": 0.5}, ErrorCode.COST_LIMIT_SCENE),
        ({"chapter": 0.5}, ErrorCode.COST_LIMIT_CHAPTER),
        ({"story": 0.5}, ErrorCode.COST_LIMIT_STORY),
    ],
)
def test_reaching_a_cap_stops(caps, expected):
    tracker = CostTracker(limits(**caps))
    tracker.ensure_budget()
    tracker.record(0.5)
    with pytest.raises(WritoryError) as exc:
        tracker.ensure_budget()
    assert code_of(exc) is expected


def test_story_spend_from_earlier_sessions_counts():
    tracker = CostTracker(limits(story=1.0), story_spent_usd=1.0)
    with pytest.raises(WritoryError) as exc:
        tracker.ensure_budget()
    assert code_of(exc) is ErrorCode.COST_LIMIT_STORY


def test_unknown_cost_fails_closed():
    tracker = CostTracker(limits())
    with pytest.raises(WritoryError) as exc:
        tracker.record(None)
    assert code_of(exc) is ErrorCode.LLM_COST_UNKNOWN


async def test_metered_client_stops_calling_model_at_cap():
    inner = FakeLLM.echo(cost_usd=0.25)
    client = MeteredClient(inner, CostTracker(limits(scene=1.0)))
    for _ in range(4):
        await client.chat("m", MSGS)
    with pytest.raises(WritoryError) as exc:
        await client.chat("m", MSGS)
    assert code_of(exc) is ErrorCode.COST_LIMIT_SCENE
    assert len(inner.calls) == 4


async def test_metered_chat_passes_extra_through():
    inner = FakeLLM.echo()
    await MeteredClient(inner, CostTracker(limits())).chat("m", MSGS, extra={"max_tokens": 5})
    assert inner.extras == [{"max_tokens": 5}]


async def test_metered_chat_json_is_metered():
    inner = FakeLLM.scripted(['{"a": 1}'], cost_usd=0.3)
    tracker = CostTracker(limits())
    from pydantic import BaseModel

    class A(BaseModel):
        a: int

    await MeteredClient(inner, tracker).chat_json("m", MSGS, A)
    assert tracker.scene_usd == pytest.approx(0.3)


async def test_metered_stream_records_cost_at_end():
    tracker = CostTracker(limits())
    client = MeteredClient(FakeLLM.echo(cost_usd=0.2), tracker)
    events = [e async for e in client.stream("m", MSGS)]
    assert isinstance(events[-1], StreamDone)
    assert tracker.scene_usd == pytest.approx(0.2)


async def test_metered_stream_checks_budget_before_calling():
    inner = FakeLLM.echo(cost_usd=0.2)
    tracker = CostTracker(limits(scene=0.1))
    tracker.record(0.1)
    with pytest.raises(WritoryError):
        [e async for e in MeteredClient(inner, tracker).stream("m", MSGS)]
    assert inner.calls == []


async def test_metered_unknown_cost_from_model_fails_closed():
    client = MeteredClient(FakeLLM.echo(cost_usd=None), CostTracker(limits()))
    with pytest.raises(WritoryError) as exc:
        await client.chat("m", MSGS)
    assert code_of(exc) is ErrorCode.LLM_COST_UNKNOWN


# --- chi phí tối đa của lời gọi không có usage (D-64) ---------------------------------------

LUNA = ModelPrice(input=0.10, output=0.50)


def estimator(max_output=1000) -> CostEstimator:
    return CostEstimator({"m/luna": LUNA}, max_output_tokens=max_output)


def test_max_cost_is_estimated_input_plus_the_full_output_cap():
    msgs = [Message(role="system", content="a" * 300), Message(role="user", content="b" * 100)]
    tokens_in = 400 / EST_CHARS_PER_TOKEN
    assert estimator().max_cost("m/luna", msgs, None) == pytest.approx(
        (tokens_in * 0.10 + 1000 * 0.50) / 1e6)


def test_max_cost_counts_the_json_schema_sent_with_the_call():
    from writory.safety.classify import Classification

    plain = estimator().max_cost("m/luna", MSGS, None)
    assert estimator().max_cost("m/luna", MSGS, Classification) > plain


def test_model_without_price_fails_closed():
    with pytest.raises(WritoryError) as exc:
        estimator().max_cost("m/khac", MSGS, None)
    assert code_of(exc) is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert "m/khac" in str(exc.value)


@pytest.mark.parametrize(("given", "sent"), [(None, 1000), (400, 400), (5000, 1000)])
def test_bound_sends_max_tokens_no_higher_than_the_cap(given, sent):
    extra = {"reasoning": {"effort": "low"}} | ({} if given is None else {"max_tokens": given})
    bounded = estimator().bound(extra)
    assert bounded["max_tokens"] == sent and bounded["reasoning"] == {"effort": "low"}
    assert estimator().bound(None) == {"max_tokens": 1000}


def test_from_config_needs_the_output_cap(tmp_path):
    config = load_config()
    assert CostEstimator.from_config(config).bound(None)["max_tokens"] == (
        config.limits.llm_call.max_output_tokens)
    unset = AppConfig.model_validate(config.model_dump(by_alias=True) | {
        "limits": config.limits.model_dump(by_alias=True) | {"llm_call": {
            "max_output_tokens": None}}})
    with pytest.raises(WritoryError) as exc:
        CostEstimator.from_config(unset)
    assert code_of(exc) is ErrorCode.CONFIG_LIMIT_NOT_SET


def test_every_repo_model_has_a_price():
    config = load_config()
    used = {m for m in config.models.roles.model_dump().values() if m is not None}
    used |= {t.model for t in config.models.writer_tiers}
    assert used <= set(config.models.prices)


def trace(sent=None, gen=None) -> CallTrace:
    return CallTrace(sent=sent, generation_id=gen)


@pytest.mark.parametrize(("exc", "t", "billed"), [
    (asyncio.CancelledError(), trace(), True),  # client không báo: có thể đã gửi
    (asyncio.CancelledError(), trace(sent=True), True),
    (asyncio.CancelledError(), trace(sent=False), False),  # chưa gửi (ví dụ đang chờ lượt)
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="ReadError"), trace(sent=True), True),
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="ConnectError"), trace(sent=False), False),
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 503, error.code=503: x"),
     trace(sent=True), False),  # nhà cung cấp từ chối trước khi sinh
    (WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 200, error.code=server_error: x"),
     trace(sent=True, gen="gen-1"), True),  # đã có generation: tra lại sẽ ra số thật
    (WritoryError(ErrorCode.WRITORY_RATE_LIMITED), trace(), False),  # bộ đếm chặn trước khi gọi
    (WritoryError(ErrorCode.LLM_AUTH_FAILED, detail="HTTP 401"), trace(sent=True), False),
    (ValueError("extra"), trace(), False),
])
def test_maybe_billed(exc, t, billed):
    assert maybe_billed(exc, t) is billed
