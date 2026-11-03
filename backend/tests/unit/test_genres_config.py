"""Danh mục thể loại `config/genres.yaml` (D-160): chủ dự án thêm thể loại bằng cách sửa file, app kiểm lúc nạp."""

import shutil
from pathlib import Path

import pytest
import yaml

from writory.config import REPO_CONFIG_DIR, ConfigError, load_config


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    return target


def _edit_genres(config_dir: Path, edit) -> None:
    path = config_dir / "genres.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def test_repo_genres_load():
    cfg = load_config()
    genres = cfg.genres
    sang_van = genres.get("sang_van")
    assert sang_van is not None and "audio" in sang_van.styles
    assert genres.for_style("prose") and genres.for_style("audio")
    assert genres.max_selected == 3
    lim = genres.limits
    assert (lim.label, lim.hint, lim.setup_brief, lim.outline_brief, lim.voice_brief) == (60, 140, 1500, 1200, 1200)
    assert cfg.limits.input.story_idea_max_chars == 1500
    assert genres.get("khong_co") is None


def test_duplicate_key_rejected(config_dir):
    _edit_genres(config_dir, lambda d: d["genres"].append(dict(d["genres"][0])))
    with pytest.raises(ConfigError, match="trùng"):
        load_config(config_dir)


def test_bad_key_rejected(config_dir):
    def edit(d):
        d["genres"][0]["key"] = "Tu Tien"
    _edit_genres(config_dir, edit)
    with pytest.raises(ConfigError, match="key"):
        load_config(config_dir)


def test_brief_over_limit_rejected(config_dir):
    def edit(d):
        d["genres"][0]["setup_brief"] = "x" * (d["limits"]["setup_brief"] + 1)
    _edit_genres(config_dir, edit)
    with pytest.raises(ConfigError, match="setup_brief"):
        load_config(config_dir)


def test_empty_styles_rejected(config_dir):
    def edit(d):
        d["genres"][0]["styles"] = []
    _edit_genres(config_dir, edit)
    with pytest.raises(ConfigError, match="styles"):
        load_config(config_dir)


def test_missing_sang_van_rejected(config_dir):
    """Truyện audio tạo trước D-160 không có khoá thể loại và được coi là sảng văn: thể loại này phải còn."""
    _edit_genres(config_dir, lambda d: d.update(genres=[g for g in d["genres"] if g["key"] != "sang_van"]))
    with pytest.raises(ConfigError, match="sang_van"):
        load_config(config_dir)
