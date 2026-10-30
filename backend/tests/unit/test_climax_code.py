"""Cao trào bằng code, không đổi đề bộ trích (D-142; sau D-129, D-139). Dấu cao trào ghi TRƯỚC khoảng của
mốc chỉ là ứng viên; cao trào đã xong thì mục tiêu các chương sau đòi HẬU QUẢ, không "đừng diễn lại".
Nền: truyện mẫu dựng bằng OverlayState, không mạng, không Neo4j."""

from tests.unit.test_pipeline_pacing import PLAN, mark, through
from writory.config import load_config
from writory.guard.plan import milestone_marks, plan_progress
from writory.pipeline.pacing import (
    GOAL_DEFAULTS,
    chapter_goals,
    render_chapter_goals,
)
from writory.pipeline.prompt_variants import GOAL_KEYS
from writory.pipeline.story_plan import StoryPlan

# 8 chương; mốc 3 là cao trào ở chương 5–6, mốc 2 là bước ngoặt ở chương 3–4, mốc kết ở chương 8.
PLAN8 = StoryPlan.model_validate({
    "acts": [{"name": "mở đầu", "from_chapter": 1, "to_chapter": 2},
             {"name": "phát triển", "from_chapter": 3, "to_chapter": 6},
             {"name": "kết", "from_chapter": 7, "to_chapter": 8}],
    "secrets": [], "must_resolve_threads": [],
    "milestones": [
        {"kind": "turning_point", "goal": "Minh nhận thanh kiếm và lá thư của Lão Gù",
         "from_chapter": 1, "to_chapter": 2},
        {"kind": "turning_point", "goal": "Lão Gù chết, Minh thành kẻ bị nghi",
         "from_chapter": 3, "to_chapter": 4},
        {"kind": "climax", "goal": "Minh biết Lan là người của Hội Hắc Kỳ",
         "from_chapter": 5, "to_chapter": 6},
        {"kind": "ending", "goal": "Minh quyết định số phận Thanh Sương",
         "from_chapter": 8, "to_chapter": 8},
    ],
})
LOOKAHEAD = 4


def goals(chapter, *extra, plan=PLAN8, done_extra=None, aftermath=2, **kw):
    # Chương `chapter` chưa tới trên truyện mẫu: gói trống cho tới đó (state đọc tới chương - 1).
    state = through(min(chapter - 1, 5), *extra)
    return chapter_goals(plan, chapter, state, milestone_lookahead=LOOKAHEAD, done_extra=done_extra,
                         climax_aftermath=aftermath, **kw)


def by_number(g):
    return {m.number: m for m in g.milestones}


# --- dấu ứng viên và dấu xong --------------------------------------------------------------------


def test_a_climax_mark_before_its_window_is_only_a_candidate():
    done, candidates = milestone_marks(PLAN8, through(4, mark(4, 3)), 4)
    assert done == {} and candidates == {3: 4}
    got = {m.number: (m.done_chapter, m.candidate_chapter)
           for m in plan_progress(PLAN8, through(4, mark(4, 3)), 4).milestones}
    assert got[3] == (None, 4)


def test_a_climax_mark_at_or_after_the_start_of_its_window_is_done():
    assert milestone_marks(PLAN8, through(5, mark(5, 3)), 5) == ({3: 5}, {})
    assert milestone_marks(PLAN8, through(6, mark(6, 3)), 6) == ({3: 6}, {})


def test_a_second_mark_inside_the_window_confirms_a_candidate():
    state = through(6, mark(4, 3), mark(6, 3))
    assert milestone_marks(PLAN8, state, 6) == ({3: 6}, {3: 4})  # xong ở chương 6; ứng viên cũ vẫn ghi


def test_turning_points_and_the_ending_keep_the_old_rule_early_marks_count():
    done, candidates = milestone_marks(PLAN8, through(3, mark(2, 2), mark(3, 2)), 3)
    assert done == {2: 2} and candidates == {}  # bước ngoặt: dấu đầu thắng, dù trước khoảng


# --- mục tiêu chương ----------------------------------------------------------------------------


def test_a_candidate_climax_stays_pending_and_gets_its_own_status():
    g = goals(5, mark(4, 3))
    m = by_number(g)[3]
    assert (m.status, m.candidate_chapter, m.done_chapter) == ("candidate", 4, None)
    assert 3 in {p.number for p in g.pending_milestones}  # bộ trích còn được đánh dấu lại
    assert dict(g.milestones_done).get(3) is None
    assert not g.gap  # ứng viên vẫn là mốc đang diễn ra


def test_a_candidate_before_the_window_is_shown_instead_of_the_next_milestone_line():
    g = goals(4, mark(3, 3))
    assert [(m.number, m.status) for m in g.milestones if m.number == 3] == [(3, "candidate")]


def test_a_confirmed_climax_is_done_and_leaves_pending():
    g = goals(6, mark(5, 3))
    m = by_number(g)[3]
    assert (m.status, m.done_chapter) == ("done", 5)
    assert 3 not in {p.number for p in g.pending_milestones}


def test_marks_from_earlier_scenes_of_this_chapter_follow_the_same_rule():
    early = goals(4, done_extra={3: 4})  # cảnh trước của chương 4 đánh dấu cao trào (khoảng 5–6)
    assert by_number(early)[3].status == "candidate"
    inside = goals(5, done_extra={3: 5})
    assert (by_number(inside)[3].status, by_number(inside)[3].done_chapter) == ("done", 5)


def test_aftermath_lines_follow_a_done_climax_for_the_configured_chapters_even_outside_its_window():
    state_marks = [mark(5, 3)]
    assert [m.status for m in goals(6, *state_marks).milestones if m.number == 3] == ["done"]
    assert [m.status for m in goals(7, *state_marks).milestones if m.number == 3] == ["done"]
    assert [m.number for m in goals(8, *state_marks).milestones if m.number == 3] == []  # hết 2 chương
    assert [m.number for m in goals(7, *state_marks, aftermath=None).milestones
            if m.number == 3] == []  # tắt: như cũ, chỉ trong khoảng của mốc


def test_aftermath_never_applies_to_turning_points():
    g = goals(5, mark(3, 2), mark(1, 1))
    assert 2 not in {m.number for m in g.milestones}  # khoảng 3–4 đã qua, bước ngoặt không có hậu quả


# --- chữ trong đề --------------------------------------------------------------------------------


def text_of(g):
    parts = render_chapter_goals(g, scene=1, scene_count=2)
    return "\n".join(str(p) for p in parts)


def test_a_done_climax_asks_for_consequences_not_for_a_pause():
    text = text_of(goals(6, mark(5, 3)))
    assert GOAL_DEFAULTS["climax_aftermath"] in text
    assert "xảy ra ở chương 5" in text
    assert GOAL_DEFAULTS["milestone_done"] not in text.split("Mốc cốt truyện")[1]
    assert "HẬU QUẢ" in GOAL_DEFAULTS["climax_aftermath"] and "không diễn lại" in (
        GOAL_DEFAULTS["climax_aftermath"])


def test_a_done_turning_point_keeps_the_old_sentence():
    g = chapter_goals(PLAN, 2, through(1, mark(1, 1)), milestone_lookahead=LOOKAHEAD)
    assert GOAL_DEFAULTS["milestone_done"] in text_of(g)
    assert GOAL_DEFAULTS["climax_aftermath"] not in text_of(g)


def test_a_candidate_climax_says_the_climax_may_not_have_happened_yet():
    text = text_of(goals(5, mark(4, 3)))
    assert GOAL_DEFAULTS["milestone_candidate"] in text
    assert "dấu sớm ở chương 4" in text
    for phrase in ("CHƯA", "hậu quả"):
        assert phrase in GOAL_DEFAULTS["milestone_candidate"], phrase


def test_the_new_sentences_can_be_overridden_by_the_prompt_variant_and_are_known_keys():
    assert {"milestone_candidate", "climax_aftermath"} <= GOAL_KEYS == set(GOAL_DEFAULTS)
    g = goals(6, mark(5, 3))
    parts = render_chapter_goals(g, scene=1, scene_count=2, texts={
        **GOAL_DEFAULTS, "climax_aftermath": "VIẾT HẬU QUẢ RIÊNG"})
    assert "VIẾT HẬU QUẢ RIÊNG" in "\n".join(str(p) for p in parts)


# --- cấu hình ---------------------------------------------------------------------------------------


def test_config_has_the_aftermath_window_in_limits_context():
    assert load_config().limits.context.climax_aftermath_chapters == 2
