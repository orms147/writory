"""Bản kế hoạch truyện (`story_plan`, design §6.1): hồi, bí mật kèm khoảng chương lộ, mạch phải
gỡ trước khi kết. Ẩn với người chơi. Người canh dùng nó để biết "lộ sớm" là gì (design §8 mục 2).

Bản tối thiểu cho người canh tuần 3; phần tạo và cập nhật kế hoạch bằng model làm sau.
"""

from typing import Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

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
    """

    fact_id: str = Field(pattern=ID_PATTERN)
    reveal_from_chapter: PositiveInt
    reveal_to_chapter: PositiveInt
    leak_terms: list[list[str]] = []

    @model_validator(mode="after")
    def _range(self) -> Self:
        _ordered(self.reveal_from_chapter, self.reveal_to_chapter, f"bí mật {self.fact_id}")
        for group in self.leak_terms:
            phrases = [p.strip() for p in group]
            if not phrases or not all(phrases) or len(set(phrases)) != len(phrases):
                raise ValueError(
                    f"bí mật {self.fact_id}: mỗi nhóm leak_terms phải có ít nhất một cụm, "
                    "không rỗng, không trùng"
                )
        return self


class StoryPlan(_Strict):
    acts: list[Act] = Field(min_length=1)
    secrets: list[Secret] = []
    must_resolve_threads: list[str] = []

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
            ("mạch", self.must_resolve_threads),
        ):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                raise ValueError(f"{what} trùng id: {dup}")
        return self

    def secret(self, fact_id: str) -> Secret | None:
        return next((s for s in self.secrets if s.fact_id == fact_id), None)
