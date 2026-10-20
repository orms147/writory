"""Sự kiện tiến trình của một chương, gửi cho giao diện qua SSE (`api/play.py`; D-36, D-46).

Đây là schema cho người chơi (G1): chỉ chữ đã qua kiểm (cảnh đã soát, lựa chọn đã dò lộ) và câu lỗi
cố định của G12. Không có id nút, lớp truth, chi tiết kỹ thuật hay lỗi người canh. Dữ liệu cho
máy chủ (gói thay đổi, dữ liệu có cấu trúc của lựa chọn, lỗi còn lại) nằm ở `ChapterOutcome`.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from writory.errors import MESSAGES, ErrorCode, WritoryError

Stage = Literal["context", "outline", "write", "review", "commit", "choices"]
STAGE_LABELS: dict[str, str] = {
    "context": "Đang dựng bối cảnh",
    "outline": "Đang lên dàn ý",
    "write": "Đang viết",
    "review": "Đang soát",
    "commit": "Đang lưu chương",
    "choices": "Đang nghĩ lựa chọn",
}

ChoiceKind = Literal["action", "dialogue", "inner"]
Tone = Literal["truth", "lie", "silence"]
KIND_LABELS: dict[str, str] = {"action": "Hành động", "dialogue": "Lời thoại", "inner": "Nội tâm"}
TONE_LABELS: dict[str, str] = {"truth": "nói thật", "lie": "nói dối", "silence": "im lặng"}


class _Event(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StageEvent(_Event):
    type: Literal["stage"] = "stage"
    stage: Stage
    scene: int | None = None  # 1, 2, 3; None cho bước của cả chương
    attempt: int | None = None  # lượt viết/soát của cảnh: 1, hoặc 2 khi viết lại
    label: str


class SceneReady(_Event):
    type: Literal["scene_ready"] = "scene_ready"
    scene: int
    text: str  # đã chuẩn hoá dấu gạch (D-31) và đã qua kiểm


class SceneBlocked(_Event):
    """Cảnh không hiện (G2). Kết thúc chương; không có gì được ghi."""

    type: Literal["scene_blocked"] = "scene_blocked"
    scene: int
    code: ErrorCode
    message: str


class ChapterCommitted(_Event):
    type: Literal["chapter_committed"] = "chapter_committed"
    chapter: int


class PlayerChoice(_Event):
    """Lựa chọn hiện cho người chơi. `id` là mã mờ để gửi lại khi chọn; không có id nút."""

    id: str
    kind: ChoiceKind
    kind_label: str
    tone: Tone | None
    tone_label: str | None
    text: str


class ChoicesReady(_Event):
    type: Literal["choices_ready"] = "choices_ready"
    chapter: int
    choices: list[PlayerChoice]


class ErrorEvent(_Event):
    """Lỗi G12: mã và câu tiếng Việt cố định. Chi tiết chỉ vào log."""

    type: Literal["error"] = "error"
    code: ErrorCode
    message: str


ChapterEvent = Annotated[
    StageEvent | SceneReady | SceneBlocked | ChapterCommitted | ChoicesReady | ErrorEvent,
    Field(discriminator="type"),
]


def stage(name: Stage, *, scene: int | None = None, attempt: int | None = None) -> StageEvent:
    return StageEvent(stage=name, scene=scene, attempt=attempt, label=STAGE_LABELS[name])


def error_event(err: WritoryError) -> ErrorEvent:
    payload = err.player_payload()
    return ErrorEvent(code=err.code, message=payload["message"])


def blocked_event(scene: int) -> SceneBlocked:
    code = ErrorCode.SCENE_LEAK_BLOCKED
    return SceneBlocked(scene=scene, code=code, message=MESSAGES[code].text())
