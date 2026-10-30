"""Lỗ G2 trên đường sổ tay (D-134, hồi quy D-132): Fact (Event, Lie) đã hé lộ hiện bằng chữ lớp truth
của nút (`player_view`, `_TEXT_FIELD`), mà G3 chỉ kiểm câu trích có trên trang, không kiểm chữ của nút
nằm trong câu trích. Trước bản sửa, một Fact không phải bí mật mà chữ có tên đang được kế hoạch bảo vệ
(`Secret.protects`, D-61) thì:
1. được bộ trích hé lộ bằng một câu trích không chứa tên đó, người canh không bắt (`_early_reveal` chỉ
   xét chính Fact bí mật);
2. sổ tay (`NotebookOut.from_view`, không qua bộ dò lộ) trả nguyên chữ đó cho người chơi;
3. tên đó vào "chữ người chơi đã thấy" (`safety.leak._seen_text`), nên bộ dò lộ thôi cấm nó, ở cả cảnh
   lẫn đường người chơi.

Bản sửa: sau người canh, `extract.drop_unquoted_leaks` bỏ cạnh đưa nút chữ vào player_view khi chữ lớp
truth của nút có điều bộ dò lộ đường người chơi chặn mà câu trích của nó không nói ra. Test ở đây đi
đúng đường của pipeline: `to_package` → người canh → `drop_unquoted_leaks`."""

import pytest

from writory.api.schemas import NotebookOut
from writory.config import load_config
from writory.graph import ChangePackage
from writory.guard import GuardKind, check_scene_package
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.bench_run import reject_reason
from writory.pipeline.extract import (
    UNQUOTED_LEAK,
    Entity,
    ExtractedEdge,
    ExtractOutput,
    drop_unquoted_leaks,
    to_package,
)
from writory.pipeline.setup import PROTAGONIST_ID
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import check_leaks, forbidden_names, leak_names, unquoted_leaks

NAME = "Lâm Hắc Y"
PLAN = StoryPlan.model_validate({
    "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
    "secrets": [{"fact_id": "f_mask", "reveal_from_chapter": 3, "reveal_to_chapter": 4,
                 "leak_terms": [["người áo đen", NAME]], "protects": ["hac_y"]}],
})
NO_PROTECTS = StoryPlan.model_validate({
    "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
    "secrets": [{"fact_id": "f_mask", "reveal_from_chapter": 3, "reveal_to_chapter": 4,
                 "leak_terms": [["người áo đen", "kẻ phản bội"]]}],
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
ENTITIES = [Entity(PROTAGONIST_ID, "Character", "Kỷ Trầm Uyên", user_authored=True),
            Entity("hac_y", "Character", NAME, aliases=("người áo đen",)),
            Entity("f_mask", "Fact", f"Người áo đen là {NAME}"),
            Entity("f_ferry", "Fact", f"{NAME} từng chèo đò ở bến này")]
PAGE = "Người áo đen chèo đò rất giỏi. Kỷ Trầm Uyên nhìn theo."
QUOTE = "Người áo đen chèo đò rất giỏi"


def _edge(type_: str, source: str, target: str, quote: str, **kw) -> ExtractedEdge:
    base = {"kind": None, "score": None, "how": None, "told_by": None, "known_as": None,
            "role": None}
    return ExtractedEdge(type=type_, source=source, target=target, quote=quote, **(base | kw))


def _reveal(fact: str, chapter: int, quote: str) -> ExtractedEdge:
    return _edge("REVEALED_TO_PLAYER", fact, f"ch{chapter}", quote)


def _pipeline(edges: list[ExtractedEdge], *, chapter: int = 1, page: str = PAGE,
              plan: StoryPlan = PLAN, earlier: tuple[ChangePackage, ...] = ()):
    """Đường của pipeline cho một cảnh: bộ trích (`to_package`) → người canh → `drop_unquoted_leaks`.
    Trả trạng thái sau cảnh và lý do bị bỏ của bước lọc (`to_package` nhận hết, người canh im)."""
    entities = [*ENTITIES, Entity(f"ch{chapter}", "Chapter", f"chương {chapter}")]
    package, rejected = to_package(
        ExtractOutput(edges=edges, close=[], new_facts=[], milestones=[]), chapter=chapter,
        commit_id=f"c{chapter}", protagonist_id=PROTAGONIST_ID, chapter_text=page,
        entities=entities, open_edges=[])
    assert rejected == []
    current = ChangePackage.model_validate({
        "commit_id": f"c{chapter}", "nodes": [{"id": f"ch{chapter}", "label": "Chapter",
                                               "number": chapter}],
        "edges": [e.model_dump(by_alias=True) for e in package.edges]})
    base = OverlayState(EmptyState(), [WORLD, *earlier])
    issues = check_scene_package(chapter=chapter, current=current, earlier=[], committed=base,
                                 plan=plan, config=load_config().guard)
    assert GuardKind.EARLY_REVEAL not in {i.kind for i in issues}
    kept, dropped = drop_unquoted_leaks(current, before=base, chapter=chapter,
                                        protagonist_id=PROTAGONIST_ID, plan=plan, story_brief="")
    return OverlayState(base, [kept]), dropped


def _reveal_ferry_in_chapter_1():
    """Bộ trích hé lộ f_ferry bằng một câu có thật trên trang (không chứa tên): to_package nhận,
    người canh không báo gì; bước lọc bỏ cạnh đó."""
    return _pipeline([_reveal("f_ferry", 1, QUOTE)])


def _shown_ids(state, chapter: int) -> set[str]:
    return {e.id for e in player_view_of(state, chapter).entries}


def test_before_the_reveal_the_name_is_forbidden():
    """Đối chứng: chưa hé lộ f_ferry thì tên bị cấm như D-61."""
    state = OverlayState(EmptyState(), [WORLD])
    view = player_view_of(state, 1)
    names = {f.term for f in forbidden_names(truth_names=leak_names(state), view=view, plan=PLAN,
                                             story_brief="", scope="scene")}
    assert NAME in names


def test_the_notebook_never_shows_a_name_the_plan_still_protects():
    state, _ = _reveal_ferry_in_chapter_1()
    notebook = NotebookOut.from_view(player_view_of(state, 1)).model_dump_json()
    assert NAME not in notebook


def test_a_revealed_fact_does_not_unlock_a_protected_name():
    state, _ = _reveal_ferry_in_chapter_1()
    view = player_view_of(state, 1)
    for scope in ("scene", "player_path"):
        hits = check_leaks(f"{NAME} đứng ở đầu bến.", view=view, truth_names=leak_names(state),
                           plan=PLAN, story_brief="", scope=scope)
        assert [h.term for h in hits] == [NAME], scope


def test_the_dropped_reveal_has_its_own_reason_for_the_bench():
    state, dropped = _reveal_ferry_in_chapter_1()
    assert "f_ferry" not in _shown_ids(state, 1)
    assert dropped == [("REVEALED_TO_PLAYER f_ferry→ch1", UNQUOTED_LEAK)]
    assert reject_reason(UNQUOTED_LEAK) == UNQUOTED_LEAK


def test_the_protagonist_knowing_the_fact_is_held_back_the_same_way():
    """KNOWS của nhân vật chính cũng đưa nút vào player_view (design §7.1): cùng luật."""
    knows = _edge("KNOWS", PROTAGONIST_ID, "f_ferry", QUOTE, how="chứng kiến")
    state, dropped = _pipeline([knows, _reveal("f_ferry", 1, QUOTE)])
    assert "f_ferry" not in _shown_ids(state, 1)
    assert sorted(dropped) == [(f"KNOWS {PROTAGONIST_ID}→f_ferry", UNQUOTED_LEAK),
                               ("REVEALED_TO_PLAYER f_ferry→ch1", UNQUOTED_LEAK)]


def test_a_quote_that_says_the_name_keeps_the_reveal():
    """Trong khoảng lộ, trang được nêu tên (scope `scene`). Câu trích có tên thì chữ sổ tay không
    nói gì hơn trang: giữ."""
    page = f"{NAME} chèo đò rất giỏi. Kỷ Trầm Uyên nhìn theo."
    state, dropped = _pipeline([_reveal("f_ferry", 3, f"{NAME} chèo đò rất giỏi")], chapter=3,
                               page=page)
    assert dropped == [] and "f_ferry" in _shown_ids(state, 3)


@pytest.mark.parametrize("quote", ["Người áo đen gỡ khăn che mặt",
                                   f"Người áo đen gỡ khăn che mặt: chính là {NAME}"])
def test_the_secret_itself_needs_its_protected_name_in_the_quote(quote):
    """Nhóm `leak_terms` của chính bí mật không tính (người canh `_early_reveal` quyết khoảng lộ),
    nhưng tên nó bảo vệ thì phải có trên trang: câu trích không nêu tên thì sổ tay không được nêu."""
    page = f"{quote}. Kỷ Trầm Uyên sững người."
    state, dropped = _pipeline([_reveal("f_mask", 3, quote)], chapter=3, page=page)
    if NAME in quote:
        assert dropped == [] and "f_mask" in _shown_ids(state, 3)
    else:
        assert dropped == [("REVEALED_TO_PLAYER f_mask→ch3", UNQUOTED_LEAK)]
        assert "f_mask" not in _shown_ids(state, 3)


def test_a_real_name_hidden_behind_a_nickname_is_held_back_too():
    """Luật (a) của D-61, không cần `protects`: người chơi biết hac_y là "Người áo đen"; Fact nêu
    tên thật mà câu trích không nêu thì sổ tay sẽ lộ tên thật."""
    nickname = ChangePackage.model_validate({
        "commit_id": "c1", "nodes": [{"id": "ch1", "label": "Chapter", "number": 1}],
        "edges": [{"type": "REVEALED_TO_PLAYER", "from": "hac_y", "to": "ch1",
                   "valid_from_chapter": 1,
                   "props": {"quote": QUOTE, "known_as": "Người áo đen"}}]})
    state, dropped = _pipeline([_reveal("f_ferry", 2, QUOTE)], chapter=2, plan=NO_PROTECTS,
                               earlier=(nickname,))
    assert "f_ferry" not in _shown_ids(state, 2)
    assert dropped == [("REVEALED_TO_PLAYER f_ferry→ch2", UNQUOTED_LEAK)]


def test_a_fact_that_restates_another_secret_is_held_back():
    """Nhóm `leak_terms` của bí mật khác còn hiệu lực, cùng một câu trong chữ Fact: lộ qua sổ tay."""
    leaky = StoryPlan.model_validate({
        "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
        "secrets": [{"fact_id": "f_mask", "reveal_from_chapter": 3, "reveal_to_chapter": 4,
                     "leak_terms": [["chèo đò", "bến này"]]}]})
    state, dropped = _pipeline([_reveal("f_ferry", 1, QUOTE)], plan=leaky)
    assert "f_ferry" not in _shown_ids(state, 1)
    assert dropped == [("REVEALED_TO_PLAYER f_ferry→ch1", UNQUOTED_LEAK)]


def test_unquoted_leaks_names_only_what_the_quote_does_not_say():
    state = OverlayState(EmptyState(), [WORLD])
    view = player_view_of(state, 1)
    args = {"view": view, "truth_names": leak_names(state), "plan": PLAN, "story_brief": ""}
    text = f"{NAME} từng chèo đò ở bến này"
    assert unquoted_leaks(text, [QUOTE], node_id="f_ferry", **args) == [NAME]
    assert unquoted_leaks(text, [f"{NAME} chèo đò"], node_id="f_ferry", **args) == []
    # Không dấu, khác hoa thường: cùng cách so của bộ dò lộ.
    assert unquoted_leaks(text, ["lam hac y cheo do"], node_id="f_ferry", **args) == []
    # Bí mật của chính nút: nhóm leak_terms không tính, tên nó bảo vệ vẫn tính.
    assert unquoted_leaks(f"Người áo đen là {NAME}", [QUOTE], node_id="f_mask", **args) == [NAME]
