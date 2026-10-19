"""edges_at / node_labels: hàm đọc cạnh đang hiệu lực kèm id, cho người canh (guard/)."""

import pytest

from writory.graph import edges_at, node_labels

pytestmark = pytest.mark.graph


def test_holds_edge_ids_follow_chapter(driver, sample_story_id):
    def at(ch):
        return [e.id for e in edges_at(driver, sample_story_id, "HOLDS", ch, target_id="sword")]

    assert at(1) == ["holds_sword_gu"]
    assert at(3) == ["holds_sword_minh_2"]
    assert at(4) == ["holds_sword_lan"]


def test_edge_row_has_endpoints_and_story_props_only(driver, sample_story_id):
    [rel] = edges_at(driver, sample_story_id, "RELATES_TO", 3, source_id="minh", target_id="lan")
    assert (rel.id, rel.source, rel.target, rel.valid_from_chapter) == (
        "rel_minh_lan_3", "minh", "lan", 3
    )
    assert rel.props["score"] == 80
    assert not {"story_id", "commit_id", "id", "valid_from_chapter"} & rel.props.keys()


def test_closed_edge_not_returned_after_close(driver, sample_story_id):
    assert edges_at(driver, sample_story_id, "RELATES_TO", 5, source_id="minh",
                    target_id="lan")[0].props["score"] == -60


def test_unknown_edge_type_rejected(driver, sample_story_id):
    with pytest.raises(ValueError):
        edges_at(driver, sample_story_id, "HOLDS]->() DETACH DELETE (", 1)


def test_other_story_sees_nothing(driver, sample_story_id, new_story_id):
    other = new_story_id()
    assert edges_at(driver, other, "HOLDS", 3, target_id="sword") == []
    assert node_labels(driver, other, ["sword"]) == {}


def test_node_labels(driver, sample_story_id):
    assert node_labels(driver, sample_story_id, ["sword", "gu", "khong_co"]) == {
        "sword": "Item", "gu": "Character"
    }
