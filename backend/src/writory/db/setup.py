"""Phiên khởi tạo truyện trong Postgres (design §4.1, D-44).

Máy chủ giữ 3 lựa chọn của mỗi bước; trình duyệt chỉ gửi số thứ tự, cộng phần sửa nhân vật chính.
Mỗi thao tác là một câu lệnh có điều kiện, nên trạng thái phiên chỉ đổi khi thao tác hợp lệ (G11):
- lưu lựa chọn của một bước chỉ khi bước trước đã chọn và bước này chưa có lựa chọn (bộ lưu trước
  được giữ, để lựa chọn người chơi đã thấy không bị đổi);
- chọn một số thứ tự nằm trong bộ đã lưu; đổi lựa chọn thì xoá các bước sau, vì chúng dựa trên
  lựa chọn cũ;
- phiên đã tạo truyện (`story_id`) thì không đổi được nữa.
"""

from dataclasses import dataclass
from typing import Any, Literal

import psycopg
from psycopg.types.json import Jsonb

from writory.errors import ErrorCode, WritoryError

SetupStep = Literal["settings", "plots", "characters"]
STEPS: tuple[SetupStep, ...] = ("settings", "plots", "characters")
_INDEX = {"settings": "setting_index", "plots": "plot_index", "characters": "character_index"}


class SetupNotFoundError(WritoryError):
    def __init__(self, detail: str = "") -> None:
        super().__init__(ErrorCode.SETUP_NOT_FOUND, detail)


class SetupStepError(WritoryError):
    """Bước chưa làm được (bước trước chưa xong, số thứ tự ngoài bộ đã lưu) hoặc phiên đã xong."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(ErrorCode.SETUP_STEP_NOT_READY, detail)


@dataclass(frozen=True)
class SetupRecord:
    id: str
    owner_id: str
    choices: dict[str, Any]
    settings: list[dict[str, Any]] | None
    setting_index: int | None
    plots: list[dict[str, Any]] | None
    plot_index: int | None
    characters: list[dict[str, Any]] | None
    character_index: int | None
    protagonist: dict[str, Any] | None
    story_id: str | None

    def options(self, step: SetupStep) -> list[dict[str, Any]] | None:
        return getattr(self, step)

    def index(self, step: SetupStep) -> int | None:
        return getattr(self, _INDEX[step])

    def chosen(self, step: SetupStep) -> dict[str, Any] | None:
        options, index = self.options(step), self.index(step)
        return None if options is None or index is None else options[index]


_SELECT = (
    "SELECT id, owner_id, choices, settings, setting_index, plots, plot_index, characters, "
    "character_index, protagonist, story_id FROM setup_sessions WHERE id = %s"
)


def _load(conn: psycopg.Connection, session_id: str) -> SetupRecord:
    row = conn.execute(_SELECT, (session_id,)).fetchone()
    if row is None:
        raise SetupNotFoundError(f"không có phiên {session_id}")
    return SetupRecord(*row)


def create_setup(
    conn: psycopg.Connection, session_id: str, *, owner_id: str, choices: dict[str, Any]
) -> SetupRecord:
    conn.execute(
        "INSERT INTO setup_sessions (id, owner_id, choices) VALUES (%s, %s, %s)",
        (session_id, owner_id, Jsonb(choices)),
    )
    return _load(conn, session_id)


def get_setup(conn: psycopg.Connection, session_id: str, *, owner_id: str) -> SetupRecord:
    """Phiên của người khác cũng báo không có (G10), không nói phiên đó tồn tại."""
    rec = _load(conn, session_id)
    if rec.owner_id != owner_id:
        raise SetupNotFoundError(f"phiên {session_id} không thuộc người này")
    return rec


def _previous(step: SetupStep) -> SetupStep | None:
    i = STEPS.index(step)
    return STEPS[i - 1] if i else None


def _later(step: SetupStep) -> tuple[SetupStep, ...]:
    return STEPS[STEPS.index(step) + 1:]


def save_setup_options(
    conn: psycopg.Connection, session_id: str, step: SetupStep, options: list[dict[str, Any]]
) -> SetupRecord:
    """Lưu lựa chọn của một bước. Bước đã có lựa chọn thì giữ bộ cũ và trả nó."""
    prev = _previous(step)
    ready = f" AND {_INDEX[prev]} IS NOT NULL" if prev else ""
    updated = conn.execute(
        f"UPDATE setup_sessions SET {step} = %s, updated_at = now() "  # tên cột lấy từ STEPS, cố định
        f"WHERE id = %s AND story_id IS NULL AND {step} IS NULL{ready}",
        (Jsonb(options), session_id),
    ).rowcount
    rec = _load(conn, session_id)
    if updated == 1 or (rec.options(step) is not None and rec.story_id is None):
        return rec
    raise SetupStepError(f"phiên {session_id}: chưa lưu được lựa chọn bước {step}")


def choose_setup_option(
    conn: psycopg.Connection, session_id: str, step: SetupStep, index: int, *,
    protagonist: dict[str, Any] | None = None,
) -> SetupRecord:
    """Chọn lựa chọn thứ `index` (từ 0) của một bước. Bước nhân vật kèm nhân vật chính đã sửa.
    Đổi sang lựa chọn khác thì xoá lựa chọn và số đã chọn của các bước sau."""
    if (step == "characters") != (protagonist is not None):
        raise ValueError("protagonist chỉ đi cùng bước characters, và bước đó bắt buộc có")
    idx = _INDEX[step]
    sets = [f"{idx} = %(i)s"]
    for later in _later(step):
        for col in (later, _INDEX[later]):
            sets.append(f"{col} = CASE WHEN {idx} IS DISTINCT FROM %(i)s THEN NULL ELSE {col} END")
    if step == "characters":
        sets.append("protagonist = %(pc)s")
    else:
        sets.append(f"protagonist = CASE WHEN {idx} IS DISTINCT FROM %(i)s THEN NULL "
                    "ELSE protagonist END")
    updated = conn.execute(
        f"UPDATE setup_sessions SET {', '.join(sets)}, updated_at = now() "
        f"WHERE id = %(id)s AND story_id IS NULL AND {step} IS NOT NULL "
        f"AND %(i)s >= 0 AND %(i)s < jsonb_array_length({step})",
        {"i": index, "id": session_id,
         "pc": Jsonb(protagonist) if protagonist is not None else None},
    ).rowcount
    rec = _load(conn, session_id)
    if updated != 1:
        raise SetupStepError(f"phiên {session_id}: không chọn được {index} ở bước {step}")
    return rec


def finish_setup(conn: psycopg.Connection, session_id: str, story_id: str) -> SetupRecord:
    """Gắn truyện vừa tạo vào phiên và chuyển chi phí khởi tạo sang truyện, trong một transaction.
    Gọi sau khi chương 0 đã ghi xong (G11)."""
    with conn.transaction():
        updated = conn.execute(
            "UPDATE setup_sessions SET story_id = %s, updated_at = now() "
            "WHERE id = %s AND story_id IS NULL AND protagonist IS NOT NULL",
            (story_id, session_id),
        ).rowcount
        if updated != 1:
            raise SetupStepError(f"phiên {session_id}: chưa chọn nhân vật hoặc đã tạo truyện")
        conn.execute(
            "UPDATE llm_costs SET story_id = %s WHERE setup_session_id = %s AND story_id IS NULL",
            (story_id, session_id),
        )
    return _load(conn, session_id)
