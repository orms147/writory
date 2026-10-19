"""Gói thay đổi đồ thị cho một lần ghi (D-6), kiểm bằng pydantic trước khi chạm Neo4j (G11)."""

import re
import unicodedata
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from writory.graph.schema import RESERVED_PROPS, EdgeType, NodeLabel

ID_PATTERN = r"^[A-Za-z0-9_.:\->@]{1,128}$"

PropValue = str | int | float | bool | list[str] | list[int] | list[float] | None


def _split_props(data: Any, known: set[str]) -> Any:
    """Cho phép dạng phẳng (như trong graph.yaml): khoá lạ được gom vào `props`."""
    if not isinstance(data, dict):
        return data
    extra = {k: v for k, v in data.items() if k not in known}
    if not extra:
        return data
    base = {k: v for k, v in data.items() if k in known}
    base["props"] = {**data.get("props", {}), **extra}
    return base


def _check_props(props: dict[str, PropValue]) -> None:
    bad = RESERVED_PROPS & props.keys()
    if bad:
        raise ValueError(f"thuộc tính dành riêng cho lớp graph: {sorted(bad)}")


class NodeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=ID_PATTERN)
    label: NodeLabel
    props: dict[str, PropValue] = {}

    @model_validator(mode="before")
    @classmethod
    def _flat(cls, data: Any) -> Any:
        return _split_props(data, {"id", "label", "props"})

    @model_validator(mode="after")
    def _reserved(self) -> Self:
        _check_props(self.props)
        return self

    @classmethod
    def from_flat(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)


class EdgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    type: EdgeType
    source: str = Field(alias="from", pattern=ID_PATTERN)
    target: str = Field(alias="to", pattern=ID_PATTERN)
    valid_from_chapter: int = Field(ge=0)
    valid_to_chapter: int | None = None
    id: str = Field(default="", pattern=r"^$|" + ID_PATTERN)
    props: dict[str, PropValue] = {}

    @model_validator(mode="before")
    @classmethod
    def _flat(cls, data: Any) -> Any:
        known = {"type", "from", "to", "source", "target", "valid_from_chapter",
                 "valid_to_chapter", "id", "props"}
        return _split_props(data, known)

    @model_validator(mode="after")
    def _check(self) -> Self:
        _check_props(self.props)
        if self.valid_to_chapter is not None and self.valid_to_chapter <= self.valid_from_chapter:
            raise ValueError("valid_to_chapter phải lớn hơn valid_from_chapter")
        if self.type == "REVEALED_TO_PLAYER":
            quote = self.props.get("quote")
            if not isinstance(quote, str) or not quote.strip():
                raise ValueError("REVEALED_TO_PLAYER phải kèm câu trích `quote` (G3)")
        if not self.id:
            key = f"{self.type}:{self.source}>{self.target}@{self.valid_from_chapter}"
            object.__setattr__(self, "id", key)
        return self


class CloseSpec(BaseModel):
    """Đóng một cạnh đã có: đặt valid_to_chapter. Không xoá sự thật cũ."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: EdgeType
    id: str = Field(pattern=ID_PATTERN)
    valid_to_chapter: int = Field(ge=1)


class ChangePackage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    commit_id: str = Field(pattern=ID_PATTERN)
    nodes: list[NodeSpec] = []
    edges: list[EdgeSpec] = []
    close: list[CloseSpec] = []

    @model_validator(mode="after")
    def _unique(self) -> Self:
        for kind, ids in (
            ("nút", [n.id for n in self.nodes]),
            ("cạnh", [e.id for e in self.edges]),
            ("close", [c.id for c in self.close]),
        ):
            dup = {i for i in ids if ids.count(i) > 1}
            if dup:
                raise ValueError(f"id {kind} trùng trong gói: {sorted(dup)}")
        return self


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def quote_in_text(quote: str, text: str) -> bool:
    """Câu trích có nằm nguyên văn trong văn bản không (G3). So sau khi chuẩn hoá NFC và khoảng trắng."""
    q = _normalize(quote)
    return bool(q) and q in _normalize(text)
