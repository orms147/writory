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


def assert_request_invalid(resp) -> None:
    assert resp.status_code == 422
    assert resp.json() == WritoryError(ErrorCode.REQUEST_INVALID).player_payload()


@pytest.mark.parametrize("step", ["settings", "plots"])
@pytest.mark.parametrize("body", [
    {"index": -1}, {"index": 3}, {"index": 99}, {"index": "hai"}, {"index": None}, {},
    {"index": 1, "title": "tự viết bối cảnh"},  # trình duyệt chỉ gửi số thứ tự
])
def test_option_index_must_be_0_to_2(client, step, body):
    assert_request_invalid(client.put(f"/setup/s1/{step}", json=body))


@pytest.mark.parametrize("body", [
    {"index": 3},
    {"index": -1, "name": "Lục Vân"},
    {"index": 0, "name": 5},
    {"index": 0, "hidden_secret": "x"},
])
def test_character_choice_body_is_checked(client, body):
    assert_request_invalid(client.put("/setup/s1/characters", json=body))


@pytest.mark.parametrize("body", [
    {"tags": {"genre": ""}, "length_level": "short"},
    {"tags": {"genre": "kiếm hiệp" * 20}, "length_level": "short"},
    {"tags": {"genre": "kiếm hiệp"}, "length_level": "khong-co"},
    {"tags": {"genre": "kiếm hiệp"}},
    {"tags": {"genre": "kiếm hiệp"}, "length_level": "short", "pov": "many"},
    {"tags": {"genre": "kiếm hiệp"}, "length_level": "short",
     "naming": {"names": "latin", "places": "hu_cau"}},
])
def test_start_body_is_checked(client, body):
    assert_request_invalid(client.post("/setup", json=body))


def test_setup_routes_not_mounted_when_dev_flag_off():
    app = create_app(dev_settings(dev=False), health_checks={"neo4j": ok}, config=CFG)
    assert not any(p.startswith("/setup") for p in app.openapi()["paths"])
    with TestClient(app) as c:
        assert c.post("/setup", json={"tags": {"genre": "x"}, "length_level": "short"}
                      ).status_code == 404


def test_story_brief_has_only_what_the_player_chose():
    choices = StoryChoices(tags=StoryTags(genre="kiếm hiệp", era="cổ đại", voice=None,
                                          darkness="vừa"),
                           length_level="short", naming=Naming(names="han_viet", places="hu_cau"))
    brief = story_brief(
        choices, SettingOption(title="Bến Lạc Hà", intro="Trấn nhỏ ven sông."),
        PlotOption(title="Thanh kiếm của cha", summary="Lần theo cái chết của cha."),
        CharacterOption(name="Lục Thanh Vân", personality="Ít nói.", backstory="Con thợ rèn."),
    )
    for part in ("kiếm hiệp", "cổ đại", "vừa", "Hán Việt", "hư cấu", "Bến Lạc Hà",
                 "Trấn nhỏ ven sông.", "Thanh kiếm của cha", "Lần theo cái chết của cha.",
                 "Lục Thanh Vân", "Ít nói.", "Con thợ rèn."):
        assert part in brief, part
    assert "None" not in brief and "giọng văn" not in brief  # tag trống thì bỏ
