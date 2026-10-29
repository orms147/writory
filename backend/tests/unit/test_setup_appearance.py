"""Ngoại hình nhân vật và cảnh sắc nơi chốn sinh ở bước khởi tạo (D-118; nền cho xuất kịch bản video).
Là lớp `truth`: thuộc tính tuỳ chọn `appearance` (Character) và `visual` (Location); thư mục khởi tạo
cũ không có vẫn dùng được. FakeLLM, không mạng."""

import copy
import json

from tests.unit.test_pipeline_setup import CFG, CHOICES, FIXTURE, PC, PLOT, SETTING, SHORT_LEVEL
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.fake import FakeLLM
from writory.pipeline.setup import (
    BUILD_TASK,
    PROMPT_VERSION,
    PROTAGONIST_ID,
    BuildOutput,
    OutCharacter,
    OutLocation,
    OutNamed,
    build_story,
    to_story_setup,
)

LOOK_NPC = "Ngoài ba mươi, vai rộng, tóc búi cao, áo vải chàm sờn vai, sẹo mảnh dưới mắt trái."
LOOK_PC = "Hai mươi mốt, gầy cao, mặt xương, tóc đen buộc gọn, áo thợ rèn cháy xém, bàn tay chai."
LOOK_PLACE = "Ánh đèn dầu vàng đục, gỗ ẩm mục, mùi cá khô và khói."


def _with_looks(*, npc: str = LOOK_NPC, pc: str = LOOK_PC, place: str = LOOK_PLACE) -> dict:
    data = copy.deepcopy(FIXTURE)
    data["characters"] = [c | {"appearance": npc} for c in data["characters"]]
    data["locations"] = [x | {"visual": place} for x in data["locations"]]
    data["protagonist_appearance"] = pc
    return data


def _setup(data: dict):
    return to_story_setup(BuildOutput.model_validate(data), protagonist=PC, commit_id="setup-c0",
                          level=SHORT_LEVEL)


def _props(setup) -> dict[str, dict]:
    return {n.id: n.props for n in setup.package.nodes}


def test_old_reply_without_the_new_fields_is_still_valid_and_adds_no_props():
    out = BuildOutput.model_validate(FIXTURE)
    assert out.protagonist_appearance == ""
    assert all(c.appearance == "" for c in out.characters)
    assert all(x.visual == "" for x in out.locations)
    props = _props(_setup(FIXTURE))
    assert not any("appearance" in p or "visual" in p for p in props.values())


def test_looks_become_optional_props_on_characters_locations_and_the_protagonist():
    out = BuildOutput.model_validate(_with_looks())
    setup = _setup(_with_looks())
    props = _props(setup)
    for c in out.characters:
        assert props[c.id]["appearance"] == LOOK_NPC
    for x in out.locations:
        assert props[x.id]["visual"] == LOOK_PLACE
    assert props[PROTAGONIST_ID]["appearance"] == LOOK_PC
    # Người chơi đã chọn tên, tính cách, quá khứ của nhân vật chính: ngoại hình không đổi chúng.
    assert props[PROTAGONIST_ID]["personality"] == PC.personality
    assert props[PROTAGONIST_ID]["user_authored"] is True
    # Phe phái và đồ vật không có cảnh sắc.
    for x in (*out.factions, *out.items):
        assert "visual" not in props[x.id] and "appearance" not in props[x.id]


def test_blank_looks_are_dropped_not_stored_as_empty_strings():
    props = _props(_setup(_with_looks(npc="  ", pc="\n", place=" ")))
    assert not any("appearance" in p or "visual" in p for p in props.values())


def test_looks_are_trimmed_to_a_single_line():
    props = _props(_setup(_with_looks(npc="  Cao gầy,\n  tóc bạc.  ")))
    npc = next(p for i, p in props.items() if i != PROTAGONIST_ID and "appearance" in p)
    assert npc["appearance"] == "Cao gầy, tóc bạc."


def test_schema_requires_the_new_fields_so_the_model_must_answer_them():
    schema = BuildOutput.model_json_schema()
    assert "protagonist_appearance" in schema["required"]
    assert "appearance" in OutCharacter.model_json_schema()["required"]
    assert "visual" in OutLocation.model_json_schema()["required"]
    assert "visual" not in OutNamed.model_json_schema()["properties"]
    assert schema["$defs"]["OutLocation"]["properties"]["visual"]["type"] == "string"


def test_prompt_version_and_task_ask_for_looks_in_vietnamese_with_the_required_parts():
    assert PROMPT_VERSION == "setup-10"
    for phrase in ("appearance", "visual", "protagonist_appearance", "tuổi", "vóc dáng",
                   "khuôn mặt", "tóc", "trang phục", "dấu hiệu nhận diện", "ánh sáng", "chất liệu",
                   "không khí"):
        assert phrase in BUILD_TASK, phrase


async def test_build_story_stores_looks_and_leaves_the_plan_alone():
    old = await build_story(CHOICES, SETTING, PLOT, PC, llm=FakeLLM.scripted([json.dumps(FIXTURE)]),
                            config=CFG, commit_id="c0")
    new = await build_story(CHOICES, SETTING, PLOT, PC,
                            llm=FakeLLM.scripted([json.dumps(_with_looks(), ensure_ascii=False)]),
                            config=CFG, commit_id="c0")
    assert new.plan == old.plan  # story_plan không đổi
    assert _props(new)[PROTAGONIST_ID]["appearance"] == LOOK_PC


async def test_the_repair_turn_hands_back_the_looks_it_already_wrote():
    data = _with_looks()
    bad = copy.deepcopy(data)
    bad["secrets"] = [bad["secrets"][0] | {"fact_id": "f_khong_co"}, bad["secrets"][1]]
    llm = FakeLLM.scripted([json.dumps(bad, ensure_ascii=False), json.dumps(data, ensure_ascii=False)])
    result = await build_story(CHOICES, SETTING, PLOT, PC, llm=llm, config=CFG, commit_id="c0")
    repair_user = "\n".join(m.content for m in llm.calls[1] if m.role == "user")
    assert LOOK_NPC in repair_user and LOOK_PC in repair_user
    assert _props(result)[PROTAGONIST_ID]["appearance"] == LOOK_PC


def test_looks_never_reach_the_player_view():
    setup = _setup(_with_looks())
    view = player_view_of(OverlayState(EmptyState(), [setup.package]), 0)
    blob = repr(view)
    for text in (LOOK_NPC, LOOK_PC, LOOK_PLACE):
        assert text not in blob
