"""Ghi chi phí mọi lời gọi model theo vai (G8, D-44): `RecordingClient` và bảng vai theo schema."""

import pytest

from writory.api.deps import ROLE_OF_SCHEMA, role_of_schema
from writory.config import CostLimits
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message, StreamDone, Usage
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM
from writory.llm.ledger import RecordingClient
from writory.pipeline.choices import ChoicesOutput
from writory.pipeline.extract import ExtractOutput
from writory.pipeline.narrator import NarratorOutput
from writory.pipeline.scene import SceneOutline
from writory.pipeline.setup import BuildOutput, CharactersOutput, PlotsOutput, SettingsOutput
from writory.safety.classify import Classification
from writory.safety.moderate import ModerationOutput

MSG = [Message(role="user", content="xin chào")]
CAP = CostLimits(per_scene=1.0, per_chapter=1.0, per_story=1.0)


def recorder():
    rows: list[tuple[str, str, Usage]] = []
    return rows, lambda role, model, usage: rows.append((role, model, usage))


async def test_records_role_model_and_usage_of_each_call():
    rows, sink = recorder()
    narrator_json = '{"known": false, "answer": null, "entry_ids": []}'
    llm = RecordingClient(FakeLLM.scripted(["a", narrator_json], cost_usd=0.002),
                          sink, role_of=role_of_schema)
    await llm.chat("m/writer", MSG)
    await llm.chat_json("m/narrator", MSG, NarratorOutput)
    assert [(r, m, u.cost_usd) for r, m, u in rows] == [
        ("writer", "m/writer", 0.002), ("narrator", "m/narrator", 0.002)]


async def test_call_without_cost_is_still_recorded_then_metering_stops():
    """Phản hồi thiếu usage.cost: vẫn có dòng nhật ký (cost NULL), rồi MeteredClient dừng (D-10)."""
    rows, sink = recorder()
    llm = MeteredClient(RecordingClient(FakeLLM.scripted(["a"], cost_usd=None), sink,
                                        role_of=role_of_schema), CostTracker(CAP))
    with pytest.raises(WritoryError) as exc:
        await llm.chat("m", MSG)
    assert exc.value.code is ErrorCode.LLM_COST_UNKNOWN
    assert [(r, u.cost_usd) for r, _, u in rows] == [("writer", None)]


async def test_failed_call_records_nothing():
    rows, sink = recorder()
    llm = RecordingClient(FakeLLM.scripted([WritoryError(ErrorCode.LLM_UNAVAILABLE)]), sink,
                          role_of=role_of_schema)
    with pytest.raises(WritoryError):
        await llm.chat("m", MSG)
    assert rows == []


async def test_stream_records_once_at_the_end():
    rows, sink = recorder()
    llm = RecordingClient(FakeLLM.scripted(["x" * 40], cost_usd=0.01), sink,
                          role_of=role_of_schema)
    events = [e async for e in llm.stream("m", MSG)]
    assert isinstance(events[-1], StreamDone)
    assert [(r, u.cost_usd) for r, _, u in rows] == [("writer", 0.01)]


@pytest.mark.parametrize(("schema", "role"), [
    (None, "writer"),
    (SceneOutline, "outline"),
    (ExtractOutput, "extract"),
    (ChoicesOutput, "choices"),
    (NarratorOutput, "narrator"),
    (Classification, "classify"),
    (SettingsOutput, "setup"),
    (PlotsOutput, "setup"),
    (CharactersOutput, "setup"),
    (BuildOutput, "setup"),
    (ModerationOutput, "moderate"),  # G9, D-57
])
def test_role_of_schema(schema, role):
    assert role_of_schema(schema) == role


def test_every_mapped_role_is_a_config_role():
    from writory.config import RoleModels

    assert set(ROLE_OF_SCHEMA.values()) <= set(RoleModels.model_fields)
