"""Phần của bộ xuất kịch bản video làm bằng code (D-125): bảng nhân vật, bảng nơi chốn, sơ đồ tuyến theo
chương dựng từ đồ thị, và nhân vật có mặt trong một cảnh. Không gọi model, không tốn tiền.

Đọc lớp `truth` qua `GraphState` (Neo4jState ở lệnh thật, OverlayState ở test; G10: Cypher chỉ nằm
trong graph/). Chỉ đọc. Mọi chữ ở đây là truth, có thể lộ bí mật: chỉ dành cho bản xuất của admin.
"""

import re
from dataclasses import dataclass

from writory.guard.state import GraphState
from writory.pipeline.bench_a_systems import AliasIndex

_TEXT_FIELD = {"Fact": "text", "Event": "description", "Lie": "content"}


@dataclass(frozen=True)
class CharacterRow:
    id: str
    name: str
    aliases: tuple[str, ...]
    appearance: str | None  # do khởi tạo sinh (D-120); truyện cũ không có
    personality: str | None
    backstory: str | None
    protagonist: bool
    user_authored: bool


@dataclass(frozen=True)
class LocationRow:
    id: str
    name: str
    aliases: tuple[str, ...]
    visual: str | None  # cảnh sắc do khởi tạo sinh (D-120); truyện cũ không có
    description: str | None
    user_authored: bool


@dataclass(frozen=True)
class Cast:
    """Mọi nhân vật và nơi chốn của truyện, theo id."""

    characters: dict[str, CharacterRow]
    locations: dict[str, LocationRow]
    factions: dict[str, str]  # id -> tên
    titles: dict[str, str]  # id -> tên hiện cho mọi nút có tên (nhân vật, nơi, phe, đồ vật)
    protagonist_id: str | None


@dataclass(frozen=True)
class RelationRow:
    source: str  # tên
    target: str
    kind: str
    score: int | None


@dataclass(frozen=True)
class KnowledgeRow:
    who: str
    text: str
    how: str | None
    kind: str  # Fact | Lie | Event


@dataclass(frozen=True)
class EventRow:
    text: str
    participants: tuple[str, ...]
    died: tuple[str, ...]


@dataclass(frozen=True)
class LieRow:
    speaker: str
    text: str


@dataclass(frozen=True)
class ChapterOverview:
    """Sơ đồ tuyến nhân vật của một chương: trạng thái cuối chương và điều mới xảy ra ở chương."""

    chapter: int
    relationships: tuple[RelationRow, ...]
    memberships: tuple[tuple[str, str], ...]  # (nhân vật, phe), hiệu lực ở cuối chương
    where: tuple[tuple[str, str], ...]  # (nhân vật, nơi), hiệu lực ở cuối chương
    knowledge: tuple[KnowledgeRow, ...]  # điều biết MỚI ở chương này (valid_from == chương)
    events: tuple[EventRow, ...]
    lies: tuple[LieRow, ...]
    mermaid: str


def _text_prop(props: dict, key: str) -> str | None:
    value = props.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def read_cast(state: GraphState) -> Cast:
    nodes = state.all_nodes()
    characters, locations, factions, titles = {}, {}, {}, {}
    for nid, row in sorted(nodes.items()):
        props = row.props
        name = _text_prop(props, "name")
        if name:
            titles[nid] = name
        aliases = tuple(a for a in (props.get("aliases") or []) if isinstance(a, str) and a.strip())
        authored = props.get("user_authored") is True
        if row.label == "Character" and name:
            characters[nid] = CharacterRow(
                nid, name, aliases, _text_prop(props, "appearance"), _text_prop(props, "personality"),
                _text_prop(props, "backstory"), props.get("is_protagonist") is True, authored)
        elif row.label == "Location" and name:
            locations[nid] = LocationRow(
                nid, name, aliases, _text_prop(props, "visual"), _text_prop(props, "description"),
                authored)
        elif row.label == "Faction" and name:
            factions[nid] = name
    protagonist = next((c.id for c in characters.values() if c.protagonist), None)
    return Cast(characters, locations, factions, titles, protagonist)


class SceneFinder:
    """Nhân vật có mặt trong một cảnh: nhân vật nào có tên hay biệt danh nằm trong chữ cảnh (khớp trọn từ,
    tên dài trước), cộng nhân vật chính, vì truyện kể ngôi "tôi" nên nhân vật chính luôn có mặt."""

    def __init__(self, cast: Cast) -> None:
        self._cast = cast
        self._index = AliasIndex({c.id: (c.name, *c.aliases) for c in cast.characters.values()})
        self._places = AliasIndex({loc.id: (loc.name, *loc.aliases) for loc in cast.locations.values()})

    def characters_in(self, text: str) -> tuple[str, ...]:
        found = [i for i in self._index.find(text) if i in self._cast.characters]
        if self._cast.protagonist_id and self._cast.protagonist_id not in found:
            found.insert(0, self._cast.protagonist_id)
        return tuple(found)

    def locations_in(self, text: str) -> tuple[str, ...]:
        return tuple(i for i in self._places.find(text) if i in self._cast.locations)


_MM_STRIP = re.compile(r"[\"`<>{}\[\]()|;#]|\s+")


def mermaid_label(text: str, limit: int = 60) -> str:
    """Chữ an toàn trong nhãn Mermaid: bỏ ngoặc, dấu nháy, xuống dòng; cắt cho gọn."""
    clean = _MM_STRIP.sub(lambda m: " " if m.group(0).isspace() else "", text).strip()
    return clean if len(clean) <= limit else clean[:limit - 1].rstrip() + "…"


def _name(cast: Cast, nid: str) -> str:
    return cast.titles.get(nid, nid)


def chapter_overview(state: GraphState, cast: Cast, chapter: int) -> ChapterOverview:
    nodes = state.all_nodes()

    def text_of(nid: str) -> str:
        row = nodes.get(nid)
        field = _TEXT_FIELD.get(row.label) if row else None
        return (_text_prop(row.props, field) or "") if row and field else ""

    relations = tuple(
        RelationRow(_name(cast, e.source), _name(cast, e.target), str(e.props.get("kind") or ""),
                    e.props.get("score") if isinstance(e.props.get("score"), int) else None)
        for e in state.edges_at("RELATES_TO", chapter)
        if e.source in cast.characters and e.target in cast.characters)
    members = tuple(
        (_name(cast, e.source), _name(cast, e.target))
        for e in state.edges_at("MEMBER_OF", chapter)
        if e.source in cast.characters and e.target in cast.factions)
    where = tuple(
        (_name(cast, e.source), _name(cast, e.target))
        for e in state.edges_at("LOCATED_AT", chapter)
        if e.source in cast.characters and e.target in cast.locations)
    knowledge = tuple(
        KnowledgeRow(_name(cast, e.source), text_of(e.target), e.props.get("how"),
                     nodes[e.target].label)
        for e in state.edges_at("KNOWS", chapter, ever=True)
        if e.valid_from_chapter == chapter and e.source in cast.characters
        and e.target in nodes and nodes[e.target].label in _TEXT_FIELD and text_of(e.target))

    deaths: dict[str, list[str]] = {}
    for e in state.edges_at("DIED_IN", chapter, ever=True):
        if e.source in cast.characters:
            deaths.setdefault(e.target, []).append(_name(cast, e.source))
    events = []
    for nid, row in sorted(nodes.items()):
        if row.label != "Event" or row.props.get("chapter") != chapter:
            continue
        who = tuple(_name(cast, e.source)
                    for e in state.edges_at("PARTICIPATED_IN", chapter, ever=True, target_id=nid)
                    if e.source in cast.characters)
        events.append(EventRow(text_of(nid), who, tuple(deaths.get(nid, ()))))

    lies = []
    for nid, row in sorted(nodes.items()):
        if row.label != "Lie" or row.props.get("chapter") != chapter:
            continue
        speakers = [_name(cast, e.source)
                    for e in state.edges_at("TOLD", chapter, ever=True, target_id=nid)]
        lies.append(LieRow(speakers[0] if speakers else "", text_of(nid)))

    return ChapterOverview(chapter, relations, members, where, knowledge, tuple(events), tuple(lies),
                           _mermaid(cast, relations, members))


def _mermaid(cast: Cast, relations: tuple[RelationRow, ...],
             members: tuple[tuple[str, str], ...]) -> str:
    """Sơ đồ quan hệ ở cuối chương: nhân vật là hộp, phe là hình viên thuốc, thuộc phe là nét đứt."""
    ids: dict[str, str] = {}

    def node(name: str, shape: str) -> str:
        key = f"{shape}:{name}"
        if key not in ids:
            ids[key] = f"{shape}{len(ids) + 1}"
        return ids[key]

    lines = ["graph LR"]
    declared: list[str] = []

    def declare(name: str, shape: str) -> str:
        nid = node(name, shape)
        label = mermaid_label(name)
        decl = f'  {nid}["{label}"]' if shape == "c" else f'  {nid}(["{label}"])'
        if decl not in declared:
            declared.append(decl)
        return nid

    edges = []
    for r in relations:
        a, b = declare(r.source, "c"), declare(r.target, "c")
        tag = r.kind if r.score is None else f"{r.kind} {r.score:+d}"
        edges.append(f'  {a} -->|"{mermaid_label(tag, 30)}"| {b}')
    for who, faction in members:
        a, f = declare(who, "c"), declare(faction, "f")
        edges.append(f"  {a} -.-> {f}")
    if not declared:
        return "graph LR\n  empty[\"chưa có quan hệ nào\"]"
    return "\n".join([*lines, *declared, *edges])
