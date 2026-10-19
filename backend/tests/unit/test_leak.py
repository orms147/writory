"""G2: dò lộ bí mật trên chữ sắp hiện cho người chơi. Bằng code, không gọi model."""

import json
import logging
import unicodedata

import pytest

from writory.errors import ErrorCode, WritoryError
from writory.graph import read_sample
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import LeakKind, check_leaks, ensure_no_leak, strip_diacritics

SAMPLE = read_sample()
PLAN = StoryPlan.model_validate({
    "acts": [{"name": "mở đầu", "from_chapter": 1, "to_chapter": 12}],
    "secrets": [
        {"fact_id": "f_gu_old_hac_ky", "reveal_from_chapter": 2, "reveal_to_chapter": 3,
         "leak_terms": [["Lão Gù", "Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6,
         "leak_terms": [["Lan", "gián điệp"], ["Lan", "người của Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_killed_gu", "reveal_from_chapter": 7, "reveal_to_chapter": 9,
         "leak_terms": [["Lan", "giết", "Lão Gù"]]},
    ],
})


def through(chapter: int) -> OverlayState:
    return OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= chapter])


def leaks(text: str, chapter: int, plan: StoryPlan = PLAN):
    return check_leaks(text, state=through(chapter), chapter=chapter, plan=plan)


# --- tên chưa hé lộ ------------------------------------------------------------------------


def test_real_name_before_reveal_is_a_leak():
    [hit] = leaks("Gã lái đò mặt sẹo, tức Lý Thất, buộc thuyền trước quán.", 4)
    assert (hit.kind, hit.term) == (LeakKind.NAME, "Lý Thất")


def test_real_name_after_reveal_is_fine():
    assert leaks("Cuối thư ký tên Lý Thất.", 5) == []


def test_name_without_diacritics_or_case_is_caught():
    assert [h.term for h in leaks("tuc ly that, nguoi cua hoi", 4)] == ["Lý Thất"]


def test_faction_name_before_its_reveal_is_a_leak():
    assert [h.term for h in leaks("Họ là người của Hội Hắc Kỳ.", 1)] == ["Hội Hắc Kỳ"]


def test_common_noun_alias_is_never_forbidden():
    # "thanh kiếm" là biệt danh trong lớp truth của Thanh Sương, nhưng không có tên riêng nào.
    assert leaks("Minh lau thanh kiếm.", 1) == []


def test_name_said_in_reveal_quote_counts_as_known():
    # ch01: "Tên thật của lão là Hồ Sĩ Bằng, nhưng cả phố chỉ gọi lão là Lão Gù" (known_as: Lão Gù).
    assert leaks("Hồ Sĩ Bằng ngồi bên bếp lò nguội.", 1) == []


# --- bí mật theo story_plan ----------------------------------------------------------------


def test_secret_before_window_is_a_leak():
    [hit] = leaks("Minh không ngờ Lan là gián điệp.", 4)
    assert hit.kind is LeakKind.SECRET
    assert hit.excerpt == "Lan là gián điệp"


def test_secret_without_diacritics_is_caught():
    assert [h.kind for h in leaks("Minh khong ngo Lan la gian diep.", 4)] == [LeakKind.SECRET]


def test_secret_inside_window_is_fine():
    assert leaks("Lan là gián điệp.", 5) == []


def test_secret_phrases_in_different_sentences_do_not_hit():
    assert leaks("Lan rót trà. Ngoài chợ người ta đồn có gián điệp.", 4) == []


def test_common_noun_lan_is_not_the_character():
    # "lan" (hoa lan) viết thường: tên một từ so có phân biệt hoa thường.
    assert leaks("Ông lão bán hoa lan kể chuyện gián điệp thời chiến.", 4) == []


def test_spy_word_alone_is_fine():
    assert leaks("Gián điệp là nghề nguy hiểm.", 4) == []


def test_secret_revealed_early_by_choice_is_no_longer_secret():
    """Lộ sớm hợp lệ (by_choice, D-22): từ đó chữ nói về bí mật không còn là lộ."""
    from writory.graph import ChangePackage

    early = ChangePackage.model_validate({
        "commit_id": "c4",
        "nodes": [{"id": "ch4", "label": "Chapter", "number": 4}],
        "edges": [{"type": "REVEALED_TO_PLAYER", "from": "f_lan_spy", "to": "ch4",
                   "valid_from_chapter": 4, "quote": "Lan là gián điệp.", "by_choice": "c3"}],
    })
    state = OverlayState(through(3), [early])
    assert check_leaks("Lan là gián điệp.", state=state, chapter=4, plan=PLAN) == []


def test_secret_without_leak_terms_warns(caplog):
    plan = StoryPlan.model_validate({
        "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 9}],
        "secrets": [{"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6}],
    })
    with caplog.at_level(logging.WARNING, logger="writory.safety.leak"):
        leaks("Trời mưa.", 4, plan)
    assert "f_lan_spy" in caplog.text
    assert "leak_terms" in caplog.text


# --- vị trí, chuẩn hoá ---------------------------------------------------------------------


def test_positions_refer_to_nfc_text():
    text = unicodedata.normalize("NFD", "Ở bến, Lý Thất cười.")
    [hit] = leaks(text, 4)
    nfc = unicodedata.normalize("NFC", text)
    assert nfc[hit.start : hit.end] == hit.excerpt == "Lý Thất"


def test_strip_diacritics_keeps_length_and_case():
    s = "Đêm Lão Gù chết, ĐỒNG hồ điểm"
    out = strip_diacritics(s)
    assert len(out) == len(s)
    assert out == "Dem Lao Gu chet, DONG ho diem"


# --- văn sạch của truyện mẫu ---------------------------------------------------------------


@pytest.mark.parametrize("chapter", [c for c in SAMPLE.chapters if c.text],
                         ids=lambda c: f"ch{c.number}")
def test_hand_written_sample_chapter_has_no_leak(chapter):
    assert leaks(chapter.text, chapter.number) == []


# --- chặn và báo lỗi (G12) -----------------------------------------------------------------


def test_ensure_no_leak_blocks_without_revealing_the_secret():
    with pytest.raises(WritoryError) as exc:
        ensure_no_leak("Minh không ngờ Lan là gián điệp.", state=through(4), chapter=4, plan=PLAN)
    err = exc.value
    assert err.code is ErrorCode.SCENE_LEAK_BLOCKED
    shown = json.dumps(err.player_payload(), ensure_ascii=False) + str(err)
    for secret in ("gián điệp", "f_lan_spy", "Lý Thất"):
        assert secret not in shown


def test_ensure_no_leak_passes_clean_text():
    ensure_no_leak("Minh rót trà.", state=through(4), chapter=4, plan=PLAN)
