"""Tạo 3 lựa chọn cuối chương (design §6.2 bước 6, §6.3; D-37). G1: model chỉ nhận player_view."""

import json
from pathlib import Path

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
    draft("action", tone="truth"),  # sắc thái chỉ cho lời thoại
    draft("inner", about=["p1"]),  # nội tâm thiếu cảm xúc
    draft("action", text="  "),
])
def test_choice_fields_must_match_kind(bad):
    with pytest.raises(ValidationError):
        ChoicesOutput.model_validate({"choices": [bad, draft(), draft("inner", about=["p1"],
                                                                     feeling="lo")]})


def test_a_dialogue_without_listeners_passes_the_schema_so_resolve_can_drop_just_that_choice():
    """D-123: người nghe ẩn danh không có mã trong sổ tay nên model không có gì để điền. Trước đây
    pydantic bỏ cả bộ; nay `_resolve` bỏ riêng lựa chọn đó (D-121)."""
    out = ChoicesOutput.model_validate({"choices": [
        draft(), draft("dialogue", tone="silence"), draft("dialogue", tone="lie", lie_content="x")]})
    assert out.choices[1].listeners == [] and out.choices[2].tone == "lie"


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


FIXTURE = Path(__file__).parents[1] / "fixtures" / "llm" / "choices_unknown_ref_run_long_ky_ao_hanh_trinh_1.json"
FIXTURE_SILENCE = FIXTURE.with_name("choices_silence_no_listener_run_long_after_ky_ao_ch10.json")
GHOST = "mã người dẫn đầu chưa có trong sổ tay"  # chuỗi ref sai nguyên văn của model ở ch14


def _fixture(name: str, refs: dict[str, str]) -> str:
    """Mẫu trả lời dựng lại từ lỗi của lượt long-ky-ao-hanh-trinh-1 (thân trả lời không được lưu);
    `{PROTAGONIST_REF}` và `{NON_CHARACTER_REF}` điền bằng mã thật của sổ tay thử."""
    raw = json.dumps(json.loads(FIXTURE.read_text(encoding="utf-8"))[name], ensure_ascii=False)
    return (raw.replace("{PROTAGONIST_REF}", refs["Trần Minh"])
            .replace("{NON_CHARACTER_REF}", refs["lá thư gấp bốn"]))


async def test_a_ref_outside_the_notebook_is_dropped_from_the_choice_not_the_whole_set(caplog):
    """Hồi quy long-ky-ao-hanh-trinh-1 ch14: model gọi "người dẫn đầu" bằng một mã không có trong sổ
    tay; truyện dừng hẳn vì cả bộ bị từ chối hai lần hai lượt. Bỏ riêng tham chiếu đó (G1: bỏ là
    đúng hướng, không đoán thêm)."""
    refs = _refs_by_text()
    llm = ScriptedLLM([_fixture("second_round_unknown_ref", refs)])
    with caplog.at_level("WARNING"):
        choices = await _make(llm)
    # Lời thoại không còn người nghe nào thì bỏ cả lựa chọn (bất biến của ChoiceDraft, D-121); hai
    # lựa chọn còn lại đủ MIN_CHOICES và MIN_KINDS nên không phải thử lại.
    assert len(llm.calls) == 1 and [c.kind for c in choices] == ["action", "inner"]
    assert choices[1].about == ("minh",)
    assert GHOST not in caplog.text and "bỏ 1 tham chiếu ngoài sổ tay, 1 lựa chọn" in caplog.text  # đếm, không ghi chữ


async def test_a_listener_that_is_not_a_character_is_dropped_too():
    refs = _refs_by_text()
    # Lời thoại mất hết người nghe thì bỏ cả lựa chọn; nội tâm có thể hướng tới một đồ vật nên giữ.
    choices = await _make(ScriptedLLM([_fixture("first_round_listener_not_a_character", refs)]))
    assert [c.kind for c in choices] == ["action", "inner"] and len(choices[1].about) == 1


async def test_the_protagonist_is_never_a_listener():
    """D-121 (review): nhân vật chính không thể là người nghe lời mình nói."""
    refs = _refs_by_text()
    me = refs["Trần Minh"]
    only_me = _reply(refs, **{"1": {"listeners": [me]}})
    choices = await _make(ScriptedLLM([only_me]))
    assert [c.kind for c in choices] == ["action", "inner"]  # lời dối chỉ có mình nghe: bỏ
    both = _reply(refs, **{"1": {"listeners": [me, refs["Phạm Thị Lan"]]}})
    kept = await _make(ScriptedLLM([both]))
    assert kept[1].listeners == ("lan",) and kept[1].lie.told_to == ("lan",)


async def test_a_truthful_line_with_no_listener_left_is_dropped_not_kept_empty():
    refs = _refs_by_text()
    truth = _reply(refs, **{"1": {"tone": "truth", "lie_content": None, "listeners": [GHOST]}})
    choices = await _make(ScriptedLLM([truth]))
    assert all(c.kind != "dialogue" for c in choices) and len(choices) == 2


async def test_a_lie_with_no_valid_listener_is_dropped_because_nobody_hears_it():
    refs = _refs_by_text()
    bad = _reply(refs, **{"1": {"listeners": [GHOST]}})
    choices = await _make(ScriptedLLM([bad]))
    assert [c.kind for c in choices] == ["action", "inner"] and all(c.lie is None for c in choices)


async def test_an_inner_choice_with_no_valid_about_is_dropped():
    bad = _reply(_refs_by_text(), **{"2": {"about": ["m999"]}})
    choices = await _make(ScriptedLLM([bad]))
    assert [c.kind for c in choices] == ["action", "dialogue"]


async def test_an_action_keeps_its_text_and_loses_only_the_unknown_ref():
    refs = _refs_by_text()
    bad = _reply(refs, **{"0": {"about": [refs["Phạm Thị Lan"], "m999"]}})
    choices = await _make(ScriptedLLM([bad]))
    assert choices[0].about == ("lan",) and choices[0].text == "Ra bến tìm cai Khải."


async def test_a_dropped_ref_never_becomes_a_node_id_in_what_the_player_gets():
    refs = _refs_by_text()
    choices = await _make(ScriptedLLM([_fixture("second_round_unknown_ref", refs)]))
    ids = {i for c in choices for i in (*c.listeners, *c.about)}
    assert ids <= {e.id for e in VIEW.entries}  # G1: chỉ id có trong player_view
    assert GHOST not in json.dumps([c.for_player().model_dump() for c in choices],
                                   ensure_ascii=False)


async def test_a_set_that_cannot_be_saved_is_retried_with_a_fixed_note_and_then_succeeds():
    refs = _refs_by_text()
    hopeless = _reply(refs, **{"0": {"kind": "inner", "feeling": "lo", "about": [GHOST]},
                               "1": {"listeners": [GHOST]}, "2": {"about": ["m999"]}})
    llm = ScriptedLLM([hopeless, _reply(refs)])
    choices = await _make(llm)
    assert len(choices) == 3 and len(llm.calls) == 2
    first, second = llm.calls
    assert len(second) == len(first) + 1
    note = second[-1]
    assert note.role == "user" and "m1, m2" in note.content
    assert GHOST not in note.content and "m999" not in note.content  # không dội lại chữ của model
    assert [m.content for m in second[:-1]] == [m.content for m in first]


async def test_a_set_that_cannot_be_saved_twice_is_still_the_old_error():
    refs = _refs_by_text()
    hopeless = _reply(refs, **{"0": {"kind": "inner", "feeling": "lo", "about": [GHOST]},
                               "1": {"listeners": [GHOST]}, "2": {"about": ["m999"]}})
    llm = ScriptedLLM([hopeless, hopeless])
    with pytest.raises(WritoryError) as exc:
        await _make(llm)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == 1 + RETRIES.extract_schema_retry


async def test_a_set_with_fewer_than_two_kinds_after_dropping_is_not_accepted():
    refs = _refs_by_text()
    # Hai lựa chọn còn lại cùng loại hành động: dưới ngưỡng MIN_KINDS, phải thử lại.
    bad = _reply(refs, **{"1": {"kind": "action", "tone": None, "lie_content": None,
                                "listeners": []},
                          "2": {"about": ["m999"]}})
    with pytest.raises(WritoryError):
        await _make(ScriptedLLM([bad, bad]))


async def test_leak_check_still_runs_on_a_salvaged_set():
    """G2 không đổi: bộ đã cứu vẫn bị dò lộ trên chữ lựa chọn."""
    refs = _refs_by_text()
    leaky = json.loads(_fixture("second_round_unknown_ref", refs))
    leaky["choices"][0]["text"] = "Lan là gián điệp, đi báo cho cai Khải."
    with pytest.raises(WritoryError) as exc:
        await _make(ScriptedLLM([json.dumps(leaky, ensure_ascii=False)]))
    assert exc.value.code is ErrorCode.CHOICES_LEAK_BLOCKED


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


async def test_the_real_rejected_body_of_ky_ao_ch10_now_gives_two_choices_not_an_error():
    """Thân THẬT bị từ chối ở lượt long-after-ky-ao ch10 (rejected.jsonl, D-115): lời thoại im lặng
    không người nghe làm pydantic bỏ cả bộ, hai lần liền, rồi cả lượt chạy tốn một lượt bấm thử lại."""
    real = json.loads(FIXTURE_SILENCE.read_text(encoding="utf-8"))["real_body"]
    ChoicesOutput.model_validate(real)  # trước đây: choices.1: value_error
    refs = _refs_by_text()
    raw = json.dumps(real, ensure_ascii=False).replace('"m30"', json.dumps(refs["Phạm Thị Lan"])
                                                       ).replace('"m31"', json.dumps(refs["Trần Minh"]))
    llm = ScriptedLLM([raw])
    choices = await _make(llm)
    assert len(llm.calls) == 1 and [c.kind for c in choices] == ["action", "inner"]
    assert choices[0].about == ("lan",) and choices[1].about == ("minh",)
