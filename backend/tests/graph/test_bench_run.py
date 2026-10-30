"""Lệnh chạy cả truyện trên Neo4j + Postgres thật (D-42): `--dry-run` qua dòng lệnh, story_id mới
mỗi lần chạy, chương ghi vào kho thật theo D-6. Model giả, không key."""

import json
import os

import pytest
import yaml

from tests.pipeline_fixtures import FIRST_PERSON, make_config
from writory.config import load_config
from writory.db import (
    StoryNotFoundError,
    chapter_records,
    current_chapter,
    delete_story_record,
    get_story,
)
from writory.graph import delete_story, player_view, story_snapshot
from writory.pipeline import bench_run

pytestmark = pytest.mark.graph

_DEFAULTS = {  # như tests/graph/conftest.py
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USER": "neo4j",
    "NEO4J_PASSWORD": "change-me-local",
    "POSTGRES_DSN": "postgresql://writory:change-me-local@localhost:5432/writory",
}


@pytest.fixture
def services_env(monkeypatch):
    for name, value in _DEFAULTS.items():
        monkeypatch.setenv(name, os.environ.get(name, value))
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)  # dry-run không cần key


def _cli(tmp_path, *extra: str, out_name: str = "out") -> tuple[int, dict]:
    """Chạy `main` với bản sao config thử và đề mẫu có giá cho đúng các model của config đó."""
    config = (load_config(tmp_path / "config") if (tmp_path / "config").exists()
              else make_config(tmp_path, **FIRST_PERSON))
    base, _ = bench_run.load_scenario(bench_run.DEFAULT_SCENARIO)
    data = base.model_dump(mode="json", by_alias=True)
    data["prices"] = {info["model"]: {"in": 0.1, "out": 0.5}
                      for info in bench_run.models_in_use(config, base).values() if info["model"]}
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    out = tmp_path / out_name
    code = bench_run.main(["--dry-run", "--scenario", str(scenario),
                           "--config-dir", str(tmp_path / "config"), "--out", str(out),
                           "--env-file", str(tmp_path / "khong-co.env"), *extra])
    return code, json.loads((out / "meta.json").read_text(encoding="utf-8"))


def test_dry_run_cli_writes_a_real_story(tmp_path, services_env, pg, driver):
    code, meta = _cli(tmp_path, "--chapters", "2", "--keep-story")
    sid = meta["story_id"]
    try:
        assert code == bench_run.EXIT_OK and meta["status"] == "done"
        assert sid.startswith("run-") and meta["exit_code"] == 0
        # Repo công khai: meta không mang đường dẫn tuyệt đối của máy chạy.
        assert (meta["scenario"]["path"], meta["config"]["dir"]) == ("scenario.yaml", "config")
        assert current_chapter(pg, sid) == 2
        assert [(r.number, r.status) for r in chapter_records(pg, sid)] == [
            (0, "committed"), (1, "committed"), (2, "committed")]
        # Đồ thị thật: người chơi biết nhân vật chính (đã chọn lúc khởi tạo, D-74) và đúng nhân vật
        # được hé lộ trên trang, bằng tên đã thấy.
        view = player_view(driver, sid, 2)
        assert [e.text for e in view.entries] == ["Cố Trường Phong", bench_run.DRY_RUN_NPC_NAME]
        assert [e.is_protagonist for e in view.entries] == [True, False]
        out = tmp_path / "out"
        for name in ("setup.json", "events.jsonl", "calls.jsonl", "report.json", "summary.md",
                     "truth_dump.json", "chapters/ch01.md", "chapters/ch02.md"):
            assert (out / name).is_file(), name
        dump = json.loads((out / "truth_dump.json").read_text(encoding="utf-8"))
        assert dump["story_id"] == sid and dump["final"]["chapter"] == 2
        assert sorted(dump["packages"]) == ["0", "1", "2"]
    finally:
        delete_story_record(pg, sid)
        delete_story(driver, sid)


def test_dry_run_cli_removes_its_story_by_default(tmp_path, services_env, pg, driver):
    code, meta = _cli(tmp_path, "--chapters", "1")
    sid = meta["story_id"]
    assert code == bench_run.EXIT_OK and meta["story_deleted"] is True
    with pytest.raises(StoryNotFoundError):
        get_story(pg, sid)
    assert story_snapshot(driver, sid).node_count == 0


def test_dry_run_cli_with_a_style_guide_and_a_prompt_variant_records_both(
        tmp_path, services_env, monkeypatch):
    """D-109: `--style-guide` và `--prompt-variant` đi từ dòng lệnh tới `meta.json` (hash file, đề bị
    thay), chạy trên kho thật; mặc định không thay gì."""
    variants = tmp_path / "prompts"
    (variants / "moi").mkdir(parents=True)
    (variants / "moi" / "choices_system.md").write_text("ĐỀ LỰA CHỌN BIẾN THỂ", encoding="utf-8")
    monkeypatch.setattr(bench_run, "PROMPTS_DIR", variants)
    guide = tmp_path / "van-phong.md"
    guide.write_text("VĂN PHONG MỚI\n", encoding="utf-8")
    code, meta = _cli(tmp_path, "--chapters", "1", "--style-guide", str(guide),
                      "--prompt-variant", "moi")
    assert code == bench_run.EXIT_OK
    assert meta["prompt_variant"]["name"] == "moi"
    assert meta["prompt_variant"]["overrides"] == ["choices_system"]
    assert meta["prompt_versions_overridden"] == ["writer", "choices"]
    assert meta["style_guide_path"] == "van-phong.md"  # repo công khai: không đường dẫn tuyệt đối
    assert meta["style_guide_sha256"] == bench_run._sha256("VĂN PHONG MỚI".encode())


def test_resume_continues_the_same_story_on_the_real_stores(tmp_path, services_env, pg, driver):
    """D-124: lượt dừng ở chương 2 chạy tiếp vào thư mục mới, cùng story_id, chương 1-2 không đổi."""
    code1, meta1 = _cli(tmp_path, "--chapters", "2", "--keep-story")
    sid = meta1["story_id"]
    try:
        assert code1 == bench_run.EXIT_OK and current_chapter(pg, sid) == 2
        before = story_snapshot(driver, sid)
        code2, meta2 = _cli(tmp_path, "--chapters", "3", "--keep-story",
                            "--resume", str(tmp_path / "out"), out_name="out2")
        assert code2 == bench_run.EXIT_OK and meta2["story_id"] == sid
        assert meta2["resumed_from"] == "out" and meta2["resume_points"][0]["chapter"] == 3
        assert current_chapter(pg, sid) == 3
        assert [(r.number, r.status) for r in chapter_records(pg, sid)] == [
            (0, "committed"), (1, "committed"), (2, "committed"), (3, "committed")]
        after = story_snapshot(driver, sid)
        assert after.node_count > before.node_count  # chương 3 ghi thêm, không mất gì
        out2 = tmp_path / "out2"
        dump = json.loads((out2 / "truth_dump.json").read_text(encoding="utf-8"))
        assert sorted(dump["packages"]) == ["0", "1", "2", "3"] and dump["final"]["chapter"] == 3
        for name in ("chapters/ch01.md", "chapters/ch02.md", "chapters/ch03.md", "report.json"):
            assert (out2 / name).is_file(), name
    finally:
        delete_story_record(pg, sid)
        delete_story(driver, sid)


def test_resume_is_refused_before_anything_is_written_when_the_story_is_gone(
        tmp_path, services_env, pg, driver):
    code1, meta1 = _cli(tmp_path, "--chapters", "1", "--keep-story")
    sid = meta1["story_id"]
    delete_story_record(pg, sid)
    delete_story(driver, sid)
    with pytest.raises(StoryNotFoundError):
        get_story(pg, sid)
    code2 = _resume_main(tmp_path, "--dry-run", "--chapters", "3")
    assert code1 == bench_run.EXIT_OK and code2 == bench_run.EXIT_CONFIG
    assert not (tmp_path / "out2").exists()


def _resume_main(tmp_path, *extra: str) -> int:
    """Chạy tiếp `out` vào `out2` qua dòng lệnh; thêm `--dry-run` hay không là việc của test."""
    return bench_run.main(["--scenario", str(tmp_path / "scenario.yaml"),
                           "--config-dir", str(tmp_path / "config"),
                           "--out", str(tmp_path / "out2"), "--resume", str(tmp_path / "out"),
                           "--env-file", str(tmp_path / "khong-co.env"), *extra])


def test_a_dry_run_resume_of_a_real_run_never_touches_the_real_story(
        tmp_path, services_env, pg, driver):
    """D-130: `--resume <thư mục thật> --dry-run --resume-allow-drift` từng cho model giả viết vào
    story_id thật rồi xoá truyện đó lúc xong (dry-run không --keep-story). Nay từ chối trước khi ghi."""
    code1, meta1 = _cli(tmp_path, "--chapters", "1", "--keep-story")
    sid = meta1["story_id"]
    try:
        meta1["dry_run"] = False  # thư mục của một lượt thật
        (tmp_path / "out" / "meta.json").write_text(json.dumps(meta1, ensure_ascii=False),
                                                    encoding="utf-8")
        before = story_snapshot(driver, sid)
        code2 = _resume_main(tmp_path, "--dry-run", "--resume-allow-drift", "--chapters", "3")
        assert code1 == bench_run.EXIT_OK and code2 == bench_run.EXIT_CONFIG
        assert not (tmp_path / "out2").exists()
        assert get_story(pg, sid) is not None and current_chapter(pg, sid) == 1
        assert story_snapshot(driver, sid).node_count == before.node_count
    finally:
        delete_story_record(pg, sid)
        delete_story(driver, sid)


def test_resume_refuses_a_story_with_a_chapter_stuck_pending(tmp_path, services_env, pg, driver):
    """D-130: chương `pending` (tiến trình chết lúc ghi) thì từ chối ngay, không tự sửa kho."""
    code1, meta1 = _cli(tmp_path, "--chapters", "1", "--keep-story")
    sid = meta1["story_id"]
    try:
        pg.execute("INSERT INTO chapters (story_id, commit_id, number, status, scenes) "
                   "VALUES (%s, %s, 2, 'pending', %s)",
                   (sid, f"{sid}-ch2", json.dumps(["Chương ghi dở."])))
        code2 = _resume_main(tmp_path, "--dry-run", "--keep-story", "--chapters", "3")
        assert code1 == bench_run.EXIT_OK and code2 == bench_run.EXIT_CONFIG
        assert not (tmp_path / "out2").exists()
        assert [(r.number, r.status) for r in chapter_records(pg, sid)] == [
            (0, "committed"), (1, "committed"), (2, "pending")]  # kho giữ nguyên
    finally:
        delete_story_record(pg, sid)
        delete_story(driver, sid)
