"""Lệnh chạy cả truyện trên Neo4j + Postgres thật (D-42): `--dry-run` qua dòng lệnh, story_id mới
mỗi lần chạy, chương ghi vào kho thật theo D-6. Model giả, không key."""

import json
import os

import pytest
import yaml

from tests.pipeline_fixtures import FIRST_PERSON, make_config
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


def _cli(tmp_path, *extra: str) -> tuple[int, dict]:
    """Chạy `main` với bản sao config thử và đề mẫu có giá cho đúng các model của config đó."""
    config = make_config(tmp_path, **FIRST_PERSON)
    base, _ = bench_run.load_scenario(bench_run.DEFAULT_SCENARIO)
    data = base.model_dump(mode="json", by_alias=True)
    data["prices"] = {info["model"]: {"in": 0.1, "out": 0.5}
                      for info in bench_run.models_in_use(config, base).values() if info["model"]}
    scenario = tmp_path / "scenario.yaml"
    scenario.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    out = tmp_path / "out"
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
