"""Schema phản hồi cho người chơi (G1). Danh sách trắng: mỗi trường khai rõ, dựng từng trường
một từ `PlayerView`, không chép cả object. Không có id lớp truth: mục mang mã công khai
(`graph.public_entries`, D-40)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from writory.graph import PlayerView, public_entries, public_lies


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
