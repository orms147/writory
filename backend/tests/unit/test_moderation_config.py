"""Danh mục kiểm duyệt trong config/moderation.yaml (G9, D-57): đủ danh mục, bất biến chặn cứng,
trần mức u tối."""

import shutil
from pathlib import Path

import pytest
import yaml

from writory.config import REPO_CONFIG_DIR, ConfigError, load_config
from writory.safety.categories import Category, Intensity, Level


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    return target


def edit(config_dir: Path, change) -> None:
    path = config_dir / "moderation.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")


def test_repo_catalogue_is_approved_and_covers_every_category():
    cfg = load_config().moderation
    assert cfg.draft is False  # chủ dự án duyệt 21/10/2026 (D-57)
    assert set(cfg.categories) == set(Category)
    assert all(rule.description.strip() for rule in cfg.categories.values())


def test_minors_sexual_content_is_hard_block_and_cannot_be_downgraded(config_dir):
    assert load_config().moderation.categories[Category.SEXUAL_MINORS].level is Level.HARD_BLOCK
    for level in ("block", "darkness_limited"):
        edit(config_dir, lambda d, lv=level: d["categories"]["sexual_minors"].update(level=lv))
        with pytest.raises(ConfigError, match="sexual_minors"):
            load_config(config_dir)


def test_catalogue_uses_all_three_levels():
    levels = {rule.level for rule in load_config().moderation.categories.values()}
    assert levels == set(Level)


def test_darkness_ceilings_cover_limited_categories_and_stay_under_the_cap():
    cfg = load_config().moderation
    limited = {c for c, r in cfg.categories.items() if r.level is Level.DARKNESS_LIMITED}
    assert limited == {Category.VIOLENCE, Category.GORE, Category.ADULT_SEXUAL}  # bản nháp
    assert set(cfg.darkness_cap) == limited
    for name, level in cfg.darkness_levels.items():
        assert set(level.ceilings) == limited, name
        for category, ceiling in level.ceilings.items():
            assert ceiling <= cfg.darkness_cap[category], (name, category)
    assert Intensity.EXTREME > Intensity.NONE  # có thứ tự để so


def test_ceiling_lookup_uses_default_for_none_and_rejects_unknown_level():
    cfg = load_config().moderation
    assert cfg.ceiling(None) == cfg.darkness_levels[cfg.default_darkness_level].ceilings
    first = next(iter(cfg.darkness_levels))
    assert cfg.ceiling(first) == cfg.darkness_levels[first].ceilings
    with pytest.raises(ValueError, match="không có"):
        cfg.ceiling("không-có-mức-này")


@pytest.mark.parametrize(
    ("change", "expect"),
    [
        (lambda d: d["categories"].pop("violence"), "violence"),
        (lambda d: d["categories"].update(thu_la={"level": "block", "description": "x"}), "thu_la"),
        (lambda d: d["categories"]["violence"].update(description="  "), "description"),
        (lambda d: d["darkness_levels"]["dark"]["ceilings"].update(gore="extreme"), "gore"),
        (lambda d: d["darkness_levels"]["dark"]["ceilings"].pop("gore"), "gore"),
        (lambda d: d["darkness_cap"].pop("violence"), "violence"),
        (lambda d: d.update(default_darkness_level="khong-co"), "default_darkness_level"),
        (lambda d: d["darkness_levels"].clear(), "darkness_levels"),
    ],
)
def test_bad_catalogue_reports_file_and_field(config_dir, change, expect):
    edit(config_dir, change)
    with pytest.raises(ConfigError) as exc:
        load_config(config_dir)
    assert "moderation.yaml" in str(exc.value)
    assert expect in str(exc.value)
