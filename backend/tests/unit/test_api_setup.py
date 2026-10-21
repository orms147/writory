"""API khởi tạo (D-45): kiểm đầu vào trước khi chạm Postgres hay model. Không Docker.

Luồng đủ trên Postgres + Neo4j: tests/graph/test_setup_api.py.
"""

import pytest
from fastapi.testclient import TestClient

from tests.api_fixtures import dev_settings
from writory.api import create_app, deps
from writory.config import load_config
from writory.errors import ErrorCode, WritoryError
from writory.pipeline.setup import (
    CharacterOption,
    Naming,
    PlotOption,
    SettingOption,
    StoryChoices,
    StoryTags,
    story_brief,
)

CFG = load_config()


async def ok() -> bool:
    return True


@pytest.fixture
def client():
    app = create_app(dev_settings(), health_checks={"neo4j": ok}, config=CFG)
    app.dependency_overrides[deps.get_pg_conn] = lambda: None  # không được dùng tới
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def assert_request_invalid(resp, fields: set[str]) -> None:
    """422 REQUEST_INVALID: câu chung, kèm đúng các trường sai (G12), không có đầu vào."""
    assert resp.status_code == 422
    payload = resp.json()
    expected = WritoryError(ErrorCode.REQUEST_INVALID).player_payload()
    assert (payload["code"], payload["message"]) == (expected["code"], expected["message"])
    assert set(payload) == {"code", "message", "fields"}
    assert set(payload["fields"]) == fields


@pytest.mark.parametrize("step", ["settings", "plots"])
@pytest.mark.parametrize(("body", "fields"), [
    ({"index": -1}, {"index"}), ({"index": 3}, {"index"}), ({"index": 99}, {"index"}),
    ({"index": "hai"}, {"index"}), ({"index": None}, {"index"}), ({}, {"index"}),
    ({"index": 1, "title": "tự viết bối cảnh"}, {"title"}),  # trình duyệt chỉ gửi số thứ tự
])
def test_option_index_must_be_0_to_2(client, step, body, fields):
    assert_request_invalid(client.put(f"/setup/s1/{step}", json=body), fields)


@pytest.mark.parametrize(("body", "fields"), [
    ({"index": 3}, {"index"}),
    ({"index": -1, "name": "Lục Vân"}, {"index"}),
    ({"index": 0, "name": 5}, {"name"}),
    ({"index": 0, "hidden_secret": "x"}, {"hidden_secret"}),
])
def test_character_choice_body_is_checked(client, body, fields):
    assert_request_invalid(client.put("/setup/s1/characters", json=body), fields)


@pytest.mark.parametrize(("body", "fields"), [
    ({"tags": {"genre": ""}, "length_level": "short"}, {"tags.genre"}),
    ({"tags": {"genre": "kiếm hiệp" * 20}, "length_level": "short"}, {"tags.genre"}),
    ({"tags": {"genre": "kiếm hiệp"}, "length_level": "khong-co"}, {"length_level"}),
    ({"tags": {"genre": "kiếm hiệp"}}, {"length_level"}),
    ({"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "pov": "many"}, {"pov"}),
    ({"tags": {"genre": "kiếm hiệp"}, "length_level": "short",
      "naming": {"names": "latin", "places": "hu_cau"}}, {"naming.names"}),
    # Mức u tối là khoá trong config/moderation.yaml `darkness_levels` (D-67).
    ({"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "darkness_level": "rat-toi"},
     {"darkness_level"}),
    ({"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "darkness_level": 2},
     {"darkness_level"}),
    ({"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "darkness_level": "x" * 40},
     {"darkness_level"}),
    # Chữ tự do "mức độ u tối" không còn (D-67): gửi lên là sai dạng, không âm thầm bỏ qua.
    ({"tags": {"genre": "kiếm hiệp", "darkness": "vừa"}, "length_level": "short"},
     {"tags.darkness"}),
])
def test_start_body_is_checked(client, body, fields):
    assert_request_invalid(client.post("/setup", json=body), fields)


def test_setup_routes_not_mounted_when_dev_flag_off():
    app = create_app(dev_settings(dev=False), health_checks={"neo4j": ok}, config=CFG)
    assert not any(p.startswith("/setup") for p in app.openapi()["paths"])
    with TestClient(app) as c:
        assert c.post("/setup", json={"tags": {"genre": "x"}, "length_level": "short"}
                      ).status_code == 404


def test_story_brief_has_only_what_the_player_chose():
    choices = StoryChoices(tags=StoryTags(genre="kiếm hiệp", era="cổ đại", voice=None),
                           length_level="short", naming=Naming(names="han_viet", places="hu_cau"),
                           darkness_level="dark")
    brief = story_brief(
        choices, SettingOption(title="Bến Lạc Hà", intro="Trấn nhỏ ven sông."),
        PlotOption(title="Thanh kiếm của cha", summary="Lần theo cái chết của cha."),
        CharacterOption(name="Lục Thanh Vân", personality="Ít nói.", backstory="Con thợ rèn."),
        moderation=CFG.moderation,
    )
    for part in ("kiếm hiệp", "cổ đại", CFG.moderation.darkness_levels["dark"].label, "Hán Việt", "hư cấu", "Bến Lạc Hà",
                 "Trấn nhỏ ven sông.", "Thanh kiếm của cha", "Lần theo cái chết của cha.",
                 "Lục Thanh Vân", "Ít nói.", "Con thợ rèn."):
        assert part in brief, part
    assert "None" not in brief and "giọng văn" not in brief  # tag trống thì bỏ
