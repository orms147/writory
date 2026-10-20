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
            "per_chapter: 0.08", "per_chapter: null"
        ),
        encoding="utf-8",
    )
    cfg = load_config(config_dir)
    assert cfg.limits.cost_usd.per_scene == 0.02
    assert cfg.limits.cost_usd.per_chapter is None


def test_using_unset_limit_raises_clear_error(config_dir: Path):
    path = config_dir / "limits.yaml"
    text = path.read_text(encoding="utf-8")
    assert "per_story: 1.00" in text, "test hỏng: config thật đã đổi"
    path.write_text(text.replace("per_story: 1.00", "per_story: null"), encoding="utf-8")
    cfg = load_config(config_dir)
    with pytest.raises(LimitNotSetError) as exc:
        cfg.limits.cost_usd.require("per_story")
    msg = str(exc.value)
    assert "cost_usd.per_story" in msg
    assert "limits.yaml" in msg


def test_require_returns_value_when_set(config_dir: Path):
    path = config_dir / "limits.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "\n  per_chapter: 0.08", "\n  per_chapter: 0.2"
        ),
        encoding="utf-8",
    )
    assert load_config(config_dir).limits.cost_usd.require("per_chapter") == 0.2


@pytest.mark.parametrize(
    ("file", "old", "new", "expect_in_msg"),
    [
        ("limits.yaml", "per_scene: 0.02", "per_scene: abc", "per_scene"),
        ("limits.yaml", "per_scene: 0.02", "per_scene: -1", "per_scene"),
        ("limits.yaml", "per_scene: 0.02", "per_scene: 0.02\n  per_sceen: 1", "per_sceen"),
        ("limits.yaml", "rewrite_per_scene: 1", "rewrite_per_scene: -1", "rewrite_per_scene"),
        ("models.yaml", '    model: "openai/gpt-6-luna"\n', "", "model"),  # mức thiếu model
        ("story_lengths.yaml", "chapter_chars: {min: 3000, max: 10000}",
         "chapter_chars: {min: 10000, max: 3000}", "chapter_chars"),
        ("quality.yaml", "dialogue_style: dash", "dialogue_style: html", "dialogue_style"),
        ("quality.yaml", "  max_repeats: 2", "  max_repeats: 0", "max_repeats"),
        ("guard.yaml", "max_score_jump_without_event: 40",
         "max_score_jump_without_event: -5", "max_score_jump_without_event"),
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


def test_settings_validation_error_never_echoes_secret_values(monkeypatch, tmp_path):
    """G7: thiếu biến môi trường thì lỗi pydantic không được in kèm giá trị đầu vào (key người khác).
    Hồi quy 20/10/2026: lỗi Settings() in đuôi OPENROUTER_API_KEY ra màn hình."""
    from pydantic import ValidationError

    from writory.config import Settings

    secret = "sk-or-v1-" + "7" * 64
    for name in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD", "POSTGRES_DSN",
                 "PLAYER_KEY_ENCRYPTION_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENROUTER_API_KEY", secret)
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=tmp_path / "missing.env")
    text = str(exc.value) + repr(exc.value)
    assert "7777777777" not in text


def test_role_extract_uses_luna_with_low_reasoning():
    """D-35: vai trích dùng GPT-6 Luna, suy luận mức thấp (bài C v2). Mức suy luận nằm trong config."""
    models = load_config().models
    assert models.roles.require("extract") == "openai/gpt-6-luna"
    assert models.role_reasoning.extract == "low"


def test_role_reasoning_rejects_unknown_effort(config_dir):
    path = config_dir / "models.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("  extract: low", "  extract: rat-cao"),
                    encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(config_dir)
    assert "role_reasoning" in str(exc.value)


def test_narrator_limits_exist_in_config():
    """D-40: số câu hỏi mỗi chương và độ dài câu hỏi người kể nằm trong limits.yaml; chưa đo
    thì để null (code dùng tới thì báo CONFIG_LIMIT_NOT_SET)."""
    limits = load_config().limits
    assert "narrator_question_max_chars" in type(limits.input).model_fields
    assert "narrator_questions_per_chapter" in type(limits.rate_limit).model_fields
    text = (REPO_CONFIG_DIR / "limits.yaml").read_text(encoding="utf-8")
    assert "narrator_question_max_chars:" in text


def test_provisional_roles_use_luna_with_low_reasoning():
    """D-47: các vai chưa có bài đo riêng dùng tạm GPT-6 Luna; vai trả JSON suy luận thấp."""
    models = load_config().models
    for role in ("outline", "guard", "choices", "narrator", "classify", "setup"):
        assert models.roles.require(role) == "openai/gpt-6-luna"
        assert getattr(models.role_reasoning, role) == "low"


def test_unset_role_raises_clear_error(config_dir):
    """D-39: vai chưa chọn model thì báo lỗi rõ, không đoán model."""
    path = config_dir / "models.yaml"
    text = path.read_text(encoding="utf-8")
    old = "  setup: openai/gpt-6-luna"
    assert old in text, "test hỏng: config thật đã đổi"
    path.write_text(text.replace(old, "  setup: null"), encoding="utf-8")
    with pytest.raises(LimitNotSetError, match="roles.setup"):
        load_config(config_dir).models.roles.require("setup")


def test_writer_tier_reasoning_none_matches_bench_d():
    """D-43: mức "standard" đặt reasoning none, như bài D đã đo GPT-6 Luna."""
    [tier] = load_config().models.writer_tiers
    assert (tier.id, tier.reasoning) == ("standard", "none")


def test_writer_tier_reasoning_is_optional_and_checked(config_dir):
    path = config_dir / "models.yaml"
    text = path.read_text(encoding="utf-8")
    without = "".join(line for line in text.splitlines(keepends=True)
                      if not line.startswith("    reasoning: none"))
    assert without != text, "test hỏng: config thật đã đổi"
    path.write_text(without, encoding="utf-8")
    assert load_config(config_dir).models.writer_tiers[0].reasoning is None
    path.write_text(text.replace("reasoning: none", "reasoning: rat-cao"), encoding="utf-8")
    with pytest.raises(ConfigError) as exc:
        load_config(config_dir)
    assert "writer_tiers" in str(exc.value)
