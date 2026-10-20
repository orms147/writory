"""Schema phản hồi cho người chơi (G1). Danh sách trắng: mỗi trường khai rõ, dựng từng trường
một từ `PlayerView`, không chép cả object. Không có id lớp truth: mục mang mã công khai
(`graph.public_entries`, D-40)."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from writory.db import SetupRecord
from writory.graph import PlayerView, public_entries, public_lies
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
    genre: Tag
    era: Tag | None = None
    voice: Tag | None = None
    darkness: Tag | None = None


class NamingIn(_Out):
    names: Literal["han_viet", "viet"]
    places: Literal["hu_cau", "that"]


class SetupStartIn(_Out):
    tags: StoryTagsIn
    length_level: str = Field(max_length=32)  # khoá trong config/story_lengths.yaml
    naming: NamingIn | None = None  # None: mặc định theo thể loại (D-32)


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
    darkness: str | None


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
            tags=TagsOut(genre=tags.genre, era=tags.era, voice=tags.voice, darkness=tags.darkness),
            length_level=choices.length_level,
            naming=NamingOut(names=choices.naming.names, places=choices.naming.places),
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
