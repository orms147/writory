"""Kiểm tham số chung cho mọi hàm của lớp graph/ (G10: bắt buộc có story_id)."""


def require_story_id(story_id: str) -> None:
    if not isinstance(story_id, str) or not story_id.strip():
        raise ValueError("story_id bắt buộc và không được rỗng")


def require_chapter(chapter: int) -> None:
    if not isinstance(chapter, int) or chapter < 0:
        raise ValueError("chapter phải là số nguyên ≥ 0")
