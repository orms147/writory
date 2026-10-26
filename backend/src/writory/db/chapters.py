"""Truyện và chương trong Postgres, và luồng ghi một chương theo D-6.

0. Trước mọi lần ghi: gói đúng quy tắc theo chương (D-21), và từ chương 1, câu trích G3 của gói có
   nguyên văn trong văn các cảnh (`quote_problems`, D-106). Sai thì báo lỗi, không ghi gì.
1. Một transaction Postgres: kiểm thứ tự, ghi chương `pending` kèm gói thay đổi (outbox).
2. `apply_package` sang Neo4j (một transaction bên đó).
3. Thành công: đặt `committed` và tăng `stories.committed_chapter` trong một transaction.
4. Neo4j từ chối gói (`GraphWriteError`): `delete_commit`, đặt `failed`.
5. Lỗi khác (Neo4j không trả lời, tiến trình chết): chương ở lại `pending`; `reconcile_pending`
   áp lại sau. Áp lại an toàn vì `apply_package` theo `commit_id`.

`stories.committed_chapter` chỉ đổi ở bước 3 (G11). Mọi lần đọc đồ thị cho người chơi và cho
pipeline dùng `current_chapter`, nên dữ liệu của chương còn `pending` không lộ ra (D-21).
Các hàm nhận kết nối psycopg ở chế độ autocommit; mỗi bước tự mở transaction của nó.
"""

import logging
from dataclasses import dataclass

import psycopg
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from psycopg.types.json import Jsonb

from writory.errors import ErrorCode, WritoryError
from writory.graph import (
    ChangePackage,
    GraphWriteError,
    PlayerView,
    apply_package,
    chapter_rule_problems,
    delete_commit,
    player_view,
    protagonist_id,
    quote_problems,
)
from writory.graph.story import require_story_id
from writory.safety.redact import redact

log = logging.getLogger(__name__)


class ChapterError(WritoryError):
    """Lỗi khi ghi chương. Mỗi lớp con mang một mã G12; chi tiết chỉ vào log (đã redact)."""

    code = ErrorCode.CHAPTER_SAVE_FAILED

    def __init__(self, detail: str = "") -> None:
        super().__init__(type(self).code, detail)


class StoryNotFoundError(ChapterError):
    code = ErrorCode.STORY_NOT_FOUND


class ChapterPackageError(ChapterError):
    """Gói sai quy tắc theo chương hoặc trùng commit_id. Chưa ghi gì."""

    code = ErrorCode.CHAPTER_PACKAGE_INVALID


class ChapterQuoteError(ChapterError):
    """Câu trích G3 của gói không có nguyên văn trong văn chương (D-106). Chưa ghi gì."""

    code = ErrorCode.CHAPTER_QUOTE_NOT_IN_TEXT


class ChapterOrderError(ChapterError):
    """Số chương không phải chương kế tiếp chương đã commit. Chưa ghi gì."""

    code = ErrorCode.CHAPTER_OUT_OF_ORDER


class PendingChapterError(ChapterError):
    """Truyện còn một chương pending; phải reconcile trước khi ghi chương mới. Chưa ghi gì."""

    code = ErrorCode.CHAPTER_PENDING


class ChapterCommitError(ChapterError):
    """Neo4j từ chối gói. Đã gỡ theo commit_id và đặt chương là failed; truyện giữ nguyên."""

    code = ErrorCode.CHAPTER_SAVE_FAILED


@dataclass(frozen=True)
class StoryRecord:
    id: str
    owner_id: str | None
    length_level: str
    committed_chapter: int | None
    darkness_level: str | None = None  # khoá moderation.darkness_levels; None = mặc định (D-67)


@dataclass(frozen=True)
class ChapterRecord:
    number: int
    commit_id: str
    status: str
    error: str | None


@dataclass(frozen=True)
class ReconcileResult:
    story_id: str
    number: int
    commit_id: str
    status: str
    error: str | None


def create_story(
    conn: psycopg.Connection, story_id: str, *, length_level: str, owner_id: str | None = None,
    darkness_level: str | None = None,
) -> StoryRecord:
    require_story_id(story_id)
    conn.execute(
        "INSERT INTO stories (id, owner_id, length_level, darkness_level) VALUES (%s, %s, %s, %s)",
        (story_id, owner_id, length_level, darkness_level),
    )
    return get_story(conn, story_id)


def get_story(conn: psycopg.Connection, story_id: str) -> StoryRecord:
    row = conn.execute(
        "SELECT id, owner_id, length_level, committed_chapter, darkness_level FROM stories "
        "WHERE id = %s",
        (story_id,),
    ).fetchone()
    if row is None:
        raise StoryNotFoundError(f"không có truyện {story_id}")
    return StoryRecord(*row)


def get_owned_story(conn: psycopg.Connection, story_id: str, owner_id: str) -> StoryRecord:
    """Truyện của người này. Truyện của người khác báo giống truyện không có (G10, 404)."""
    story = get_story(conn, story_id)
    if story.owner_id != owner_id:
        raise StoryNotFoundError(f"truyện {story_id} không thuộc người này")
    return story


def chapter_scenes(conn: psycopg.Connection, story_id: str, number: int) -> list[str] | None:
    """Văn các cảnh của một chương đã commit (đúng chữ đã hiện cho người chơi); None nếu chưa có."""
    row = conn.execute(
        "SELECT scenes FROM chapters WHERE story_id = %s AND number = %s AND status = 'committed'",
        (story_id, number),
    ).fetchone()
    return None if row is None else list(row[0])


def delete_story_record(conn: psycopg.Connection, story_id: str) -> None:
    """Xoá truyện khỏi Postgres (chương và gói xoá theo). Đồ thị xoá riêng: graph.delete_story."""
    require_story_id(story_id)
    conn.execute("DELETE FROM stories WHERE id = %s", (story_id,))


def current_chapter(conn: psycopg.Connection, story_id: str) -> int | None:
    """Chương hiện hành: chương đã commit cuối cùng (None = chưa có). Hàm DUY NHẤT trả giá trị
    này; mọi truy vấn đồ thị cho người chơi và cho pipeline lấy chương từ đây."""
    return get_story(conn, story_id).committed_chapter


def committed_player_view(conn: psycopg.Connection, driver: Driver, story_id: str) -> PlayerView:
    """`player_view` ở chương hiện hành. Chưa commit chương nào thì rỗng."""
    chapter = current_chapter(conn, story_id)
    if chapter is None:
        return PlayerView(story_id, 0, (), ())
    return player_view(driver, story_id, chapter)


def chapter_records(conn: psycopg.Connection, story_id: str) -> list[ChapterRecord]:
    rows = conn.execute(
        "SELECT number, commit_id, status, error FROM chapters WHERE story_id = %s "
        "ORDER BY number, created_at",
        (story_id,),
    ).fetchall()
    return [ChapterRecord(*r) for r in rows]


def commit_chapter(
    conn: psycopg.Connection,
    driver: Driver,
    story_id: str,
    number: int,
    scenes: list[str],
    package: ChangePackage,
) -> ChapterRecord:
    require_story_id(story_id)
    problems = chapter_rule_problems(package, number)
    if problems:
        raise ChapterPackageError("; ".join(problems))
    if number >= 1:  # chương 0: câu trích là dòng của thiết lập truyện (D-74), không phải văn
        problems = quote_problems(package, scenes, protagonist=_protagonist(driver, story_id, package))
        if problems:
            detail = f"truyện {story_id} chương {number}: " + "; ".join(problems)
            log.warning("không ghi chương: câu trích không có trong văn (G3): %s", redact(detail))
            raise ChapterQuoteError(detail)
    _record_pending(conn, story_id, number, scenes, package)
    _apply(conn, driver, story_id, package)
    _mark_committed(conn, story_id, number, package.commit_id)
    return ChapterRecord(number, package.commit_id, "committed", None)


def _protagonist(driver: Driver, story_id: str, package: ChangePackage) -> str:
    """Id nhân vật chính cho kiểm G3: nút của chính gói (truyện mẫu khai nhân vật chính ở chương 1),
    không thì đọc đồ thị. Gói không có KNOWS thì không cần (không đọc Neo4j)."""
    if not any(e.type == "KNOWS" for e in package.edges):
        return ""
    for n in package.nodes:
        if n.label == "Character" and n.props.get("is_protagonist") is True:
            return n.id
    return protagonist_id(driver, story_id)


def reconcile_pending(
    conn: psycopg.Connection, driver: Driver, story_id: str | None = None
) -> list[ReconcileResult]:
    """Áp lại mọi chương còn pending (của một truyện, hoặc của mọi truyện)."""
    rows = conn.execute(
        "SELECT c.story_id, c.number, c.commit_id, p.package "
        "FROM chapters c JOIN change_packages p USING (story_id, commit_id) "
        "WHERE c.status = 'pending' AND (%s::text IS NULL OR c.story_id = %s::text) "
        "ORDER BY c.story_id, c.number",
        (story_id, story_id),
    ).fetchall()
    results = []
    for sid, number, commit_id, raw in rows:
        package = ChangePackage.model_validate(raw)
        try:
            _apply(conn, driver, sid, package)
            _mark_committed(conn, sid, number, commit_id)
            results.append(ReconcileResult(sid, number, commit_id, "committed", None))
        except ChapterCommitError as exc:
            results.append(ReconcileResult(sid, number, commit_id, "failed", str(exc)))
        except (Neo4jError, DriverError) as exc:
            results.append(ReconcileResult(sid, number, commit_id, "pending", redact(str(exc))))
    return results


def _record_pending(
    conn: psycopg.Connection,
    story_id: str,
    number: int,
    scenes: list[str],
    package: ChangePackage,
) -> None:
    try:
        with conn.transaction():
            row = conn.execute(
                "SELECT committed_chapter FROM stories WHERE id = %s FOR UPDATE", (story_id,)
            ).fetchone()
            if row is None:
                raise StoryNotFoundError(f"không có truyện {story_id}")
            pending = conn.execute(
                "SELECT number FROM chapters WHERE story_id = %s AND status = 'pending'",
                (story_id,),
            ).fetchone()
            if pending is not None:
                raise PendingChapterError(f"chương {pending[0]} còn pending, cần reconcile trước")
            expected = 0 if row[0] is None else row[0] + 1
            if number != expected:
                raise ChapterOrderError(f"chương kế tiếp là {expected}, không phải {number}")
            conn.execute(
                "INSERT INTO chapters (story_id, commit_id, number, status, scenes) "
                "VALUES (%s, %s, %s, 'pending', %s)",
                (story_id, package.commit_id, number, Jsonb(scenes)),
            )
            conn.execute(
                "INSERT INTO change_packages (story_id, commit_id, package) VALUES (%s, %s, %s)",
                (story_id, package.commit_id, Jsonb(package.model_dump(mode="json", by_alias=True))),
            )
    except psycopg.errors.UniqueViolation as exc:
        raise ChapterPackageError(f"commit_id {package.commit_id} đã dùng trong truyện") from exc


def _apply(conn: psycopg.Connection, driver: Driver, story_id: str, package: ChangePackage) -> None:
    try:
        apply_package(driver, story_id, package)
    except GraphWriteError as exc:
        # Transaction Neo4j đã rollback; gỡ thêm theo commit_id cho chắc (D-6 bước 4).
        delete_commit(driver, story_id, package.commit_id)
        _mark_failed(conn, story_id, package.commit_id, redact(str(exc)))
        raise ChapterCommitError(f"commit {package.commit_id}: {exc}") from exc


def _mark_committed(conn: psycopg.Connection, story_id: str, number: int, commit_id: str) -> None:
    with conn.transaction():
        updated = conn.execute(
            "UPDATE chapters SET status = 'committed', updated_at = now() "
            "WHERE story_id = %s AND commit_id = %s AND status = 'pending'",
            (story_id, commit_id),
        ).rowcount
        if updated != 1:
            raise ChapterError(f"chương {commit_id} không còn pending")
        previous = None if number == 0 else number - 1
        updated = conn.execute(
            "UPDATE stories SET committed_chapter = %s, updated_at = now() "
            "WHERE id = %s AND committed_chapter IS NOT DISTINCT FROM %s::integer",
            (number, story_id, previous),
        ).rowcount
        if updated != 1:
            raise ChapterError(f"truyện {story_id} không ở chương {previous}")


def _mark_failed(conn: psycopg.Connection, story_id: str, commit_id: str, error: str) -> None:
    conn.execute(
        "UPDATE chapters SET status = 'failed', error = %s, updated_at = now() "
        "WHERE story_id = %s AND commit_id = %s AND status = 'pending'",
        (error, story_id, commit_id),
    )
