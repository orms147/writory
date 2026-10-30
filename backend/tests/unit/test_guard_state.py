"""OverlayState: phủ các gói chưa ghi lên trạng thái đã commit, cùng nghĩa "ở chương N" với graph/."""

import pytest

from writory.graph import ChangePackage, read_sample
from writory.guard.state import EmptyState, OverlayState

SAMPLE = read_sample()


def through(chapter: int) -> OverlayState:
    """Trạng thái như khi chương 0..chapter đã commit."""
    return OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= chapter])


def ids(rows) -> list[str]:
    return [r.id for r in rows]


def test_holds_follow_opens_and_closes():
    state = through(5)
    assert ids(state.edges_at("HOLDS", 1, target_id="sword")) == ["holds_sword_gu"]
    assert ids(state.edges_at("HOLDS", 3, target_id="sword")) == ["holds_sword_minh_2"]
    assert ids(state.edges_at("HOLDS", 4, target_id="sword")) == ["holds_sword_lan"]
    assert state.edges_at("HOLDS", 0, target_id="sword") == []


def test_overlay_can_close_an_edge_of_the_base():
    pending = ChangePackage.model_validate({
        "commit_id": "c6",
        "edges": [{"type": "HOLDS", "from": "khai", "to": "sword", "valid_from_chapter": 6}],
        "close": [{"type": "HOLDS", "id": "HOLDS:minh>sword@5", "valid_to_chapter": 6}],
    })
    state = OverlayState(through(5), [pending])
    assert [r.source for r in state.edges_at("HOLDS", 6, target_id="sword")] == ["khai"]
    assert [r.source for r in state.edges_at("HOLDS", 5, target_id="sword")] == ["minh"]


def test_edge_row_carries_props_and_window():
    [rel] = through(5).edges_at("RELATES_TO", 3, source_id="minh", target_id="lan")
    assert (rel.id, rel.valid_from_chapter, rel.valid_to_chapter) == ("rel_minh_lan_3", 3, 5)
    assert rel.props["score"] == 80


def test_node_labels_and_protagonist():
    state = through(2)
    assert state.node_labels(["sword", "gu", "e_gu_death"]) == {"sword": "Item", "gu": "Character"}
    assert state.protagonist_id() == "minh"


def test_empty_state_has_no_protagonist():
    with pytest.raises(LookupError):
        EmptyState().protagonist_id()


def test_unknown_edge_type_rejected():
    with pytest.raises(ValueError):
        through(1).edges_at("NOT_A_TYPE", 1)


def test_named_nodes_carry_truth_names():
    names = through(5).named_nodes()
    assert names["ly_that"] == ("Lý Thất", "gã lái đò mặt sẹo")
    assert names["sword"] == ("Thanh Sương", "thanh kiếm")
    assert "f_lan_spy" not in names


def test_player_view_of_overlay_follows_known_as():
    from writory.guard.state import player_view_of

    [ch4] = [e for e in player_view_of(through(4), 4).entries if e.id == "ly_that"]
    assert (ch4.text, ch4.aliases) == ("gã lái đò mặt sẹo", ())
    [ch5] = [e for e in player_view_of(through(5), 5).entries if e.id == "ly_that"]
    assert (ch5.text, ch5.aliases) == ("Lý Thất", ("gã lái đò mặt sẹo",))
    assert ch5.quote == "một gã lái đò mặt sẹo buộc thuyền ngay trước quán trà"
    assert ch5.quotes == ("một gã lái đò mặt sẹo buộc thuyền ngay trước quán trà",
                          "Cuối thư ký tên Lý Thất.")


# Lời nói dối với người mới chỉ biết qua biệt danh (D-17, G1). Fixture riêng của test: truyện
# mẫu không có cảnh này nên không thêm vào data/sample-story/.
LIE_TO_LY_THAT = ChangePackage.model_validate({
    "commit_id": "test-lie-ly-that",
    "nodes": [
        {"id": "l_to_ly_that", "label": "Lie", "chapter": 4,
         "content": "Minh nói với gã lái đò rằng anh không biết gì về thanh kiếm"},
        {"id": "x_stranger", "label": "Character", "name": "Đỗ Bá Kiên"},
        {"id": "l_to_stranger", "label": "Lie", "chapter": 4, "content": "Minh nói mình là học trò"},
    ],
    "edges": [
        {"type": "TOLD", "from": "minh", "to": "l_to_ly_that", "valid_from_chapter": 4},
        {"type": "TOLD_TO", "from": "l_to_ly_that", "to": "ly_that", "valid_from_chapter": 4},
        {"type": "TOLD", "from": "minh", "to": "l_to_stranger", "valid_from_chapter": 4},
        {"type": "TOLD_TO", "from": "l_to_stranger", "to": "x_stranger", "valid_from_chapter": 4},
    ],
})


def lie_story(chapter: int) -> OverlayState:
    packages = [c.package for c in SAMPLE.chapters if c.number <= chapter]
    return OverlayState(EmptyState(), [*packages, LIE_TO_LY_THAT] if chapter >= 4 else packages)


def test_lie_hearer_shown_by_name_player_knows_never_truth_name():
    from writory.guard.state import player_view_of

    ch4 = player_view_of(lie_story(4), 4)
    told = {lie.id: lie.told_to for lie in ch4.lies}
    assert told["l_to_ly_that"] == ("gã lái đò mặt sẹo",)
    assert "Lý Thất" not in repr(ch4)
    ch5 = player_view_of(lie_story(5), 5)
    assert {lie.id: lie.told_to for lie in ch5.lies}["l_to_ly_that"] == ("Lý Thất",)


def test_lie_to_unrevealed_hearer_is_kept_with_neutral_name():
    from writory.graph.player_view import UNKNOWN_HEARER
    from writory.guard.state import player_view_of

    view = player_view_of(lie_story(4), 4)
    assert {lie.id: lie.told_to for lie in view.lies}["l_to_stranger"] == (UNKNOWN_HEARER,)
    assert "Đỗ Bá Kiên" not in repr(view)


# Hé lộ cùng một nút dưới ba tên theo thứ tự A (ch1), B (ch2), A (ch3): chữ hiện là `known_as` của lần
# hé lộ mới nhất (docs/graph-schema.md, mục player_view; D-17). Trước đây gộp tên giữ lần xuất hiện
# ĐẦU, nên ở chương 3 chữ hiện vẫn là B.
def _renamed(chapter: int) -> ChangePackage:
    names = {1: "gã lái đò", 2: "Lý Thất", 3: "gã lái đò"}
    nodes = [{"id": f"ch{chapter}", "label": "Chapter", "number": chapter}]
    if chapter == 1:
        nodes += [{"id": "hero", "label": "Character",
                   "props": {"name": "Minh", "is_protagonist": True}},
                  {"id": "ferry", "label": "Character",
                   "props": {"name": "Lý Thất", "aliases": ["gã lái đò"]}}]
    return ChangePackage.model_validate({
        "commit_id": f"c{chapter}", "nodes": nodes,
        "edges": [{"type": "REVEALED_TO_PLAYER", "from": "ferry", "to": f"ch{chapter}",
                   "valid_from_chapter": chapter, "known_as": names[chapter],
                   "quote": f"{names[chapter]} buộc thuyền ở chương {chapter}"}],
    })


RENAMED = [_renamed(n) for n in (1, 2, 3)]


@pytest.mark.parametrize(("chapter", "shown", "aliases"), [
    (1, "gã lái đò", ()),
    (2, "Lý Thất", ("gã lái đò",)),
    (3, "gã lái đò", ("Lý Thất",)),
])
def test_shown_name_is_the_known_as_of_the_newest_reveal(chapter, shown, aliases):
    from writory.guard.state import player_view_of

    state = OverlayState(EmptyState(), RENAMED[:chapter])
    [entry] = [e for e in player_view_of(state, chapter).entries if e.id == "ferry"]
    assert (entry.text, entry.aliases) == (shown, aliases)
    assert entry.since_chapter == 1  # chương biết lần đầu không đổi
