import shutil
from pathlib import Path

import pytest

from writory.config import (
    REPO_CONFIG_DIR,
    ConfigError,
    LimitNotSetError,
    Settings,
    load_config,
)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Bản sao config/ thật, để từng test sửa một file."""
    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    return target


def test_repo_config_loads():
    cfg = load_config()
    assert cfg.limits.retries.rewrite_per_scene >= 0
    assert cfg.story_lengths.levels  # có ít nhất một mức độ dài


def test_null_means_not_set(config_dir: Path):
    (config_dir / "limits.yaml").write_text(
        (config_dir / "limits.yaml").read_text(encoding="utf-8").replace(
            "per_scene: null", "per_scene: 0.05"
        ),
        encoding="utf-8",
    )
    cfg = load_config(config_dir)
    assert cfg.limits.cost_usd.per_scene == 0.05
    assert cfg.limits.cost_usd.per_chapter is None


def test_using_unset_limit_raises_clear_error():
    cfg = load_config()
    if cfg.limits.cost_usd.per_story is not None:
        pytest.skip("trần per_story đã được đặt trong config thật")
    with pytest.raises(LimitNotSetError) as exc:
        cfg.limits.cost_usd.require("per_story")
    msg = str(exc.value)
    assert "cost_usd.per_story" in msg
    assert "limits.yaml" in msg


def test_require_returns_value_when_set(config_dir: Path):
    path = config_dir / "limits.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "\n  per_chapter: null", "\n  per_chapter: 0.2"
        ),
        encoding="utf-8",
    )
    assert load_config(config_dir).limits.cost_usd.require("per_chapter") == 0.2


@pytest.mark.parametrize(
    ("file", "old", "new", "expect_in_msg"),
    [
        ("limits.yaml", "per_scene: null", "per_scene: abc", "per_scene"),
        ("limits.yaml", "per_scene: null", "per_scene: -1", "per_scene"),
        ("limits.yaml", "per_scene: null", "per_scene: null\n  per_sceen: 1", "per_sceen"),
        ("limits.yaml", "rewrite_per_scene: 1", "rewrite_per_scene: -1", "rewrite_per_scene"),
        ("models.yaml", "writer_tiers: []", "writer_tiers:\n  - id: x\n    label: X", "model"),
        ("story_lengths.yaml", "chapter_chars: {min: 3000, max: 10000}",
         "chapter_chars: {min: 10000, max: 3000}", "chapter_chars"),
        ("quality.yaml", "dialogue_style: dash", "dialogue_style: html", "dialogue_style"),
        ("quality.yaml", "  max_repeats: null", "  max_repeats: 0", "max_repeats"),
    ],
)
def test_bad_schema_reports_file_and_field(config_dir, file, old, new, expect_in_msg):
    path = config_dir / file
    text = path.read_text(encoding="utf-8")
    assert old in text, "test hỏng: config thật đã đổi"
    path.write_text(text.replace(old, new), encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(config_dir)
    msg = str(exc.value)
    assert file in msg
    assert expect_in_msg in msg


def test_missing_file_reports_path(config_dir: Path):
    (config_dir / "models.yaml").unlink()
    with pytest.raises(ConfigError, match="models.yaml"):
        load_config(config_dir)


def test_invalid_yaml_reports_file(config_dir: Path):
    (config_dir / "limits.yaml").write_text("cost_usd: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="limits.yaml"):
        load_config(config_dir)


def test_settings_read_env_and_hide_secrets(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("NEO4J_URI", "bolt://example:7687")
    monkeypatch.setenv("NEO4J_USER", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw-should-not-print")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://u:dsn-secret@h/db")
    monkeypatch.setenv("PLAYER_KEY_ENCRYPTION_KEY", "enc-should-not-print")
    s = Settings(_env_file=None)
    assert s.neo4j_uri == "bolt://example:7687"
    assert s.neo4j_password.get_secret_value() == "pw-should-not-print"
    shown = repr(s) + str(s)
    for secret in ("pw-should-not-print", "dsn-secret", "enc-should-not-print"):
        assert secret not in shown


def test_settings_missing_required_env_is_clear(monkeypatch: pytest.MonkeyPatch):
    for name in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "POSTGRES_DSN",
                 "PLAYER_KEY_ENCRYPTION_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(Exception, match="(?i)neo4j_password"):
        Settings(_env_file=None)
