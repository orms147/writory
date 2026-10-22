"""Khởi tạo truyện (design §4.1, §6.1; D-38, D-39, D-54).

Bốn bước, mỗi bước một lời gọi `chat_json` với schema strict (mọi trường bắt buộc; trống là null
hoặc danh sách rỗng), kiểm bằng pydantic rồi kiểm quy tắc bằng code:
1. `propose_settings`: đúng 3 bối cảnh mở.
2. `propose_plots`: đúng 3 hướng cốt truyện cho bối cảnh đã chọn.
3. `propose_characters`: đúng 3 nhân vật chính; người chơi sửa được tên, tính cách, quá khứ.
4. `build_story`: bản kế hoạch truyện (`StoryPlan`, ẩn) + gói thay đổi chương 0 (D-21).

Module này không ghi gì. Nơi gọi lưu bản kế hoạch và ghi gói qua `db.commit_chapter(..., 0, ...)`.

- G4: chữ đi qua tay người chơi (tag, bối cảnh và hướng đã chọn, nhân vật chính đã sửa) chỉ vào vai
  user, bọc `UserAuthored`. Nút nhân vật chính do code dựng từ chữ người chơi, mang
  `user_authored: true`; model chỉ nhắc tới nó qua `PROTAGONIST_ID`. Lượt sửa của `build_story`:
  câu trả lời trước (model viết, có thể nhắc lại chữ người chơi) vào khối dữ liệu
  `previous_answer`; danh sách lỗi (id lớp truth, chữ model viết) đứng ngoài khối, qua
  `escape_text`. Cả hai ở vai user; vai `setup` vốn được thấy lớp truth.
- G1: lựa chọn ở bước 1–3 hiện cho người chơi, nên prompt cấm viết bí mật vào đó. Gói chương 0
  chỉ có REVEALED_TO_PLAYER của nhân vật chính (D-74) và nhân vật chính không KNOWS gì (D-76);
  code kiểm player_view ở chương 0 chỉ có mục nhân vật chính bằng định nghĩa duy nhất
  (`guard.state.player_view_of`).
- G11, D-39, D-14: JSON sai schema thử lại theo `retries.extract_schema_retry`, lỗi mạng tạm thời
  theo `retries.llm_transient` (`with_json_retries`). Bước 1–3 sai quy tắc thì báo
  STORY_SETUP_INVALID ngay, không tự gọi lại model.
- D-54 (`build_story`): id sai dạng thì code chuẩn hoá (`normalize_ids`), không gọi lại model. Sai
  quy tắc thì gọi model sửa tối đa `retries.setup_repair` lượt, kèm danh sách lỗi; lượt sửa vẫn
  thử lại JSON sai schema riêng như trên. Vẫn sai thì `SetupInvalidError` (STORY_SETUP_INVALID):
  log chỉ có loại lỗi, không trả kế hoạch hay gói nửa vời.
- D-76: `protagonist` trong `known_by` (KNOWS của nhân vật chính ở chương 0) thì code bỏ
  (`drop_protagonist_knows`) sau chuẩn hoá id, trước mọi phép kiểm; không tính là lỗi, không tốn
  lượt sửa. Log chỉ có số cạnh bị bỏ.
"""

import logging
import re
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from writory.config import AppConfig, LengthLevel, ModerationConfig
from writory.errors import ErrorCode, WritoryError
from writory.graph.package import (
    ID_MAX_LEN,
    ID_PATTERN,
    ChangePackage,
    EdgeSpec,
    chapter_rule_problems,
)
from writory.graph.schema import NAMED_LABELS
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.base import LLMClient, Message, require_model, role_extra
from writory.llm.retry import with_json_retries
from writory.pipeline.story_plan import MilestoneKind, StoryPlan
from writory.safety.moderate import darkness_brief
from writory.safety.wrap import (
    DATA_NOTICE,
    UserAuthored,
    escape_text,
    system_message,
    user_message,
)

log = logging.getLogger(__name__)

# Đổi chữ prompt thì tăng số. setup-3: mốc và nhịp của kế hoạch (D-49). setup-4: luật id có dạng và
# ví dụ, luật nhịp không tính chương cuối, đề lượt sửa (D-54). setup-5: `protects` của bí mật về
# danh tính (D-61). setup-6: `known_by` chỉ gồm nhân vật khác, kể cả với bối cảnh chung (D-76).
PROMPT_VERSION = "setup-7"
ROLE = "setup"  # config/models.yaml roles.setup, role_reasoning.setup
OPTION_COUNT = 3  # design §4.1: 3 bối cảnh, 3 hướng, 3 nhân vật
SECRETS_MIN, SECRETS_MAX = 1, 3  # design §6.1: 1–3 bí mật lớn
# Một cụm đứng riêng (tên phe, "gián điệp") trúng cả văn sạch (D-26), nên mỗi nhóm cần từ 2 cụm.
LEAK_GROUP_MIN_PHRASES = 2
INITIAL_CHAPTER = 0  # D-21: chương 0 là thế giới lúc khởi tạo
INITIAL_CHAPTER_ID = f"ch{INITIAL_CHAPTER}"  # đích của hé lộ nhân vật chính ở chương 0 (D-74)
PROTAGONIST_ID = "protagonist"
# Dòng trong thiết lập truyện (`story_brief`) nêu tên nhân vật chính. Câu trích của hé lộ nhân vật
# chính ở chương 0 là đúng dòng này, nên G3 giữ nguyên: câu trích có thật trong chữ người chơi đã
# thấy (D-52 coi thiết lập truyện là chữ đã thấy).
PROTAGONIST_BRIEF_PREFIX = "Nhân vật chính: "
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


_GENRE_PARTS = re.compile(r"\s*[·/,|]\s*")


def default_naming(genre: str) -> Naming:
    """Nhãn ghép ("Kỳ ảo · tu tiên") lấy phần đầu tiên có trong bảng (D-75)."""
    for part in (genre, *_GENRE_PARTS.split(genre)):
        naming = DEFAULT_NAMING.get(_key(part))
        if naming is not None:
            return naming
    return FALLBACK_NAMING


# --- lựa chọn của người chơi -------------------------------------------------------------------


class StoryTags(_Strict):
    """Tag người chơi chọn (design §4.1 bước 1). Coi là chữ người chơi (G4): có thể là chữ tự gõ.

    `darkness`: chữ tự do cũ, chỉ còn để đọc phiên và đề đã lưu trước D-67; mức u tối giờ là
    `StoryChoices.darkness_level`, API không nhận trường này nữa."""

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
    # Khoá trong config/moderation.yaml `darkness_levels` (D-67); None = `default_darkness_level`.
    darkness_level: str | None = None

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
    protects: list[str]  # id nút có tên mà bí mật giấu danh tính (D-61); bí mật khác: []


class OutMilestone(_Out):
    kind: MilestoneKind
    goal: str
    from_chapter: int
    to_chapter: int


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
    milestones: list[OutMilestone]


@dataclass(frozen=True)
class StorySetup:
    plan: StoryPlan
    package: ChangePackage


# --- lỗi của build_story (D-54) ------------------------------------------------------------------

ProblemKind = Literal[
    "id",  # chuẩn hoá id: hai id ra cùng một id, hoặc không đổi được
    "package", "plan",  # pydantic của gói chương 0, của bản kế hoạch
    "chapter_0", "nodes", "protagonist", "edges", "player_view",  # luật của gói chương 0
    "acts", "length", "milestones", "pacing", "secrets", "threads",  # luật của bản kế hoạch
]


@dataclass(frozen=True)
class SetupProblem:
    """Một lỗi của đầu ra `build_story`. `kind` được vào log và file chung của bộ đo. `text` nêu id
    lớp truth và số chương: chỉ cho model `setup` ở lượt sửa và cho truth_dump của bộ đo."""

    kind: ProblemKind
    text: str


def problem_kinds(problems: Iterable[SetupProblem]) -> dict[str, int]:
    """Số lỗi theo loại, xếp theo tên loại."""
    return dict(sorted(Counter(p.kind for p in problems).items()))


def _kinds_text(problems: Iterable[SetupProblem]) -> str:
    return ", ".join(f"{kind} ×{n}" for kind, n in problem_kinds(problems).items())


class SetupInvalidError(WritoryError):
    """STORY_SETUP_INVALID của `build_story`, `to_story_setup`. `detail` (vào log, G12) chỉ có loại
    lỗi và số lượt sửa đã dùng; danh sách lỗi đầy đủ ở `problems` (D-54)."""

    def __init__(self, problems: Sequence[SetupProblem], *, repairs: int = 0) -> None:
        self.problems = tuple(problems)
        self.repairs = repairs
        super().__init__(ErrorCode.STORY_SETUP_INVALID,
                         detail=f"sai quy tắc sau {repairs} lượt sửa: {_kinds_text(self.problems)}")


# --- chuẩn hoá id bằng code (D-54) --------------------------------------------------------------
# Lần chạy tu-tien-2 hỏng lượt khởi tạo đầu vì model đặt id có dấu, có khoảng trắng. Code sửa trên
# đầu ra của model, trước mọi phép kiểm, cùng một ánh xạ cho mọi chỗ khai và mọi chỗ nhắc tới.

SAFE_ID_PATTERN = r"^[a-z0-9_]+$"  # dạng id đề yêu cầu; hẹp hơn ID_PATTERN
_ID_RE = re.compile(ID_PATTERN)
_UNSAFE_RUN = re.compile(r"[^a-z0-9_]+")
# Tên có dấu làm ví dụ cho luật id trong đề; id ví dụ sinh bằng `normalize_id`.
ID_EXAMPLES = ("Lão Đạo Sĩ", "Hội Kiếm", "Đoàn Khương")
# Phần của đầu ra model khai id. Hồi và mốc không có id.
_ID_SECTIONS = ("characters", "locations", "factions", "items", "facts", "threads")


def normalize_id(raw: str) -> str:
    """Id đã khớp `ID_PATTERN` giữ nguyên. Id khác: chữ thường, bỏ dấu tiếng Việt (đ → d), mỗi đoạn
    khoảng trắng hay ký tự ngoài [a-z0-9_] thành một `_`, bỏ `_` ở hai đầu, cắt còn `ID_MAX_LEN`
    ký tự. Không ra được id nào (chuỗi rỗng, toàn ký tự lạ) thì trả nguyên chuỗi, để phép kiểm
    báo lỗi."""
    if _ID_RE.fullmatch(raw):
        return raw
    text = unicodedata.normalize("NFD", raw.lower().replace("đ", "d"))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = _UNSAFE_RUN.sub("_", text).strip("_")[:ID_MAX_LEN].rstrip("_")
    return text or raw


def _map_ids(data: dict[str, Any], fn: Callable[[str], str]) -> None:
    """Áp `fn` tại chỗ lên mọi id của đầu ra model (dạng dict): chỗ khai (`_ID_SECTIONS`) và chỗ
    nhắc tới (`about`, `known_by`, from/to của cạnh, `fact_id` và `protects` của bí mật). Id mạch
    của kế hoạch lấy từ chỗ khai của mạch."""
    for section in _ID_SECTIONS:
        for x in data[section]:
            x["id"] = fn(x["id"])
    for f in data["facts"]:
        f["about"] = [fn(i) for i in f["about"]]
        f["known_by"] = [fn(i) for i in f["known_by"]]
    for e in data["edges"]:
        e["source"], e["target"] = fn(e["source"]), fn(e["target"])
    for s in data["secrets"]:
        s["fact_id"] = fn(s["fact_id"])
        s["protects"] = [fn(i) for i in s["protects"]]


def normalize_ids(output: BuildOutput) -> tuple[BuildOutput, list[SetupProblem]]:
    """Chuẩn hoá mọi id của đầu ra model bằng `normalize_id`. Hai id khác nhau ra cùng một id (kể
    cả trùng `PROTAGONIST_ID`) thì không gộp: giữ nguyên cả hai và báo lỗi. `PROTAGONIST_ID`
    không bao giờ bị đổi."""
    data = output.model_dump()
    raws: set[str] = set()

    def collect(i: str) -> str:
        raws.add(i)
        return i

    _map_ids(data, collect)
    groups: dict[str, set[str]] = defaultdict(set)
    groups[PROTAGONIST_ID].add(PROTAGONIST_ID)
    for raw in raws:
        groups[normalize_id(raw)].add(raw)
    mapping: dict[str, str] = {}
    problems: list[SetupProblem] = []
    for fixed, group in sorted(groups.items()):
        if len(group) > 1:
            problems.append(SetupProblem("id", (
                f"các id {', '.join(repr(r) for r in sorted(group))} khác nhau nhưng đổi sang "
                f"dạng {SAFE_ID_PATTERN} đều ra {fixed!r}: đặt cho mỗi thứ một id riêng")))
            continue
        [raw] = group
        if raw != fixed:
            mapping[raw] = fixed
        elif not _ID_RE.fullmatch(raw):
            problems.append(SetupProblem("id", f"id {raw!r} không đổi được sang dạng "
                                               f"{SAFE_ID_PATTERN}"))
    _map_ids(data, lambda i: mapping.get(i, i))
    return BuildOutput.model_validate(data), problems


# --- KNOWS của nhân vật chính ở chương 0 (D-76) -------------------------------------------------
# Lần chạy tu-tien-4 tốn một lượt sửa vì model ghi `protagonist` vào `known_by` của 5 fact bối
# cảnh, dù đề cấm. KNOWS của nhân vật chính là điều người chơi biết (D-16), mà ở chương 0 người chơi
# chưa đọc trang nào (D-38), nên các cạnh này luôn bỏ được, không mất gì của thế giới: fact vẫn còn,
# nhân vật khác vẫn biết nó.


def drop_protagonist_knows(output: BuildOutput) -> tuple[BuildOutput, int]:
    """Bỏ `PROTAGONIST_ID` khỏi `known_by` của mọi fact. Trả đầu ra mới và số cạnh KNOWS đã bỏ."""
    dropped = sum(f.known_by.count(PROTAGONIST_ID) for f in output.facts)
    if not dropped:
        return output, 0
    data = output.model_dump()
    for f in data["facts"]:
        f["known_by"] = [i for i in f["known_by"] if i != PROTAGONIST_ID]
    return BuildOutput.model_validate(data), dropped


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

_ID_EXAMPLES_TEXT = "; ".join(f"{name} → `{normalize_id(name)}`" for name in ID_EXAMPLES)

BUILD_TASK = f"""Việc: dựng bản kế hoạch truyện (ẩn với người chơi) và thế giới lúc truyện bắt \
đầu (chương 0, trước trang đầu tiên), từ bối cảnh, hướng cốt truyện và nhân vật chính người chơi \
đã chọn.

Nhân vật chính đã có sẵn với id `{PROTAGONIST_ID}`: dùng id này khi nói tới nhân vật chính. Không \
khai lại nhân vật chính trong `characters`, không đổi tên, tính cách hay quá khứ của họ.

Định danh `id`: chỉ gồm chữ cái ASCII thường không dấu, chữ số và dấu gạch dưới, đúng dạng \
`{SAFE_ID_PATTERN}`: không dấu tiếng Việt, không khoảng trắng, không ký tự nào khác. Ví dụ: \
{_ID_EXAMPLES_TEXT}. Id duy nhất trong cả truyện. Mọi id nhắc tới trong `about`, `known_by`, `edges`, `secrets` phải là id đã khai trong \
cùng câu trả lời, viết y hệt.

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
`known_by`: id nhân vật đã biết điều đó từ trước khi truyện bắt đầu; chỉ ghi các nhân vật khác, \
không bao giờ ghi `{PROTAGONIST_ID}`. Điều này đúng cả với bối cảnh chung mà nhân vật chính hẳn \
đã biết (thế cục, phe phái, lời đồn, chuyện trong quá khứ của họ): `known_by` của nhân vật chính \
là sổ tay của người chơi, mà người chơi chưa đọc trang nào. Điều nhân vật chính biết sẽ hiện ra \
trên trang khi truyện kể tới. Fact chỉ nhân vật chính biết thì để `known_by` rỗng.
- `edges`: tình trạng lúc truyện bắt đầu, theo bảng "Cạnh trong `edges`" ở cuối đề.
- `threads`: các mạch chính và phụ: `description`, khoảng chương dự kiến gỡ (`due_from_chapter`, \
`due_to_chapter`) trong số chương của truyện, `must_resolve` là true nếu mạch phải gỡ trước khi \
kết. Mạch phải gỡ thì phải gỡ xong trong đúng khoảng này. Mỗi mạch phải gỡ hỏi đúng một câu hỏi \
chính (một việc phải xảy ra hoặc một điều phải biết): mô tả không ghép hai việc bằng "và" hay dấu \
chấm phẩy, việc thứ hai thì làm thành mạch khác. Mạch xong khi câu hỏi chính ấy có câu trả lời.
- `milestones`: các mốc chính của cốt truyện, ẩn với người chơi: `kind` là `turning_point` (bước \
ngoặt), `climax` (cao trào) hoặc `ending` (kết); `goal`: một câu, điều phải xảy ra ở mốc đó; \
`from_chapter`, `to_chapter`: khoảng chương mốc phải xảy ra. Mỗi hồi có ít nhất một mốc có \
`to_chapter` nằm trong hồi. Đúng một mốc `ending`, nằm ở chương cuối (`from_chapter` = \
`to_chapter` = chương cuối).
- `secrets`: từ {SECRETS_MIN} tới {SECRETS_MAX} bí mật lớn, mỗi cái là một cú lật người chơi chưa \
biết. `fact_id`: id fact chứa bí mật. `reveal_from_chapter`, `reveal_to_chapter`: khoảng chương \
dự kiến lộ cho người chơi, trong số chương của truyện. `leak_terms`: các nhóm cụm từ; khi mọi cụm \
của một nhóm cùng nằm trong một câu thì coi như bí mật đã lộ. Mỗi nhóm có ít nhất \
{LEAK_GROUP_MIN_PHRASES} cụm, viết đúng chữ truyện sẽ dùng, ví dụ [["Lan", "gián điệp"], \
["Lan", "người của Hội Kiếm"]]. `protects`: chỉ với bí mật về danh tính (ai thật ra là ai, tên \
thật của kẻ giấu mặt, nhân vật đội lốt người khác), id các nhân vật, nơi chốn, phe phái hay đồ \
vật mà tên phải giữ kín cho tới khi bí mật lộ; tới lúc đó truyện chỉ gọi chúng bằng biệt danh \
viết thường. Bí mật khác thì để danh sách rỗng. Không ghi `{PROTAGONIST_ID}`.

Ở bước này chưa có gì được hé lộ cho người chơi: người chơi chưa đọc trang nào."""


def _pacing_rule(level: LengthLevel) -> str:
    """Nhịp theo độ dài truyện (D-49): số trong config/story_lengths.yaml, kiểm lại ở
    `initial_problems`. Chương cuối không tính giới hạn số việc đến hạn (D-54)."""
    m = level.milestones
    return (f"Nhịp cho độ dài này: {m.min}–{m.max} mốc. Mỗi chương, trừ chương cuối, có tối đa "
            f"{level.max_due_per_chapter} việc đến hạn; một việc đến hạn ở chương N là một bí mật "
            "có `reveal_to_chapter` = N, một mạch phải gỡ có `due_to_chapter` = N, hoặc một mốc "
            "có `to_chapter` = N. Chương cuối là chương kết, được gỡ nhiều mạch cùng lúc nên không "
            "tính giới hạn này. Ở các chương còn lại, rải các hạn ra, không dồn vào một chương.")

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
    task: str, choices: StoryChoices, config: AppConfig, *parts: str | UserAuthored
) -> list[Message]:
    level = choices.level(config)
    brief: list[str | UserAuthored] = [
        f"Độ dài truyện: {level.label}, {level.chapters.min}–{level.chapters.max} chương.",
        _POV_TEXT[choices.pov],
        "Tag người chơi đã chọn:",
        UserAuthored(_tags_text(choices.tags), "story_tags"),
        # Mức u tối người chơi chọn (D-67): bọc như tag, vì đi cùng lựa chọn của người chơi.
        "Mức u tối người chơi đã chọn:",
        UserAuthored(darkness_brief(config.moderation, choices.darkness_level), "darkness_level"),
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
    retries = config.limits.retries
    output, _ = await with_json_retries(
        lambda: llm.chat_json(model, messages, schema, extra=extra),
        schema_retries=retries.extract_schema_retry, transient_retries=retries.llm_transient,
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
    out = await _ask(llm, config, _messages(SETTINGS_TASK, choices, config), SettingsOutput)
    return _three(out.options)


async def propose_plots(
    choices: StoryChoices, setting: SettingOption, *, llm: LLMClient, config: AppConfig
) -> list[PlotOption]:
    messages = _messages(PLOTS_TASK, choices, config, "Bối cảnh đã chọn:", _setting_data(setting))
    return _three((await _ask(llm, config, messages, PlotsOutput)).options)


async def propose_characters(
    choices: StoryChoices, setting: SettingOption, plot: PlotOption, *,
    llm: LLMClient, config: AppConfig,
) -> list[CharacterOption]:
    messages = _messages(
        CHARACTERS_TASK, choices, config,
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


def story_brief(
    choices: StoryChoices, setting: SettingOption, plot: PlotOption, protagonist: CharacterOption,
    *, moderation: ModerationConfig | None,
) -> str:
    """Thiết lập truyện người chơi đã chọn, cho đề dàn ý và đề viết mỗi chương
    (`ChapterRequest.story_brief`; nơi dùng luôn bọc như dữ liệu, G4). Có quy ước tên và địa danh,
    vì prompt mọi bước sinh nội dung phải nhận nó (D-32), và mức u tối đã chọn cùng trần của nó
    (`moderation`, D-67), để model viết biết trần mà kiểm duyệt đầu ra sẽ áp. `moderation=None`
    chỉ để dựng lại thiết lập của lần chạy trước D-67 (không có dòng mức u tối, bài đo E)."""
    pc = _clean_protagonist(protagonist)
    naming = choices.naming
    darkness = [] if moderation is None else [darkness_brief(moderation, choices.darkness_level)]
    return "\n".join([
        _tags_text(choices.tags),
        *darkness,  # D-67
        _POV_TEXT[choices.pov],
        f"Quy ước tên và địa danh: {NAMES_TEXT[naming.names]}; {PLACES_TEXT[naming.places]}.",
        f"Bối cảnh: {setting.title}\n{setting.intro}",
        f"Hướng cốt truyện: {plot.title}\n{plot.summary}",
        f"{PROTAGONIST_BRIEF_PREFIX}{pc.name}\nTính cách: {pc.personality}\nQuá khứ: {pc.backstory}",
    ])


async def build_story(
    choices: StoryChoices, setting: SettingOption, plot: PlotOption, protagonist: CharacterOption,
    *, llm: LLMClient, config: AppConfig, commit_id: str,
    on_repair: Callable[[Sequence[SetupProblem]], None] | None = None,
) -> StorySetup:
    """Bản kế hoạch + gói chương 0. `protagonist` là nhân vật người chơi đã chọn (và có thể đã sửa).

    Sai quy tắc thì gọi model sửa tối đa `retries.setup_repair` lượt (D-54), mỗi lượt qua `llm`
    như lời gọi đầu (nên qua MeteredClient của nơi gọi, tính vào trần). `on_repair` nhận danh sách
    lỗi ngay trước mỗi lượt sửa (bộ đo đếm lượt sửa)."""
    pc = _clean_protagonist(protagonist)
    level = choices.level(config)
    task = build_task(level)
    parts: tuple[str | UserAuthored, ...] = (
        "Bối cảnh đã chọn:", _setting_data(setting),
        "Hướng cốt truyện đã chọn:", _plot_data(plot),
        f"Nhân vật chính (id `{PROTAGONIST_ID}`), người chơi đã chọn và có thể đã sửa:",
        "Tên:", UserAuthored(pc.name, "protagonist_name"),
        "Tính cách:", UserAuthored(pc.personality, "protagonist_personality"),
        "Quá khứ:", UserAuthored(pc.backstory, "protagonist_backstory"),
    )
    output = await _ask(llm, config, _messages(task, choices, config, *parts), BuildOutput)
    limit = config.limits.retries.setup_repair
    repairs = 0
    while True:
        output, setup, problems = _check_build(output, protagonist=pc, commit_id=commit_id,
                                               level=level)
        if setup is not None:
            return setup
        if repairs >= limit:
            log.warning("khởi tạo: kế hoạch vẫn sai quy tắc sau %d lượt sửa (%s)", repairs,
                        _kinds_text(problems))
            raise SetupInvalidError(problems, repairs=repairs)
        repairs += 1
        log.info("khởi tạo: kế hoạch sai quy tắc (%s); gọi model sửa, lượt %d/%d",
                 _kinds_text(problems), repairs, limit)
        if on_repair is not None:
            on_repair(problems)
        messages = _messages(task, choices, config, *parts, *_repair_parts(output, problems))
        output = await _ask(llm, config, messages, BuildOutput)


def build_task(level: LengthLevel) -> str:
    """Đề của bước 4: phần việc, luật nhịp theo độ dài (D-49), rồi khối bảng cạnh sinh từ luật
    (`edge_rules`) đứng riêng."""
    return f"{BUILD_TASK}\n\n{_pacing_rule(level)}\n\n{edge_rules()}"


REPAIR_INTRO = ("Câu trả lời trước của bạn bị trả lại vì sai quy tắc. Đây là câu trả lời đó, các "
                "id sai dạng đã được hệ thống đổi sang dạng đúng (trừ những id trùng nhau sau khi "
                "đổi):")
REPAIR_TASK = ("Trả lại toàn bộ câu trả lời theo đúng schema và mọi luật ở trên, sửa hết các lỗi "
               "này; phần không có lỗi thì giữ nguyên.")


def _repair_parts(
    previous: BuildOutput, problems: Sequence[SetupProblem]
) -> tuple[str | UserAuthored, ...]:
    """Phần thêm vào vai user cho lượt sửa (D-54). Câu trả lời trước có thể chép lại chữ người chơi
    nên vào khối dữ liệu; danh sách lỗi (id, chữ model viết) đứng ngoài khối, qua `escape_text`."""
    listed = "\n".join(f"- {escape_text(p.text)}" for p in problems)
    return (REPAIR_INTRO, UserAuthored(previous.model_dump_json(), "previous_answer"),
            f"Lỗi cần sửa:\n{listed}", REPAIR_TASK)


# --- đổi đầu ra thành kế hoạch + gói, rồi kiểm -------------------------------------------------


def _named(label: str, x: OutCharacter | OutNamed, **props: Any) -> dict[str, Any]:
    aliases = [a for a in x.aliases if a.strip()]
    return {"id": x.id, "label": label,
            "props": {"name": x.name, **({"aliases": aliases} if aliases else {}), **props}}


def _edge(etype: str, source: str, target: str, **props: Any) -> dict[str, Any]:
    return {"type": etype, "from": source, "to": target, "valid_from_chapter": INITIAL_CHAPTER,
            "props": {k: v for k, v in props.items() if v is not None}}


def _validated[M: BaseModel](
    model: type[M], data: dict[str, Any], what: str, kind: ProblemKind,
    problems: list[SetupProblem],
) -> M | None:
    try:
        return model.model_validate(data)
    except ValidationError as e:
        problems += [
            SetupProblem(kind, f"{what}: {'.'.join(str(p) for p in err['loc']) or '(gốc)'}: "
                               f"{err['msg']}")
            for err in e.errors(include_input=False, include_url=False)
        ]
        return None


def to_story_setup(
    output: BuildOutput, *, protagonist: CharacterOption, commit_id: str, level: LengthLevel
) -> StorySetup:
    """Chuẩn hoá id rồi đổi đầu ra của model thành `StoryPlan` + gói chương 0 và kiểm
    (`initial_problems`). Có lỗi thì ném `SetupInvalidError` kèm toàn bộ danh sách lỗi, không trả
    phần nào."""
    _, setup, problems = _check_build(output, protagonist=protagonist, commit_id=commit_id,
                                      level=level)
    if setup is None:
        raise SetupInvalidError(problems)
    return setup


def _check_build(
    output: BuildOutput, *, protagonist: CharacterOption, commit_id: str, level: LengthLevel
) -> tuple[BuildOutput, StorySetup | None, list[SetupProblem]]:
    """(đầu ra đã chuẩn hoá id và bỏ KNOWS của nhân vật chính, kết quả nếu không có lỗi nào, danh
    sách lỗi)."""
    output, problems = normalize_ids(output)
    output, dropped = drop_protagonist_knows(output)
    if dropped:
        # Chỉ số cạnh và loại, không id hay chữ của fact (G12).
        log.info("khởi tạo: bỏ %d cạnh KNOWS của nhân vật chính ở chương 0 (D-76)", dropped)
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
    # Người chơi đã chọn (và có thể đã sửa) nhân vật chính lúc khởi tạo, nên biết tên nó từ chương 0
    # (D-74). Chỉ mục này: mọi điều khác về nhân vật chính vẫn theo luật cũ.
    nodes.append({"id": INITIAL_CHAPTER_ID, "label": "Chapter",
                  "props": {"number": INITIAL_CHAPTER}})
    edges.append(_edge("REVEALED_TO_PLAYER", PROTAGONIST_ID, INITIAL_CHAPTER_ID,
                       quote=f"{PROTAGONIST_BRIEF_PREFIX}{pc.name}", known_as=pc.name))

    package = _validated(ChangePackage, {"commit_id": commit_id, "nodes": nodes, "edges": edges},
                         "gói chương 0", "package", problems)
    plan = _validated(StoryPlan, {
        "acts": [a.model_dump() for a in output.acts],
        "secrets": [s.model_dump() for s in output.secrets],
        # Khoảng phải gỡ = khoảng dự kiến gỡ của chính mạch đó (một nguồn: đầu ra của model).
        "must_resolve_threads": [
            {"thread_id": t.id, "resolve_from_chapter": t.due_from_chapter,
             "resolve_to_chapter": t.due_to_chapter}
            for t in output.threads if t.must_resolve
        ],
        "milestones": [m.model_dump() for m in output.milestones],
    }, "bản kế hoạch", "plan", problems)
    if package is not None and plan is not None:
        problems += _initial_problems(plan, package, level=level)
    if problems or package is None or plan is None:
        return output, None, problems
    return output, StorySetup(plan=plan, package=package), []


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

# --- bảng cạnh trong đề build_story, sinh từ `_ENDPOINTS` --------------------------------------
# Lần chạy evals/results/2026-10-20-run-tu-tien-1/ hỏng lượt khởi tạo đầu vì model nối RELATES_TO
# giữa Character và Faction. Đề nói kiểu cạnh nào nối những nhãn nào bằng đúng luật mà
# `initial_problems` kiểm, nên đề và phép kiểm không lệch nhau. Chữ chú thích mỗi kiểu ở đây; cặp
# nhãn chỉ ở `_ENDPOINTS`.

# Nhãn → phần trong đầu ra của model (chữ model thấy trong schema).
_LABEL_SECTIONS = {
    "Character": f"nhân vật (`characters` hoặc `{PROTAGONIST_ID}`)",
    "Location": "nơi chốn (`locations`)",
    "Item": "đồ vật (`items`)",
    "Faction": "phe (`factions`)",
}
_EDGE_NOTES = {
    "RELATES_TO": "`kind` như bạn, thù, thầy trò, người yêu; `score` từ -100 đến 100; có hướng, "
                  "mỗi chiều một cạnh",
    "LOCATED_AT": "mỗi thứ ở một nơi",
    "HOLDS": "đồ vật đang giữ; mỗi đồ vật một người giữ",
    "MEMBER_OF": "nhân vật là thành viên của phe",
}


def edge_rules() -> str:
    """Khối "Cạnh trong `edges`" của đề build_story: mỗi kiểu cạnh model được khai ở chương 0, nối
    từ nhãn nào tới nhãn nào, đọc thẳng từ `_ENDPOINTS`."""

    def side(labels: frozenset[str]) -> str:
        return " hoặc ".join(_LABEL_SECTIONS[label] for label in sorted(labels))

    head = ("Cạnh trong `edges` (chỉ các kiểu và cặp nhãn dưới đây, theo chiều từ → tới; nối khác "
            "bảng này thì thế giới không dựng được):")
    lines = [head]
    for etype in get_args(InitialEdgeType):
        sources, targets = _ENDPOINTS[etype]
        lines.append(f"- `{etype}`: {side(sources)} → {side(targets)}; {_EDGE_NOTES[etype]}.")
    lines.append("Kiểu khác `RELATES_TO` thì `kind` và `score` là null. Quan hệ không có trong "
                 "bảng (ví dụ một nhân vật ngầm qua lại với một phe mà mình không thuộc về) thì "
                 "viết thành một fact, không viết thành cạnh.")
    return "\n".join(lines)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def initial_problems(plan: StoryPlan, package: ChangePackage, *, level: LengthLevel) -> list[str]:
    """Kiểm bằng code bản kế hoạch và gói chương 0 (D-38), kể cả nhịp theo mức độ dài (D-49).
    Rỗng là hợp lệ. Luật luôn đúng của kế hoạch (khoảng trong số chương, mốc kết, hồi có mốc)
    nằm trong validator của `StoryPlan`.

    Lỗi chỉ nêu id, nhãn và số chương, không chép chữ của truyện. Danh sách này chỉ vào lượt sửa
    và truth_dump; log chỉ có loại lỗi (D-54, `SetupProblem`)."""
    return [p.text for p in _initial_problems(plan, package, level=level)]


def _initial_problems(
    plan: StoryPlan, package: ChangePackage, *, level: LengthLevel
) -> list[SetupProblem]:
    labels = {n.id: n.label for n in package.nodes}
    protagonists = {n.id for n in package.nodes if n.props.get("is_protagonist") is True}
    problems = [SetupProblem("chapter_0", f"chương 0: {p}")
                for p in chapter_rule_problems(package, INITIAL_CHAPTER)]
    problems += [SetupProblem("nodes", p) for p in _node_problems(package)]
    if len(protagonists) != 1 or labels[next(iter(protagonists))] != "Character":
        problems.append(SetupProblem("protagonist", (
            f"cần đúng một nhân vật chính (Character có is_protagonist), "
            f"có {len(protagonists)}: {sorted(protagonists)}")))
    problems += [SetupProblem("edges", p) for p in _edge_problems(package, labels, protagonists)]
    problems += _plan_problems(plan, package, labels, level)
    if not problems:
        # Lưới cuối, theo định nghĩa duy nhất của player_view (G1): chỉ biết nhân vật chính.
        view = player_view_of(OverlayState(EmptyState(), [package]), INITIAL_CHAPTER)
        if [e.id for e in view.entries] != [PROTAGONIST_ID] or view.lies:
            problems.append(SetupProblem("player_view", (
                f"player_view ở chương 0 chỉ được có nhân vật chính {PROTAGONIST_ID}, có: "
                f"{sorted({e.id for e in view.entries} | {x.id for x in view.lies})}")))
    return problems


def _node_problems(package: ChangePackage) -> list[str]:
    problems = []
    names: dict[tuple[str, str], list[str]] = {}
    for n in package.nodes:
        if n.label == "Chapter":
            if n.id != INITIAL_CHAPTER_ID or n.props.get("number") != INITIAL_CHAPTER:
                problems.append(f"nút {n.id}: nhãn Chapter chỉ dùng cho {INITIAL_CHAPTER_ID} "
                                f"(number {INITIAL_CHAPTER}) ở chương 0")
            continue
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
    names = {n.id: n.props.get("name") for n in package.nodes}
    reveals: Counter[str] = Counter()
    for e in package.edges:
        if e.type == "REVEALED_TO_PLAYER":
            reveals[e.source] += 1
            problems += _reveal_problems(e, labels, protagonists, names)
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
    for pid in protagonists:
        if reveals[pid] != 1:
            problems.append(f"nhân vật chính {pid} phải có đúng một REVEALED_TO_PLAYER ở chương 0 "
                            f"(người chơi đã chọn tên nó), có {reveals[pid]}")
    return problems


def _reveal_problems(
    e: EdgeSpec, labels: dict[str, str], protagonists: set[str], names: dict[str, object]
) -> list[str]:
    """Ở chương 0 chỉ nhân vật chính được hé lộ, tới `ch0`, bằng đúng tên người chơi đã chọn và câu
    trích chứa tên đó (D-74). Người chơi chưa đọc trang nào, nên không nút nào khác."""
    if e.source not in protagonists:
        return [(f"cạnh {e.id}: chương 0 chỉ hé lộ nhân vật chính, không hé lộ {e.source} "
                 "(REVEALED_TO_PLAYER); người chơi chưa đọc trang nào")]
    problems = []
    if e.target != INITIAL_CHAPTER_ID or labels.get(e.target) != "Chapter":
        problems.append(f"cạnh {e.id}: REVEALED_TO_PLAYER ở chương 0 phải tới {INITIAL_CHAPTER_ID}")
    # `known_as` nằm trong `quote` đã do `EdgeSpec` bảo đảm khi dựng gói (D-17).
    if e.props.get("known_as") != names.get(e.source):
        problems.append(f"cạnh {e.id}: known_as phải đúng tên nhân vật chính người chơi đã chọn")
    return problems


def _plan_problems(
    plan: StoryPlan, package: ChangePackage, labels: dict[str, str], level: LengthLevel
) -> list[SetupProblem]:
    problems: list[SetupProblem] = []

    def add(kind: ProblemKind, text: str) -> None:
        problems.append(SetupProblem(kind, text))

    expected = 1
    for i, act in enumerate(plan.acts, 1):
        if act.from_chapter != expected:
            add("acts", f"hồi thứ {i} bắt đầu ở chương {act.from_chapter}, cần chương "
                        f"{expected}: các hồi phải liền nhau từ chương 1")
        expected = act.to_chapter + 1
    total, chapters, milestones = plan.total_chapters, level.chapters, level.milestones
    if not chapters.min <= total <= chapters.max:
        add("length", f"kế hoạch có {total} chương, mức độ dài cần {chapters.min}–{chapters.max}")
    if not milestones.min <= len(plan.milestones) <= milestones.max:
        add("milestones", f"cần {milestones.min}–{milestones.max} mốc, có {len(plan.milestones)}")
    # Chương cuối không tính (D-54): chương kết vốn gỡ nhiều mạch cùng lúc.
    cap = level.max_due_per_chapter
    for c, n in plan.deadlines().items():
        if c != total and n > cap:
            add("pacing", f"chương {c} có {n} việc đến hạn, tối đa {cap} (trừ chương cuối)")
    if not SECRETS_MIN <= len(plan.secrets) <= SECRETS_MAX:
        add("secrets", f"cần {SECRETS_MIN}–{SECRETS_MAX} bí mật, có {len(plan.secrets)}")
    for s in plan.secrets:
        if labels.get(s.fact_id) != "Fact":
            add("secrets", f"bí mật {s.fact_id} không trỏ tới Fact có trong gói")
        if not s.leak_terms:
            add("secrets", f"bí mật {s.fact_id} thiếu leak_terms (D-26)")
        elif any(len(group) < LEAK_GROUP_MIN_PHRASES for group in s.leak_terms):
            add("secrets", f"bí mật {s.fact_id}: mỗi nhóm leak_terms cần ít nhất "
                           f"{LEAK_GROUP_MIN_PHRASES} cụm")
        for node_id in s.protects:  # D-61: id phải là nút có tên có thật trong gói
            if node_id == PROTAGONIST_ID:
                add("secrets", f"bí mật {s.fact_id}: protects không được có {PROTAGONIST_ID} "
                               "(tên do người chơi chọn, D-48)")
            elif labels.get(node_id) not in NAMED_LABELS:
                add("secrets", f"bí mật {s.fact_id}: protects có {node_id}, không phải nút có tên "
                               "trong gói (Character, Location, Faction, Item)")
    threads = {n.id: n.props for n in package.nodes if n.label == "Thread"}
    for t in plan.thread_ids:
        if t not in threads:
            add("threads", f"mạch {t} không có nút Thread trong gói")
    for tid, props in threads.items():
        planted = props.get("planted_chapter")
        low, high = props.get("due_from_chapter"), props.get("due_to_chapter")
        if not _is_int(planted) or planted != INITIAL_CHAPTER:
            add("threads", f"mạch {tid}: planted_chapter phải là {INITIAL_CHAPTER}")
        if not (_is_int(low) and _is_int(high) and 1 <= low <= high <= total):
            add("threads", f"mạch {tid}: khoảng gỡ {low}–{high} phải nằm trong chương 1–{total}")
    return problems
