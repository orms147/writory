"""Đường đi một chương trên Neo4j + Postgres thật (D-36): nạp truyện mẫu chương 0–3 qua
`commit_chapter`, viết chương 4 bằng model giả, rồi kiểm chương đã ghi, đồ thị và player_view."""

import pytest

from tests.pipeline_fixtures import (
    PLAN,
    SAMPLE,
    SCENE_2,
    ScriptedLLM,
    full_script,
    make_config,
)
from writory.db import chapter_records, commit_chapter, create_story, current_chapter
from writory.graph import item_holder, knows, player_view, story_snapshot
from writory.llm.cost import CostTracker
from writory.pipeline.chapter import ChapterRequest, ChapterRun
from writory.pipeline.store import GraphStore
from writory.quality import normalize_dashes

pytestmark = pytest.mark.graph


def _story_through_3(pg, driver, sid):
    create_story(pg, sid, length_level="short")
    for ch in SAMPLE.chapters[:4]:
        commit_chapter(pg, driver, sid, ch.number, [ch.text] if ch.text else [], ch.package)


async def _run(pg, driver, sid, tmp_path, script):
    config = make_config(tmp_path)
    llm = ScriptedLLM(script)
    run = ChapterRun(
        ChapterRequest(present_ids=("minh", "lan"), scene_count=2,
                       story_brief="Kiếm hiệp, ngôi thứ ba bám Minh.", player_action=None),
        llm=llm, store=GraphStore(pg, driver, sid), config=config, plan=PLAN,
        tracker=CostTracker(config.limits.cost_usd), style_guide="Văn phong thử.",
    )
    return [e async for e in run.events()], run.outcome, llm


async def test_chapter_4_is_committed_and_visible(pg, driver, new_db_story_id, tmp_path):
    sid = new_db_story_id()
    _story_through_3(pg, driver, sid)
    before = story_snapshot(driver, sid)

    events, outcome, llm = await _run(pg, driver, sid, tmp_path, full_script())

    assert [e.type for e in events if e.type != "stage"] == [
        "scene_ready", "scene_ready", "chapter_committed", "choices_ready"]
    assert current_chapter(pg, sid) == 4
    assert [(r.number, r.status) for r in chapter_records(pg, sid)][-1] == (4, "committed")
    # Đồ thị có thay đổi mới của chương 4, đọc lại qua lớp graph/.
    assert story_snapshot(driver, sid).edge_count > before.edge_count
    assert knows(driver, sid, "lan", "l_sword_father", 4).how == "suy ra"
    assert item_holder(driver, sid, "sword", 4).id == "lan"
    assert item_holder(driver, sid, "sword", 3).id == "minh"  # chương cũ giữ nguyên
    # player_view ở chương 4: gã lái đò hiện bằng tên người chơi biết, không bằng tên thật (D-17).
    view = player_view(driver, sid, 4)
    ly = next(e for e in view.entries if e.id == "ly_that")
    assert ly.text == "gã lái đò mặt sẹo" and ly.since_chapter == 4
    assert "Lý Thất" not in repr(view)
    assert "f_lan_spy" not in {e.id for e in view.entries}
    assert outcome.committed and len(outcome.choices) == 3
    # Tóm tắt chương 4 lưu ở Postgres (D-49), cho đề của chương 5 và 6.
    from tests.pipeline_fixtures import SUMMARY_TEXT
    from writory.db import load_chapter_summaries

    assert load_chapter_summaries(pg, sid, [4]) == {4: SUMMARY_TEXT}
    # Context của model viết đến từ writer_context thật trên Neo4j.
    writer = [c for c in llm.calls if c[0].content.startswith("Văn phong thử.")]
    assert len(writer) == 2 and "Sự thật cần tôn trọng" in writer[0][-1].content
    assert normalize_dashes(SCENE_2) in {e.text for e in events if e.type == "scene_ready"}


async def test_blocked_chapter_writes_nothing(pg, driver, new_db_story_id, tmp_path):
    from tests.pipeline_fixtures import EXTRACT_1, SCENE_1_LEAK, outline_reply

    sid = new_db_story_id()
    _story_through_3(pg, driver, sid)
    before = story_snapshot(driver, sid)
    script = [outline_reply(), SCENE_1_LEAK, EXTRACT_1, SCENE_1_LEAK, EXTRACT_1]
    events, outcome, _ = await _run(pg, driver, sid, tmp_path, script)

    assert [e.type for e in events if e.type != "stage"] == ["scene_blocked"]
    assert current_chapter(pg, sid) == 3
    assert story_snapshot(driver, sid) == before
    assert [r.number for r in chapter_records(pg, sid)] == [0, 1, 2, 3]
    assert not outcome.committed
