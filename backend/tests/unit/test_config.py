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
        ("limits.yaml", "setup_repair: 1", "setup_repair: -1", "setup_repair"),
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


def test_a_file_missing_from_the_dir_is_taken_from_the_repo_config(config_dir: Path):
    """D-140: thư mục config của bộ đo chỉ cần chứa phần khác `config/`. Thư mục không có file nào mới là lỗi
    (`test_meta_config.py`), và file CÓ mặt mà hỏng vẫn báo đúng tên file (các test quanh đây)."""
    (config_dir / "models.yaml").unlink()
    assert load_config(config_dir).models == load_config().models


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


PROJECT_MODEL = "openai/gpt-6-luna"  # D-102 (thay D-100): mọi vai và mức model viết


def test_role_extract_uses_the_project_model_with_low_reasoning():
    """D-35, D-100: vai trích dùng model của dự án, suy luận mức thấp. Mức suy luận nằm trong
    config (số đo bài C v2 là của GPT-6 Luna, chưa đo lại với model mới)."""
    models = load_config().models
    assert models.roles.require("extract") == PROJECT_MODEL
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


def test_provisional_roles_use_the_project_model_with_low_reasoning():
    """D-47, D-100: các vai chưa có bài đo riêng dùng tạm model của dự án; vai trả JSON suy luận thấp."""
    models = load_config().models
    for role in ("outline", "choices", "narrator", "classify", "setup", "overreach"):
        assert models.roles.require(role) == PROJECT_MODEL
        assert getattr(models.role_reasoning, role) == "low"


def test_unset_role_raises_clear_error(config_dir):
    """D-39: vai chưa chọn model thì báo lỗi rõ, không đoán model."""
    path = config_dir / "models.yaml"
    text = path.read_text(encoding="utf-8")
    old = f"  setup: {PROJECT_MODEL}"
    assert old in text, "test hỏng: config thật đã đổi"
    path.write_text(text.replace(old, "  setup: null"), encoding="utf-8")
    with pytest.raises(LimitNotSetError, match="roles.setup"):
        load_config(config_dir).models.roles.require("setup")


def test_writer_tier_reasoning_none_matches_bench_d():
    """D-43: mức "standard" đặt reasoning none (như bài D đã đo; model nay là của D-100)."""
    [tier] = load_config().models.writer_tiers
    assert (tier.id, tier.reasoning, tier.model) == ("standard", "none", PROJECT_MODEL)


def test_every_configured_model_has_a_price_and_no_price_is_orphaned():
    """Mọi model ở `roles` và `writer_tiers` có giá trong `prices` (không thì lời gọi bằng key người
    chơi bị từ chối trước khi gửi, D-64), và `prices` không giữ giá của model không dùng nữa."""
    models = load_config().models
    used = {m for m in models.roles.model_dump().values() if m} | {t.model for t in models.writer_tiers}
    assert used <= set(models.prices) and set(models.prices) <= used


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


def test_every_configured_role_is_used_and_guard_has_no_model_role():
    """D-88: người canh bản 1 chỉ kiểm bằng code, nên config không có vai `guard`. Mọi vai trong
    `roles` phải có code gọi `require_model(..., "<vai>")` (hoặc `ROLE = "<vai>"`): không vai chết."""
    import re

    from writory.config import RoleModels, RoleReasoning

    assert "guard" not in RoleModels.model_fields
    assert "guard" not in RoleReasoning.model_fields
    text = (REPO_CONFIG_DIR / "models.yaml").read_text(encoding="utf-8")
    assert not re.search(r"^\s+guard:", text, re.MULTILINE)

    src = Path(__file__).resolve().parents[2] / "src" / "writory"
    code = "\n".join(p.read_text(encoding="utf-8") for p in src.rglob("*.py"))
    for role in RoleModels.model_fields:
        used = (re.search(rf'require_model\([^)]*"{role}"\)', code)
                or re.search(rf'^ROLE = "{role}"', code, re.MULTILINE))
        assert used, f"vai {role!r} trong config/models.yaml không có code nào dùng"


def test_story_lengths_open_to_players_are_short_and_medium():
    """D-88 (chủ dự án, 22/10/2026): bản 1 mở Ngắn và Vừa; Dài, Tiểu thuyết mở sau khi đo thật.
    Mỗi mức phải ghi rõ `player_selectable` (test dưới: thiếu là sai schema)."""
    lengths = load_config().story_lengths
    assert list(lengths.player_levels()) == ["short", "medium"]
    assert {k for k, v in lengths.levels.items() if not v.player_selectable} == {"long", "novel"}


def test_story_length_without_player_selectable_is_a_schema_error(config_dir):
    path = config_dir / "story_lengths.yaml"
    text = path.read_text(encoding="utf-8")
    old = "max_due_per_chapter: 3, player_selectable: false}"
    assert old in text, "test hỏng: config thật đã đổi"
    path.write_text(text.replace(old, "max_due_per_chapter: 3}", 1), encoding="utf-8")
    with pytest.raises(ConfigError, match="player_selectable"):
        load_config(config_dir)


def test_story_lengths_need_at_least_one_open_level(config_dir):
    path = config_dir / "story_lengths.yaml"
    text = path.read_text(encoding="utf-8")
    assert "player_selectable: true" in text, "test hỏng: config thật đã đổi"
    path.write_text(text.replace("player_selectable: true", "player_selectable: false"),
                    encoding="utf-8")
    with pytest.raises(ConfigError, match="player_selectable"):
        load_config(config_dir)


def test_the_writer_tier_points_back_to_bench_d_and_no_provider_is_ignored():
    """D-102: Luna đã qua bài D (`eval_result`), nên không còn lý do loại nhà cung cấp nào; cơ chế
    `provider_ignore` của D-100 vẫn còn, danh sách rỗng."""
    models = load_config().models
    [tier] = models.writer_tiers
    assert tier.eval_result == "evals/results/2026-10-20-quality-r2/"
    assert models.provider_ignore == []
    assert PROJECT_MODEL in models.prices
