"""Nhân vật chính luôn có đúng một nơi ở sau mỗi chương, trên Neo4j thật (D-112)."""

import pytest

from writory.graph import ChangePackage, apply_package
from writory.guard.state import Neo4jState
from writory.pipeline.extract import Entity, ExtractedEdge, ExtractOutput, OpenEdge, to_package
from writory.pipeline.pacing import standstill

pytestmark = pytest.mark.graph

ENTITIES = [Entity("hero", "Character", "Minh"), Entity("ben", "Location", "bến đò"),
            Entity("cho", "Location", "chợ")]


def _start(driver, sid):
    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c0",
        "nodes": [{"id": "hero", "label": "Character",
                   "props": {"name": "Minh", "is_protagonist": True}},
                  {"id": "ben", "label": "Location", "props": {"name": "bến đò"}},
                  {"id": "cho", "label": "Location", "props": {"name": "chợ"}}],
        "edges": [{"type": "LOCATED_AT", "from": "hero", "to": "ben", "valid_from_chapter": 0}]}))
    return Neo4jState(driver, sid)


def _extract(state, chapter, edges, close=()):
    here = [OpenEdge(r.id, r.type, r.source, r.target)
            for r in state.edges_at("LOCATED_AT", chapter - 1, source_id="hero")]
    pkg, _ = to_package(
        ExtractOutput(edges=edges, close=list(close)), chapter=chapter, commit_id=f"c{chapter}",
        protagonist_id="hero", chapter_text="Minh đi.", entities=ENTITIES, open_edges=here)
    return pkg


def _move(target):
    return ExtractedEdge(type="LOCATED_AT", source="hero", target=target, kind=None, score=None,
                         how=None, told_by=None, quote=None, known_as=None, role=None)


def test_a_close_without_a_new_place_leaves_the_old_place_in_the_graph(driver, new_story_id):
    sid = new_story_id()
    state = _start(driver, sid)
    old = state.edges_at("LOCATED_AT", 0, source_id="hero")[0]
    apply_package(driver, sid, _extract(state, 1, [], close=[old.id]))
    rows = state.edges_at("LOCATED_AT", 1, source_id="hero")
    assert [(r.id, r.target) for r in rows] == [(old.id, "ben")]
    assert standstill(state, 5, 4) is not None  # cờ không mù: nhân vật chính vẫn ở bến đò


def test_moving_leaves_exactly_one_open_place_even_if_the_model_forgot_to_close(driver, new_story_id):
    sid = new_story_id()
    state = _start(driver, sid)
    apply_package(driver, sid, _extract(state, 1, [_move("cho")]))
    rows = state.edges_at("LOCATED_AT", 1, source_id="hero")
    assert [r.target for r in rows] == ["cho"]
    assert standstill(state, 3, 2).chapters == 2  # tính từ chương 1, không phải chương 0


def test_idle_chapters_on_the_real_graph_counts_the_run_since_the_last_change(driver, new_story_id):
    """D-121: `idle_chapters` đọc ba lần `ever=True` rồi tính trong Python; kết quả phải như cũ trên Neo4j."""
    from writory.graph import CloseSpec
    from writory.pipeline.pacing import Idle, idle_chapters

    sid = new_story_id()
    state = _start(driver, sid)
    old = state.edges_at("LOCATED_AT", 0, source_id="hero")[0]
    for chapter in range(1, 6):
        move = chapter == 3
        apply_package(driver, sid, ChangePackage.model_validate({
            "commit_id": f"c{chapter}",
            "nodes": [{"id": f"ch{chapter}", "label": "Chapter", "props": {"number": chapter}}],
            "edges": ([{"type": "LOCATED_AT", "from": "hero", "to": "cho", "valid_from_chapter": 3}]
                      if move else []),
            "close": ([CloseSpec(type="LOCATED_AT", id=old.id, valid_to_chapter=3).model_dump(
                by_alias=True)] if move else []),
        }))
    assert idle_chapters(state, 6, 2) == Idle(2)  # ch4, ch5; ch3 đổi nơi
    assert idle_chapters(state, 6, 3) is None
    assert idle_chapters(state, 4, 1) is None  # chương 3 vừa đổi nơi
    assert idle_chapters(state, 3, 2) == Idle(2)  # ch1, ch2 trước khi đi
