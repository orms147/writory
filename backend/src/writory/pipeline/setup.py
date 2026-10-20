"""Khởi tạo truyện (design §4.1, §6.1; D-38, D-39).

Bốn bước, mỗi bước một lời gọi `chat_json` với schema strict (mọi trường bắt buộc; trống là null
hoặc danh sách rỗng), kiểm bằng pydantic rồi kiểm quy tắc bằng code:
1. `propose_settings`: đúng 3 bối cảnh mở.
2. `propose_plots`: đúng 3 hướng cốt truyện cho bối cảnh đã chọn.
3. `propose_characters`: đúng 3 nhân vật chính; người chơi sửa được tên, tính cách, quá khứ.
4. `build_story`: bản kế hoạch truyện (`StoryPlan`, ẩn) + gói thay đổi chương 0 (D-21).

Module này không ghi gì. Nơi gọi lưu bản kế hoạch và ghi gói qua `db.commit_chapter(..., 0, ...)`.

- G4: chữ đi qua tay người chơi (tag, bối cảnh và hướng đã chọn, nhân vật chính đã sửa) chỉ vào vai
  user, bọc `UserAuthored`. Nút nhân vật chính do code dựng từ chữ người chơi, mang
  `user_authored: true`; model chỉ nhắc tới nó qua `PROTAGONIST_ID`.
- G1: lựa chọn ở bước 1–3 hiện cho người chơi, nên prompt cấm viết bí mật vào đó. Gói chương 0
  không có REVEALED_TO_PLAYER và nhân vật chính không KNOWS gì; code kiểm player_view ở chương 0
  rỗng bằng định nghĩa duy nhất (`guard.state.player_view_of`).
- G11, D-39: JSON sai schema thử lại theo `retries.extract_schema_retry`; sai quy tắc thì báo
  STORY_SETUP_INVALID ngay, không tự gọi lại model, không trả kế hoạch hay gói nửa vời.
"""

import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from writory.config import AppConfig, IntRange, LengthLevel
from writory.errors import ErrorCode, WritoryError
from writory.graph.package import ChangePackage, chapter_rule_problems
from writory.graph.schema import NAMED_LABELS
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.base import LLMClient, Message, require_model, role_extra
from writory.llm.retry import RETRY_SCHEMA, with_retries
from writory.pipeline.story_plan import StoryPlan
from writory.safety.wrap import DATA_NOTICE, UserAuthored, system_message, user_message

PROMPT_VERSION = "setup-1"  # đổi chữ prompt thì tăng số
ROLE = "setup"  # config/models.yaml roles.setup, role_reasoning.setup
OPTION_COUNT = 3  # design §4.1: 3 bối cảnh, 3 hướng, 3 nhân vật
SECRETS_MIN, SECRETS_MAX = 1, 3  # design §6.1: 1–3 bí mật lớn
# Một cụm đứng riêng (tên phe, "gián điệp") trúng cả văn sạch (D-26), nên mỗi nhóm cần từ 2 cụm.
LEAK_GROUP_MIN_PHRASES = 2
INITIAL_CHAPTER = 0  # D-21: chương 0 là thế giới lúc khởi tạo
PROTAGONIST_ID = "protagonist"
INITIAL_KNOWS_HOW = "tự biết"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- quy ước tên và địa danh (D-32) ---------------------------------------------------------


class Naming(_Strict):
    """Quy ước tên nhân vật và địa danh (D-32). Dùng chung với bài đo D (`quality.bench_d`)."""

    names: Literal["han_viet", "viet"]
    places: Literal["hu_cau", "that"]


NAMES_TEXT = {"han_viet": "tên nhân vật kiểu Hán Việt", "viet": "tên nhân vật kiểu Việt"}
PLACES_TEXT = {"hu_cau": "địa danh hư cấu, không dùng địa danh có thật",
               "that": "được dùng địa danh có thật"}
_NAMES_HINT = {
    "han_viet": "Tên kiểu Hán Việt: họ tên đọc theo âm Hán Việt, như trong truyện cổ trang, "
                "kiếm hiệp.",
    "viet": "Tên kiểu Việt: họ tên người Việt thường ngày.",
}
_PLACES_HINT = {
    "hu_cau": "Địa danh hư cấu: tự đặt tên nơi chốn; không dùng tên nước, tỉnh, thành phố, sông "
              "núi có thật.",
    "that": "Có thể dùng địa danh có thật khi hợp với truyện; nơi nhỏ (quán, nhà, ngõ) vẫn tự đặt "
            "tên được.",
}


def _key(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


_HAN_VIET = Naming(names="han_viet", places="hu_cau")
_VIET_FICTIONAL = Naming(names="viet", places="hu_cau")
_VIET_REAL = Naming(names="viet", places="that")

# Mặc định theo thể loại, đúng bảng ở design §4.1 bước 1. Người chơi đổi được.
DEFAULT_NAMING: dict[str, Naming] = {
    _key(genre): naming
    for genres, naming in (
        (("cổ trang", "kỳ ảo", "tu tiên", "kiếm hiệp", "huyền huyễn"), _HAN_VIET),
        (("hiện đại", "tương lai giả tưởng", "hậu tận thế", "khoa huyễn"), _VIET_FICTIONAL),
        (("hiện thực", "đô thị", "trinh thám", "lịch sử", "học đường"), _VIET_REAL),
    )
    for genre in genres
}
# Thể loại ngoài bảng: địa danh hư cấu, để không tự ý đưa nơi có thật vào truyện (D-38).
FALLBACK_NAMING = _VIET_FICTIONAL


def default_naming(genre: str) -> Naming:
    return DEFAULT_NAMING.get(_key(genre), FALLBACK_NAMING)


# --- lựa chọn của người chơi -------------------------------------------------------------------


class StoryTags(_Strict):
    """Tag người chơi chọn (design §4.1 bước 1). Coi là chữ người chơi (G4): có thể là chữ tự gõ."""

    genre: str = Field(min_length=1)
    era: str | None = None
    voice: str | None = None
    darkness: str | None = None


PovMode = Literal["protagonist"]  # bản 1: chỉ nhân vật chính; "nhiều nhân vật" là bản 3


class StoryChoices(_Strict):
    """Những gì người chơi chọn trước bước 1 (design §4.1 bước 1–3)."""

    tags: StoryTags
    length_level: str  # khoá trong config/story_lengths.yaml `levels`
    pov: PovMode = "protagonist"
    naming: Naming

    def level(self, config: AppConfig) -> LengthLevel:
        try:
            return config.story_lengths.levels[self.length_level]
        except KeyError:
            raise ValueError(
                f"mức độ dài {self.length_level!r} không có trong config/story_lengths.yaml"
            ) from None


# --- đầu ra của model ------------------------------------------------------------------------
# Schema strict: mọi trường bắt buộc, không ràng buộc độ dài hay số phần tử trong schema (chưa kiểm
# nhà cung cấp nào nhận); số lượng và quy tắc kiểm bằng code sau khi đọc.


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SettingOption(_Out):
    title: str
    intro: str


class PlotOption(_Out):
    title: str
    summary: str


class CharacterOption(_Out):
    """Nhân vật chính đề xuất. Người chơi chọn rồi sửa được; từ đó mọi trường là chữ người chơi."""

    name: str
    personality: str
    backstory: str


class SettingsOutput(_Out):
    options: list[SettingOption]


class PlotsOutput(_Out):
    options: list[PlotOption]


class CharactersOutput(_Out):
    options: list[CharacterOption]


# Kiểu cạnh model khai ở chương 0. KNOWS và ABOUT do code dựng từ `facts`; không có
# REVEALED_TO_PLAYER (người chơi chưa đọc trang nào), không có cạnh cần Event hay Lie.
InitialEdgeType = Literal["RELATES_TO", "LOCATED_AT", "HOLDS", "MEMBER_OF"]


class OutAct(_Out):
    name: str
    from_chapter: int
    to_chapter: int


class OutCharacter(_Out):
    id: str
    name: str
    aliases: list[str]
    personality: str
    backstory: str


class OutNamed(_Out):
    """Nơi chốn, phe hoặc đồ vật."""

    id: str
    name: str
    aliases: list[str]
    description: str


class OutFact(_Out):
    id: str
    text: str
    about: list[str]  # id những thứ mệnh đề nói tới -> ABOUT
    known_by: list[str]  # id nhân vật đã biết từ trước trang đầu -> KNOWS, how "tự biết"


class OutEdge(_Out):
    type: InitialEdgeType
    source: str
    target: str
    kind: str | None  # RELATES_TO
    score: int | None  # RELATES_TO: -100…100


class OutThread(_Out):
    id: str
    description: str
    due_from_chapter: int
    due_to_chapter: int
    must_resolve: bool


class OutSecret(_Out):
    fact_id: str
    reveal_from_chapter: int
    reveal_to_chapter: int
    leak_terms: list[list[str]]


class BuildOutput(_Out):
    acts: list[OutAct]
    characters: list[OutCharacter]
    locations: list[OutNamed]
    factions: list[OutNamed]
    items: list[OutNamed]
    facts: list[OutFact]
    edges: list[OutEdge]
    threads: list[OutThread]
    secrets: list[OutSecret]


@dataclass(frozen=True)
class StorySetup:
    plan: StoryPlan
    package: ChangePackage


# --- prompt ----------------------------------------------------------------------------------

_COMMON = """Bạn là người thiết kế truyện cho WriTory, trò chơi truyện tương tác tiếng Việt: người \
chơi sống cuộc đời nhân vật chính qua từng lựa chọn.

Quy tắc chung:
- Viết hoàn toàn bằng tiếng Việt có dấu, tự nhiên, không văn dịch. Không chêm tiếng Anh, không \
dùng chữ Hán; tên riêng theo quy ước tên và địa danh dưới đây.
- Bám các tag người chơi đã chọn (thể loại, thời đại, giọng văn, mức độ u tối) và độ dài truyện.
- Trả về JSON đúng schema. Mọi trường đều phải có."""

SETTINGS_TASK = """Việc: đề xuất đúng 3 bối cảnh mở đầu cho truyện, khác nhau rõ rệt về nơi chốn, \
hoàn cảnh và chuyện mở màn.
Mỗi bối cảnh có `title` (tên ngắn) và `intro` (một đoạn 3–5 câu: thế giới, nơi chốn, không khí, \
và chuyện vừa xảy ra kéo nhân vật chính vào truyện).
Người chơi đọc cả ba để chọn, nên không viết ra bí mật hay cú lật nào của truyện."""

PLOTS_TASK = """Việc: dựa trên bối cảnh người chơi đã chọn, đề xuất đúng 3 hướng cốt truyện khác \
nhau rõ rệt.
Mỗi hướng có `title` (tên ngắn) và `summary` (3–5 câu: xung đột chính, điều nhân vật chính muốn, \
trở ngại lớn, hợp với độ dài truyện).
Người chơi đọc cả ba để chọn, nên không viết ra bí mật, kẻ chủ mưu hay cú lật; chỉ nêu điều nhân \
vật chính có thể biết lúc truyện bắt đầu."""

CHARACTERS_TASK = """Việc: dựa trên bối cảnh và hướng cốt truyện người chơi đã chọn, đề xuất đúng \
3 nhân vật chính khác nhau rõ rệt để người chơi nhập vai.
Mỗi nhân vật có `name` (họ tên theo quy ước tên ở trên), `personality` (tính cách, 1–2 câu) và \
`backstory` (quá khứ, 2–4 câu, vì sao nhân vật dính vào cốt truyện).
Người chơi đọc và sửa được cả ba trường, nên không viết ra bí mật của truyện, kể cả bí mật về \
chính nhân vật đó."""

BUILD_TASK = f"""Việc: dựng bản kế hoạch truyện (ẩn với người chơi) và thế giới lúc truyện bắt \
đầu (chương 0, trước trang đầu tiên), từ bối cảnh, hướng cốt truyện và nhân vật chính người chơi \
đã chọn.

Nhân vật chính đã có sẵn với id `{PROTAGONIST_ID}`: dùng id này khi nói tới nhân vật chính. Không \
khai lại nhân vật chính trong `characters`, không đổi tên, tính cách hay quá khứ của họ.

Định danh `id`: chữ thường không dấu, số và dấu gạch dưới, duy nhất trong cả truyện, ví dụ `lan`, \
`hoi_kiem`, `f_lan_gian_diep`. Mọi id nhắc tới trong `about`, `known_by`, `edges`, `secrets` phải \
là id đã khai trong cùng câu trả lời.

Các phần:
- `acts`: các hồi theo thứ tự (mở đầu, phát triển, cao trào, kết), phủ liền các chương từ chương 1 \
tới chương cuối, không chồng, không hở. Chương cuối của hồi cuối là tổng số chương, nằm trong \
khoảng của độ dài truyện.
- `characters`: các nhân vật khác: `name`, `aliases` (biệt danh, cách gọi khác; không có thì để \
danh sách rỗng), `personality`, `backstory`.
- `locations`, `factions`, `items`: nơi chốn, phe phái, đồ vật quan trọng: `name`, `aliases`, \
`description` (một câu).
- `facts`: sự thật của thế giới lúc truyện bắt đầu, mỗi cái đúng MỘT mệnh đề (`text`); chi tiết \
của một bí mật (ai làm, vì sao) là fact riêng. `about`: id những thứ mệnh đề nói tới. \
`known_by`: id nhân vật đã biết điều đó từ trước khi truyện bắt đầu. Nhân vật chính lúc này chưa \
biết fact nào: không bao giờ ghi `{PROTAGONIST_ID}` vào `known_by`; điều nhân vật chính biết sẽ \
hiện ra trên trang khi truyện kể tới.
- `edges`: tình trạng lúc truyện bắt đầu. `RELATES_TO` (nhân vật → nhân vật: `kind` như bạn, thù, \
thầy trò, người yêu; `score` từ -100 đến 100; có hướng, mỗi chiều một cạnh). `LOCATED_AT` (nhân \
vật hoặc đồ vật → nơi chốn; mỗi thứ một nơi). `HOLDS` (nhân vật → đồ vật đang giữ; mỗi đồ vật một \
người giữ). `MEMBER_OF` (nhân vật → phe). Kiểu khác `RELATES_TO` thì `kind` và `score` là null.
- `threads`: các mạch chính và phụ: `description`, khoảng chương dự kiến gỡ (`due_from_chapter`, \
`due_to_chapter`) trong số chương của truyện, `must_resolve` là true nếu mạch phải gỡ trước khi \
kết.
- `secrets`: từ {SECRETS_MIN} tới {SECRETS_MAX} bí mật lớn, mỗi cái là một cú lật người chơi chưa \
biết. `fact_id`: id fact chứa bí mật. `reveal_from_chapter`, `reveal_to_chapter`: khoảng chương \
dự kiến lộ cho người chơi, trong số chương của truyện. `leak_terms`: các nhóm cụm từ; khi mọi cụm \
của một nhóm cùng nằm trong một câu thì coi như bí mật đã lộ. Mỗi nhóm có ít nhất \
{LEAK_GROUP_MIN_PHRASES} cụm, viết đúng chữ truyện sẽ dùng, ví dụ [["Lan", "gián điệp"], \
["Lan", "người của Hội Kiếm"]].

Ở bước này chưa có gì được hé lộ cho người chơi: người chơi chưa đọc trang nào."""

_POV_TEXT = {
    "protagonist": "Góc nhìn: chỉ nhân vật chính. Người chơi chỉ biết những gì nhân vật chính "
                   "thấy, nghe, suy ra.",
}
_TAG_LABELS = (("genre", "thể loại"), ("era", "thời đại"), ("voice", "giọng văn"),
               ("darkness", "mức độ u tối"))


def _naming_rule(naming: Naming) -> str:
    return (
        f"Quy ước tên và địa danh (bắt buộc): {NAMES_TEXT[naming.names]}; "
        f"{PLACES_TEXT[naming.places]}. Áp dụng cho mọi tên bạn đặt: nhân vật, nơi chốn, phe "
        f"phái, đồ vật, biệt danh.\n{_NAMES_HINT[naming.names]}\n{_PLACES_HINT[naming.places]}"
    )


def _tags_text(tags: StoryTags) -> str:
    return "\n".join(
        f"{label}: {value.strip()}"
        for field, label in _TAG_LABELS
        if (value := getattr(tags, field)) and value.strip()
    )


def _setting_data(setting: SettingOption) -> UserAuthored:
    # Bối cảnh và hướng đã chọn được trình duyệt gửi lại, nên coi là chữ người chơi (G4).
    return UserAuthored(f"{setting.title}\n{setting.intro}", "setting")


def _plot_data(plot: PlotOption) -> UserAuthored:
    return UserAuthored(f"{plot.title}\n{plot.summary}", "plot")


def _messages(
    task: str, choices: StoryChoices, level: LengthLevel, *parts: str | UserAuthored
) -> list[Message]:
    brief: list[str | UserAuthored] = [
        f"Độ dài truyện: {level.label}, {level.chapters.min}–{level.chapters.max} chương.",
        _POV_TEXT[choices.pov],
        "Tag người chơi đã chọn:",
        UserAuthored(_tags_text(choices.tags), "story_tags"),
    ]
    return [
        system_message(_COMMON, _naming_rule(choices.naming), task, DATA_NOTICE),
        user_message(*brief, *parts),
    ]


# --- gọi model -------------------------------------------------------------------------------


def _invalid(problems: list[str]) -> WritoryError:
    return WritoryError(ErrorCode.STORY_SETUP_INVALID, detail="; ".join(problems))


async def _ask[T: BaseModel](
    llm: LLMClient, config: AppConfig, messages: list[Message], schema: type[T]
) -> T:
    model = require_model(config.models.roles, ROLE)
    extra = role_extra(config.models, ROLE)
    output, _ = await with_retries(
        lambda: llm.chat_json(model, messages, schema, extra=extra),
        max_retries=config.limits.retries.extract_schema_retry,
        retry_on=RETRY_SCHEMA,
    )
    return output


def _three[O: _Out](options: list[O]) -> list[O]:
    problems = []
    if len(options) != OPTION_COUNT:
        problems.append(f"cần đúng {OPTION_COUNT} lựa chọn, nhận {len(options)}")
    for i, option in enumerate(options, 1):
        blank = [k for k, v in option.model_dump().items() if not v.strip()]
        if blank:
            problems.append(f"lựa chọn {i} có trường rỗng: {blank}")
    if problems:
        raise _invalid(problems)
    return list(options)


async def propose_settings(
    choices: StoryChoices, *, llm: LLMClient, config: AppConfig
) -> list[SettingOption]:
    level = choices.level(config)
    out = await _ask(llm, config, _messages(SETTINGS_TASK, choices, level), SettingsOutput)
    return _three(out.options)


async def propose_plots(
    choices: StoryChoices, setting: SettingOption, *, llm: LLMClient, config: AppConfig
) -> list[PlotOption]:
    level = choices.level(config)
    messages = _messages(PLOTS_TASK, choices, level, "Bối cảnh đã chọn:", _setting_data(setting))
    return _three((await _ask(llm, config, messages, PlotsOutput)).options)


async def propose_characters(
    choices: StoryChoices, setting: SettingOption, plot: PlotOption, *,
    llm: LLMClient, config: AppConfig,
) -> list[CharacterOption]:
    level = choices.level(config)
    messages = _messages(
        CHARACTERS_TASK, choices, level,
        "Bối cảnh đã chọn:", _setting_data(setting),
        "Hướng cốt truyện đã chọn:", _plot_data(plot),
    )
    return _three((await _ask(llm, config, messages, CharactersOutput)).options)


def _clean_protagonist(pc: CharacterOption) -> CharacterOption:
    """Chữ người chơi giữ nguyên, chỉ bỏ khoảng trắng hai đầu. Trường rỗng là lỗi đầu vào."""
    cleaned = CharacterOption(**{k: v.strip() for k, v in pc.model_dump().items()})
    blank = [k for k, v in cleaned.model_dump().items() if not v]
    if blank:
        raise ValueError(f"nhân vật chính có trường rỗng: {blank}")
    return cleaned


async def build_story(
    choices: StoryChoices, setting: SettingOption, plot: PlotOption, protagonist: CharacterOption,
    *, llm: LLMClient, config: AppConfig, commit_id: str,
) -> StorySetup:
    """Bản kế hoạch + gói chương 0. `protagonist` là nhân vật người chơi đã chọn (và có thể đã sửa)."""
    pc = _clean_protagonist(protagonist)
    level = choices.level(config)
    messages = _messages(
        BUILD_TASK, choices, level,
        "Bối cảnh đã chọn:", _setting_data(setting),
        "Hướng cốt truyện đã chọn:", _plot_data(plot),
        f"Nhân vật chính (id `{PROTAGONIST_ID}`), người chơi đã chọn và có thể đã sửa:",
        "Tên:", UserAuthored(pc.name, "protagonist_name"),
        "Tính cách:", UserAuthored(pc.personality, "protagonist_personality"),
        "Quá khứ:", UserAuthored(pc.backstory, "protagonist_backstory"),
    )
    output = await _ask(llm, config, messages, BuildOutput)
    return to_story_setup(output, protagonist=pc, commit_id=commit_id, chapters=level.chapters)


# --- đổi đầu ra thành kế hoạch + gói, rồi kiểm -------------------------------------------------


def _named(label: str, x: OutCharacter | OutNamed, **props: Any) -> dict[str, Any]:
    aliases = [a for a in x.aliases if a.strip()]
    return {"id": x.id, "label": label,
            "props": {"name": x.name, **({"aliases": aliases} if aliases else {}), **props}}


def _edge(etype: str, source: str, target: str, **props: Any) -> dict[str, Any]:
    return {"type": etype, "from": source, "to": target, "valid_from_chapter": INITIAL_CHAPTER,
            "props": {k: v for k, v in props.items() if v is not None}}


def _validated[M: BaseModel](
    model: type[M], data: dict[str, Any], what: str, problems: list[str]
) -> M | None:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        problems += [
            f"{what}: {'.'.join(str(p) for p in err['loc']) or '(gốc)'}: {err['msg']}"
            for err in e.errors(include_input=False, include_url=False)
        ]
        return None


def to_story_setup(
    output: BuildOutput, *, protagonist: CharacterOption, commit_id: str, chapters: IntRange
) -> StorySetup:
    """Đổi đầu ra của model thành `StoryPlan` + gói chương 0 rồi kiểm (`initial_problems`).
    Có lỗi thì ném STORY_SETUP_INVALID kèm toàn bộ danh sách lỗi, không trả phần nào."""
    pc = _clean_protagonist(protagonist)
    nodes: list[dict[str, Any]] = [{
        "id": PROTAGONIST_ID, "label": "Character",
        "props": {"name": pc.name, "personality": pc.personality, "backstory": pc.backstory,
                  "is_protagonist": True, "user_authored": True},
    }]
    nodes += [_named("Character", c, personality=c.personality, backstory=c.backstory)
              for c in output.characters]
    for label, group in (("Location", output.locations), ("Faction", output.factions),
                         ("Item", output.items)):
        nodes += [_named(label, x, description=x.description) for x in group]
    nodes += [{"id": f.id, "label": "Fact", "props": {"text": f.text}} for f in output.facts]
    nodes += [
        {"id": t.id, "label": "Thread",
         "props": {"description": t.description, "planted_chapter": INITIAL_CHAPTER,
                   "due_from_chapter": t.due_from_chapter, "due_to_chapter": t.due_to_chapter}}
        for t in output.threads
    ]
    edges = [
        _edge(e.type, e.source, e.target,
              **({"kind": e.kind, "score": e.score} if e.type == "RELATES_TO" else {}))
        for e in output.edges
    ]
    for f in output.facts:
        edges += [_edge("ABOUT", f.id, target) for target in f.about]
        edges += [_edge("KNOWS", who, f.id, how=INITIAL_KNOWS_HOW) for who in f.known_by]

    problems: list[str] = []
    package = _validated(ChangePackage, {"commit_id": commit_id, "nodes": nodes, "edges": edges},
                         "gói chương 0", problems)
    plan = _validated(StoryPlan, {
        "acts": [a.model_dump() for a in output.acts],
        "secrets": [s.model_dump() for s in output.secrets],
        "must_resolve_threads": [t.id for t in output.threads if t.must_resolve],
    }, "bản kế hoạch", problems)
    if package is not None and plan is not None:
        problems += initial_problems(plan, package, chapters=chapters)
    if problems or package is None or plan is None:
        raise _invalid(problems)
    return StorySetup(plan=plan, package=package)


# Nhãn và cạnh dùng ở chương 0, kèm nhãn hai đầu hợp lệ (docs/graph-schema.md, mục Chương 0).
INITIAL_LABELS = frozenset({"Character", "Location", "Item", "Faction", "Fact", "Thread"})
_ENDPOINTS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "RELATES_TO": (frozenset({"Character"}), frozenset({"Character"})),
    "LOCATED_AT": (frozenset({"Character", "Item"}), frozenset({"Location"})),
    "HOLDS": (frozenset({"Character"}), frozenset({"Item"})),
    "MEMBER_OF": (frozenset({"Character"}), frozenset({"Faction"})),
    "KNOWS": (frozenset({"Character"}), frozenset({"Fact"})),
    "ABOUT": (frozenset({"Fact"}), NAMED_LABELS | {"Fact"}),
}
_TEXT_PROP = {"Fact": "text", "Thread": "description"}


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def initial_problems(plan: StoryPlan, package: ChangePackage, *, chapters: IntRange) -> list[str]:
    """Kiểm bằng code bản kế hoạch và gói chương 0 (D-38). Rỗng là hợp lệ.

    Lỗi chỉ nêu id, nhãn và số chương, không chép chữ của truyện: chi tiết vào log (G12)."""
    labels = {n.id: n.label for n in package.nodes}
    protagonists = {n.id for n in package.nodes if n.props.get("is_protagonist") is True}
    problems = [f"chương 0: {p}" for p in chapter_rule_problems(package, INITIAL_CHAPTER)]
    problems += _node_problems(package)
    if len(protagonists) != 1 or labels[next(iter(protagonists))] != "Character":
        problems.append(f"cần đúng một nhân vật chính (Character có is_protagonist), "
                        f"có {len(protagonists)}: {sorted(protagonists)}")
    problems += _edge_problems(package, labels, protagonists)
    problems += _plan_problems(plan, package, labels, chapters)
    if not problems:
        # Lưới cuối, theo định nghĩa duy nhất của player_view (G1): người chơi chưa biết gì.
        view = player_view_of(OverlayState(EmptyState(), [package]), INITIAL_CHAPTER)
        if view.entries or view.lies:
            problems.append("player_view ở chương 0 phải rỗng, có: "
                            f"{sorted({e.id for e in view.entries} | {x.id for x in view.lies})}")
    return problems


def _node_problems(package: ChangePackage) -> list[str]:
    problems = []
    names: dict[tuple[str, str], list[str]] = {}
    for n in package.nodes:
        if n.label not in INITIAL_LABELS:
            problems.append(f"nút {n.id}: nhãn {n.label} không dùng ở chương 0")
            continue
        field = "name" if n.label in NAMED_LABELS else _TEXT_PROP[n.label]
        value = n.props.get(field)
        if not isinstance(value, str) or not value.strip():
            problems.append(f"nút {n.id} ({n.label}): thiếu `{field}`")
        elif n.label in NAMED_LABELS:
            names.setdefault((n.label, _key(value)), []).append(n.id)
    problems += [f"{label} trùng tên: {ids}" for (label, _), ids in names.items() if len(ids) > 1]
    return problems


def _edge_problems(
    package: ChangePackage, labels: dict[str, str], protagonists: set[str]
) -> list[str]:
    problems = []
    holders: Counter[str] = Counter()
    places: Counter[str] = Counter()
    for e in package.edges:
        if e.type == "REVEALED_TO_PLAYER":
            problems.append(f"cạnh {e.id}: chương 0 không có REVEALED_TO_PLAYER, người chơi chưa "
                            "đọc trang nào")
            continue
        if e.type not in _ENDPOINTS:
            problems.append(f"cạnh {e.id}: kiểu {e.type} không dùng ở chương 0")
            continue
        missing = [i for i in (e.source, e.target) if i not in labels]
        if missing:
            problems.append(f"cạnh {e.id} trỏ tới nút không có trong gói: {missing}")
            continue
        sources, targets = _ENDPOINTS[e.type]
        if labels[e.source] not in sources or labels[e.target] not in targets:
            problems.append(f"cạnh {e.id}: {e.type} không nối "
                            f"{labels[e.source]} → {labels[e.target]}")
        if e.type == "KNOWS":
            if e.source in protagonists:
                problems.append(f"cạnh {e.id}: nhân vật chính chưa biết gì ở chương 0 (KNOWS của "
                                "nhân vật chính là điều người chơi biết, D-16)")
            if e.props.get("how") != INITIAL_KNOWS_HOW:
                problems.append(f"cạnh {e.id}: KNOWS ở chương 0 phải có how = "
                                f"{INITIAL_KNOWS_HOW!r}")
        elif e.type == "RELATES_TO":
            kind, score = e.props.get("kind"), e.props.get("score")
            if not (isinstance(kind, str) and kind.strip()) or not (
                _is_int(score) and -100 <= score <= 100
            ):
                problems.append(f"cạnh {e.id}: RELATES_TO cần `kind` và `score` trong -100…100")
        elif e.type == "HOLDS":
            holders[e.target] += 1
        elif e.type == "LOCATED_AT":
            places[e.source] += 1
    problems += [f"đồ vật {i} có {n} người giữ" for i, n in holders.items() if n > 1]
    problems += [f"{i} ở {n} nơi cùng lúc" for i, n in places.items() if n > 1]
    return problems


def _plan_problems(
    plan: StoryPlan, package: ChangePackage, labels: dict[str, str], chapters: IntRange
) -> list[str]:
    problems = []
    expected = 1
    for i, act in enumerate(plan.acts, 1):
        if act.from_chapter != expected:
            problems.append(f"hồi thứ {i} bắt đầu ở chương {act.from_chapter}, cần chương "
                            f"{expected}: các hồi phải liền nhau từ chương 1")
        expected = act.to_chapter + 1
    total = plan.total_chapters
    if not chapters.min <= total <= chapters.max:
        problems.append(f"kế hoạch có {total} chương, mức độ dài cần "
                        f"{chapters.min}–{chapters.max}")
    if not SECRETS_MIN <= len(plan.secrets) <= SECRETS_MAX:
        problems.append(f"cần {SECRETS_MIN}–{SECRETS_MAX} bí mật, có {len(plan.secrets)}")
    for s in plan.secrets:
        if labels.get(s.fact_id) != "Fact":
            problems.append(f"bí mật {s.fact_id} không trỏ tới Fact có trong gói")
        if s.reveal_to_chapter > total:
            problems.append(f"bí mật {s.fact_id}: khoảng lộ {s.reveal_from_chapter}–"
                            f"{s.reveal_to_chapter} vượt quá {total} chương")
        if not s.leak_terms:
            problems.append(f"bí mật {s.fact_id} thiếu leak_terms (D-26)")
        elif any(len(group) < LEAK_GROUP_MIN_PHRASES for group in s.leak_terms):
            problems.append(f"bí mật {s.fact_id}: mỗi nhóm leak_terms cần ít nhất "
                            f"{LEAK_GROUP_MIN_PHRASES} cụm")
    threads = {n.id: n.props for n in package.nodes if n.label == "Thread"}
    problems += [f"mạch {t} không có nút Thread trong gói"
                 for t in plan.must_resolve_threads if t not in threads]
    for tid, props in threads.items():
        planted = props.get("planted_chapter")
        low, high = props.get("due_from_chapter"), props.get("due_to_chapter")
        if not _is_int(planted) or planted != INITIAL_CHAPTER:
            problems.append(f"mạch {tid}: planted_chapter phải là {INITIAL_CHAPTER}")
        if not (_is_int(low) and _is_int(high) and 1 <= low <= high <= total):
            problems.append(f"mạch {tid}: khoảng gỡ {low}–{high} phải nằm trong chương 1–{total}")
    return problems
