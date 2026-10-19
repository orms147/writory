import pytest

from writory.config import CostLimits
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone
from writory.llm.cost import CostTracker, MeteredClient
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
