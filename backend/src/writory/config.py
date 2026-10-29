"""Cấu hình: biến môi trường (Settings) và các file config/*.yaml.

Trong YAML, `null` nghĩa là "chưa đặt". Code cần một trần chưa đặt thì gọi `require()`;
hàm đó báo lỗi rõ ràng chứ không coi là vô hạn.
"""

from ipaddress import IPv4Network, IPv6Network, ip_network
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    NonNegativeFloat,
    NonNegativeInt,
    PositiveInt,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from writory.safety.categories import Category, Intensity, Level

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
    # Giây chờ trước lần thử lại thứ 1, 2, 3… của lỗi tạm (LLM_UNAVAILABLE, LLM_TIMEOUT); ngắn hơn số lần
    # thử lại thì lặp lần cuối; rỗng = không chờ (D-123).
    transient_backoff_seconds: list[NonNegativeFloat] = []
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
    # Đoạn nguyên văn đã hiện trên trang đưa vào ngữ cảnh dàn ý và viết (D-85).
    page_quotes_top_k: NonNegativeInt | None = None  # số đoạn tối đa mỗi lời gọi; 0 = tắt
    page_quotes_chunk_chars: PositiveInt | None = None  # cỡ một đoạn khi chia chương
    page_quotes_max_chars: PositiveInt | None = None  # tổng độ dài chữ tối đa của các đoạn
    page_quotes_neighbors: NonNegativeInt = 0  # đoạn liền sau mỗi đoạn trúng cũng lấy (D-96)
    forbidden_names_max: PositiveInt | None = None  # số nút tối đa trong mục tên cấm (D-94)
    standstill_chapters: PositiveInt | None = None  # nhân vật chính ở yên từng ấy chương (D-98)
    # Theo dõi mốc đã diễn ra (D-116): bộ trích được đánh dấu mốc bắt đầu trong chừng ấy chương tới;
    # null = tắt theo dõi (mục tiêu chương như trước, bộ trích không nhận mục mốc).
    milestone_lookahead: PositiveInt | None = None
    # Từng ấy chương liền không đổi trạng thái nào thì đề đòi đổi (D-112); None = tắt.
    idle_chapters: PositiveInt | None = None
    # Ba cờ của đề v3 (D-110): mặc định pydantic là tắt; bật ở limits.yaml (D-111).
    character_personality_max_chars: NonNegativeInt = 0  # tính cách NPC vào đề dàn ý và viết; 0 = tắt
    character_appearance_max_chars: NonNegativeInt = 0  # ngoại hình NPC vào đề dàn ý và viết; 0 = tắt (D-118)
    previous_openings: NonNegativeInt = 0  # số chương gần nhất có câu mở đưa vào đề viết; 0 = tắt
    previous_opening_max_chars: PositiveInt | None = None  # độ dài tối đa một câu mở
    unplanned_chapter_goal: bool = False  # chương không có mốc vẫn phải đổi tình thế cụ thể
    # Cứ từng ấy chương kể từ lần đổi pha trước (hoặc lần nhắc trước) thì mục tiêu chương đòi đổi pha
    # (D-119); None = tắt, đề y hệt cũ.
    phase_shift_every: PositiveInt | None = None


class LLMCallLimits(_Section):
    """Mọi lời gọi model trả bằng key người chơi (D-64): `max_output_tokens` được gửi làm
    `max_tokens` (gồm token suy luận), nên cũng là chặn trên của chi phí ước tính khi lời gọi không
    có usage (huỷ, đứt, thiếu usage.cost)."""

    _path = "llm_call"
    _file = "limits.yaml"
    max_output_tokens: PositiveInt | None = None
    # Hạn TỔNG của một lời gọi, giây (D-113): quá hạn thì LLM_TIMEOUT, coi như lỗi tạm. Khác hạn từng
    # lần đọc/ghi của httpx, vốn không bắt được máy chủ nhỏ giọt byte hay kết nối chết không báo.
    deadline_seconds: PositiveInt | None = None


class ChapterEstimateLimits(_Section):
    """Ước tính chi phí chương tới khi truyện chưa có chương nào đo được (D-87). Số tạm."""

    _path = "chapter_estimate"
    _file = "limits.yaml"
    default_usd: NonNegativeFloat | None = None


class AuthLimits(_Section):
    """Đăng nhập bằng mã mời (D-89), chỉ dùng khi `AUTH_MODE=invite`. Số tạm (D-47)."""

    _path = "auth"
    _file = "limits.yaml"
    session_ttl_hours: PositiveInt | None = None  # phiên hết hạn sau ngần này giờ kể từ lúc đăng nhập
    login_attempts_per_window: PositiveInt | None = None  # số lần nhập mã mỗi máy trong một cửa sổ
    login_window_seconds: PositiveInt | None = None  # độ dài cửa sổ cố định của bộ đếm trên


class FactLimits(_Section):
    """Fact mới do bộ trích tạo sau chương 0 (D-93). `max_new_per_chapter` 0 = tắt. Số tạm (D-47)."""

    _path = "facts"
    _file = "limits.yaml"
    max_new_per_chapter: NonNegativeInt | None = None  # trần cả chương, không phải mỗi cảnh
    text_max_chars: PositiveInt | None = None  # một câu ngắn
    duplicate_overlap: float | None = Field(default=None, gt=0, le=1)  # Jaccard âm tiết
    # Fact gần như nằm trọn trong Fact khác và cùng ABOUT một thực thể (D-95)
    related_overlap: float | None = Field(default=None, gt=0, le=1)
    grounded_min: float | None = Field(default=None, gt=0, le=1)  # tỉ lệ âm tiết có trên trang
    writer_max_page_facts: PositiveInt | None = None  # Fact từ trang mà ngữ cảnh người viết giữ


class LimitsConfig(_Strict):
    cost_usd: CostLimits
    retries: RetryLimits
    rate_limit: RateLimits
    input: InputLimits
    narrator_notebook: NarratorNotebookLimits
    context: ContextLimits
    facts: FactLimits = FactLimits()
    llm_call: LLMCallLimits = LLMCallLimits()
    chapter_estimate: ChapterEstimateLimits = ChapterEstimateLimits()
    auth: AuthLimits = AuthLimits()


# --- models.yaml -----------------------------------------------------------------------


class RoleModels(_Section):
    _path = "roles"
    _file = "models.yaml"
    outline: str | None
    extract: str | None
    choices: str | None
    narrator: str | None
    classify: str | None
    setup: str | None
    summary: str | None = None  # tóm tắt chương vừa ghi (D-49)
    moderate: str | None = None  # kiểm duyệt nội dung, G9 (D-57)


ReasoningEffort = Literal["none", "minimal", "low", "medium", "high"]


class RoleReasoning(_Strict):
    """Mức suy luận (reasoning effort của OpenRouter) cho từng vai; null = mặc định của model."""

    outline: ReasoningEffort | None = None
    extract: ReasoningEffort | None = None
    choices: ReasoningEffort | None = None
    narrator: ReasoningEffort | None = None
    classify: ReasoningEffort | None = None
    setup: ReasoningEffort | None = None
    summary: ReasoningEffort | None = None
    moderate: ReasoningEffort | None = None


class WriterTier(_Strict):
    id: str
    label: str
    model: str
    eval_result: str
    # Mức suy luận của model viết, như `role_reasoning`; null = mặc định của model (D-43).
    reasoning: ReasoningEffort | None = None


class ModelPrice(_Strict):
    """USD / 1 triệu token. Chỉ để ước tính chi phí tối đa của lời gọi không có usage (D-64);
    chi phí thật luôn lấy từ `usage.cost` hoặc tra lại theo id generation."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)
    input: NonNegativeFloat = Field(alias="in")
    output: NonNegativeFloat = Field(alias="out")


class ModelsConfig(_Strict):
    roles: RoleModels
    role_reasoning: RoleReasoning = RoleReasoning()
    writer_tiers: list[WriterTier]
    # Model nào không có giá thì lời gọi bằng key người chơi bị từ chối trước khi gửi (D-64).
    prices: dict[str, ModelPrice] = Field(default_factory=dict)
    # Nhà cung cấp OpenRouter không được dùng (D-100): có nơi nhận `structured_outputs` mà trả JSON
    # hỏng. Đi vào `provider.ignore` của mọi lời gọi qua `role_extra`.
    provider_ignore: list[str] = Field(default_factory=list)


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
    # Người chơi được chọn mức này lúc khởi tạo (D-88). Bắt buộc ghi rõ ở từng mức. Mức đóng vẫn
    # chạy được bằng lệnh đo (`pipeline/bench_run.py`), để đo trước khi mở.
    player_selectable: bool


class StoryLengthsConfig(_Strict):
    chars_per_word_page: PositiveInt
    chapter_chars: IntRange
    scenes_per_chapter: IntRange
    levels: dict[str, LengthLevel] = Field(min_length=1)

    @model_validator(mode="after")
    def _some_level_open(self) -> Self:
        if not any(level.player_selectable for level in self.levels.values()):
            raise ValueError("levels: cần ít nhất một mức player_selectable: true (D-88)")
        return self

    def player_levels(self) -> dict[str, LengthLevel]:
        """Các mức người chơi được chọn, theo thứ tự trong config (D-88)."""
        return {k: v for k, v in self.levels.items() if v.player_selectable}


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


# --- moderation.yaml -------------------------------------------------------------------


def _parse_intensity(value):
    return Intensity.parse(value) if isinstance(value, str) else value


IntensityName = Annotated[Intensity, BeforeValidator(_parse_intensity)]


class CategoryRule(_Strict):
    level: Level
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def _filled(self) -> Self:
        if not self.description.strip():
            raise ValueError("description rỗng")
        return self


class DarknessLevel(_Strict):
    label: str = Field(min_length=1)
    ceilings: dict[Category, IntensityName]  # trần cho từng loại bị giới hạn theo mức u tối


class ModerationConfig(_Strict):
    """Danh mục kiểm duyệt (G9, D-57). Danh sách loại là cố định trong code (`safety.categories`);
    config chọn mức xử lý, chữ mô tả (vào prompt) và trần mức u tối."""

    draft: bool  # true = chờ chủ dự án duyệt; false = đã duyệt (D-57)
    categories: dict[Category, CategoryRule]
    intensity_scale: dict[IntensityName, str]  # chữ mô tả mild, strong, extreme (vào prompt)
    darkness_cap: dict[Category, IntensityName]  # trần tuyệt đối, mọi mức u tối
    darkness_levels: dict[str, DarknessLevel] = Field(min_length=1)
    default_darkness_level: str  # dùng khi truyện chưa có mức u tối đọc được
    # Số lần kiểm độc lập mỗi đầu vào của người chơi; một lần báo chặn là chặn (D-79). Trần 5 để
    # lỗi gõ không nhân chi phí trên key người chơi.
    input_votes: int = Field(ge=1, le=5, strict=True)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        missing = sorted(c.value for c in set(Category) - set(self.categories))
        if missing:
            raise ValueError(f"categories thiếu loại: {missing}")
        if self.categories[Category.SEXUAL_MINORS].level is not Level.HARD_BLOCK:
            raise ValueError("categories.sexual_minors phải là hard_block (G9: config không hạ được)")
        limited = {c for c, r in self.categories.items() if r.level is Level.DARKNESS_LIMITED}
        if set(self.darkness_cap) != limited:
            raise ValueError(
                f"darkness_cap phải có đúng các loại darkness_limited: {sorted(c.value for c in limited)}"
            )
        wanted = {Intensity.MILD, Intensity.STRONG, Intensity.EXTREME}
        if set(self.intensity_scale) != wanted:
            raise ValueError("intensity_scale phải có đúng mild, strong, extreme")
        for name, level in self.darkness_levels.items():
            if set(level.ceilings) != limited:
                raise ValueError(
                    f"darkness_levels.{name}.ceilings phải có đúng các loại darkness_limited: "
                    f"{sorted(c.value for c in limited)}"
                )
            for category, ceiling in level.ceilings.items():
                if ceiling > self.darkness_cap[category]:
                    raise ValueError(
                        f"darkness_levels.{name}.ceilings.{category.value} vượt darkness_cap"
                    )
        if self.default_darkness_level not in self.darkness_levels:
            raise ValueError("default_darkness_level không có trong darkness_levels")
        return self

    def ceiling(self, level: str | None) -> dict[Category, Intensity]:
        """Trần theo từng loại cho một mức u tối; None là mức mặc định."""
        name = self.default_darkness_level if level is None else level
        if name not in self.darkness_levels:
            raise ValueError(f"mức u tối {name!r} không có trong config/moderation.yaml")
        return dict(self.darkness_levels[name].ceilings)


# --- nạp -------------------------------------------------------------------------------


class AppConfig(_Strict):
    limits: LimitsConfig
    models: ModelsConfig
    story_lengths: StoryLengthsConfig
    quality: QualityConfig
    guard: GuardConfig
    moderation: ModerationConfig


_FILES: dict[str, tuple[str, type[BaseModel]]] = {
    "limits": ("limits.yaml", LimitsConfig),
    "models": ("models.yaml", ModelsConfig),
    "story_lengths": ("story_lengths.yaml", StoryLengthsConfig),
    "quality": ("quality.yaml", QualityConfig),
    "guard": ("guard.yaml", GuardConfig),
    "moderation": ("moderation.yaml", ModerationConfig),
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
    # Chế độ `dev` (không đăng nhập, mọi người là người chơi dev): mount router của người chơi
    # (D-41). Mặc định tắt; chỉ bật trên máy dev. Chế độ `invite` không cần cờ này (D-89).
    enable_dev_routes: bool = False
    # Cách biết người đang dùng (D-89). `dev`: mọi người là người chơi dev, router chỉ mount khi bật
    # `enable_dev_routes` (như D-41). `invite`: đăng nhập bằng mã mời, router luôn mount, thiếu hay
    # sai phiên thì AUTH_REQUIRED. Mặc định `dev` để app đang chạy trên máy dev không đổi.
    auth_mode: Literal["dev", "invite"] = "dev"
    # `prod`: máy chủ cho người chơi thật (D-103). App từ chối khởi động nếu cấu hình nguy hiểm
    # (`prod_problems`), tự chạy migration và tạo ràng buộc Neo4j lúc khởi động, tắt trang OpenAPI.
    app_env: Literal["dev", "prod"] = "dev"
    # Proxy tin cậy (D-103): danh sách IP hoặc mạng, cách nhau dấu phẩy. Chỉ yêu cầu đến từ các địa
    # chỉ này mới được đọc `X-Real-IP`/`X-Forwarded-For` (địa chỉ máy cho bộ đếm lần nhập mã) và
    # `X-Forwarded-Proto`. Rỗng: không tin header nào.
    trusted_proxies: str = ""

    @field_validator("trusted_proxies")
    @classmethod
    def _proxies_parse(cls, value: str) -> str:
        parse_trusted_proxies(value)
        return value


ProxyNetwork = IPv4Network | IPv6Network

# Độ dài tối thiểu của mật khẩu Neo4j và Postgres ở `APP_ENV=prod` (D-103).
MIN_PROD_SECRET_CHARS = 16
# Mật khẩu mẫu của `.env.example` và docker-compose.yml: không bao giờ dùng ở prod.
_EXAMPLE_SECRET_MARK = "change-me"


def parse_trusted_proxies(value: str) -> tuple[ProxyNetwork, ...]:
    """`TRUSTED_PROXIES` → các mạng. Chỉ nhận IP hoặc mạng viết đúng (không tên máy, không `*`,
    không bit máy thừa như `172.30.80.10/24`), để lỗi gõ không thành tin cả Internet."""
    nets: list[ProxyNetwork] = []
    for part in value.split(","):
        item = part.strip()
        if not item:
            continue
        try:
            nets.append(ip_network(item, strict=True))
        except ValueError:
            raise ValueError(
                f"TRUSTED_PROXIES: {item[:40]!r} không phải IP hay mạng (vd 172.30.80.10, "
                "10.0.0.0/8)") from None
    return tuple(nets)


def _weak_secret(value: str) -> bool:
    return len(value) < MIN_PROD_SECRET_CHARS or _EXAMPLE_SECRET_MARK in value.lower()


def prod_problems(settings: Settings) -> list[str]:
    """Lý do không được chạy `APP_ENV=prod` (D-103); rỗng là được. Chỉ nêu tên biến, không bao
    giờ chép giá trị (G7)."""
    from psycopg.conninfo import conninfo_to_dict

    problems: list[str] = []
    if settings.auth_mode != "invite":
        problems.append("AUTH_MODE phải là invite ở APP_ENV=prod (D-89, D-103)")
    if _weak_secret(settings.neo4j_password.get_secret_value()):
        problems.append(f"NEO4J_PASSWORD yếu hoặc là mật khẩu mẫu: cần ít nhất "
                        f"{MIN_PROD_SECRET_CHARS} ký tự ngẫu nhiên")
    try:
        pg_password = conninfo_to_dict(settings.postgres_dsn.get_secret_value()).get("password")
    except Exception:  # noqa: BLE001 — DSN sai dạng; lỗi của psycopg có thể chép lại DSN
        problems.append("POSTGRES_DSN sai dạng")
    else:
        if not pg_password or _weak_secret(pg_password):
            problems.append(f"POSTGRES_DSN không có mật khẩu, hoặc mật khẩu yếu hay là mật khẩu "
                            f"mẫu: cần ít nhất {MIN_PROD_SECRET_CHARS} ký tự ngẫu nhiên")
    return problems
