"""Mạch phải gỡ khai bí mật trả lời nó (`answered_by`, D-135): code dời khoảng gỡ về sau khoảng lộ của
bí mật ở bước dựng (`pipeline.setup`), không tốn lượt sửa; id lạ là lỗi, đi lượt sửa (D-54). FakeLLM,
không mạng."""

import copy
import html
import json
import logging

from tests.unit.test_pipeline_setup import (
    _ACCENTED,
    CFG,
    CHOICES,
    FIXTURE,
    PC,
    PLOT,
    SETTING,
    SHORT_LEVEL,
    _block,
)
from writory.llm.fake import FakeLLM
from writory.pipeline.setup import (
    BUILD_TASK,
    PROMPT_VERSION,
    REPAIR_INTRO,
    BuildOutput,
    OutThread,
    build_story,
    initial_problems,
    to_story_setup,
)
from writory.pipeline.story_plan import WindowShift
from writory.safety.wrap import CLOSE_TAG


def _data(windows: dict[str, tuple[int, int]] | None = None, **answers: list[str]) -> dict:
    """FIXTURE (câu trả lời cũ, không có `answered_by`), thêm `answered_by` cho mọi mạch (mặc định
    rỗng) và đổi khoảng dự kiến gỡ của vài mạch."""
    data = copy.deepcopy(FIXTURE)
    for t in data["threads"]:
        t["answered_by"] = answers.get(t["id"], [])
        if windows and t["id"] in windows:
            t["due_from_chapter"], t["due_to_chapter"] = windows[t["id"]]
    return data


def _dumps(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)


def _setup(data: dict):
    return to_story_setup(BuildOutput.model_validate(data), protagonist=PC, commit_id="c0",
                          level=SHORT_LEVEL)


def _node_window(setup, thread_id: str) -> tuple[int, int]:
    [node] = [n for n in setup.package.nodes if n.id == thread_id]
    return node.props["due_from_chapter"], node.props["due_to_chapter"]


def _plan_window(setup, thread_id: str) -> tuple[int, int]:
    t = setup.plan.thread(thread_id)
    return t.resolve_from_chapter, t.resolve_to_chapter


def test_schema_and_prompt_ask_for_the_link():
    assert PROMPT_VERSION == "setup-11"
    assert "answered_by" in OutThread.model_json_schema()["required"]  # JSON schema strict
    for phrase in ("`answered_by`", "`fact_id`", "`reveal_from_chapter`", "`due_from_chapter`"):
        assert phrase in BUILD_TASK, phrase


def test_old_reply_without_the_link_has_no_links_and_no_shifts():
    """Câu trả lời trước `setup-11` (fixture, thư mục `--setup-from` cũ): không liên kết, không dời."""
    assert all(t.answered_by == [] for t in BuildOutput.model_validate(FIXTURE).threads)
    setup = _setup(FIXTURE)
    assert all(t.answered_by == [] for t in setup.plan.must_resolve_threads)
    assert setup.shifts == ()


def test_link_reaches_the_plan_for_must_resolve_threads_only_and_duplicates_merge():
    data = _data(t_ai_giet_cha=["f_ha_lao_giet_cha", "f_ha_lao_giet_cha"],
                 t_doan_khuong=["f_khong_co"])  # mạch không phải gỡ: bỏ qua, không lỗi
    setup = _setup(data)
    assert setup.plan.thread("t_ai_giet_cha").answered_by == ["f_ha_lao_giet_cha"]
    assert setup.plan.thread("t_chuoi_kiem").answered_by == []
    assert setup.plan.thread("t_doan_khuong") is None
    assert setup.shifts == ()  # mạch 5–6, bí mật 5–6: đã khớp


async def test_thread_starting_before_its_secret_is_shifted_by_code_without_a_repair_call(caplog):
    caplog.set_level(logging.INFO, logger="writory.pipeline.setup")
    data = _data({"t_ai_giet_cha": (2, 6)}, t_ai_giet_cha=["f_ha_lao_giet_cha"])
    llm = FakeLLM.scripted([_dumps(data)])
    seen = []
    setup = await build_story(CHOICES, SETTING, PLOT, PC, llm=llm, config=CFG, commit_id="c0",
                              on_repair=seen.append)
    assert len(llm.calls) == 1 and seen == []
    assert setup.shifts == (WindowShift("t_ai_giet_cha", (2, 6), (5, 6), ("f_ha_lao_giet_cha",)),)
    # Một nguồn (D-49): khoảng phải gỡ của kế hoạch và khoảng dự kiến gỡ trên nút Thread cùng dời.
    assert _plan_window(setup, "t_ai_giet_cha") == _node_window(setup, "t_ai_giet_cha") == (5, 6)
    assert setup.plan.answer_mismatches() == ()
    assert initial_problems(setup.plan, setup.package, level=SHORT_LEVEL) == []
    # Log chỉ có số mạch, không id (G12).
    assert "dời khoảng gỡ của 1 mạch" in caplog.text and "t_ai_giet_cha" not in caplog.text


def test_thread_due_before_the_secret_opens_moves_its_deadline_too():
    """Mạch 1–2, bí mật 5–6: hạn mới là chương cuối của khoảng lộ (chương 6 là chương cuối, không tính
    giới hạn nhịp, D-54)."""
    setup = _setup(_data({"t_chuoi_kiem": (1, 2)}, t_chuoi_kiem=["f_ha_lao_giet_cha"]))
    [shift] = setup.shifts
    assert (shift.before, shift.after, shift.end_moved) == ((1, 2), (5, 6), True)
    assert _plan_window(setup, "t_chuoi_kiem") == _node_window(setup, "t_chuoi_kiem") == (5, 6)
    assert setup.plan.deadlines()[6] > SHORT_LEVEL.max_due_per_chapter


async def test_unknown_or_non_secret_answer_id_is_a_problem_for_the_repair_round():
    for bad, words in (("f_khong_co", "không phải bí mật"),
                       ("f_chuoi_kiem_ban_do", "là fact nhưng không phải bí mật")):
        data = _data(t_chuoi_kiem=[bad])
        llm = FakeLLM.scripted([_dumps(data), _dumps(_data())])
        seen: list[list[str]] = []
        setup = await build_story(
            CHOICES, SETTING, PLOT, PC, llm=llm, config=CFG, commit_id="c0",
            on_repair=lambda problems, seen=seen: seen.append([p.kind for p in problems]))
        assert len(llm.calls) == 2 and seen == [["answered_by"]]
        assert setup.plan.thread("t_chuoi_kiem").answered_by == []
        [user] = [m.content for m in llm.calls[1] if m.role == "user"]
        problems = user.split(CLOSE_TAG)[-1]
        assert f"mạch t_chuoi_kiem: answered_by có {bad}" in problems and words in problems


async def test_accented_answer_ids_are_normalized_with_the_rest():
    text = _dumps(_data(t_ai_giet_cha=["f_ha_lao_giet_cha"]))
    for good, bad in _ACCENTED.items():
        text = text.replace(f'"{good}"', json.dumps(bad, ensure_ascii=False))
    setup = await build_story(CHOICES, SETTING, PLOT, PC, llm=FakeLLM.scripted([text]), config=CFG,
                              commit_id="c0")
    assert setup.plan.thread("t_ai_giet_cha").answered_by == ["f_ha_lao_giet_cha"]


async def test_the_repair_turn_hands_back_the_shifted_window():
    """Lượt sửa vì lỗi khác: câu trả lời trước có khoảng đã dời, và đề nói vì sao nó khác."""
    good = _data({"t_ai_giet_cha": (2, 6)}, t_ai_giet_cha=["f_ha_lao_giet_cha"])
    bad = copy.deepcopy(good)
    bad["secrets"][0]["fact_id"] = "f_khong_co"
    llm = FakeLLM.scripted([_dumps(bad), _dumps(good)])
    setup = await build_story(CHOICES, SETTING, PLOT, PC, llm=llm, config=CFG, commit_id="c0")
    [user] = [m.content for m in llm.calls[1] if m.role == "user"]
    previous = json.loads(html.unescape(_block(user, "previous_answer")))
    [thread] = [t for t in previous["threads"] if t["id"] == "t_ai_giet_cha"]
    assert (thread["due_from_chapter"], thread["due_to_chapter"]) == (5, 6)
    assert REPAIR_INTRO in user and "khoảng gỡ" in REPAIR_INTRO
    assert _plan_window(setup, "t_ai_giet_cha") == (5, 6)
