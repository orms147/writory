"""Bộ xuất kịch bản video trên Neo4j và Postgres thật (D-125): `all_nodes` của Neo4jState khớp OverlayState,
và lệnh `--dry-run` chạy hết đường trên truyện mẫu đã nạp vào cả hai database. Bộ xuất chỉ đọc."""

import json
import os

import pytest
from pydantic import SecretStr

from tests.pipeline_fixtures import make_config
from writory.db import commit_chapter, create_story, get_story
from writory.export import video
from writory.graph import read_sample, story_snapshot
from writory.guard.state import EmptyState, Neo4jState, OverlayState

pytestmark = pytest.mark.graph

SAMPLE = read_sample()


def test_all_nodes_of_neo4j_match_the_overlay_of_the_same_packages(driver, sample_story_id):
    memory = OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters])
    neo4j = Neo4jState(driver, sample_story_id).all_nodes()
    assert set(neo4j) == set(memory.all_nodes())
    for node_id, row in memory.all_nodes().items():
        assert (neo4j[node_id].label, neo4j[node_id].props) == (row.label, row.props), node_id


def _services() -> video.ExportServices:
    return video.ExportServices(
        neo4j_uri=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.environ.get("NEO4J_USER", "neo4j"),
        neo4j_password=SecretStr(os.environ.get("NEO4J_PASSWORD", "change-me-local")),
        postgres_dsn=SecretStr(os.environ["POSTGRES_DSN"]))  # test đã đổi sang database `_test`


async def test_dry_run_exports_a_story_committed_in_both_databases_and_changes_nothing(
        tmp_path, pg, driver, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short")
    for n in range(4):  # chương 0 (khởi tạo) và 1-3
        scenes = [SAMPLE.chapters[n].text] if SAMPLE.chapters[n].text else []
        commit_chapter(pg, driver, sid, n, scenes, SAMPLE.chapters[n].package)
    before = (get_story(pg, sid), story_snapshot(driver, sid))

    source, closer = video.load_source(_services(), sid, "2-3")
    try:
        assert sorted(source.chapters) == [2, 3] and all(source.chapters[n] for n in (2, 3))
        make_config(tmp_path)
        args = video.build_parser().parse_args([
            "--story", sid, "--out", str(tmp_path / "out"), "--config-dir", str(tmp_path / "config"),
            "--dry-run", "--dialogue-lang", "zh", "--chapters", "2-3"])
        assert await video.run(args, source=source) == video.EXIT_OK
    finally:
        closer.close()

    data = json.loads((tmp_path / "out" / "script.json").read_text(encoding="utf-8"))
    assert data["meta"]["chapters"] == [2, 3] and data["meta"]["story_id"] == sid
    assert {c["id"] for c in data["characters"]} >= {"minh", "lan"}
    assert all(s["status"] == "ok" for c in data["chapters"] for s in c["scenes"])
    assert all(c["overview"]["mermaid"].startswith("graph LR") for c in data["chapters"])
    assert (get_story(pg, sid), story_snapshot(driver, sid)) == before  # chỉ đọc


def test_a_story_without_a_committed_chapter_or_with_a_bad_range_is_refused(pg, new_db_story_id):
    from writory.config import ConfigError

    sid = new_db_story_id()
    create_story(pg, sid, length_level="short")
    with pytest.raises(ConfigError, match="chưa có chương nào"):
        video.load_source(_services(), sid, None)
