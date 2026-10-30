"""Đề khởi tạo `setup-10`: ngoại hình chỉ tả điều nhìn thấy và phân biệt được nhau (D-122), và bộ đếm
mềm `appearance_variety` (không phải lỗi, không vào lượt sửa; chỉ vào report của bộ đo). Không mạng."""

from writory.graph.package import ChangePackage
from writory.pipeline.setup import (
    BUILD_TASK,
    PROMPT_VERSION,
    appearance_variety,
)


def _package(**by_id: str) -> ChangePackage:
    nodes = [{"id": i, "label": "Character", "props": {"name": i.title(), "appearance": text}}
             for i, text in by_id.items()]
    nodes.append({"id": "kho", "label": "Location", "props": {"name": "Kho", "visual": "Tối."}})
    nodes.append({"id": "npc_khong_ta", "label": "Character", "props": {"name": "Không tả"}})
    return ChangePackage.model_validate({"commit_id": "c0", "nodes": nodes, "edges": []})


def _appearance_part() -> str:
    start = BUILD_TASK.index("- `characters`")
    end = BUILD_TASK.index("- `locations`")
    return BUILD_TASK[start:end]


def test_prompt_version_is_setup_11():
    assert PROMPT_VERSION == "setup-11"


def test_prompt_asks_for_what_is_seen_not_habits_or_the_player_s_past():
    part = _appearance_part()
    for phrase in ("thói quen", "cử chỉ", "thương tật", "nghề", "quá khứ", "không mở bằng"):
        assert phrase in part, phrase
    assert "dáng đi" not in part  # lời mẫu cũ kéo model sang tả cử chỉ


def test_prompt_asks_each_character_to_differ_from_the_others_in_the_same_set():
    part = _appearance_part()
    assert "ít nhất hai" in part and "so với" in part
    for phrase in ("khuôn mặt", "tóc", "vóc dáng"):
        assert phrase in part, phrase
    assert "tóc đen" in part  # dặn đừng mặc định cả bộ cùng màu tóc


def test_protagonist_appearance_is_told_not_to_copy_the_players_job_or_backstory():
    start = BUILD_TASK.index("- `protagonist_appearance`")
    end = BUILD_TASK.index("- `locations`")
    part = BUILD_TASK[start:end]
    assert "nghề" in part and "quá khứ" in part and "không chép" in part


# --- bộ đếm mềm -----------------------------------------------------------------------------------


def test_variety_counts_openings_hair_and_the_word_trong():
    got = appearance_variety(_package(
        a="Trông ngoài ba mươi, vai rộng, tóc đen buộc gọn.",
        b="Trông gần năm mươi, thấp đậm, tóc đen lẫn bạc cắt sát.",
        c="Mái tóc bạc phơ rũ qua vai, mắt sâu, gò má cao.",
        d="Gầy cao, mặt dài, tóc nâu đỏ xoăn nhẹ.",
    ))
    assert got["characters"] == 5 and got["with_appearance"] == 4  # nhân vật không tả không tính
    assert got["starts_with_trong"] == 2
    assert got["opening_repeats"] == 1  # a, b cùng mở "Trông"; c, d mở khác
    assert got["hair"] == {"đen": 2, "bạc": 1, "nâu": 1}
    assert got["hair_repeats"] == 1  # 4 nhân vật có màu tóc, 3 màu khác nhau


def test_variety_ignores_case_punctuation_and_unicode_form():
    import unicodedata

    nfd = unicodedata.normalize("NFD", "TRÔNG ngoài hai mươi, TÓC ĐEN dài.")
    got = appearance_variety(_package(a=nfd, b="trông già hơn tuổi: tóc đen ngắn."))
    assert got["starts_with_trong"] == 2 and got["opening_repeats"] == 1
    assert got["hair"] == {"đen": 2}


def test_variety_marks_unknown_hair_instead_of_guessing():
    got = appearance_variety(_package(a="Cao gầy, đầu cạo trọc.", b="Thấp đậm, tóc rối."))
    assert got["hair"] == {"không rõ": 2} and got["hair_repeats"] == 1


def test_variety_of_a_package_without_looks_is_all_zero():
    got = appearance_variety(ChangePackage.model_validate({
        "commit_id": "c0", "nodes": [{"id": "x", "label": "Character", "props": {"name": "X"}}],
        "edges": []}))
    assert got == {"characters": 1, "with_appearance": 0, "starts_with_trong": 0,
                   "opening_repeats": 0, "hair": {}, "hair_repeats": 0}


def test_variety_report_carries_numbers_only_never_the_text():
    got = appearance_variety(_package(a="Trông ngoài ba mươi, tóc đen.", b="Vai rộng, tóc bạc."))
    flat = repr(got)
    assert "ngoài ba mươi" not in flat and "Vai rộng" not in flat
