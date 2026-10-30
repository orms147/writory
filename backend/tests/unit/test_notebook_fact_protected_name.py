"""Lỗ G2 trên đường sổ tay (chưa sửa; thiết kế bản sửa chưa quyết): Fact đã hé lộ hiện bằng chữ lớp
truth của nút (`player_view`, `_TEXT_FIELD`), mà G3 chỉ kiểm câu trích có trên trang, không kiểm chữ
của Fact nằm trong câu trích. Một Fact không phải bí mật mà chữ có tên đang được kế hoạch bảo vệ
(`Secret.protects`, D-61) thì:
1. được bộ trích hé lộ bằng một câu trích không chứa tên đó, người canh không bắt (`_early_reveal` chỉ
   xét chính Fact bí mật);
2. sổ tay (`NotebookOut.from_view`, không qua bộ dò lộ) trả nguyên chữ đó cho người chơi;
3. tên đó vào "chữ người chơi đã thấy" (`safety.leak._seen_text`), nên bộ dò lộ thôi cấm nó, ở cả cảnh
   lẫn đường người chơi.

Hai test dưới đây là `xfail(strict=True)`: chạy đỏ cho tới khi lỗ được vá, rồi phải bỏ marker."""

import pytest

from writory.api.schemas import NotebookOut
from writory.config import load_config
from writory.graph import ChangePackage
from writory.guard import GuardKind, check_scene_package
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.extract import Entity, ExtractedEdge, ExtractOutput, to_package
from writory.pipeline.setup import PROTAGONIST_ID
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import check_leaks, forbidden_names, leak_names

NAME = "Lâm Hắc Y"
PLAN = StoryPlan.model_validate({
    "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
    "secrets": [{"fact_id": "f_mask", "reveal_from_chapter": 3, "reveal_to_chapter": 4,
                 "leak_terms": [["người áo đen", NAME]], "protects": ["hac_y"]}],
})
WORLD = ChangePackage.model_validate({
    "commit_id": "c0",
    "nodes": [
        {"id": PROTAGONIST_ID, "label": "Character",
         "props": {"name": "Kỷ Trầm Uyên", "is_protagonist": True, "user_authored": True}},
        {"id": "hac_y", "label": "Character", "props": {"name": NAME, "aliases": ["người áo đen"]}},
        {"id": "f_mask", "label": "Fact", "props": {"text": f"Người áo đen là {NAME}"}},
        # Không phải bí mật của kế hoạch, nhưng chữ có tên mà bí mật f_mask bảo vệ.
        {"id": "f_ferry", "label": "Fact", "props": {"text": f"{NAME} từng chèo đò ở bến này"}},
    ],
    "edges": [{"type": "ABOUT", "from": "f_ferry", "to": "hac_y", "valid_from_chapter": 0}],
})
PAGE = "Người áo đen chèo đò rất giỏi. Kỷ Trầm Uyên nhìn theo."


def _reveal_ferry_in_chapter_1() -> OverlayState:
    """Bộ trích hé lộ f_ferry bằng một câu có thật trên trang (không chứa tên): to_package nhận,
    người canh không báo gì."""
    entities = [Entity(PROTAGONIST_ID, "Character", "Kỷ Trầm Uyên", user_authored=True),
                Entity("hac_y", "Character", NAME, aliases=("người áo đen",)),
                Entity("f_mask", "Fact", f"Người áo đen là {NAME}"),
                Entity("f_ferry", "Fact", f"{NAME} từng chèo đò ở bến này"),
                Entity("ch1", "Chapter", "chương 1")]
    edge = ExtractedEdge(type="REVEALED_TO_PLAYER", source="f_ferry", target="ch1", kind=None,
                         score=None, how=None, told_by=None, quote="Người áo đen chèo đò rất giỏi",
                         known_as=None, role=None)
    package, rejected = to_package(
        ExtractOutput(edges=[edge], close=[], new_facts=[], milestones=[]), chapter=1,
        commit_id="c1", protagonist_id=PROTAGONIST_ID, chapter_text=PAGE, entities=entities,
        open_edges=[])
    assert rejected == []
    chapter = ChangePackage.model_validate({
        "commit_id": "c1", "nodes": [{"id": "ch1", "label": "Chapter", "number": 1}],
        "edges": [e.model_dump(by_alias=True) for e in package.edges]})
    base = OverlayState(EmptyState(), [WORLD])
    issues = check_scene_package(chapter=1, current=chapter, earlier=[], committed=base, plan=PLAN,
                                 config=load_config().guard)
    assert GuardKind.EARLY_REVEAL not in {i.kind for i in issues}
    return OverlayState(base, [chapter])


def test_before_the_reveal_the_name_is_forbidden():
    """Đối chứng: chưa hé lộ f_ferry thì tên bị cấm như D-61."""
    state = OverlayState(EmptyState(), [WORLD])
    view = player_view_of(state, 1)
    names = {f.term for f in forbidden_names(truth_names=leak_names(state), view=view, plan=PLAN,
                                             story_brief="", scope="scene")}
    assert NAME in names


@pytest.mark.xfail(strict=True, reason="lỗ G2 sổ tay: chữ Fact đã hé lộ không qua bộ dò lộ")
def test_the_notebook_never_shows_a_name_the_plan_still_protects():
    state = _reveal_ferry_in_chapter_1()
    notebook = NotebookOut.from_view(player_view_of(state, 1)).model_dump_json()
    assert NAME not in notebook


@pytest.mark.xfail(strict=True, reason="lỗ G2 sổ tay: tên trong chữ Fact thành 'đã thấy', thôi bị cấm")
def test_a_revealed_fact_does_not_unlock_a_protected_name():
    state = _reveal_ferry_in_chapter_1()
    view = player_view_of(state, 1)
    for scope in ("scene", "player_path"):
        hits = check_leaks(f"{NAME} đứng ở đầu bến.", view=view, truth_names=leak_names(state),
                           plan=PLAN, story_brief="", scope=scope)
        assert [h.term for h in hits] == [NAME], scope
