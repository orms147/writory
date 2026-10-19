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
