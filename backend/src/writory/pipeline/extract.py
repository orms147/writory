"""Trích thay đổi đồ thị từ văn bản một chương (design §6.2 bước 3; G3, G11, D-17, D-21, D-22).

Đầu vào: danh mục thực thể đang có (id, nhãn, tên/chữ), các cạnh đang hiệu lực, văn bản chương.
Đầu ra: `ChangePackage` của chương N. Model chỉ được tham chiếu id trong danh mục (G11); bản đầu
chưa tạo nút mới, nên danh mục phải có sẵn mọi nút của chương (bài C v1, docs/eval.md).

Model trả JSON theo `ExtractOutput`: mọi trường bắt buộc, giá trị trống là null, để dùng được với
JSON schema strict. Code đổi sang `ChangePackage`, kiểm từng cạnh một: cạnh sai quy tắc bị bỏ và
đếm lại (`ExtractResult.rejected`), không làm hỏng cả gói. Một trong các quy tắc: `known_as` trùng
tên hay biệt danh lớp truth của một nút khác thì bỏ cạnh, vì người chơi sẽ biết nút này dưới tên
của nút kia (D-62, `safety.reveal.known_as_conflicts`).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from writory.graph.commit import needs_known_as
from writory.graph.package import KNOWS_HOW, ChangePackage, CloseSpec, EdgeSpec, quote_in_text
from writory.graph.schema import NAMED_LABELS
from writory.llm.base import ChatResult, LLMClient
from writory.safety.reveal import known_as_conflicts
from writory.safety.wrap import (
    DATA_NOTICE,
    UserAuthored,
    escape_text,
    system_message,
    user_message,
)

PROMPT_VERSION = "extract-2"  # đổi chữ prompt thì tăng số. extract-2: luật rút từ lý do bị bỏ ở bài C v1

# Kiểu cạnh model được trích. FEELS (lựa chọn nội tâm) do bước ghi lựa chọn ghi, không trích.
ExtractEdgeType = Literal[
    "RELATES_TO", "LOCATED_AT", "HOLDS", "MEMBER_OF", "PARTICIPATED_IN", "DIED_IN",
    "KNOWS", "TOLD", "TOLD_TO", "ABOUT", "RESOLVED_IN", "REVEALED_TO_PLAYER",
]
KnowsHow = Literal["chứng kiến", "được kể", "suy ra", "tự biết", "tự làm"]
assert set(KnowsHow.__args__) == set(KNOWS_HOW)


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExtractedEdge(_Out):
    type: ExtractEdgeType
    source: str
    target: str
    kind: str | None  # RELATES_TO: bạn, thù, yêu, thầy trò…
    score: int | None  # RELATES_TO: −100…100
    how: KnowsHow | None  # KNOWS
    told_by: str | None  # KNOWS với how = "được kể"
    quote: str | None  # REVEALED_TO_PLAYER và KNOWS của nhân vật chính: nguyên văn trong chương
    known_as: str | None  # hé lộ nút có tên: tên người chơi thấy, nằm trong quote
    role: str | None  # PARTICIPATED_IN


class ExtractOutput(_Out):
    edges: list[ExtractedEdge]
    close: list[str]  # id các cạnh đang hiệu lực không còn đúng ở cuối chương


@dataclass(frozen=True)
class Entity:
    id: str
    label: str
    text: str  # tên (nút có tên), chữ của Fact/Event/Lie/Thread, hoặc tiêu đề chương
    aliases: tuple[str, ...] = ()
    user_authored: bool = False

    @classmethod
    def from_node(cls, node_id: str, label: str, props: Mapping[str, Any]) -> "Entity":
        """Mục danh mục từ thuộc tính một nút (lớp truth: tên thật, không phải known_as)."""
        text = (props.get("name") or props.get("text") or props.get("description")
                or props.get("content") or props.get("title") or node_id)
        aliases = tuple(props.get("aliases") or ()) if "name" in props else ()
        return cls(id=node_id, label=label, text=str(text), aliases=aliases,
                   user_authored=bool(props.get("user_authored", False)))


@dataclass(frozen=True)
class OpenEdge:
    id: str
    type: str
    source: str
    target: str


@dataclass
class ExtractResult:
    package: ChangePackage
    rejected: list[tuple[str, str]] = field(default_factory=list)  # (mô tả cạnh, lý do)
    chat: ChatResult | None = None


SYSTEM_PROMPT = """Bạn là người ghi chép đồ thị của một truyện tương tác tiếng Việt. Đọc văn bản một chương và ghi lại những gì THAY ĐỔI hoặc ĐƯỢC HÉ LỘ trong chương đó, dưới dạng cạnh giữa các thực thể.

Quy tắc:
- Chỉ dùng id có trong danh mục thực thể. Không bịa id.
- Chỉ ghi điều xảy ra hoặc được hé lộ trong CHƯƠNG NÀY; điều đã đúng từ trước (đã có trong danh sách cạnh đang hiệu lực) thì không ghi lại.
- Một cạnh đang hiệu lực không còn đúng ở cuối chương (đồ vật đổi chủ, đổi chỗ ở, quan hệ đổi) thì ghi id của nó vào `close` và ghi cạnh mới thay thế.
- Mọi trường không dùng thì để null.

Kiểu cạnh:
- RELATES_TO (nhân vật → nhân vật): B là gì của A lúc này; `kind` (bạn, thù, yêu, thầy trò, người quen…) và `score` từ -100 đến 100. Có hướng: ghi riêng mỗi chiều nếu cả hai đổi.
- LOCATED_AT (nhân vật/đồ vật → nơi chốn), HOLDS (nhân vật → đồ vật đang giữ), MEMBER_OF (nhân vật → phe).
- PARTICIPATED_IN (nhân vật → sự kiện), `role` nếu rõ; DIED_IN (nhân vật → sự kiện nhân vật chết).
- KNOWS (nhân vật → sự thật/sự kiện/lời nói dối): nhân vật biết điều đó từ chương này. `how` là một trong: "chứng kiến", "được kể", "suy ra", "tự biết", "tự làm". Nếu "được kể" thì `told_by` là id người kể. KNOWS tới một lời nói dối nghĩa là biết đó là lời dối.
- TOLD (người nói → lời nói dối) và TOLD_TO (lời nói dối → người nghe).
- ABOUT (sự thật/sự kiện → thực thể mà nó nói về).
- RESOLVED_IN (mạch → nút chương này): một mạch, cài cắm hay câu hỏi bỏ ngỏ được gỡ (trả lời, kết thúc) trong chương này.
- REVEALED_TO_PLAYER (thực thể → nút chương này): điều người chơi được thấy trên trang ở chương này, theo góc nhìn nhân vật chính.

Hé lộ cho người chơi:
- Mỗi thực thể trong danh mục xuất hiện trên trang LẦN ĐẦU ở chương này (chưa có cạnh REVEALED_TO_PLAYER trong danh sách cạnh đang hiệu lực) thì ghi một cạnh REVEALED_TO_PLAYER tới nút chương này. Đã hé lộ ở chương trước thì không ghi lại.
- Không đánh dấu hé lộ một bí mật mà trang chỉ gợi ý hay để người đọc đoán. Chỉ ghi khi trang nói rõ điều đó.

Câu trích (`quote`):
- Bắt buộc với REVEALED_TO_PLAYER và với KNOWS mà người biết là nhân vật chính. Không có câu trích thì KHÔNG ghi cạnh đó.
- Chép NGUYÊN VĂN một đoạn ngắn liền mạch trong chương (một câu là đủ); không sửa chữ, không ghép hai đoạn, không thêm dấu ba chấm.
- Hé lộ một nhân vật, nơi chốn, đồ vật hay phe thì `known_as` là cái tên người chơi đọc thấy trên trang, CHÉP Y NGUYÊN từ bên trong `quote` (cùng chữ hoa, cùng dấu). Không dùng tên thật nếu trang chỉ gọi bằng biệt danh.

Không ghi trùng: mỗi bộ (kiểu, từ, tới) chỉ một cạnh.
"""


def _entity_line(e: Entity) -> list[str | UserAuthored]:
    # Tên/chữ nút do model khởi tạo hay model trích viết: ngoài khối dữ liệu thì escape (G4).
    # Id giữ nguyên để model chép lại được: ID_PATTERN không cho `<`, `&`, nên id không tạo được thẻ.
    head = f"- {e.id} | {e.label} | "
    aliases = f" (gọi là: {', '.join(e.aliases)})" if e.aliases else ""
    if e.user_authored:
        return [head, UserAuthored(e.text + aliases, "entity")]
    return [head + escape_text(e.text + aliases)]


def build_messages(
    *, chapter: int, chapter_id: str, protagonist_id: str, chapter_text: str,
    entities: list[Entity], open_edges: list[OpenEdge],
):
    parts: list[str | UserAuthored] = [
        f"Chương: {chapter} (id nút chương: {chapter_id}). Nhân vật chính: {protagonist_id}.",
        "Danh mục thực thể (id | nhãn | tên hoặc nội dung):",
    ]
    for e in entities:
        parts += _entity_line(e)
    parts.append("Cạnh đang hiệu lực trước chương này (id | kiểu | từ → tới):")
    parts += [f"- {o.id} | {o.type} | {o.source} → {o.target}" for o in open_edges] or ["- (không có)"]
    # Văn bản chương có thể chứa chữ người chơi (tên, hành động tự viết): luôn bọc như dữ liệu (G4).
    parts += ["Văn bản chương:", UserAuthored(chapter_text, "chapter_text")]
    return [system_message(SYSTEM_PROMPT, DATA_NOTICE), user_message(*parts)]


def _node(known: dict[str, Entity], node_id: str, protagonist_id: str) -> dict:
    """Dạng `needs_known_as` cần (graph/commit.py)."""
    return {"labels": [known[node_id].label], "protagonist": node_id == protagonist_id}


def to_package(
    output: ExtractOutput, *, chapter: int, commit_id: str, protagonist_id: str,
    chapter_text: str, entities: list[Entity], open_edges: list[OpenEdge],
) -> tuple[ChangePackage, list[tuple[str, str]]]:
    """Đổi đầu ra của model thành `ChangePackage`; cạnh sai quy tắc bị bỏ, kèm lý do."""
    known = {e.id: e for e in entities}
    # Tên lớp truth của mọi nút có tên, kể cả tên người chơi viết: để bắt `known_as` của nút khác.
    names = {e.id: (e.text, *e.aliases) for e in entities if e.label in NAMED_LABELS}
    open_by_id = {o.id: o for o in open_edges}
    rejected: list[tuple[str, str]] = []
    edges: list[EdgeSpec] = []
    seen: set[str] = set()
    for x in output.edges:
        desc = f"{x.type} {x.source}→{x.target}"
        missing = [i for i in (x.source, x.target, x.told_by) if i is not None and i not in known]
        if missing:
            rejected.append((desc, f"id không có trong danh mục: {missing}"))
            continue
        if x.quote is not None and not quote_in_text(x.quote, chapter_text):
            rejected.append((desc, "câu trích không có nguyên văn trong chương (G3)"))
            continue
        if x.type == "KNOWS" and x.source == protagonist_id and not x.quote:
            # G3: người chơi chỉ biết điều có trên trang; thiếu bằng chứng thì không ghi.
            rejected.append((desc, "nhân vật chính biết mà không có câu trích (G3)"))
            continue
        props = {
            k: v for k, v in (("kind", x.kind), ("score", x.score), ("how", x.how),
                              ("told_by", x.told_by), ("quote", x.quote), ("role", x.role))
            if v is not None
        }
        if needs_known_as(x.type, _node(known, x.source, protagonist_id),
                          _node(known, x.target, protagonist_id)):
            if not x.known_as:
                rejected.append((desc, "hé lộ nút có tên mà thiếu known_as (D-17)"))
                continue
            node = x.source if x.type == "REVEALED_TO_PLAYER" else x.target
            others = known_as_conflicts(x.known_as, node, names)
            if others:
                rejected.append((desc, f"known_as là tên của nút khác: {others} (D-62)"))
                continue
            props["known_as"] = x.known_as
        try:
            spec = EdgeSpec.model_validate(
                {"type": x.type, "from": x.source, "to": x.target, "valid_from_chapter": chapter,
                 "props": props}
            )
        except ValidationError as e:
            rejected.append((desc, "; ".join(err["msg"] for err in e.errors(include_url=False))))
            continue
        if spec.id in seen:
            rejected.append((desc, "trùng cạnh trong cùng gói"))
            continue
        seen.add(spec.id)
        edges.append(spec)
    close: list[CloseSpec] = []
    for cid in dict.fromkeys(output.close):
        if cid not in open_by_id:
            rejected.append((f"close {cid}", "không phải cạnh đang hiệu lực"))
            continue
        close.append(CloseSpec(type=open_by_id[cid].type, id=cid, valid_to_chapter=chapter))
    return ChangePackage(commit_id=commit_id, edges=edges, close=close), rejected


async def extract_changes(
    llm: LLMClient, model: str, *, chapter: int, chapter_id: str, commit_id: str,
    protagonist_id: str, chapter_text: str, entities: list[Entity], open_edges: list[OpenEdge],
    extra: Mapping[str, Any] | None = None,
) -> ExtractResult:
    """Một lời gọi model. Lỗi schema để nơi gọi thử lại theo RETRY_SCHEMA (G11, D-14)."""
    messages = build_messages(
        chapter=chapter, chapter_id=chapter_id, protagonist_id=protagonist_id,
        chapter_text=chapter_text, entities=entities, open_edges=open_edges,
    )
    output, chat = await llm.chat_json(model, messages, ExtractOutput, extra=extra)
    package, rejected = to_package(
        output, chapter=chapter, commit_id=commit_id, protagonist_id=protagonist_id,
        chapter_text=chapter_text,
        entities=entities, open_edges=open_edges,
    )
    return ExtractResult(package=package, rejected=rejected, chat=chat)
