"""Schema phản hồi cho người chơi (G1). Danh sách trắng: mỗi trường khai rõ, dựng từng trường
một từ `PlayerView`, không chép cả object. Không có id lớp truth: mục mang mã công khai
(`graph.public_entries`, D-40)."""

import re
from datetime import UTC
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from writory.config import AppConfig, StoryLengthsConfig
from writory.db import OwnerCosts, SetupRecord, StorySummaryRecord
from writory.graph import PlayerView, public_entries, public_lies
from writory.pipeline.events import PlayerChoice
from writory.pipeline.setup import OPTION_COUNT, StoryChoices


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class NotebookEntryOut(_Out):
    ref: str  # mã công khai "m1", "m2"…; ổn định trong một chương
    kind: Literal["Character", "Location", "Item", "Faction", "Fact", "Event", "Lie"]
    text: str  # chữ hiện (known_as với nút có tên, D-17)
    aliases: list[str]  # các known_as khác đã hé lộ
    since_chapter: int
    quote: str | None  # câu trích lần đầu, nguyên văn trên trang (G3)
    about: list[str]  # mã của các mục khác trong cùng sổ tay
    # Mục là nhân vật chính, tức chính người chơi (D-74); giao diện ghi nhãn "Bạn" (D-76). Người
    # chơi đã chọn nhân vật này lúc khởi tạo, nên cờ không phải điều của lớp truth.
    is_protagonist: bool


class NotebookLieOut(_Out):
    content: str
    chapter: int
    told_to: list[str]  # tên người chơi biết của người nghe, hoặc "(người chưa rõ tên)"


class NotebookOut(_Out):
    chapter: int
    entries: list[NotebookEntryOut]
    lies: list[NotebookLieOut]

    @classmethod
    def from_view(cls, view: PlayerView) -> "NotebookOut":
        entries = public_entries(view)
        ref_of = {e.id: ref for ref, e in entries}
        return cls(
            chapter=view.chapter,
            entries=[
                NotebookEntryOut(
                    ref=ref,
                    kind=e.kind,
                    text=e.text,
                    aliases=list(e.aliases),
                    since_chapter=e.since_chapter,
                    quote=e.quote,
                    about=[ref_of[a] for a in e.about if a in ref_of],
                    is_protagonist=e.is_protagonist,
                )
                for ref, e in entries
            ],
            lies=[
                NotebookLieOut(content=lie.content, chapter=lie.chapter,
                               told_to=list(lie.told_to))
                for _, lie in public_lies(view)
            ],
        )


class NarratorQuestionIn(_Out):
    # Độ dài kiểm trong ask_narrator theo config (limits.input.narrator_question_max_chars).
    question: str


class NarratorAnswerOut(_Out):
    answer: str
    remaining: int  # số câu còn hỏi được ở chương này, sau câu vừa rồi (D-65)
    source_chapters: list[int]  # chương của các mục câu trả lời dẫn; rỗng khi NOT_KNOWN (D-65)


class NarratorRemainingOut(_Out):
    remaining: int


# --- key người chơi (G7, D-45) ---------------------------------------------------------------


class PlayerKeyIn(_Out):
    # SecretStr: repr/log của model không lộ key. Dạng key kiểm bằng `safety.crypto`.
    api_key: SecretStr


class PlayerKeyOut(_Out):
    """Không bao giờ có key: chỉ có hay không, và 4 ký tự cuối ("•••• 7f3a" ở giao diện)."""

    has_key: bool
    last4: str | None


# --- khởi tạo truyện (design §4.1, D-45) -------------------------------------------------------

TAG_MAX_CHARS = 60  # tag là nhãn ngắn; trần cứng để thân yêu cầu không phình
EDIT_HARD_MAX_CHARS = 5000  # trần cứng của trường sửa nhân vật; giới hạn thật: limits.input

Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1,
                                       max_length=TAG_MAX_CHARS)]
# Số thứ tự lựa chọn: chỉ số nguyên JSON, 0…OPTION_COUNT-1. Trình duyệt không gửi chữ lựa chọn.
OptionIndex = Annotated[int, Field(ge=0, le=OPTION_COUNT - 1, strict=True)]
Edit = Annotated[str | None, Field(max_length=EDIT_HARD_MAX_CHARS)]


class StoryTagsIn(_Out):
    # Không còn `darkness` chữ tự do: mức u tối là `SetupStartIn.darkness_level` (D-67).
    genre: Tag
    era: Tag | None = None
    voice: Tag | None = None


class NamingIn(_Out):
    names: Literal["han_viet", "viet"]
    places: Literal["hu_cau", "that"]


class SetupStartIn(_Out):
    tags: StoryTagsIn
    length_level: str = Field(max_length=32)  # khoá trong config/story_lengths.yaml
    naming: NamingIn | None = None  # None: mặc định theo thể loại (D-32)
    # Khoá trong config/moderation.yaml `darkness_levels`; None: `default_darkness_level` (D-67).
    darkness_level: str | None = Field(default=None, max_length=32)
    # Kiểu truyện (D-153): "prose" truyện chữ như trước, "audio" kịch bản để TTS đọc.
    style: Literal["prose", "audio"] = "prose"


class OptionChoiceIn(_Out):
    index: OptionIndex


class CharacterChoiceIn(_Out):
    """Chọn nhân vật thứ `index`, kèm phần người chơi sửa (null: giữ chữ của lựa chọn)."""

    index: OptionIndex
    name: Edit = None
    personality: Edit = None
    backstory: Edit = None


class TagsOut(_Out):
    genre: str
    era: str | None
    voice: str | None


class NamingOut(_Out):
    names: str
    places: str


class SettingOut(_Out):
    title: str
    intro: str


class PlotOut(_Out):
    title: str
    summary: str


class CharacterOut(_Out):
    name: str
    personality: str
    backstory: str


SetupStage = Literal["settings", "plots", "characters", "finalize", "done"]


class SetupOut(_Out):
    """Trạng thái phiên khởi tạo. Chỉ có điều người chơi chọn hoặc đọc; không có bản kế hoạch,
    bí mật hay id lớp truth (G1). `step`: bước người chơi đang ở; danh sách null là chưa tạo."""

    session_id: str
    step: SetupStage
    tags: TagsOut
    length_level: str
    naming: NamingOut
    darkness_level: str | None  # khoá mức u tối đã chọn (D-67); None chỉ ở phiên tạo trước D-67
    style: Literal["prose", "audio"]  # kiểu truyện (D-153)
    settings: list[SettingOut] | None
    setting_index: int | None
    plots: list[PlotOut] | None
    plot_index: int | None
    characters: list[CharacterOut] | None
    character_index: int | None
    protagonist: CharacterOut | None
    story_id: str | None  # có khi đã tạo truyện; dùng cho /stories/{story_id}/…

    @classmethod
    def from_record(cls, rec: SetupRecord) -> "SetupOut":
        choices = StoryChoices.model_validate(rec.choices)
        tags = choices.tags

        def character(o: dict) -> CharacterOut:
            return CharacterOut(name=o["name"], personality=o["personality"],
                                backstory=o["backstory"])

        if rec.story_id is not None:
            step: SetupStage = "done"
        elif rec.protagonist is not None:
            step = "finalize"
        elif rec.plot_index is not None:
            step = "characters"
        elif rec.setting_index is not None:
            step = "plots"
        else:
            step = "settings"
        return cls(
            session_id=rec.id,
            step=step,
            tags=TagsOut(genre=tags.genre, era=tags.era, voice=tags.voice),
            length_level=choices.length_level,
            naming=NamingOut(names=choices.naming.names, places=choices.naming.places),
            darkness_level=choices.darkness_level,
            style=choices.style,
            settings=None if rec.settings is None else [
                SettingOut(title=o["title"], intro=o["intro"]) for o in rec.settings],
            setting_index=rec.setting_index,
            plots=None if rec.plots is None else [
                PlotOut(title=o["title"], summary=o["summary"]) for o in rec.plots],
            plot_index=rec.plot_index,
            characters=None if rec.characters is None else [
                character(o) for o in rec.characters],
            character_index=rec.character_index,
            protagonist=None if rec.protagonist is None else character(rec.protagonist),
            story_id=rec.story_id,
        )


# --- chơi: chương, lựa chọn, hành động (design §4.2, D-46) -----------------------------------

CHOICE_ID_PATTERN = r"^choice-[0-9a-f]{12}$"  # id mờ do pipeline/choices.py đặt
ACTION_HARD_MAX_CHARS = 5000  # trần cứng; giới hạn thật: limits.input.custom_action_max_chars


class ChoiceIn(_Out):
    choice_id: str = Field(pattern=CHOICE_ID_PATTERN)


class CustomActionIn(_Out):
    # Rỗng và độ dài theo config kiểm trong safety.classify (G5), với mã lỗi riêng.
    text: str = Field(max_length=ACTION_HARD_MAX_CHARS)


class ActionOut(_Out):
    """Hành động dẫn tới chương `for_chapter`. Với lựa chọn: đúng chữ người chơi đã thấy."""

    for_chapter: int
    source: Literal["choice", "custom"]
    text: str


class ChoicesOut(_Out):
    chapter: int
    choices: list[PlayerChoice]  # id mờ, loại, sắc thái, chữ (pipeline/events.py)


class ChapterOut(_Out):
    number: int
    scenes: list[str]  # đúng chữ đã hiện, đã qua mọi phép kiểm (D-1)


class StoryOut(_Out):
    story_id: str
    length_level: str
    chapter: int  # chương đã ghi cuối; 0 = vừa khởi tạo, chưa có trang nào
    pending: bool  # còn chương đang lưu dở (D-6): chưa viết tiếp được
    choices: list[PlayerChoice]  # bộ lựa chọn cuối chương hiện tại; rỗng ở chương 0
    action: ActionOut | None  # hành động đã chọn cho chương sau
    next_ready: bool  # viết được chương sau ngay
    finished: bool  # đã tới chương cuối theo kế hoạch
    style: Literal["prose", "audio"]  # kiểu truyện (D-153)


# --- giao diện: tủ truyện, cấu hình công khai, chi phí (D-66) -----------------------------------

# Hết câu: dấu chấm, chấm than, chấm hỏi, ba chấm (kể cả "…"), kèm ngoặc đóng ngay sau, rồi khoảng
# trắng. Regex chỉ để tách câu (định dạng), không đọc ý định.
_SENTENCE_END = re.compile(r"[.!?…]+[\"”’»)\]]*(?=\s)")
_DIALOGUE = "- "  # dấu thoại sau chuẩn hoá (D-31)


def last_sentence(text: str) -> str | None:
    """Câu cuối của dòng có chữ cuối cùng, đúng chữ đã hiện (một đoạn con của `text`). Bỏ dấu thoại
    "- " ở đầu dòng. Không có chữ thì None."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    line = lines[-1]
    if line.startswith(_DIALOGUE) or line == _DIALOGUE.strip():
        line = line[len(_DIALOGUE):].strip()
    start = 0
    for m in _SENTENCE_END.finditer(line):
        start = m.end()
    sentence = line[start:].strip()
    return sentence or None


class StorySummaryOut(_Out):
    """Một truyện trong tủ truyện. Chỉ chữ người chơi đã thấy; `finished` là một cờ tính từ kế
    hoạch ẩn, không kèm số chương của kế hoạch (G1)."""

    story_id: str
    title: str | None  # hướng truyện đã chọn lúc khởi tạo; None: truyện không qua /setup
    length_level: str
    length_label: str | None  # nhãn trong config/story_lengths.yaml; None: khoá không còn
    chapter: int  # chương đã commit
    finished: bool
    last_excerpt: str | None  # câu cuối của cảnh cuối đã hiện; None ở chương 0
    updated_at: str  # ISO 8601, UTC
    style: Literal["prose", "audio"]  # kiểu truyện (D-153)

    @classmethod
    def from_record(cls, rec: StorySummaryRecord,
                    lengths: StoryLengthsConfig) -> "StorySummaryOut":
        chapter = rec.committed_chapter or 0
        level = lengths.levels.get(rec.length_level)
        return cls(
            story_id=rec.id, title=rec.title, length_level=rec.length_level,
            length_label=None if level is None else level.label, chapter=chapter,
            finished=rec.total_chapters is not None and chapter >= rec.total_chapters,
            last_excerpt=None if rec.last_scene is None else last_sentence(rec.last_scene),
            updated_at=rec.updated_at.astimezone(UTC).isoformat(),
            style=rec.style,
        )


class StoryListOut(_Out):
    stories: list[StorySummaryOut]


class InputLimitsOut(_Out):
    custom_action_max_chars: int | None
    character_name_max_chars: int | None
    personality_max_chars: int | None
    backstory_max_chars: int | None
    narrator_question_max_chars: int | None


class CostCapsOut(_Out):
    per_scene: float | None
    per_chapter: float | None
    per_story: float | None


class StoryLengthOut(_Out):
    key: str
    label: str
    chapters_min: int
    chapters_max: int
    style: Literal["prose", "audio"]  # kiểu truyện dùng mức này (D-155)
    minutes: int | None  # phút nghe ước tính của mức audio; None với truyện chữ


class WriterTierOut(_Out):
    label: str


class DarknessLevelOut(_Out):
    key: str
    label: str


class PublicConfigOut(_Out):
    """Các số giao diện cần, lấy từ config/ (null = chưa đặt). Không model id, giá, trần nội bộ của
    mức u tối hay ngưỡng của người canh, kiểm văn (G1, D-66, D-67)."""

    input: InputLimitsOut
    narrator_questions_per_chapter: int | None
    rewrite_per_scene: int
    cost_usd: CostCapsOut
    story_lengths: list[StoryLengthOut]  # chỉ mức người chơi được chọn, theo thứ tự config (D-88)
    writer_tier: WriterTierOut
    darkness_levels: list[DarknessLevelOut]  # theo thứ tự trong config/moderation.yaml
    default_darkness_level: str
    chapter_estimate_default_usd: float | None  # số cho màn không gắn truyện (D-87)

    @classmethod
    def from_config(cls, config: AppConfig, *, writer_label: str) -> "PublicConfigOut":
        lim = config.limits
        mod = config.moderation
        return cls(
            input=InputLimitsOut(
                custom_action_max_chars=lim.input.custom_action_max_chars,
                character_name_max_chars=lim.input.character_name_max_chars,
                personality_max_chars=lim.input.personality_max_chars,
                backstory_max_chars=lim.input.backstory_max_chars,
                narrator_question_max_chars=lim.input.narrator_question_max_chars,
            ),
            narrator_questions_per_chapter=lim.rate_limit.narrator_questions_per_chapter,
            rewrite_per_scene=lim.retries.rewrite_per_scene,
            cost_usd=CostCapsOut(per_scene=lim.cost_usd.per_scene,
                                 per_chapter=lim.cost_usd.per_chapter,
                                 per_story=lim.cost_usd.per_story),
            story_lengths=[
                StoryLengthOut(key=k, label=v.label, chapters_min=v.chapters.min,
                               chapters_max=v.chapters.max, style=v.style, minutes=v.minutes)
                for k, v in config.story_lengths.player_levels().items()
            ],
            writer_tier=WriterTierOut(label=writer_label),
            darkness_levels=[DarknessLevelOut(key=k, label=v.label)
                             for k, v in mod.darkness_levels.items()],
            default_darkness_level=mod.default_darkness_level,
            chapter_estimate_default_usd=lim.chapter_estimate.default_usd,
        )


class StoryCostOut(_Out):
    story_id: str
    spent_usd: float


class ChapterEstimateOut(_Out):
    """Ước tính chi phí chương tới, bằng key của người chơi (D-87). `usd` null: không có số nào.
    Không model, giá, chi phí từng vai hay id (G1)."""

    chapter: int  # chương sẽ viết tiếp
    usd: float | None
    source: Literal["story_median", "default"]
    chapters_used: int  # số chương đã ghi của chính truyện dùng để ước (0 khi dùng số mặc định)


class PlayerCostsOut(_Out):
    """Số người chơi đã trả bằng key của mình, từ nhật ký chi phí. Không có gì của key (G7)."""

    total_usd: float
    this_month_usd: float  # tháng dương lịch theo UTC (D-66)
    stories: list[StoryCostOut]  # truyện tiêu gần nhất trước

    @classmethod
    def from_costs(cls, costs: OwnerCosts) -> "PlayerCostsOut":
        return cls(total_usd=costs.total_usd, this_month_usd=costs.this_month_usd,
                   stories=[StoryCostOut(story_id=sid, spent_usd=usd)
                            for sid, usd in costs.stories])
