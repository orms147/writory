"""Gói thay đổi theo commit_id (D-6, G11) và tách truyện theo story_id (G10)."""

import pytest

from writory.graph import (
    ChangePackage,
    CommitConflictError,
    GraphIntegrityError,
    InvalidPackageError,
    MissingEntityError,
    apply_package,
    delete_commit,
    item_holder,
    load_sample_story,
    player_view,
    read_sample,
    story_snapshot,
)

pytestmark = pytest.mark.graph


def _pkg(commit_id, nodes=(), edges=(), close=()):
    return ChangePackage.model_validate(
        {"commit_id": commit_id, "nodes": list(nodes), "edges": list(edges), "close": list(close)}
    )


def test_reapplying_same_commit_does_not_duplicate(driver, new_story_id):
    sid = new_story_id()
    load_sample_story(driver, sid)
    before = story_snapshot(driver, sid)
    load_sample_story(driver, sid)
    assert story_snapshot(driver, sid) == before
    assert before.node_count > 30 and before.edge_count > 50


def test_failure_midway_leaves_nothing(driver, new_story_id):
    sid = new_story_id()
    load_sample_story(driver, sid)
    before = story_snapshot(driver, sid)
    bad = _pkg(
        "bad-commit",
        nodes=[{"id": "new_guy", "label": "Character", "props": {"name": "Người lạ"}}],
        edges=[
            {"type": "RELATES_TO", "from": "new_guy", "to": "minh", "valid_from_chapter": 6,
             "kind": "lạ", "score": 0},
            # Nút không tồn tại: lỗi sau khi nút và cạnh đầu đã được ghi trong transaction.
            {"type": "HOLDS", "from": "new_guy", "to": "ghost_item", "valid_from_chapter": 6},
        ],
        close=[{"type": "HOLDS", "id": "holds_sword_gu", "valid_to_chapter": 6}],
    )
    with pytest.raises(MissingEntityError, match="ghost_item"):
        apply_package(driver, sid, bad)
    assert story_snapshot(driver, sid) == before


def test_closing_already_closed_edge_from_other_commit_fails_atomically(driver, new_story_id):
    sid = new_story_id()
    load_sample_story(driver, sid)
    before = story_snapshot(driver, sid)
    bad = _pkg(
        "c-close",
        nodes=[{"id": "x1", "label": "Item", "props": {"name": "X"}}],
        close=[{"type": "HOLDS", "id": "holds_sword_gu", "valid_to_chapter": 6}],
    )
    with pytest.raises(CommitConflictError):
        apply_package(driver, sid, bad)
    assert story_snapshot(driver, sid) == before


def test_node_id_owned_by_other_commit_is_rejected(driver, new_story_id):
    # Thực thể mới phải khai riêng; không được ghi đè thực thể đã có (G11).
    sid = new_story_id()
    load_sample_story(driver, sid)
    bad = _pkg("c-dup", nodes=[{"id": "lan", "label": "Character", "props": {"name": "Lan giả"}}])
    with pytest.raises(CommitConflictError):
        apply_package(driver, sid, bad)


def test_delete_commit_restores_previous_state(driver, new_story_id):
    sid = new_story_id()
    sample = read_sample()
    for ch in sample.chapters[:5]:  # chương 0–4
        apply_package(driver, sid, ch.package)
    after_ch4 = story_snapshot(driver, sid)

    apply_package(driver, sid, sample.chapters[5].package)
    assert item_holder(driver, sid, "sword", 5).id == "minh"

    delete_commit(driver, sid, "sample-ch5")
    assert story_snapshot(driver, sid) == after_ch4
    # Cạnh "Lan giữ kiếm" đã được mở lại.
    assert item_holder(driver, sid, "sword", 5).id == "lan"


def test_delete_commit_refuses_when_later_commit_depends_on_it(driver, new_story_id):
    sid = new_story_id()
    load_sample_story(driver, sid)
    before = story_snapshot(driver, sid)
    with pytest.raises(CommitConflictError):
        delete_commit(driver, sid, "sample-ch1")
    assert story_snapshot(driver, sid) == before


def test_two_stories_with_same_names_do_not_mix(driver, new_story_id):
    a, b = new_story_id(), new_story_id()
    load_sample_story(driver, a)
    # Truyện B có nhân vật cùng id, cùng tên, nhưng sự thật khác và bí mật đã hé lộ ngay chương 1.
    apply_package(driver, b, _pkg(
        "b-ch1",
        nodes=[
            {"id": "ch1", "label": "Chapter", "props": {"number": 1}},
            {"id": "lan", "label": "Character", "props": {"name": "Phạm Thị Lan"}},
            {"id": "sword", "label": "Item", "props": {"name": "Thanh Sương"}},
            {"id": "f_lan_spy", "label": "Fact", "props": {"text": "Lan là gián điệp"}},
        ],
        edges=[
            {"type": "HOLDS", "from": "lan", "to": "sword", "valid_from_chapter": 1},
            {"type": "REVEALED_TO_PLAYER", "from": "f_lan_spy", "to": "ch1",
             "valid_from_chapter": 1, "quote": "Lan là gián điệp"},
        ],
    ))
    assert item_holder(driver, a, "sword", 1).id == "gu"
    assert item_holder(driver, b, "sword", 1).id == "lan"
    assert "f_lan_spy" not in {e.id for e in player_view(driver, a, 3).entries}
    assert "f_lan_spy" in {e.id for e in player_view(driver, b, 1).entries}
    assert story_snapshot(driver, b).node_count == 4


def test_every_function_requires_story_id(driver):
    with pytest.raises(ValueError):
        item_holder(driver, "", "sword", 1)
    with pytest.raises(ValueError):
        player_view(driver, "  ", 1)


def test_two_open_holders_is_reported_not_hidden(driver, new_story_id):
    # Quên đóng cạnh HOLDS cũ là lỗi ghi; đọc phải báo, không được chọn đại một người giữ.
    sid = new_story_id()
    load_sample_story(driver, sid)
    apply_package(driver, sid, _pkg(
        "c-second-holder",
        edges=[{"type": "HOLDS", "from": "khai", "to": "sword", "valid_from_chapter": 6}],
    ))
    with pytest.raises(GraphIntegrityError):
        item_holder(driver, sid, "sword", 6)


@pytest.mark.parametrize("edge", [
    {"type": "REVEALED_TO_PLAYER", "from": "khai", "to": "ch5", "valid_from_chapter": 5,
     "id": "reveal_khai_again", "quote": "Lan là người của Hội Hắc Kỳ."},
    {"type": "KNOWS", "from": "minh", "to": "sword", "valid_from_chapter": 5,
     "how": "chứng kiến", "quote": "Thanh Sương nằm dưới mấy lớp áo"},
])
def test_named_reveal_without_known_as_is_rejected(driver, new_story_id, edge):
    # D-17: thiếu known_as thì player_view không biết hiện tên gì; không được ghi.
    sid = new_story_id()
    load_sample_story(driver, sid)
    before = story_snapshot(driver, sid)
    with pytest.raises(InvalidPackageError, match="known_as"):
        apply_package(driver, sid, _pkg("c-no-known-as", edges=[edge]))
    assert story_snapshot(driver, sid) == before
