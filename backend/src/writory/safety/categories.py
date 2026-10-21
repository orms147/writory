"""Danh mục loại nội dung và mức độ cho kiểm duyệt (G9, D-57). Chỉ có kiểu dữ liệu: danh sách
chính thức, mức xử lý từng loại và chữ mô tả nằm trong `config/moderation.yaml`.

Module này không import gì của `writory` để `config.py` dùng được mà không vòng import.
"""

from enum import IntEnum, StrEnum


class Category(StrEnum):
    SEXUAL_MINORS = "sexual_minors"  # tình dục liên quan trẻ vị thành niên
    REAL_WORLD_HARM = "real_world_harm"  # hướng dẫn gây hại dùng được ngoài đời thật
    INCITEMENT_REAL_GROUP = "incitement_real_group"  # kích động nhắm vào nhóm người thật
    POLITICAL_PROPAGANDA_REAL = "political_propaganda_real"  # tuyên truyền nhắm vào người/tổ chức thật
    VIOLENCE = "violence"
    GORE = "gore"
    ADULT_SEXUAL = "adult_sexual"  # tình dục giữa người trưởng thành


class Level(StrEnum):
    HARD_BLOCK = "hard_block"  # chặn cứng, độc lập với mức u tối; config không hạ được
    BLOCK = "block"  # chặn
    DARKNESS_LIMITED = "darkness_limited"  # cho tới trần của mức u tối


class Intensity(IntEnum):
    """Mức độ miêu tả của loại nội dung bị giới hạn theo mức u tối. Có thứ tự để so với trần."""

    NONE = 0
    MILD = 1
    STRONG = 2
    EXTREME = 3

    @classmethod
    def parse(cls, name: str) -> "Intensity":
        return cls[name.upper()]

