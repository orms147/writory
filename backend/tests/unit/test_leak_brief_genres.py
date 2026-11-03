"""G2 hồi quy sau review D-160: nhãn thể loại và chữ đầu câu trong ý tưởng không làm một tên bí mật thành "đã thấy".

`story_brief` có dòng tag (nhãn thể loại như "Hài hước · đời thường": "Hài" bỏ dấu thành "Hai", trùng tên "Hải") và dòng ý
tưởng người chơi gõ (chữ viết hoa đầu câu như "Hải sản", "Trong làng" không phải tên). Thiết kế D-160 chỉ coi tên người
chơi tự gõ GIỮA câu trong ý tưởng là đã thấy."""

import pytest

from writory.graph import ChangePackage
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.setup import PROTAGONIST_ID
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import LeakKind, check_leaks

PLAN = StoryPlan.model_validate({
    "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
    "secrets": [{"fact_id": "f_mask", "reveal_from_chapter": 3, "reveal_to_chapter": 4,
                 "leak_terms": [["người áo đen", "Hải"]], "protects": ["hai"]}],
})
TEXT = "Hải đứng ở đầu bến."


def world() -> OverlayState:
    nodes = [
        {"id": PROTAGONIST_ID, "label": "Character",
         "props": {"name": "Kỷ Trầm Uyên", "is_protagonist": True, "user_authored": True}},
        {"id": "hai", "label": "Character", "props": {"name": "Hải", "aliases": ["người áo đen"]}},
        {"id": "f_mask", "label": "Fact", "props": {"text": "Người áo đen là Hải"}},
    ]
    return OverlayState(EmptyState(), [ChangePackage.model_validate({"commit_id": "c0", "nodes": nodes})])


def hits(brief: str):
    state = world()
    from writory.safety.leak import leak_names
    return check_leaks(TEXT, view=player_view_of(state, 1), truth_names=leak_names(state), plan=PLAN,
                       story_brief=brief, scope="scene")


def test_protected_name_is_blocked_without_brief():
    [hit] = hits("")
    assert (hit.kind, hit.term) == (LeakKind.NAME, "Hải")


@pytest.mark.parametrize("brief", [
    "thể loại: Hài hước · đời thường, Võ hiệp · giang hồ\ngiọng văn: Trầm, lạnh",
    "Ý tưởng của người chơi: Hải sản ở chợ rẻ. Trong làng ai cũng biết.",
    "Ý tưởng của người chơi: \"Hải\" là tên quán. Chợ đông.",
])
def test_genre_labels_and_sentence_initial_idea_words_do_not_unprotect(brief):
    [hit] = hits(brief)
    assert hit.term == "Hải"


def test_name_typed_mid_sentence_in_idea_counts_as_seen():
    """Thiết kế D-160 (chủ dự án duyệt): tên người chơi tự gõ trong ý tưởng là tên người chơi đã biết."""
    assert hits("Ý tưởng của người chơi: bạn thân tên Hải ganh ghét ngầm.") == []


def test_setting_and_protagonist_lines_still_count_as_seen():
    """Phần thiết lập người chơi đã đọc (bối cảnh, nhân vật chính) vẫn tính như trước (D-52)."""
    assert hits("Bối cảnh: Bến Hải\nMột bến sông.") == []


def test_tag_labels_match_the_story_brief_tag_lines():
    """Bộ dò lộ bỏ qua đúng các dòng tag mà `story_brief` viết (một nguồn: `BRIEF_TAG_LABELS`)."""
    from writory.pipeline.setup import _TAG_LABELS
    from writory.safety.leak import BRIEF_TAG_LABELS
    assert tuple(label for _, label in _TAG_LABELS) == BRIEF_TAG_LABELS


def test_multiline_idea_stays_on_the_idea_line():
    """Ý tưởng nhiều dòng (ô nhập cho xuống dòng) gộp thành một dòng, để dòng sau không bị tính như chữ thường."""
    from writory.config import load_config
    from writory.pipeline.setup import (
        CharacterOption,
        Naming,
        PlotOption,
        SettingOption,
        StoryChoices,
        StoryTags,
        story_brief,
    )
    from writory.safety.leak import BRIEF_IDEA_PREFIX
    choices = StoryChoices(tags=StoryTags(genre="Đô thị"), genres=("do_thi",), idea="bạn thân ganh ghét.\nHải sản rẻ.",
                           length_level="short", naming=Naming(names="viet", places="that"))
    brief = story_brief(choices, SettingOption(title="Hẻm", intro="Một con hẻm."), PlotOption(title="Nợ", summary="Trả nợ."),
                        CharacterOption(name="Trần Lục", personality="Lì.", backstory="Thợ."),
                        moderation=load_config().moderation)
    [line] = [ln for ln in brief.splitlines() if "Hải sản" in ln]
    assert line == BRIEF_IDEA_PREFIX + "bạn thân ganh ghét. Hải sản rẻ."
    assert hits(brief)[0].term == "Hải"  # "Hải sản" đầu câu không mở khoá tên "Hải"
