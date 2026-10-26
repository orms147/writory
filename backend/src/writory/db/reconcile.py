"""Áp lại chương kẹt `pending` mà không giẫm lên việc đang chạy (D-6, D-46, D-105).

`reconcile_pending` áp lại mọi chương `pending` nó thấy. Chương `pending` có thể là việc kẹt (tiến
trình chết, Neo4j không trả lời) hoặc là việc đang ghi ở tiến trình khác. Mọi đường ghi chương giữ
khoá `story` của truyện (viết chương: `api/play.get_chapter_job`; chương 0: `db.plans.start_story`),
và khoá đó tự nhả khi tiến trình chết. Nên ở đây mỗi truyện được giữ khoá đó trước khi áp lại:
giữ được thì chương `pending` là việc kẹt; không giữ được thì có việc đang chạy, bỏ qua.
"""

import logging

import psycopg
from neo4j import Driver

from writory.db.chapters import ReconcileResult, reconcile_pending
from writory.db.locks import StoryBusyError, job_lock
from writory.safety.redact import redact

log = logging.getLogger(__name__)


def reconcile_idle_stories(conn: psycopg.Connection, driver: Driver) -> list[ReconcileResult]:
    """Áp lại chương `pending` của mọi truyện không có việc đang chạy.

    Kết quả mỗi chương: `committed`, `failed` (Neo4j từ chối gói), `pending` (Neo4j không trả lời,
    hoặc lỗi bất ngờ ở truyện đó: tên lỗi trong `error`, sang truyện sau), `busy` (truyện đang giữ
    khoá, không đụng)."""
    rows = conn.execute(
        "SELECT story_id, number, commit_id FROM chapters WHERE status = 'pending' "
        "ORDER BY story_id, number"
    ).fetchall()
    by_story: dict[str, list[tuple[int, str]]] = {}
    for sid, number, commit_id in rows:
        by_story.setdefault(sid, []).append((number, commit_id))
    results: list[ReconcileResult] = []
    for sid, chapters in by_story.items():
        try:
            with job_lock(conn, "story", sid):
                results.extend(reconcile_pending(conn, driver, story_id=sid))
        except StoryBusyError:
            results.extend(ReconcileResult(sid, n, c, "busy", None) for n, c in chapters)
        except Exception as exc:  # noqa: BLE001 — một truyện hỏng không chặn truyện khác
            log.warning("áp lại truyện %s lỗi: %s", sid, redact(f"{type(exc).__name__}: {exc}"))
            results.extend(ReconcileResult(sid, n, c, "pending", type(exc).__name__)
                           for n, c in chapters)
    return results
