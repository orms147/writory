"""Tạo 3 lựa chọn cuối chương (design §6.2 bước 6, §6.3; D-37). G1: model chỉ nhận player_view."""

import json

import pytest
from pydantic import ValidationError

from tests.pipeline_fixtures import PLAN, SAMPLE, TRUTH_AT_4, ScriptedLLM
from writory.config import load_config
from writory.errors import ErrorCode, WritoryError
from writory.graph import public_entries
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.choices import (
    STALLED_NOTE,
    SYSTEM_PROMPT,
    TONE_GUIDANCE,
    ChoicesOutput,
    build_choice_messages,
    make_choices,
)
from writory.pipeline.story_plan import StoryPlan
from writory.safety.wrap import OPEN_TAG_START

RETRIES = load_config().limits.retries
STATE = OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= 3])
VIEW = player_view_of(STATE, 3, story_id="s")
SCENE = "Minh ngồi bên cửa sổ, nhìn xuống bến. Quán trà đầu bến hôm nay đóng cửa."


def draft(kind="action", **kw) -> dict:
    base = {"kind": kind, "text": "Làm gì đó.", "tone": None, "lie_content": None,
            "listeners": [], "about": [], "feeling": None}
    return base | kw


def test_exactly_three_choices_of_at_least_two_kinds():
    with pytest.raises(ValidationError):
        ChoicesOutput.model_validate({"choices": [draft(), draft()]})
    with pytest.raises(ValidationError):
        ChoicesOutput.model_validate({"choices": [draft(), draft(), draft()]})
    ChoicesOutput.model_validate({"choices": [
        draft(), draft(), draft("inner", about=["p1"], feeling="lo")]})


@pytest.mark.parametrize("bad", [
    draft("dialogue", listeners=["p1"]),  # lời thoại thiếu sắc thái
    draft("dialogue", tone="lie", listeners=["p1"]),  # nói dối thiếu nội dung
    draft("dialogue", tone="lie", lie_content="x"),  # nói dối không có người nghe
    draft("action", tone="truth"),  # sắc thái chỉ cho lời thoại
    draft("inner", about=["p1"]),  # nội tâm thiếu cảm xúc
    draft("action", text="  "),
])
def test_choice_fields_must_match_kind(bad):
    with pytest.raises(ValidationError):
        ChoicesOutput.model_validate({"choices": [bad, draft(), draft("inner", about=["p1"],
                                                                     feeling="lo")]})


def test_context_is_player_view_only_with_public_codes():
    """G1: chỉ sổ tay dựng từ player_view (mã công khai của public_entries, D-40) và cảnh vừa
    hiện; id lớp truth của nút không vào prompt."""
    messages, refs = build_choice_messages(VIEW, protagonist_id="minh", last_scene_text=SCENE)
    system, user = messages
    assert system.role == "system" and system.content.startswith(SYSTEM_PROMPT[:60])
    text = "\n".join(m.content for m in messages)
    assert refs == {ref: e.id for ref, e in public_entries(VIEW)}
    for entry in VIEW.entries:
        assert f": {entry.text}" in user.content
    assert all(t not in text for t in TRUTH_AT_4)
    assert all(f"[{e.id}]" not in text and f" {e.id} " not in text for e in VIEW.entries)
    me = next(ref for ref, e in public_entries(VIEW) if e.id == "minh")
    assert f"Nhân vật chính: [{me}] Trần Minh" in user.content
    assert OPEN_TAG_START not in system.content and user.content.count(OPEN_TAG_START) == 2


def _reply(refs_by_text, **override) -> str:
    lan = refs_by_text["Phạm Thị Lan"]
    choices = [
        draft(text="Ra bến tìm cai Khải."),
        draft("dialogue", text="Bảo Lan rằng mình chưa từng thấy lá thư nào.", tone="lie",
              lie_content="Minh chưa từng thấy lá thư nào", listeners=[lan]),
        draft("inner", text="Thầm thương Lan.", about=[lan], feeling="thương"),
    ]
    return json.dumps({"choices": [c | override.get(str(i), {}) for i, c in enumerate(choices)]},
                      ensure_ascii=False)


def _refs_by_text():
    _, refs = build_choice_messages(VIEW, protagonist_id="minh", last_scene_text=SCENE)
    text = {e.id: e.text for e in VIEW.entries}
    return {text[eid]: ref for ref, eid in refs.items()}


async def _make(llm, *, brief: str = "", plan: StoryPlan = PLAN, stalled: bool = False):
    return await make_choices(
        llm, "m", view=VIEW, protagonist_id="minh", last_scene_text=SCENE,
        truth_names=STATE.named_nodes(), plan=plan, retries=RETRIES, story_brief=brief,
        stalled=stalled,
    )


def _plan(fact_id: str, **change) -> StoryPlan:
    """PLAN với một bí mật đổi vài trường (khoảng lộ, `protects`)."""
    return StoryPlan.model_validate({**PLAN.model_dump(), "secrets": [
        {**s.model_dump(), **change} if s.fact_id == fact_id else s.model_dump()
        for s in PLAN.secrets]})


async def test_refs_resolve_to_entity_ids():
    choices = await _make(ScriptedLLM([_reply(_refs_by_text())]))
    lie = choices[1]
    assert lie.lie is not None and lie.lie.told_to == ("lan",) and lie.listeners == ("lan",)
    assert choices[2].feeling == "thương" and choices[2].about == ("lan",)
    assert len({c.id for c in choices}) == 3
    player = choices[1].for_player()
    assert player.kind == "dialogue" and player.tone == "lie" and player.kind_label
    assert "lan" not in player.model_dump_json().replace("Lan", "")  # không lộ id


async def test_unknown_ref_is_bad_response_and_retried_once():
    refs = _refs_by_text()
    bad = _reply(refs, **{"2": {"about": ["m999"]}})
    llm = ScriptedLLM([bad, bad])
    with pytest.raises(WritoryError) as exc:
        await _make(llm)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == 1 + RETRIES.extract_schema_retry


async def test_listener_must_be_a_character():
    refs = _refs_by_text()
    letter = refs["lá thư gấp bốn"]
    bad = _reply(refs, **{"1": {"listeners": [letter]}})
    with pytest.raises(WritoryError):
        await _make(ScriptedLLM([bad, bad]))


async def test_leak_in_lie_content_blocks_all_choices():
    """G2: mọi chữ có thể tới người chơi (kể cả nội dung lời nói dối sẽ vào sổ tay) đều được dò."""
    refs = _refs_by_text()
    leak = _reply(refs, **{"1": {"lie_content": "Lan là gián điệp"}})
    with pytest.raises(WritoryError) as exc:
        await _make(ScriptedLLM([leak]))
    assert exc.value.code is ErrorCode.CHOICES_LEAK_BLOCKED
    assert "gián điệp" not in str(exc.value)


async def test_name_from_setup_text_is_not_a_leak_in_choices():
    """D-52: tên người chơi đã đọc lúc khởi tạo (thiết lập truyện) là chữ đã thấy, kể cả tên được
    kế hoạch bảo vệ (D-61); tên bị bảo vệ mà người chơi chưa thấy vẫn bị dò."""
    named = _reply(_refs_by_text(), **{"0": {"text": "Xuống bến tìm Lý Thất."}})
    plan = _plan("f_lan_killed_gu", protects=["ly_that"])
    with pytest.raises(WritoryError) as exc:
        await _make(ScriptedLLM([named]), plan=plan)
    assert exc.value.code is ErrorCode.CHOICES_LEAK_BLOCKED
    choices = await _make(ScriptedLLM([named]), plan=plan,
                          brief="Bối cảnh: bến Sương, lái đò Lý Thất.")
    assert choices[0].text == "Xuống bến tìm Lý Thất."


async def test_unprotected_truth_name_is_not_a_leak_in_choices():
    """D-61: chỉ tên bí mật bị cấm. Lý Thất chưa hé lộ ở chương 3 nhưng không được bảo vệ."""
    named = _reply(_refs_by_text(), **{"0": {"text": "Xuống bến tìm Lý Thất."}})
    choices = await _make(ScriptedLLM([named]))
    assert choices[0].text == "Xuống bến tìm Lý Thất."


async def test_choices_block_every_secret_not_in_player_view_regardless_of_window():
    """D-61, `player_path`: bí mật đã tới khoảng lộ (từ chương 3) mà cảnh chưa hé lộ vẫn bị dò
    trên chữ lựa chọn; trước đây chỉ dò khi chương < `reveal_from_chapter`."""
    leak = _reply(_refs_by_text(), **{"0": {"text": "Hỏi thẳng Lan có phải gián điệp không."}})
    with pytest.raises(WritoryError) as exc:
        await _make(ScriptedLLM([leak]), plan=_plan("f_lan_spy", reveal_from_chapter=3))
    assert exc.value.code is ErrorCode.CHOICES_LEAK_BLOCKED


def test_prompt_asks_to_vary_dialogue_tone_when_the_scene_fits():
    """Lần chạy tu-tien-1 (notes.md mục 6): cả 6 chương, mọi lời thoại đều "nói thật". Đề khuyến
    khích nói dối hoặc im lặng khi hợp cảnh; code không ép (design §6.2 chỉ đòi tối thiểu 2 loại)."""
    [system, _], _ = build_choice_messages(VIEW, protagonist_id="minh", last_scene_text=SCENE)
    assert TONE_GUIDANCE in system.content
    for word in ('"lie"', '"silence"', "nói thật không phải mặc định", "hợp cảnh"):
        assert word in TONE_GUIDANCE
    lan = _refs_by_text()["Phạm Thị Lan"]
    honest = _reply(_refs_by_text(), **{"1": {"tone": "truth", "lie_content": None,
                                               "listeners": [lan]}})
    ChoicesOutput.model_validate_json(honest)  # nói thật vẫn hợp lệ: không ép bằng code


# --- lựa chọn khi truyện đứng yên (D-98) --------------------------------------------------------
# Hồi quy long-tu-tien-1: ba lựa chọn cuối chương 10, 14, 15 đều là "giữ yên, dò thêm, tự nhắc mình
# thận trọng". Cờ "đứng yên" chỉ là đúng/sai, không mang tên nơi chốn (G1).


def _user(stalled: bool) -> str:
    kwargs = {"stalled": stalled} if stalled else {}
    [_, user], _ = build_choice_messages(VIEW, protagonist_id="minh", last_scene_text=SCENE, **kwargs)
    return user.content


def test_stalled_story_asks_for_a_choice_that_breaks_the_standoff():
    text = _user(True)
    assert "thế giằng co" in text and "nhất một" in text and "không chỉ giữ yên" in text


def test_story_that_moves_gets_the_same_prompt_as_before():
    assert "thế giằng co" not in _user(False)
    assert _user(False) == "\n".join(
        m.content for m in build_choice_messages(VIEW, protagonist_id="minh",
                                                 last_scene_text=SCENE)[0][1:])


def test_the_stalled_note_is_fixed_code_text_and_the_rest_of_the_prompt_is_unchanged():
    """G1: cờ chỉ thêm đúng một đoạn chữ cố định của code, không tên, id hay chữ lớp truth."""
    assert STALLED_NOTE in _user(True)
    squash = lambda t: "".join(t.split())
    assert squash(_user(True).replace(STALLED_NOTE, "")) == squash(_user(False))
    assert "{" not in STALLED_NOTE and OPEN_TAG_START not in STALLED_NOTE  # không có chỗ điền chữ


async def test_make_choices_passes_the_flag_into_the_prompt():
    llm = ScriptedLLM([_reply(_refs_by_text())])
    await _make(llm, stalled=True)
    assert "thế giằng co" in llm.calls[0][-1].content


# --- đề lựa chọn ghi đè cho bộ đo (D-109) -------------------------------------------------------


def test_choices_system_prompt_can_be_replaced_without_touching_the_user_message():
    base, _ = build_choice_messages(VIEW, protagonist_id="minh", last_scene_text=SCENE)
    new, _ = build_choice_messages(VIEW, protagonist_id="minh", last_scene_text=SCENE,
                                   system_prompt="ĐỀ LỰA CHỌN BIẾN THỂ")
    assert new[0].content.startswith("ĐỀ LỰA CHỌN BIẾN THỂ") and SYSTEM_PROMPT[:40] not in new[0].content
    assert new[1].content == base[1].content  # sổ tay và cảnh vẫn bọc như cũ (G4)
    assert OPEN_TAG_START in new[1].content


async def test_make_choices_sends_the_replaced_system_prompt_and_g1_still_holds():
    llm = ScriptedLLM([_reply(_refs_by_text())])
    await make_choices(
        llm, "m", view=VIEW, protagonist_id="minh", last_scene_text=SCENE,
        truth_names=STATE.named_nodes(), plan=PLAN, retries=RETRIES, story_brief="",
        system_prompt="ĐỀ LỰA CHỌN BIẾN THỂ")
    sent = "\n".join(m.content for m in llm.calls[0])
    assert llm.calls[0][0].content.startswith("ĐỀ LỰA CHỌN BIẾN THỂ")
    for secret in TRUTH_AT_4:  # lớp truth vẫn không vào đề tạo lựa chọn
        assert secret not in sent
