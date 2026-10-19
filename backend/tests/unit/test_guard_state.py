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
