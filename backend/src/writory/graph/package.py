"""Gói thay đổi đồ thị cho một lần ghi (D-6), kiểm bằng pydantic trước khi chạm Neo4j (G11)."""

import re
import unicodedata
from collections.abc import Sequence
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from writory.graph.schema import RESERVED_PROPS, EdgeType, NodeLabel

ID_MAX_LEN = 128
ID_PATTERN = rf"^[A-Za-z0-9_.:\->@]{{1,{ID_MAX_LEN}}}$"

PropValue = str | int | float | bool | list[str] | list[int] | list[float] | None

# Cách một nhân vật biết điều gì (cạnh KNOWS, D-22). "được kể" bắt buộc có `told_by`.
KNOWS_HOW = ("chứng kiến", "được kể", "suy ra", "tự biết", "tự làm")
TOLD = "được kể"
_ID_RE = re.compile(ID_PATTERN)


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
        quote = self.props.get("quote")
        if self.type == "REVEALED_TO_PLAYER" and (not isinstance(quote, str) or not quote.strip()):
            raise ValueError("REVEALED_TO_PLAYER phải kèm câu trích `quote` (G3)")
        if "known_as" in self.props:
            known_as = self.props["known_as"]
            if not isinstance(known_as, str) or not isinstance(quote, str) or not quote_in_text(
                known_as, quote
            ):
                raise ValueError("`known_as` phải nằm trong `quote` (D-17)")
        self._check_knowledge_props()
        if not self.id:
            key = f"{self.type}:{self.source}>{self.target}@{self.valid_from_chapter}"
            object.__setattr__(self, "id", key)
        return self


    def _check_knowledge_props(self) -> None:
        """D-22: `how` thuộc KNOWS_HOW; "được kể" kèm `told_by`; `by_choice` là id lựa chọn."""
        props = self.props
        if "how" in props:
            how = props["how"]
            how = unicodedata.normalize("NFC", how) if isinstance(how, str) else how
            if self.type != "KNOWS" or how not in KNOWS_HOW:
                raise ValueError(f"`how` chỉ dùng cho KNOWS, một trong {KNOWS_HOW}; nhận {how!r}")
            object.__setattr__(self, "props", {**props, "how": how})
        told = self.props.get("how") == TOLD
        told_by = props.get("told_by")
        if told and not (isinstance(told_by, str) and _ID_RE.fullmatch(told_by)):
            raise ValueError("KNOWS với how = \"được kể\" phải có `told_by` là id người kể")
        if not told and "told_by" in props:
            raise ValueError("`told_by` chỉ dùng khi how = \"được kể\"")
        if "by_choice" in props:
            choice = props["by_choice"]
            if self.type not in ("KNOWS", "REVEALED_TO_PLAYER") or not (
                isinstance(choice, str) and _ID_RE.fullmatch(choice)
            ):
                raise ValueError("`by_choice` là id lựa chọn, chỉ trên KNOWS/REVEALED_TO_PLAYER")


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


def chapter_rule_problems(package: ChangePackage, chapter: int) -> list[str]:
    """Gói của chương N chỉ mở cạnh từ chương N và chỉ đóng cạnh ở chương N (D-21).
    Nhờ vậy, khi chương N còn pending, đọc ở chương N-1 không thấy gì của nó."""
    problems = [
        f"cạnh {e.id} mở từ chương {e.valid_from_chapter}, gói thuộc chương {chapter}"
        for e in package.edges
        if e.valid_from_chapter != chapter
    ]
    problems += [
        f"cạnh {e.id} đặt sẵn ngày đóng (chương {e.valid_to_chapter})"
        for e in package.edges
        if e.valid_to_chapter is not None
    ]
    problems += [
        f"close {c.id} ở chương {c.valid_to_chapter}, gói thuộc chương {chapter}"
        for c in package.close
        if c.valid_to_chapter != chapter
    ]
    return problems


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def quote_in_text(quote: str, text: str) -> bool:
    """Câu trích có nằm nguyên văn trong văn bản không (G3). So sau khi chuẩn hoá NFC và khoảng trắng."""
    q = _normalize(quote)
    return bool(q) and q in _normalize(text)


_QUOTE_SHOWN_CHARS = 80


def quote_problems(package: ChangePackage, scenes: Sequence[str], *, protagonist: str) -> list[str]:
    """Kiểm cuối của G3 ở bước ghi chương N >= 1 (D-106): câu trích phải có nguyên văn trong văn
    đã hiện của chính chương đó, trong một cảnh (`quote_in_text`).

    - `REVEALED_TO_PLAYER` và `KNOWS` từ nhân vật chính: bắt buộc có `quote`, và `quote` ở trên trang.
    - `RESOLVED_IN` có `quote`: `quote` ở trên trang (gói dựng tay có thể không có quote).
    - Nút `Chapter` mang `milestones` (mốc đã diễn ra, D-115): có đủ một `milestone_quotes` cho mỗi
      mốc, và mỗi câu ở trên trang.

    Mọi câu trích của đường pipeline đều lấy từ chữ một cảnh: bộ trích (`to_package`), tự hé lộ
    (D-62, câu chứa tên), Fact mới (D-93). Chương 0 không qua đây: câu trích của nó là dòng của
    thiết lập truyện (`story_brief`, D-74), không phải văn chương. Trả danh sách lỗi cho log."""
    problems = []
    for e in package.edges:
        required = e.type == "REVEALED_TO_PLAYER" or (e.type == "KNOWS" and e.source == protagonist)
        if not required and e.type != "RESOLVED_IN":
            continue
        quote = e.props.get("quote")
        if quote is None and not required:
            continue
        if not isinstance(quote, str) or not quote.strip():
            problems.append(f"cạnh {e.type} {e.id} thiếu câu trích (G3)")
        elif not any(quote_in_text(quote, s) for s in scenes):
            shown = _normalize(quote)[:_QUOTE_SHOWN_CHARS]
            problems.append(f"cạnh {e.type} {e.id}: câu trích không có trong văn chương: {shown!r}")
    for n in package.nodes:
        marks = n.props.get("milestones")
        if n.label != "Chapter" or marks is None:
            continue
        quotes = n.props.get("milestone_quotes")
        if not isinstance(marks, list) or not isinstance(quotes, list) or len(quotes) != len(marks):
            problems.append(f"nút {n.id}: mốc đã diễn ra thiếu câu trích tương ứng (G3)")
            continue
        for number, quote in zip(marks, quotes, strict=True):
            if not isinstance(quote, str) or not any(quote_in_text(quote, s) for s in scenes):
                shown = _normalize(str(quote))[:_QUOTE_SHOWN_CHARS]
                problems.append(f"nút {n.id}: câu trích của mốc {number} không có trong văn chương: "
                                f"{shown!r}")
    return problems
