"""G1: lớp người chơi biết không chứa bí mật trước khi nó được hé lộ trên trang."""

import dataclasses

import pytest

from writory.graph import ChangePackage, apply_package, player_view

pytestmark = pytest.mark.graph

SECRET = "f_lan_spy"
NEVER_REVEALED = ["f_lan_killed_gu", "t_sealed_letter", "t_who_killed"]


def _ids(view):
    return {e.id for e in view.entries}


def _all_text(view) -> str:
    return repr(dataclasses.asdict(view))


def test_secret_hidden_at_chapter_3(driver, sample_story_id):
    view = player_view(driver, sample_story_id, 3)
    assert SECRET not in _ids(view)
    # Không lộ qua nội dung của mục khác: chữ "gián điệp" và quan hệ với Hội không xuất hiện.
    text = _all_text(view)
    assert "gián điệp" not in text
    assert "MEMBER_OF" not in text


def test_secret_revealed_at_chapter_5_with_quote(driver, sample_story_id):
    view = player_view(driver, sample_story_id, 5)
    entry = next(e for e in view.entries if e.id == SECRET)
    assert entry.since_chapter == 5
    assert entry.quote == "Lan là người của Hội Hắc Kỳ."


@pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
def test_truth_only_items_never_in_view(driver, sample_story_id, chapter):
    view = player_view(driver, sample_story_id, chapter)
    assert not set(NEVER_REVEALED) & _ids(view)
    text = _all_text(view)
    assert "kẻ giết" not in text          # vai trong sự kiện, chỉ có ở lớp sự thật
    assert "con mồi" not in text          # cảm nghĩ thật của Lan về Minh


def test_event_revealed_later_than_it_happened(driver, sample_story_id):
    # Lan lấy kiếm ở chương 4, nhưng người chơi chỉ biết ở chương 5.
    assert "e_sword_stolen" not in _ids(player_view(driver, sample_story_id, 4))
    assert "e_sword_stolen" in _ids(player_view(driver, sample_story_id, 5))


def test_view_exposes_only_whitelisted_fields(driver, sample_story_id):
    view = player_view(driver, sample_story_id, 5)
    fields = {f.name for f in dataclasses.fields(view.entries[0])}
    # `quotes`: mọi câu trích đã hiện trên trang, cho bộ dò lộ G2 (D-26). Không phải chữ của lớp truth.
    assert fields == {"id", "kind", "text", "aliases", "since_chapter", "quote", "about", "quotes"}
    assert all(q.strip() for e in view.entries for q in e.quotes)


def test_protagonist_lies_are_listed_without_discovery_state(driver, sample_story_id):
    view = player_view(driver, sample_story_id, 4)
    assert {lie.id for lie in view.lies} == {"l_sword_father", "l_home_night"}
    assert all(not hasattr(lie, "discovered") for lie in view.lies)


def test_nickname_shown_before_real_name_is_revealed(driver, sample_story_id):
    # D-17: gã lái đò ra mắt ở chương 4 bằng biệt danh; tên thật "Lý Thất" chỉ lộ ở chương 5.
    ch4 = player_view(driver, sample_story_id, 4)
    entry = next(e for e in ch4.entries if e.id == "ly_that")
    assert entry.text == "gã lái đò mặt sẹo"
    assert "Lý Thất" not in _all_text(ch4)

    ch5 = player_view(driver, sample_story_id, 5)
    entry = next(e for e in ch5.entries if e.id == "ly_that")
    assert entry.text == "Lý Thất"
    assert "gã lái đò mặt sẹo" in entry.aliases
    assert entry.since_chapter == 4


def test_truth_name_and_aliases_never_shown(driver, new_story_id):
    sid = new_story_id()
    apply_package(driver, sid, ChangePackage.model_validate({
        "commit_id": "c1",
        "nodes": [
            {"id": "ch1", "label": "Chapter", "props": {"number": 1}},
            {"id": "hero", "label": "Character",
             "props": {"name": "Người Chính", "is_protagonist": True}},
            {"id": "x", "label": "Character",
             "props": {"name": "Hoàng Tử Mất Tích", "aliases": ["Điện Hạ"]}},
            {"id": "blade", "label": "Item", "props": {"name": "Long Tuyền"}},
        ],
        "edges": [
            {"type": "REVEALED_TO_PLAYER", "from": "x", "to": "ch1", "valid_from_chapter": 1,
             "quote": "Một người đàn ông áo đen đứng ở cổng.", "known_as": "người đàn ông áo đen"},
            {"type": "KNOWS", "from": "hero", "to": "blade", "valid_from_chapter": 1,
             "how": "chứng kiến", "quote": "Hắn đeo một thanh kiếm cũ.", "known_as": "thanh kiếm cũ"},
        ],
    }))
    view = player_view(driver, sid, 1)
    text = _all_text(view)
    for secret in ("Hoàng Tử Mất Tích", "Điện Hạ", "Long Tuyền"):
        assert secret not in text
    by_id = {e.id: e for e in view.entries}
    assert by_id["x"].text == "người đàn ông áo đen"
    assert by_id["blade"].text == "thanh kiếm cũ"
