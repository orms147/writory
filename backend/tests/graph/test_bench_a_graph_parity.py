"""Bài đo A (D-72): hệ đồ thị đọc Neo4j qua lớp graph/ cho CÙNG ngữ cảnh như đọc gói trong bộ nhớ.
Nhờ vậy lần chạy khô (nền bộ nhớ) đại diện đúng cho lần chạy thật (nền Neo4j)."""

import asyncio

import pytest

from writory.config import load_config
from writory.guard.state import Neo4jState
from writory.pipeline.bench_a import RunOptions, open_graph_backend, run_bench
from writory.pipeline.bench_a_data import load_data
from writory.pipeline.bench_a_systems import build_graph_context
from writory.quality.bench_d import Store

pytestmark = pytest.mark.graph

DATA = load_data()


def test_neo4j_and_memory_give_the_same_graph_context_for_every_question(driver, sample_story_id):
    neo4j = Neo4jState(driver, sample_story_id)
    for q in DATA.questions.questions:
        from_neo4j = build_graph_context(neo4j, q.question, q.ask_chapter, story=DATA.story)
        from_memory = build_graph_context(DATA.state_at(q.ask_chapter), q.question,
                                          q.ask_chapter, story=DATA.story)
        assert from_neo4j.text == from_memory.text, q.id
        assert from_neo4j.facts == from_memory.facts, q.id


def test_dry_run_on_the_neo4j_backend_is_perfect_for_the_oracle(tmp_path):
    out = tmp_path / "neo4j-run"
    opts = RunOptions(out=out, dry_run=True, samples=1, systems=["graph"], graph_backend="neo4j")
    assert asyncio.run(run_bench(DATA, opts, config=load_config(), log=lambda _: None)) == 0
    rows = Store(out).rows("results.jsonl")
    assert len(rows) == len(DATA.questions.questions) and all(r["correct"] for r in rows)
    assert Store(out).read_meta()["runs"][-1]["graph_backend"] == "neo4j"


def test_neo4j_backend_loads_a_private_story_and_removes_it(driver):
    from writory.pipeline.bench_a import STORY_ID

    probe = Neo4jState(driver, STORY_ID)
    state_for, close = open_graph_backend("neo4j", DATA)
    try:
        assert state_for(3).protagonist_id() == "minh"
        assert probe.node_labels(["minh"]) == {"minh": "Character"}
    finally:
        close()
    assert probe.node_labels(["minh"]) == {}
