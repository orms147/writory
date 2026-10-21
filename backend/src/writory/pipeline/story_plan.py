"""Bản kế hoạch truyện (`story_plan`, design §6.1): hồi, mốc cốt truyện, bí mật kèm khoảng chương
lộ, mạch phải gỡ kèm khoảng chương gỡ. Ẩn với người chơi. Người canh dùng nó để biết "lộ sớm" và
"trễ hạn" là gì (design §8 mục 2); đề dàn ý và đề viết nhận mục tiêu của chương từ đây
(`pipeline.pacing`, D-49).

Tạo lúc khởi tạo truyện: `pipeline.setup.build_story` (D-38). Cập nhật khi lựa chọn làm lệch hướng
thì chưa làm.

Tương thích ngược (D-49): kế hoạch cũ (Postgres `story_plans`, fixture) có `must_resolve_threads`
là danh sách id và không có `milestones`; vẫn đọc được. Mạch không có khoảng gỡ thì nơi dùng lấy
khoảng dự kiến gỡ trên nút `Thread` (`guard.plan`).
"""

import re
from collections import Counter
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator

from writory.graph.package import ID_PATTERN


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def _ordered(low: int, high: int, what: str) -> None:
    if low > high:
        raise ValueError(f"{what}: chương đầu ({low}) lớn hơn chương cuối ({high})")


class Act(_Strict):
    name: str = Field(min_length=1)
    from_chapter: PositiveInt
    to_chapter: PositiveInt

    @model_validator(mode="after")
    def _range(self) -> Self:
        _ordered(self.from_chapter, self.to_chapter, f"hồi {self.name!r}")
        return self


class Secret(_Strict):
    """Một bí mật và khoảng chương dự kiến lộ cho người chơi.

    `leak_terms`: các nhóm cụm từ cho bộ dò lộ (G2, D-26). Một nhóm "trúng" khi mọi cụm trong
    nhóm cùng nằm trong một câu, ví dụ [["Lan", "gián điệp"], ["Lan", "người của Hội Hắc Kỳ"]].

    `protects`: id các nút có tên mà bí mật này giấu danh tính (D-61). Tên và biệt danh lớp truth của
    chúng bị cấm cùng điều kiện với `leak_terms`: bí mật chưa lộ. Kế hoạch cũ không có trường này
    (mặc định rỗng).
    """

    fact_id: str = Field(pattern=ID_PATTERN)
    reveal_from_chapter: PositiveInt
    reveal_to_chapter: PositiveInt
    leak_terms: list[list[str]] = []
    protects: list[str] = []

    @model_validator(mode="after")
    def _range(self) -> Self:
        _ordered(self.reveal_from_chapter, self.reveal_to_chapter, f"bí mật {self.fact_id}")
        if len(set(self.protects)) != len(self.protects):
            raise ValueError(f"bí mật {self.fact_id}: protects có id trùng")
        for node_id in self.protects:
            if not re.fullmatch(ID_PATTERN, node_id):
                raise ValueError(f"bí mật {self.fact_id}: protects có id sai dạng: {node_id!r}")
        for group in self.leak_terms:
            phrases = [p.strip() for p in group]
            if not phrases or not all(phrases) or len(set(phrases)) != len(phrases):
                raise ValueError(
                    f"bí mật {self.fact_id}: mỗi nhóm leak_terms phải có ít nhất một cụm, "
                    "không rỗng, không trùng"
                )
        return self


class ThreadPlan(_Strict):
    """Mạch phải gỡ trước khi kết, kèm khoảng chương phải gỡ (D-49). Kế hoạch cũ không có khoảng
    (cả hai None)."""

    thread_id: str = Field(pattern=ID_PATTERN)
    resolve_from_chapter: PositiveInt | None = None
    resolve_to_chapter: PositiveInt | None = None

    @model_validator(mode="after")
    def _range(self) -> Self:
        low, high = self.resolve_from_chapter, self.resolve_to_chapter
        if (low is None) != (high is None):
            raise ValueError(f"mạch {self.thread_id}: khoảng gỡ phải có đủ chương đầu và cuối")
        if low is not None and high is not None:
            _ordered(low, high, f"mạch {self.thread_id}")
        return self


MilestoneKind = Literal["turning_point", "climax", "ending"]  # bước ngoặt, cao trào, kết


class Milestone(_Strict):
    """Một mốc chính của cốt truyện: điều phải xảy ra trong khoảng chương (D-49). `goal` là chữ
    lớp truth, chỉ vào đề dàn ý và đề viết."""

    kind: MilestoneKind
    goal: str
    from_chapter: PositiveInt
    to_chapter: PositiveInt

    @model_validator(mode="after")
    def _range(self) -> Self:
        if not self.goal.strip():
            raise ValueError("mốc: goal không được rỗng")
        _ordered(self.from_chapter, self.to_chapter, f"mốc {self.kind}")
        return self


class StoryPlan(_Strict):
    acts: list[Act] = Field(min_length=1)
    secrets: list[Secret] = []
    must_resolve_threads: list[ThreadPlan] = []
    milestones: list[Milestone] = []

    @field_validator("must_resolve_threads", mode="before")
    @classmethod
    def _legacy_thread_ids(cls, value: Any) -> Any:
        """Kế hoạch cũ: danh sách id mạch, chưa có khoảng gỡ."""
        if isinstance(value, list):
            return [{"thread_id": v} if isinstance(v, str) else v for v in value]
        return value

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        for prev, act in zip(self.acts, self.acts[1:], strict=False):
            if act.from_chapter <= prev.to_chapter:
                raise ValueError(
                    f"hồi {act.name!r} bắt đầu ở chương {act.from_chapter}, "
                    f"chồng lên hoặc đứng trước hồi {prev.name!r} (tới chương {prev.to_chapter})"
                )
        for what, ids in (
            ("bí mật", [s.fact_id for s in self.secrets]),
            ("mạch", list(self.thread_ids)),
        ):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                raise ValueError(f"{what} trùng id: {dup}")
        total = self.total_chapters
        windows = [(f"bí mật {s.fact_id}", s.reveal_to_chapter) for s in self.secrets]
        windows += [(f"mạch {t.thread_id}", t.resolve_to_chapter) for t in self.must_resolve_threads
                    if t.resolve_to_chapter is not None]
        windows += [(f"mốc {m.kind}", m.to_chapter) for m in self.milestones]
        beyond = [what for what, high in windows if high > total]
        if beyond:
            raise ValueError(f"khoảng chương vượt quá {total} chương của truyện: {beyond}")
        if self.milestones:
            self._check_milestones(total)
        return self

    def _check_milestones(self, total: int) -> None:
        """Mốc kết đúng một, nằm ở chương cuối; mỗi hồi có ít nhất một mốc hết hạn trong hồi."""
        endings = [m for m in self.milestones if m.kind == "ending"]
        if len(endings) != 1:
            raise ValueError(f"cần đúng một mốc kết (ending), có {len(endings)}")
        if (endings[0].from_chapter, endings[0].to_chapter) != (total, total):
            raise ValueError(f"mốc kết phải nằm ở chương cuối ({total}), đang ở chương "
                             f"{endings[0].from_chapter}–{endings[0].to_chapter}")
        empty = [i for i, a in enumerate(self.acts, 1)
                 if not any(a.from_chapter <= m.to_chapter <= a.to_chapter
                            for m in self.milestones)]
        if empty:
            raise ValueError(f"hồi thứ {empty} không có mốc nào kết thúc trong hồi")

    @property
    def total_chapters(self) -> int:
        """Số chương của truyện theo kế hoạch: chương cuối của hồi cuối (các hồi xếp theo thứ tự)."""
        return self.acts[-1].to_chapter

    @property
    def thread_ids(self) -> tuple[str, ...]:
        return tuple(t.thread_id for t in self.must_resolve_threads)

    def secret(self, fact_id: str) -> Secret | None:
        return next((s for s in self.secrets if s.fact_id == fact_id), None)

    def thread(self, thread_id: str) -> ThreadPlan | None:
        return next((t for t in self.must_resolve_threads if t.thread_id == thread_id), None)

    def act_of(self, chapter: int) -> tuple[int, Act] | None:
        """(thứ tự 1-based, hồi) chứa chương này."""
        return next(((i, a) for i, a in enumerate(self.acts, 1)
                     if a.from_chapter <= chapter <= a.to_chapter), None)

    def deadlines(self) -> dict[int, int]:
        """Số việc đến hạn ở mỗi chương: bí mật (`reveal_to_chapter`), mạch phải gỡ có khoảng
        (`resolve_to_chapter`), mốc (`to_chapter`). Luật "không dồn vào một chương" (D-49) so số
        này với `story_lengths.levels.*.max_due_per_chapter`, trừ chương cuối (D-54,
        `pipeline.setup`)."""
        due: Counter[int] = Counter(s.reveal_to_chapter for s in self.secrets)
        due.update(t.resolve_to_chapter for t in self.must_resolve_threads
                   if t.resolve_to_chapter is not None)
        due.update(m.to_chapter for m in self.milestones)
        return dict(sorted(due.items()))
