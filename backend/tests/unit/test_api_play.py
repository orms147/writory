"""Route chơi (D-46): phần không cần Docker. Luồng đủ trên Postgres + Neo4j:
tests/graph/test_play_api.py."""

import json

import pytest
from fastapi.testclient import TestClient

from tests.api_fixtures import dev_settings
from writory.api import create_app, deps
from writory.api.play import action_text, choice_from_record, choice_record, sse_event
from writory.config import load_config
from writory.db import StoryRecord
from writory.errors import ErrorCode, WritoryError
from writory.pipeline.choices import Choice, LieEffect
from writory.pipeline.events import ChoicesReady, SceneReady, error_event, stage

CFG = load_config()
LIE = Choice(id="choice-0123456789ab", kind="dialogue", tone="lie",
             text="Nói với Lan rằng kiếm đã gửi cai Khải giữ.", listeners=("lan",),
             about=("sword",), lie=LieEffect("Thanh Sương đang ở chỗ cai Khải", ("lan",)),
             feeling=None)
INNER = Choice(id="choice-ba9876543210", kind="inner", tone=None,
               text="Thầm nghĩ Lan biết nhiều hơn cô nói.", listeners=(), about=("lan",),
               lie=None, feeling="nghi ngờ")


async def ok() -> bool:
    return True


@pytest.fixture
def client():
    app = create_app(dev_settings(), health_checks={"neo4j": ok}, config=CFG)
    # Không Docker: dependency chạy trước khi kiểm thân yêu cầu, nên thay cả truyện.
    app.dependency_overrides[deps.get_pg_conn] = lambda: None
    app.dependency_overrides[deps.get_owned_story] = (
        lambda story_id: StoryRecord(story_id, "dev", "short", 3))
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.mark.parametrize("choice", [LIE, INNER])
def test_choice_record_roundtrip(choice):
    record = choice_record(choice)
    assert json.loads(json.dumps(record)) == record  # lưu được thành jsonb
    assert choice_from_record(record) == choice


def test_action_text_carries_structured_data_for_the_writer():
    lie = action_text(LIE)
    assert LIE.text in lie and "Lời thoại" in lie and "nói dối" in lie
    assert "Thanh Sương đang ở chỗ cai Khải" in lie
    inner = action_text(INNER)
    assert INNER.text in inner and "Nội tâm" in inner and "nghi ngờ" in inner
    assert "lan" not in lie.replace("Lan", "")  # không có id nút


def test_sse_event_is_named_by_type_and_has_no_ids():
    events = [stage("write", scene=1, attempt=1), SceneReady(scene=1, text="Mưa."),
              ChoicesReady(chapter=4, choices=[LIE.for_player(), INNER.for_player()]),
              error_event(WritoryError(ErrorCode.LLM_UNAVAILABLE, detail="HTTP 502 xyz"))]
    for event in events:
        sse = sse_event(event)
        assert sse.event == event.type and sse.id is None
        assert sse.data == event
    dumped = sse_event(events[2]).data.model_dump_json()
    for server_only in ('"listeners"', '"told_to"', '"lie":', '"about"', '"feeling"', '"lan"',
                        "sword"):
        assert server_only not in dumped
    assert "xyz" not in sse_event(events[3]).data.model_dump_json()


def assert_request_invalid(resp, fields: list[str]) -> None:
    assert resp.status_code == 422
    expected = WritoryError(ErrorCode.REQUEST_INVALID, fields=fields).player_payload()
    assert resp.json() == expected


@pytest.mark.parametrize(("body", "fields"), [
    ({"choice_id": "lan"}, ["choice_id"]),
    ({"choice_id": "choice-XYZ"}, ["choice_id"]),
    ({"choice_id": "choice-0123456789ab", "kind": "action"}, ["kind"]),
    ({"choice_id": 7}, ["choice_id"]),
    ({}, ["choice_id"]),
])
def test_choice_body_is_checked(client, body, fields):
    assert_request_invalid(client.post("/stories/s1/choice", json=body), fields)


@pytest.mark.parametrize(("body", "fields"), [
    ({"text": 5}, ["text"]), ({"text": ["a"]}, ["text"]), ({}, ["text"]),
    ({"text": "a", "label": "x"}, ["label"]),
])
def test_custom_action_body_is_checked(client, body, fields):
    assert_request_invalid(client.post("/stories/s1/action", json=body), fields)


def test_play_routes_not_mounted_when_dev_flag_off():
    app = create_app(dev_settings(dev=False), health_checks={"neo4j": ok}, config=CFG)
    assert not any(p.startswith("/stories") for p in app.openapi()["paths"])
    with TestClient(app) as c:
        for method, path in (("POST", "/stories/s1/chapters/next"), ("GET", "/stories/s1"),
                             ("POST", "/stories/s1/choices"), ("GET", "/stories/s1/chapters/1")):
            assert c.request(method, path).status_code == 404
        assert c.post("/stories/s1/choice", json={"choice_id": "choice-0123456789ab"}
                      ).status_code == 404
        assert c.post("/stories/s1/action", json={"text": "Tôi đi."}).status_code == 404
