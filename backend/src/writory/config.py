"""Cấu hình: biến môi trường (Settings) và các file config/*.yaml.

Trong YAML, `null` nghĩa là "chưa đặt". Code cần một trần chưa đặt thì gọi `require()`;
hàm đó báo lỗi rõ ràng chứ không coi là vô hạn.
"""

from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    SecretStr,
    ValidationError,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_CONFIG_DIR = REPO_ROOT / "config"


class ConfigError(Exception):
    """File cấu hình thiếu, không đọc được, hoặc sai schema."""


class LimitNotSetError(Exception):
    """Code dùng một giá trị đang là null (chưa đặt) trong config."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Section(_Strict):
    """Nhóm giá trị có thể null. `require` đọc giá trị, báo lỗi nếu chưa đặt."""

    _path: str = ""
    _file: str = ""

    def require(self, name: str):
        value = getattr(self, name)
        if value is None:
            raise LimitNotSetError(
                f"{self._path}.{name} chưa đặt (null) trong config/{self._file}; "
                "đặt giá trị trước khi dùng tính năng cần nó."
            )
        return value


# --- limits.yaml -----------------------------------------------------------------------


class CostLimits(_Section):
    _path = "cost_usd"
    _file = "limits.yaml"
    per_scene: NonNegativeFloat | None
    per_chapter: NonNegativeFloat | None
    per_story: NonNegativeFloat | None


class RetryLimits(_Strict):
    rewrite_per_scene: NonNegativeInt
    extract_schema_retry: NonNegativeInt
    llm_transient: NonNegativeInt


class RateLimits(_Section):
    _path = "rate_limit"
    _file = "limits.yaml"
    llm_calls_per_minute_per_user: PositiveInt | None
    narrator_questions_per_chapter: NonNegativeInt | None


class InputLimits(_Section):
    _path = "input"
    _file = "limits.yaml"
    custom_action_max_chars: PositiveInt | None
    character_name_max_chars: PositiveInt | None
    backstory_max_chars: PositiveInt | None


class ContextLimits(_Section):
    _path = "context"
    _file = "limits.yaml"
    writer_max_neighbors: PositiveInt | None


class LimitsConfig(_Strict):
    cost_usd: CostLimits
    retries: RetryLimits
    rate_limit: RateLimits
    input: InputLimits
    context: ContextLimits


# --- models.yaml -----------------------------------------------------------------------


class RoleModels(_Section):
    _path = "roles"
    _file = "models.yaml"
    outline: str | None
    extract: str | None
    guard: str | None
    choices: str | None
    narrator: str | None
    classify: str | None


class WriterTier(_Strict):
    id: str
    label: str
    model: str
    eval_result: str


class ModelsConfig(_Strict):
    roles: RoleModels
    writer_tiers: list[WriterTier]


# --- story_lengths.yaml ----------------------------------------------------------------


class IntRange(_Strict):
    min: PositiveInt
    max: PositiveInt

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.min > self.max:
            raise ValueError(f"min ({self.min}) lớn hơn max ({self.max})")
        return self


class LengthLevel(_Strict):
    label: str
    target_chars: PositiveInt
    chapters: IntRange


class StoryLengthsConfig(_Strict):
    chars_per_word_page: PositiveInt
    chapter_chars: IntRange
    scenes_per_chapter: IntRange
    levels: dict[str, LengthLevel] = Field(min_length=1)


# --- quality.yaml ----------------------------------------------------------------------


class RepetitionConfig(_Section):
    _path = "repetition"
    _file = "quality.yaml"
    ngram_words: PositiveInt | None
    max_repeats: PositiveInt | None


class ForeignScriptConfig(_Section):
    _path = "foreign_script"
    _file = "quality.yaml"
    latin_run_min_words: PositiveInt | None
    allowed_latin_words: list[str]


class ClicheConfig(_Strict):
    draft: bool
    phrases: list[str]


class QualityConfig(_Strict):
    dialogue_style: Literal["dash", "quotes"]
    repetition: RepetitionConfig
    foreign_script: ForeignScriptConfig
    cliches: ClicheConfig


# --- guard.yaml ------------------------------------------------------------------------


class RelationshipGuard(_Section):
    _path = "relationship"
    _file = "guard.yaml"
    max_score_jump_without_event: int | None = Field(ge=1, le=200)


class GuardConfig(_Strict):
    relationship: RelationshipGuard


# --- nạp -------------------------------------------------------------------------------


class AppConfig(_Strict):
    limits: LimitsConfig
    models: ModelsConfig
    story_lengths: StoryLengthsConfig
    quality: QualityConfig
    guard: GuardConfig


_FILES: dict[str, tuple[str, type[BaseModel]]] = {
    "limits": ("limits.yaml", LimitsConfig),
    "models": ("models.yaml", ModelsConfig),
    "story_lengths": ("story_lengths.yaml", StoryLengthsConfig),
    "quality": ("quality.yaml", QualityConfig),
    "guard": ("guard.yaml", GuardConfig),
}


def _load_file(path: Path, schema: type[BaseModel]) -> BaseModel:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise ConfigError(f"{path.name}: không đọc được file ({path}): {e}") from e
    except yaml.YAMLError as e:
        raise ConfigError(f"{path.name}: YAML không hợp lệ: {e}") from e
    try:
        return schema.model_validate(raw)
    except ValidationError as e:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']) or '(gốc)'}: {err['msg']}"
            for err in e.errors()
        )
        raise ConfigError(f"{path.name}: sai schema: {problems}") from e


def load_config(config_dir: Path = REPO_CONFIG_DIR) -> AppConfig:
    parts = {key: _load_file(config_dir / name, schema) for key, (name, schema) in _FILES.items()}
    return AppConfig(**parts)


# --- biến môi trường -------------------------------------------------------------------


class Settings(BaseSettings):
    """Biến môi trường. Danh sách đầy đủ: .env.example."""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    # Key của chủ dự án, chỉ cho bộ đo. Người chơi dùng key riêng (D-2), lưu mã hoá trong DB.
    openrouter_api_key: SecretStr | None = None
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: SecretStr
    postgres_dsn: SecretStr
    # Khoá Fernet mã hoá key OpenRouter của người chơi (G7). Cách tạo: docs/runbook.md
    player_key_encryption_key: SecretStr
