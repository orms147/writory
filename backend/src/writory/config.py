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
    # `build_story` sai quy tắc: số lượt gọi lại model kèm danh sách lỗi, riêng với thử lại JSON
    # sai schema (D-14, D-54).
    setup_repair: NonNegativeInt


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
    personality_max_chars: PositiveInt | None  # nhân vật chính người chơi sửa (D-45)
    narrator_question_max_chars: PositiveInt | None  # câu hỏi người kể (D-40)


class NarratorNotebookLimits(_Section):
    """Truy hồi sổ tay cho người kể (D-59): ngưỡng cắt và số mục luôn kèm."""

    _path = "narrator_notebook"
    _file = "limits.yaml"
    max_entries: PositiveInt | None
    max_chars: PositiveInt | None
    recent_entries: PositiveInt | None
    keyword_entries: PositiveInt | None

    @model_validator(mode="after")
    def _recent_fits(self) -> Self:
        if (self.max_entries is not None and self.recent_entries is not None
                and self.recent_entries >= self.max_entries):
            raise ValueError(
                f"recent_entries ({self.recent_entries}) phải nhỏ hơn max_entries "
                f"({self.max_entries})")
        return self


class ContextLimits(_Section):
    _path = "context"
    _file = "limits.yaml"
    writer_max_neighbors: PositiveInt | None
    summary_max_chars: PositiveInt | None = None  # độ dài tối đa của tóm tắt chương (D-49)


class LimitsConfig(_Strict):
    cost_usd: CostLimits
    retries: RetryLimits
    rate_limit: RateLimits
    input: InputLimits
    narrator_notebook: NarratorNotebookLimits
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
    setup: str | None
    summary: str | None = None  # tóm tắt chương vừa ghi (D-49)


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high"]


class RoleReasoning(_Strict):
    """Mức suy luận (reasoning effort của OpenRouter) cho từng vai; null = mặc định của model."""

    outline: ReasoningEffort | None = None
    extract: ReasoningEffort | None = None
    guard: ReasoningEffort | None = None
    choices: ReasoningEffort | None = None
    narrator: ReasoningEffort | None = None
    classify: ReasoningEffort | None = None
    setup: ReasoningEffort | None = None
    summary: ReasoningEffort | None = None


class WriterTier(_Strict):
    id: str
    label: str
    model: str
    eval_result: str
    # Mức suy luận của model viết, như `role_reasoning`; null = mặc định của model (D-43).
    reasoning: ReasoningEffort | None = None


class ModelsConfig(_Strict):
    roles: RoleModels
    role_reasoning: RoleReasoning = RoleReasoning()
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
    # Nhịp của bản kế hoạch (design §6.1, D-49): số mốc cốt truyện, và số việc đến hạn tối đa ở
    # một chương (bí mật, mạch phải gỡ, mốc có chương cuối của khoảng là chương đó). Chương cuối
    # không tính (D-54).
    milestones: IntRange
    max_due_per_chapter: PositiveInt


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


NarrationPerson = Literal["first", "third"]


class NarrationConfig(_Section):
    """Ngôi kể của lời kể (D-51). `person` là ngôi đã chốt của truyện; ngưỡng tính bằng số lần
    "tôi" trên 100 từ lời kể."""

    _path = "narration"
    _file = "quality.yaml"
    person: NarrationPerson
    min_words: PositiveInt | None
    first_person_min_per_100_words: NonNegativeFloat | None
    first_person_max_per_100_words: NonNegativeFloat | None


class QualityConfig(_Strict):
    dialogue_style: Literal["dash", "quotes"]
    repetition: RepetitionConfig
    foreign_script: ForeignScriptConfig
    cliches: ClicheConfig
    narration: NarrationConfig


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

    # hide_input_in_errors: lỗi thiếu/sai biến không in kèm giá trị đầu vào, vì đầu vào có key (G7).
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore",
                                      hide_input_in_errors=True)

    # Key của chủ dự án, chỉ cho bộ đo. Người chơi dùng key riêng (D-2), lưu mã hoá trong DB.
    openrouter_api_key: SecretStr | None = None
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: SecretStr
    postgres_dsn: SecretStr
    # Khoá Fernet mã hoá key OpenRouter của người chơi (G7). Cách tạo: docs/runbook.md
    player_key_encryption_key: SecretStr
    # Mount router chưa có đăng nhập (sổ tay, hỏi người kể; D-41). Mặc định tắt: chưa kiểm được
    # truyện thuộc ai (G10), nên chỉ bật trên máy dev.
    enable_dev_routes: bool = False
