"""Lớp người chơi biết (`player_view`). Định nghĩa DUY NHẤT; mọi đường ra cho người chơi
(sổ tay, hỏi người kể, tạo lựa chọn) phải lấy dữ liệu từ đây (G1).

Ở chương N, người chơi biết (góc nhìn chỉ nhân vật chính, design §7.1):
1. nút có cạnh REVEALED_TO_PLAYER tới một chương ≤ N (kèm câu trích, G3);
2. nút mà nhân vật chính KNOWS từ chương ≤ N;
3. lời nói dối do chính nhân vật chính nói (người chơi đã chọn nói).

Chỉ trả các trường trong danh sách trắng dưới đây. Không trả cạnh, quan hệ, vai trong sự kiện,
người giữ đồ vật, hay thuộc tính nào khác của lớp sự thật.

Nút có tên (Character/Location/Item/Faction) KHÔNG hiện `name` hay `aliases` của lớp sự thật:
chữ hiện là `known_as` trên cạnh hé lộ mới nhất tới chương N, biệt danh là các `known_as` còn lại (D-17).

Định nghĩa nằm trong MỘT hàm thuần, `build_player_view`, nhận bản ghi thô. `player_view` gom bản
ghi từ Neo4j; `writory.guard.state.player_view_of` gom từ GraphState (nền đã commit + gói chưa
ghi). Test so hai đường: tests/graph/test_guard_state_parity.py.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from neo4j import Driver, RoutingControl

from writory.graph.schema import ENTITY, NAMED_LABELS
from writory.graph.story import require_chapter, require_story_id

# Nhãn được phép hiện. Nút có tên lấy chữ từ `known_as`; các nhãn dưới đây lấy từ thuộc tính nút.
_TEXT_FIELD = {"Fact": "text", "Event": "description", "Lie": "content"}
_SHOWN = NAMED_LABELS | _TEXT_FIELD.keys()


@dataclass(frozen=True)
class PlayerEntry:
    id: str
    kind: str
    text: str
    aliases: tuple[str, ...]
    since_chapter: int
    quote: str | None
    about: tuple[str, ...]  # id các mục khác trong cùng player_view mà mục này nói về
    # Mọi câu trích đã hé lộ mục này, theo thứ tự chương. Đều là chữ đã có trên trang; bộ dò lộ
    # (G2, D-26) dùng để biết người chơi đã thấy gì. Giao diện chỉ cần `quote` (câu đầu tiên).
    quotes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlayerLie:
    id: str
    content: str
    chapter: int
    told_to: tuple[str, ...]  # tên người chơi biết của người nghe (known_as), hoặc UNKNOWN_HEARER


@dataclass(frozen=True)
class PlayerView:
    story_id: str
    chapter: int
    entries: tuple[PlayerEntry, ...]
    lies: tuple[PlayerLie, ...]


@dataclass(frozen=True)
class KnownRecord:
    """Một cạnh làm người chơi biết một nút: REVEALED_TO_PLAYER, hoặc KNOWS của nhân vật chính."""

    node_id: str
    labels: tuple[str, ...]
    props: dict  # thuộc tính của nút (chỉ đọc trường chữ theo _TEXT_FIELD)
    edge_id: str
    since: int
    quote: str | None
    known_as: str | None


# Tên hiện cho người nghe mà người chơi chưa biết tên: chuỗi cố định, không chứa dữ liệu truth (D-17).
UNKNOWN_HEARER = "(người chưa rõ tên)"


@dataclass(frozen=True)
class LieRecord:
    id: str
    content: str
    chapter: int
    told_to: tuple[str, ...]  # id người nghe; build_player_view đổi ra tên người chơi biết


def build_player_view(
    story_id: str,
    chapter: int,
    known: Iterable[KnownRecord],
    about_edges: Iterable[tuple[str, str]],
    lies: Iterable[LieRecord],
) -> PlayerView:
    """Định nghĩa duy nhất của player_view (G1, D-16, D-17). Đầu vào đã lọc tới chương N:
    `known` và `about_edges` là cạnh có valid_from_chapter <= N; `lies` là lời nói dối của nhân
    vật chính."""
    # Một nút có thể được biết qua nhiều đường và nhiều lần (ví dụ biệt danh trước, tên thật sau).
    seen: dict[str, list[KnownRecord]] = {}
    kinds: dict[str, str] = {}
    for rec in known:
        kind = next((lb for lb in rec.labels if lb in _SHOWN), None)
        if kind is None:
            continue
        kinds[rec.node_id] = kind
        seen.setdefault(rec.node_id, []).append(rec)

    shown: dict[str, tuple] = {}
    for nid, recs in seen.items():
        recs.sort(key=lambda r: (r.since, r.edge_id))
        kind = kinds[nid]
        if kind in NAMED_LABELS:
            names = list(dict.fromkeys(r.known_as for r in recs if r.known_as))
            if not names:
                continue  # không biết người chơi gọi nó là gì: không hiện, thay vì lộ tên thật
            text, aliases = names[-1], tuple(names[:-1])
        else:
            text, aliases = recs[0].props.get(_TEXT_FIELD[kind], ""), ()
        quotes = tuple(dict.fromkeys(r.quote for r in recs if r.quote))
        shown[nid] = (kind, text, aliases, recs[0].since, recs[0].quote, quotes)

    about: dict[str, set[str]] = {}
    for x, y in about_edges:
        if x in shown and y in shown:
            about.setdefault(x, set()).add(y)

    entries = tuple(
        PlayerEntry(
            id=nid,
            kind=kind,
            text=text,
            aliases=aliases,
            since_chapter=since,
            quote=quote,
            about=tuple(sorted(about.get(nid, ()))),
            quotes=quotes,
        )
        for nid, (kind, text, aliases, since, quote, quotes) in sorted(
            shown.items(), key=lambda kv: (kv[1][3], kv[0])
        )
    )
    # Người nghe hiện bằng tên người chơi biết trong chính view này, không bao giờ bằng `name`
    # (D-17). Chưa biết thì hiện UNKNOWN_HEARER; vẫn giữ lời nói dối vì người chơi đã chọn nói nó.
    def hearer(cid: str) -> str:
        return shown[cid][1] if cid in shown and shown[cid][0] == "Character" else UNKNOWN_HEARER

    lie_rows = tuple(
        PlayerLie(r.id, r.content, r.chapter, tuple(sorted(hearer(h) for h in r.told_to)))
        for r in sorted(lies, key=lambda r: (r.chapter, r.id))
    )
    return PlayerView(story_id, chapter, entries, lie_rows)


_KNOWN_QUERY = f"""
MATCH (x:{ENTITY} {{story_id: $story_id}})-[r:REVEALED_TO_PLAYER]->(:{ENTITY}:Chapter {{story_id: $story_id}})
WHERE r.valid_from_chapter <= $chapter
RETURN x AS x, r.id AS edge_id, r.valid_from_chapter AS since, r.quote AS quote,
       r.known_as AS known_as
UNION ALL
MATCH (:{ENTITY}:Character {{story_id: $story_id, is_protagonist: true}})-[r:KNOWS]->
      (x:{ENTITY} {{story_id: $story_id}})
WHERE r.valid_from_chapter <= $chapter
RETURN x AS x, r.id AS edge_id, r.valid_from_chapter AS since, r.quote AS quote,
       r.known_as AS known_as
"""

_ABOUT_QUERY = f"""
MATCH (x:{ENTITY} {{story_id: $story_id}})-[r:ABOUT]->(y:{ENTITY} {{story_id: $story_id}})
WHERE x.id IN $ids AND y.id IN $ids AND r.valid_from_chapter <= $chapter
RETURN x.id AS source, y.id AS target
"""

_LIES_QUERY = f"""
MATCH (:{ENTITY}:Character {{story_id: $story_id, is_protagonist: true}})-[r:TOLD]->
      (l:{ENTITY}:Lie {{story_id: $story_id}})-[:TOLD_TO]->(h:{ENTITY}:Character {{story_id: $story_id}})
WHERE r.valid_from_chapter <= $chapter
RETURN l.id AS id, l.content AS content, l.chapter AS chapter, collect(h.id) AS told_to
"""


def player_view(driver: Driver, story_id: str, chapter: int) -> PlayerView:
    """player_view đọc từ Neo4j: gom bản ghi rồi gọi build_player_view."""
    require_story_id(story_id)
    require_chapter(chapter)
    params = {"story_id": story_id, "chapter": chapter}

    def read(query: str, **extra):
        return driver.execute_query(
            query, parameters_={**params, **extra}, routing_=RoutingControl.READ
        ).records

    known = [
        KnownRecord(
            node_id=r["x"]["id"], labels=tuple(r["x"].labels), props=dict(r["x"]),
            edge_id=r["edge_id"], since=r["since"], quote=r["quote"], known_as=r["known_as"],
        )
        for r in read(_KNOWN_QUERY)
    ]
    ids = sorted({k.node_id for k in known})
    about_edges = [(r["source"], r["target"]) for r in read(_ABOUT_QUERY, ids=ids)]
    lies = [
        LieRecord(r["id"], r["content"], r["chapter"], tuple(r["told_to"]))
        for r in read(_LIES_QUERY)
    ]
    return build_player_view(story_id, chapter, known, about_edges, lies)


def player_knowledge_about(
    driver: Driver, story_id: str, entity_id: str, chapter: int
) -> list[PlayerEntry]:
    """§7.3: Người chơi đã được biết điều gì về X. Lọc trên player_view, không truy vấn riêng."""
    view = player_view(driver, story_id, chapter)
    return [e for e in view.entries if e.id == entity_id or entity_id in e.about]
