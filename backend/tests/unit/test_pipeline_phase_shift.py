"""Đổi pha (pipeline/pacing.py `phase_shift`, `limits.context.phase_shift_every`): cứ mỗi N chương kể từ
lần đổi pha trước, mục tiêu chương thêm một câu đòi đổi nơi, người cầm trịch hay luật chơi, không thêm
một mối nguy cùng loại. "Đổi pha" đo từ đồ thị và kế hoạch: nhân vật chính tới một nơi chưa từng tới, hoặc
chương đầu của một hồi. Nhắc cũng tính là mốc mới, nên câu lặp mỗi N chương chứ không mỗi chương.

Nền: một truyện nhỏ dựng tay bằng OverlayState (như test_pipeline_pacing.py, không dùng truyện mẫu).
"""

import pytest

from writory.config import ConfigError, load_config
from writory.graph import ChangePackage
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.pacing import (
    GOAL_DEFAULTS,
    PhaseShift,
    chapter_goals,
    phase_shift,
    render_chapter_goals,
)
from writory.pipeline.prompt_variants import load_prompt_variant
from writory.pipeline.story_plan import StoryPlan


def _plan(*acts: tuple[int, int]) -> StoryPlan:
    return StoryPlan.model_validate({
        "acts": [{"name": f"hồi {i}", "from_chapter": a, "to_chapter": b}
                 for i, (a, b) in enumerate(acts, 1)],
        "secrets": [], "must_resolve_threads": [], "milestones": []})


ONE_ACT = _plan((1, 12))
TWO_ACTS = _plan((1, 3), (4, 12))

_BASE = ChangePackage.model_validate({
    "commit_id": "c0",
    "nodes": [
        {"id": "minh", "label": "Character", "props": {"name": "Minh", "is_protagonist": True}},
        {"id": "lan", "label": "Character", "props": {"name": "Lan"}},
        {"id": "ben", "label": "Location", "props": {"name": "bến đò"}},
        {"id": "cho", "label": "Location", "props": {"name": "chợ"}},
        {"id": "chua", "label": "Location", "props": {"name": "chùa"}}],
    "edges": [{"type": "LOCATED_AT", "from": "minh", "to": "ben", "valid_from_chapter": 0}],
})


def _pkg(chapter: int, *edges: dict) -> ChangePackage:
    return ChangePackage.model_validate({
        "commit_id": f"c{chapter}",
        "nodes": [{"id": f"ch{chapter}", "label": "Chapter", "props": {"number": chapter}}],
        "edges": [{"valid_from_chapter": chapter, **e} for e in edges]})


def _quiet(chapter: int) -> ChangePackage:
    """Chương có chữ nhưng không đổi nơi: chỉ một quan hệ đổi điểm."""
    return _pkg(chapter, {"type": "RELATES_TO", "from": "minh", "to": "lan",
                          "props": {"kind": "bạn", "score": 50 + chapter}})


def _goes(chapter: int, place: str) -> ChangePackage:
    return _pkg(chapter, {"type": "LOCATED_AT", "from": "minh", "to": place})


def story(upto: int, **moves: str) -> OverlayState:
    """Tới hết chương `upto`; `moves` {"c3": "cho"} là nhân vật chính tới `cho` ở chương 3."""
    by_chapter = {int(k.removeprefix("c")): v for k, v in moves.items()}
    return OverlayState(EmptyState(), [
        _BASE, *(_goes(c, by_chapter[c]) if c in by_chapter else _quiet(c)
                 for c in range(1, upto + 1))])


EVERY = 5


# --- tắt là tắt --------------------------------------------------------------------------------


def test_off_means_off():
    state = story(9)
    assert phase_shift(ONE_ACT, state, 10, None) is None
    assert chapter_goals(ONE_ACT, 10, state).phase_shift is None
    assert chapter_goals(ONE_ACT, 10, state, phase_shift_every=None).phase_shift is None


# --- nhịp: N chương không đổi pha thì bật ------------------------------------------------------


def test_it_fires_after_every_chapters_without_a_phase_change():
    state = story(4)
    assert phase_shift(ONE_ACT, state, 5, EVERY) == PhaseShift(5)  # ch0 là lần đổi pha đầu
    assert phase_shift(ONE_ACT, story(3), 4, EVERY) is None  # mới 4 chương
    assert phase_shift(ONE_ACT, state, 5, 6) is None


def test_going_somewhere_new_restarts_the_clock():
    state = story(6, c2="cho")
    assert phase_shift(ONE_ACT, state, 6, EVERY) is None  # mới 4 chương từ ch2
    assert phase_shift(ONE_ACT, story(7, c2="cho"), 8, EVERY) is None  # ch7 đã nhắc, mới 1 chương
    assert phase_shift(ONE_ACT, story(6, c2="cho"), 7, EVERY) == PhaseShift(5)


def test_returning_to_a_place_already_visited_is_not_a_phase_change():
    """Quay lại bến đò (chương 0) hay chợ (chương 1) là đúng dạng lặp: không đổi pha."""
    state = story(5, c1="cho", c3="ben", c4="cho")
    assert phase_shift(ONE_ACT, state, 6, EVERY) == PhaseShift(5)  # tính từ ch1, không phải ch4
    wrong = story(5, c1="cho", c3="chua", c4="chua")  # nơi mới ở ch3
    assert phase_shift(ONE_ACT, wrong, 6, EVERY) is None


def test_the_place_at_chapter_zero_counts_as_visited():
    state = story(5, c5="ben")  # quay lại nơi xuất phát: không phải pha mới
    assert phase_shift(ONE_ACT, state, 6, 6) == PhaseShift(6)  # tính từ ch0, không phải ch5


def test_the_first_chapter_of_a_later_act_is_a_phase_change():
    # Hồi hai bắt đầu ở ch4: đồng hồ chạy từ ch4, nên ch5 chưa tới, ch9 tới.
    state = story(8)
    assert phase_shift(TWO_ACTS, state, 5, EVERY) is None
    assert phase_shift(ONE_ACT, state, 5, EVERY) == PhaseShift(5)  # không có hồi hai thì đã nhắc ở ch5
    assert phase_shift(TWO_ACTS, state, 9, EVERY) == PhaseShift(5)
    assert phase_shift(ONE_ACT, state, 9, EVERY) is None  # đã nhắc ở ch5, mới 4 chương


def test_the_start_of_the_first_act_is_not_a_phase_change():
    # Chương 1 là chương đầu của hồi một: không tính là đổi pha (nếu tính, ch6 mới nhắc).
    assert phase_shift(ONE_ACT, story(4), 5, EVERY) == PhaseShift(5)


def test_a_reminder_restarts_the_clock_so_the_line_comes_every_n_chapters_not_every_chapter():
    state = story(9)
    got = [phase_shift(ONE_ACT, state, c, 3) for c in range(2, 10)]
    assert got == [None, PhaseShift(3), None, None, PhaseShift(3), None, None, PhaseShift(3)]


def test_without_a_protagonist_only_the_acts_count_and_nothing_breaks():
    empty = OverlayState(EmptyState(), [])
    assert phase_shift(ONE_ACT, empty, 5, EVERY) == PhaseShift(5)
    assert phase_shift(TWO_ACTS, empty, 5, EVERY) is None


def test_the_answer_for_a_chapter_does_not_depend_on_the_scene_being_written():
    """Cảnh hai của chương 5 thấy gói cảnh một (cạnh mở ở ch5): chỉ đọc tới ch4 như `standstill`."""
    state = story(4)
    scene_one = _goes(5, "chua")
    with_scene = OverlayState(state, [scene_one])
    assert phase_shift(ONE_ACT, with_scene, 5, EVERY) == phase_shift(ONE_ACT, state, 5, EVERY)


# --- trong mục tiêu chương ----------------------------------------------------------------------


def test_chapter_goals_carry_the_phase_shift_only_when_asked():
    state = story(4)
    assert chapter_goals(ONE_ACT, 5, state).phase_shift is None
    assert chapter_goals(ONE_ACT, 5, state, phase_shift_every=EVERY).phase_shift == PhaseShift(5)


def test_never_on_the_last_chapter():
    state = story(11)
    assert phase_shift(ONE_ACT, state, 12, 4) == PhaseShift(4)  # tới nhịp (ch4, 8, 12)...
    assert chapter_goals(ONE_ACT, 12, state, phase_shift_every=4).phase_shift is None  # ...mà là chương cuối
    assert chapter_goals(ONE_ACT, 8, state, phase_shift_every=4).phase_shift == PhaseShift(4)


def test_standstill_or_idle_already_asks_for_a_change_so_the_phase_line_stays_out():
    state = story(4)
    assert chapter_goals(ONE_ACT, 5, state, standstill_chapters=4).standstill is not None
    assert chapter_goals(ONE_ACT, 5, state, standstill_chapters=4,
                         phase_shift_every=EVERY).phase_shift is None
    idle = chapter_goals(ONE_ACT, 5, state, idle_chapters=4, phase_shift_every=EVERY)
    assert idle.idle is not None and idle.phase_shift is None
    assert chapter_goals(ONE_ACT, 5, state, phase_shift_every=EVERY).phase_shift is not None


def test_the_phase_sentence_is_in_the_goals_text_with_the_chapter_count_and_nowhere_else():
    shifted = chapter_goals(ONE_ACT, 5, story(4), phase_shift_every=EVERY)
    text = "\n".join(p for p in render_chapter_goals(shifted, scene=1, scene_count=2)
                     if isinstance(p, str))
    assert "ĐỔI PHA" in text and "Đã 5 chương" in text and "{chapters}" not in text
    plain = chapter_goals(ONE_ACT, 5, story(4))
    assert "ĐỔI PHA" not in "\n".join(p for p in render_chapter_goals(plain, scene=1, scene_count=2)
                                      if isinstance(p, str))


def test_the_phase_sentence_can_be_replaced_by_goals_yaml_text():
    shifted = chapter_goals(ONE_ACT, 5, story(4), phase_shift_every=EVERY)
    text = "\n".join(p for p in render_chapter_goals(
        shifted, scene=1, scene_count=1, texts={"phase_shift": "Sang trang: {chapters} chương rồi."})
        if isinstance(p, str))
    assert "- Sang trang: 5 chương rồi." in text and "ĐỔI PHA" not in text


def test_the_default_sentence_names_the_three_changes_and_forbids_one_more_danger():
    sentence = GOAL_DEFAULTS["phase_shift"]
    assert "{chapters}" in sentence
    for needle in ("đổi nơi", "người nắm quyền quyết định", "luật chơi", "KHÔNG thêm một mối nguy"):
        assert needle in sentence, needle


def test_a_goals_yaml_without_the_chapter_slot_for_phase_shift_is_refused(tmp_path):
    folder = tmp_path / "moi"
    folder.mkdir(parents=True)
    (folder / "goals.yaml").write_text("phase_shift: Đổi pha đi.\n", encoding="utf-8")
    with pytest.raises(ConfigError, match=r"phase_shift thiếu chỗ điền \{chapters\}"):
        load_prompt_variant("moi", root=tmp_path)
    (folder / "goals.yaml").write_text("phase_shift: Đổi pha sau {chapters} chương.\n",
                                       encoding="utf-8")
    assert load_prompt_variant("moi", root=tmp_path).goal_texts["phase_shift"].startswith("Đổi pha")


# --- cấu hình ---------------------------------------------------------------------------------


def test_the_threshold_is_off_by_default_in_the_repo_config():
    assert load_config().limits.context.phase_shift_every is None
