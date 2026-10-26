"""Áp lại chương kẹt `pending` lúc app khởi động (D-6, D-105), trên Postgres và Neo4j thật.

Khởi động thật: `create_app` ở `APP_ENV=prod` với `prepare_storage` mặc định (migration →
`ensure_schema` → áp lại). Truyện đang có việc giữ khoá `story` (D-46) thì không bị đụng.
"""

import psycopg
import pytest
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable

import writory.api.app as app_mod
import writory.db.chapters as chapters_mod
import writory.db.plans as plans_mod
from tests.graph.test_deploy_storage import storage_settings
from writory.api import create_app
from writory.config import load_config
from writory.db import (
    StoryBusyError,
    chapter_records,
    commit_chapter,
    create_story,
    current_chapter,
    job_lock,
    reconcile_idle_stories,
    start_story,
)
from writory.graph import ChangePackage, read_sample, story_snapshot
from writory.pipeline.story_plan import StoryPlan

pytestmark = pytest.mark.graph

SAMPLE = read_sample()
CFG = load_config()


async def _ok() -> bool:
    return True


def _scenes(n):
    return [SAMPLE.chapters[n].text] if SAMPLE.chapters[n].text else []


def _story_with(pg, driver, sid, up_to):
    create_story(pg, sid, length_level="short")
    for n in range(up_to + 1):
        commit_chapter(pg, driver, sid, n, _scenes(n), SAMPLE.chapters[n].package)


def _stuck_pending(pg, driver, sid, number, package, monkeypatch):
    """Ghi chương `pending` kèm gói trong outbox, như khi Neo4j không trả lời giữa chừng. Văn là
    văn chương mẫu, để câu trích của gói qua kiểm G3 ở bước ghi (D-106)."""

    def down(*_args, **_kwargs):
        raise ServiceUnavailable("neo4j tắt (giả lập)")

    monkeypatch.setattr(chapters_mod, "apply_package", down)
    with pytest.raises(ServiceUnavailable):
        commit_chapter(pg, driver, sid, number, _scenes(number), package)
    monkeypatch.undo()
    assert chapter_records(pg, sid)[-1].status == "pending"


def _status(pg, sid, commit_id):
    return next(r.status for r in chapter_records(pg, sid) if r.commit_id == commit_id)


def _start_prod_app(isolated_postgres, monkeypatch):
    """Khởi động app prod thật trên kho test. Mật khẩu test là mật khẩu mẫu, nên bỏ qua phép kiểm
    cấu hình prod (`prod_problems`, có test riêng ở tests/unit/test_deploy.py)."""
    monkeypatch.setattr(app_mod, "prod_problems", lambda _s: [])
    settings = storage_settings(isolated_postgres).model_copy(
        update={"app_env": "prod", "auth_mode": "invite"})
    return TestClient(create_app(settings, health_checks={"neo4j": _ok}, config=CFG))


def test_app_startup_reconciles_a_pending_chapter(pg, driver, new_db_story_id, isolated_postgres,
                                                  monkeypatch):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    _stuck_pending(pg, driver, sid, 2, SAMPLE.chapters[2].package, monkeypatch)
    assert current_chapter(pg, sid) == 1

    with _start_prod_app(isolated_postgres, monkeypatch) as client:
        # Đã áp xong trước khi nhận yêu cầu đầu.
        assert _status(pg, sid, SAMPLE.chapters[2].package.commit_id) == "committed"
        assert current_chapter(pg, sid) == 2
        assert client.get("/health").status_code == 200


def test_app_startup_marks_a_rejected_package_failed_and_still_starts(
    pg, driver, new_db_story_id, isolated_postgres, monkeypatch
):
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    graph_before = story_snapshot(driver, sid)
    bad = ChangePackage.model_validate({
        "commit_id": "bad-ch2",
        "edges": [{"type": "HOLDS", "from": "minh", "to": "ghost_item", "valid_from_chapter": 2}],
    })
    _stuck_pending(pg, driver, sid, 2, bad, monkeypatch)

    with _start_prod_app(isolated_postgres, monkeypatch) as client:
        assert client.get("/health").status_code == 200
    # Neo4j từ chối gói: chương `failed`, truyện và đồ thị giữ nguyên, viết lại được (D-6 bước 4).
    failed = [r for r in chapter_records(pg, sid) if r.commit_id == "bad-ch2"]
    assert failed[0].status == "failed" and "ghost_item" in failed[0].error
    assert current_chapter(pg, sid) == 1
    assert story_snapshot(driver, sid) == graph_before
    commit_chapter(pg, driver, sid, 2, _scenes(2), SAMPLE.chapters[2].package)
    assert current_chapter(pg, sid) == 2


def test_app_startup_skips_a_story_whose_lock_is_held(pg, driver, new_db_story_id,
                                                      isolated_postgres, monkeypatch):
    """Một tiến trình khác đang viết truyện này (giữ khoá `story`, D-46): chương `pending` của nó
    là việc đang chạy, không phải việc kẹt. Không áp, không đổi trạng thái."""
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    _stuck_pending(pg, driver, sid, 2, SAMPLE.chapters[2].package, monkeypatch)
    commit_id = SAMPLE.chapters[2].package.commit_id
    graph_pending = story_snapshot(driver, sid)

    with (psycopg.connect(isolated_postgres, autocommit=True) as writer,
          job_lock(writer, "story", sid)):
        with _start_prod_app(isolated_postgres, monkeypatch):
            pass
        assert _status(pg, sid, commit_id) == "pending"
        assert current_chapter(pg, sid) == 1
        assert story_snapshot(driver, sid) == graph_pending
        busy = [r for r in reconcile_idle_stories(pg, driver) if r.story_id == sid]
        assert [r.status for r in busy] == ["busy"]
    # Khoá nhả: lần khởi động sau (hay lệnh tay) áp được.
    done = [r for r in reconcile_idle_stories(pg, driver) if r.story_id == sid]
    assert [r.status for r in done] == ["committed"]
    assert current_chapter(pg, sid) == 2


def test_reconcile_holds_the_story_lock_while_applying(pg, driver, new_db_story_id,
                                                       isolated_postgres, monkeypatch):
    """Trong lúc áp lại, yêu cầu viết chương của truyện đó (cùng khoá) báo bận."""
    sid = new_db_story_id()
    _story_with(pg, driver, sid, 1)
    _stuck_pending(pg, driver, sid, 2, SAMPLE.chapters[2].package, monkeypatch)
    real_apply = chapters_mod.apply_package
    seen: list[bool] = []

    def apply_and_probe(drv, story_id, package):
        with psycopg.connect(isolated_postgres, autocommit=True) as other:
            try:
                with job_lock(other, "story", story_id):
                    seen.append(False)
            except StoryBusyError:
                seen.append(True)
        return real_apply(drv, story_id, package)

    monkeypatch.setattr(chapters_mod, "apply_package", apply_and_probe)
    results = [r for r in reconcile_idle_stories(pg, driver) if r.story_id == sid]
    assert [r.status for r in results] == ["committed"]
    assert seen == [True]


def test_chapter_0_is_written_under_the_story_lock(pg, driver, new_db_story_id,
                                                   isolated_postgres, monkeypatch):
    """Khởi tạo ghi chương 0 dưới khoá `story` của truyện mới, như viết chương: tiến trình khác
    khởi động đúng lúc đó không áp lại chương 0 đang ghi dở."""
    sid = new_db_story_id()
    real_commit = plans_mod.commit_chapter
    seen: list[bool] = []

    def commit_and_probe(conn, drv, story_id, number, scenes, package):
        with psycopg.connect(isolated_postgres, autocommit=True) as other:
            try:
                with job_lock(other, "story", story_id):
                    seen.append(False)
            except StoryBusyError:
                seen.append(True)
        return real_commit(conn, drv, story_id, number, scenes, package)

    monkeypatch.setattr(plans_mod, "commit_chapter", commit_and_probe)
    plan = StoryPlan.model_validate({"acts": [{"name": "Một", "from_chapter": 1,
                                               "to_chapter": 3}]})
    start_story(pg, driver, sid, owner_id="dev", length_level="short", brief="b", plan=plan,
                initial=SAMPLE.chapters[0].package)
    assert seen == [True]
    assert current_chapter(pg, sid) == 0
