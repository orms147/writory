"""OverlayState trên nền rỗng + gói truyện mẫu phải trả đúng như Neo4j (graph.edges_at).
Nhờ vậy unit test và bài B chạy không cần Neo4j mà vẫn đúng nghĩa của lớp graph/."""

import pytest

from writory.graph import read_sample
from writory.graph.schema import EDGE_TYPES
from writory.guard.state import EmptyState, Neo4jState, OverlayState

pytestmark = pytest.mark.graph


def test_overlay_matches_neo4j_for_every_edge_type_and_chapter(driver, sample_story_id):
    sample = read_sample()
    memory = OverlayState(EmptyState(), [c.package for c in sample.chapters])
    neo4j = Neo4jState(driver, sample_story_id)
    for chapter in range(7):
        for edge_type in EDGE_TYPES:
            assert memory.edges_at(edge_type, chapter) == neo4j.edges_at(edge_type, chapter), (
                edge_type, chapter
            )
    every_id = [n.id for c in sample.chapters for n in c.package.nodes]
    assert memory.node_labels(every_id) == neo4j.node_labels(every_id)
    assert memory.protagonist_id() == neo4j.protagonist_id()


def test_named_nodes_match_neo4j(driver, sample_story_id):
    memory = OverlayState(EmptyState(), [c.package for c in read_sample().chapters])
    assert memory.named_nodes() == Neo4jState(driver, sample_story_id).named_nodes()


def test_player_view_from_overlay_matches_neo4j(driver, sample_story_id):
    """player_view có MỘT định nghĩa (build_player_view): Overlay và Neo4j phải ra giống hệt."""
    from writory.graph import player_view
    from writory.guard.state import player_view_of

    memory = OverlayState(EmptyState(), [c.package for c in read_sample().chapters])
    for chapter in range(7):
        assert player_view_of(memory, chapter, story_id=sample_story_id) == player_view(
            driver, sample_story_id, chapter
        ), chapter


def test_edges_ever_opened_includes_closed_edges(driver, sample_story_id):
    memory = OverlayState(EmptyState(), [c.package for c in read_sample().chapters])
    neo4j = Neo4jState(driver, sample_story_id)
    for state in (memory, neo4j):
        ids = [e.id for e in state.edges_at("HOLDS", 5, target_id="sword", ever=True)]
        assert ids == ["HOLDS:minh>sword@5", "holds_sword_gu", "holds_sword_lan",
                       "holds_sword_minh_2"]


def test_lie_hearer_name_parity_after_d17_fix(driver, new_story_id):
    """Sửa told_to (D-17) ở cả hai đường: Neo4j và Overlay vẫn ra player_view giống hệt."""
    from tests.unit.test_guard_state import LIE_TO_LY_THAT
    from writory.graph import apply_package, load_sample_story, player_view
    from writory.guard.state import player_view_of

    sid = new_story_id()
    sample = load_sample_story(driver, sid)
    apply_package(driver, sid, LIE_TO_LY_THAT)
    memory = OverlayState(EmptyState(), [*(c.package for c in sample.chapters), LIE_TO_LY_THAT])
    for chapter in range(7):
        neo4j_view = player_view(driver, sid, chapter)
        assert player_view_of(memory, chapter, story_id=sid) == neo4j_view, chapter
        if chapter == 4:
            assert "Lý Thất" not in repr(neo4j_view)


def test_newest_known_as_parity(driver, new_story_id):
    """Nút hé lộ dưới tên A, rồi B, rồi lại A: Neo4j và Overlay cùng hiện A ở chương 3 (D-17)."""
    from tests.unit.test_guard_state import RENAMED
    from writory.graph import apply_package, player_view
    from writory.guard.state import player_view_of

    sid = new_story_id()
    for package in RENAMED:
        apply_package(driver, sid, package)
    memory = OverlayState(EmptyState(), RENAMED)
    for chapter in range(1, 4):
        neo4j_view = player_view(driver, sid, chapter)
        assert player_view_of(memory, chapter, story_id=sid) == neo4j_view, chapter
    [entry] = [e for e in player_view(driver, sid, 3).entries if e.id == "ferry"]
    assert (entry.text, entry.aliases) == ("gã lái đò", ("Lý Thất",))
