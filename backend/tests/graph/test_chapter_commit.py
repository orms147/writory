"""Ghi một chương theo D-6: Postgres là nguồn gốc, Neo4j áp theo commit_id. G11: không đổi
trạng thái truyện trước khi ghi thành công. Người chơi và pipeline chỉ thấy chương đã commit."""

import pytest
from neo4j.exceptions import ServiceUnavailable

import writory.db.chapters as chapters_mod
from writory.db import (
    ChapterCommitError,
    ChapterOrderError,
    ChapterPackageError,
    ChapterQuoteError,
    PendingChapterError,
    chapter_records,
    commit_chapter,
    committed_player_view,
    create_story,
    current_chapter,
    get_story,
    migrate,
    reconcile_pending,
)
from writory.graph import (
    ChangePackage,
    MissingEntityError,
    item_holder,
    read_sample,
    story_snapshot,
)

pytestmark = pytest.mark.graph

SAMPLE = read_sample()


def _scenes(n):
    return [SAMPLE.chapters[n].text] if SAMPLE.chapters[n].text else []


def _commit(pg, driver, sid, n):
    return commit_chapter(pg, driver, sid, n, _scenes(n), SAMPLE.chapters[n].package)


def _story_with(pg, driver, sid, up_to):
    create_story(pg, sid, length_level="short")
    for n in range(up_to + 1):
        _commit(pg, driver, sid, n)


def _statuses(pg, sid):
    return [(r.number, r.status) for r in chapter_records(pg, sid)]


def _state(pg, driver, sid):
    return get_story(pg, sid), story_snapshot(driver, sid), _statuses(pg, sid)


def test_migrate_is_idempotent(pg):
    assert migrate(pg) == []


def test_new_story_has_no_current_chapter(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    create_story(pg, sid, length_level="short")
    assert current_chapter(pg, sid) is None
    assert committed_player_view(pg, driver, sid).entries == ()


def test_commit_sample_story_chapter_by_chapter(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 5)
    assert current_chapter(pg, sid) == 5
    assert _statuses(pg, sid) == [(n, "committed") for n in range(6)]
    assert "f_lan_spy" in {e.id for e in committed_player_view(pg, driver, sid).entries}
    assert story_snapshot(driver, sid).node_count > 30


def test_out_of_order_chapter_changes_nothing(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    before = _state(pg, driver, sid)
    with pytest.raises(ChapterOrderError):
        _commit(pg, driver, sid, 3)
    assert _state(pg, driver, sid) == before


def test_package_breaking_chapter_rule_rejected_before_any_write(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    before = _state(pg, driver, sid)
    bad = ChangePackage.model_validate({
        "commit_id": "backdated",
        "edges": [{"type": "HOLDS", "from": "khai", "to": "sword", "valid_from_chapter": 1}],
    })
    with pytest.raises(ChapterPackageError):
        commit_chapter(pg, driver, sid, 2, ["..."], bad)
    assert _state(pg, driver, sid) == before


def test_quote_not_in_chapter_text_rejected_before_any_write(pg, driver, new_db_story_id):
    """G3 ở bước ghi (D-106, hồi quy): gói đúng của chương 3 truyện mẫu, nhưng văn đi kèm không có
    các câu trích của nó, thì không ghi gì: Postgres không có chương 3, đồ thị giữ nguyên."""
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 2)
    package = SAMPLE.chapters[3].package
    assert any(e.type == "REVEALED_TO_PLAYER" for e in package.edges)
    before = _state(pg, driver, sid)
    with pytest.raises(ChapterQuoteError):
        commit_chapter(pg, driver, sid, 3, ["Trời mưa suốt đêm, không ai nói gì."], package)
    assert _state(pg, driver, sid) == before
    assert [r.number for r in chapter_records(pg, sid)] == [0, 1, 2]

    # Cùng gói, đúng văn của chương: ghi được.
    _commit(pg, driver, sid, 3)
    assert current_chapter(pg, sid) == 3


def test_protagonist_knows_without_quote_rejected(pg, driver, new_db_story_id):
    """Nhân vật chính biết điều gì thì phải có câu trích trên trang (G3); nhân vật chính lấy từ đồ thị."""
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    before = _state(pg, driver, sid)
    bad = ChangePackage.model_validate({
        "commit_id": "knows-no-quote",
        "nodes": [{"id": "ch2", "label": "Chapter", "props": {"number": 2}}],
        "edges": [{"type": "KNOWS", "from": SAMPLE.protagonist, "to": "f_lan_spy",
                   "valid_from_chapter": 2, "how": "suy ra"}],
    })
    with pytest.raises(ChapterQuoteError):
        commit_chapter(pg, driver, sid, 2, [SAMPLE.chapters[2].text], bad)
    assert _state(pg, driver, sid) == before


def test_graph_failure_midway_keeps_story_state(pg, driver, new_db_story_id):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 2)
    story_before, graph_before = get_story(pg, sid), story_snapshot(driver, sid)
    bad = ChangePackage.model_validate({
        "commit_id": "bad-ch3",
        "nodes": [{"id": "ch3", "label": "Chapter", "props": {"number": 3}}],
        "edges": [
            {"type": "RELATES_TO", "from": "minh", "to": "lan", "valid_from_chapter": 3,
             "kind": "yêu", "score": 80},
            {"type": "HOLDS", "from": "minh", "to": "ghost_item", "valid_from_chapter": 3},
        ],
    })
    with pytest.raises(ChapterCommitError):
        commit_chapter(pg, driver, sid, 3, ["cảnh lỗi"], bad)

    assert get_story(pg, sid) == story_before
    assert current_chapter(pg, sid) == 2
    assert story_snapshot(driver, sid) == graph_before
    failed = [r for r in chapter_records(pg, sid) if r.commit_id == "bad-ch3"]
    assert failed[0].status == "failed" and "ghost_item" in failed[0].error

    # Viết lại chương 3 với gói đúng (commit_id mới) thì được.
    _commit(pg, driver, sid, 3)
    assert current_chapter(pg, sid) == 3


def test_crash_after_neo4j_before_committed_then_reconcile(
    pg, driver, new_db_story_id, monkeypatch
):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 4)

    def crash(*_args, **_kwargs):
        raise RuntimeError("tiến trình chết")

    monkeypatch.setattr(chapters_mod, "_mark_committed", crash)
    with pytest.raises(RuntimeError):
        _commit(pg, driver, sid, 5)
    monkeypatch.undo()

    # Neo4j đã có dữ liệu chương 5, nhưng chương đó còn pending: không ai được thấy.
    assert _statuses(pg, sid)[-1] == (5, "pending")
    assert current_chapter(pg, sid) == 4
    view = committed_player_view(pg, driver, sid)
    assert view.chapter == 4
    assert "f_lan_spy" not in {e.id for e in view.entries}
    assert item_holder(driver, sid, "sword", current_chapter(pg, sid)).id == "lan"

    # Còn chương pending thì không ghi chương mới.
    with pytest.raises(PendingChapterError):
        commit_chapter(pg, driver, sid, 6, ["..."], ChangePackage(commit_id="ch6"))

    graph_after_crash = story_snapshot(driver, sid)
    results = reconcile_pending(pg, driver)
    assert any(r.story_id == sid and r.status == "committed" for r in results)
    assert current_chapter(pg, sid) == 5
    assert story_snapshot(driver, sid) == graph_after_crash  # áp lại không nhân đôi
    assert "f_lan_spy" in {e.id for e in committed_player_view(pg, driver, sid).entries}
    assert reconcile_pending(pg, driver, story_id=sid) == []


def test_neo4j_down_leaves_pending_then_reconcile(pg, driver, new_db_story_id, monkeypatch):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    graph_before = story_snapshot(driver, sid)

    def down(*_args, **_kwargs):
        raise ServiceUnavailable("neo4j tắt")

    monkeypatch.setattr(chapters_mod, "apply_package", down)
    with pytest.raises(ServiceUnavailable):
        _commit(pg, driver, sid, 2)
    # Chưa biết Neo4j đã áp hay chưa, nên giữ pending để reconcile, không đặt failed.
    assert _statuses(pg, sid)[-1] == (2, "pending")
    assert current_chapter(pg, sid) == 1
    assert story_snapshot(driver, sid) == graph_before

    still_down = reconcile_pending(pg, driver, story_id=sid)
    assert [r.status for r in still_down] == ["pending"]
    monkeypatch.undo()

    assert [r.status for r in reconcile_pending(pg, driver, story_id=sid)] == ["committed"]
    assert current_chapter(pg, sid) == 2


def test_stored_error_is_redacted(pg, driver, new_db_story_id, monkeypatch):
    # chapters.error chỉ để log, nhưng vẫn không được chứa chuỗi giống key (G7).
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    fake_key = "sk-or-v1-" + "c3" * 32

    def reject(*_args, **_kwargs):
        raise MissingEntityError(f"id không có trong truyện: ['x'] {fake_key}")

    monkeypatch.setattr(chapters_mod, "apply_package", reject)
    with pytest.raises(ChapterCommitError) as info:
        _commit(pg, driver, sid, 2)
    stored = chapter_records(pg, sid)[-1]
    assert stored.status == "failed"
    assert fake_key not in stored.error and "[REDACTED]" in stored.error
    assert fake_key not in str(info.value)
