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
"""

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


@dataclass(frozen=True)
class PlayerLie:
    id: str
    content: str
    chapter: int
    told_to: tuple[str, ...]  # tên người nghe


@dataclass(frozen=True)
class PlayerView:
    story_id: str
    chapter: int
    entries: tuple[PlayerEntry, ...]
    lies: tuple[PlayerLie, ...]


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
RETURN x.id AS id, collect(y.id) AS about
"""

_LIES_QUERY = f"""
MATCH (:{ENTITY}:Character {{story_id: $story_id, is_protagonist: true}})-[r:TOLD]->
      (l:{ENTITY}:Lie {{story_id: $story_id}})-[:TOLD_TO]->(h:{ENTITY}:Character {{story_id: $story_id}})
WHERE r.valid_from_chapter <= $chapter
RETURN l.id AS id, l.content AS content, l.chapter AS chapter, collect(h.name) AS told_to
ORDER BY chapter, id
"""


def player_view(driver: Driver, story_id: str, chapter: int) -> PlayerView:
    require_story_id(story_id)
    require_chapter(chapter)
    params = {"story_id": story_id, "chapter": chapter}

    def read(query: str, **extra):
        return driver.execute_query(
            query, parameters_={**params, **extra}, routing_=RoutingControl.READ
        ).records

    # Một nút có thể được biết qua nhiều đường và nhiều lần (ví dụ biệt danh trước, tên thật sau).
    seen: dict[str, list] = {}
    kinds: dict[str, str] = {}
    for rec in read(_KNOWN_QUERY):
        node = rec["x"]
        kind = next((lb for lb in node.labels if lb in _SHOWN), None)
        if kind is None:
            continue
        kinds[node["id"]] = kind
        seen.setdefault(node["id"], []).append(rec)

    shown: dict[str, tuple[str, str, tuple[str, ...], int, str | None]] = {}
    for nid, recs in seen.items():
        recs.sort(key=lambda r: (r["since"], r["edge_id"]))
        kind = kinds[nid]
        if kind in NAMED_LABELS:
            names = list(dict.fromkeys(r["known_as"] for r in recs if r["known_as"]))
            if not names:
                continue  # không biết người chơi gọi nó là gì: không hiện, thay vì lộ tên thật
            text, aliases = names[-1], tuple(names[:-1])
        else:
            text, aliases = recs[0]["x"].get(_TEXT_FIELD[kind], ""), ()
        shown[nid] = (kind, text, aliases, recs[0]["since"], recs[0]["quote"])

    about = {r["id"]: tuple(sorted(r["about"])) for r in read(_ABOUT_QUERY, ids=list(shown))}

    entries = tuple(
        PlayerEntry(
            id=nid,
            kind=kind,
            text=text,
            aliases=aliases,
            since_chapter=since,
            quote=quote,
            about=about.get(nid, ()),
        )
        for nid, (kind, text, aliases, since, quote) in sorted(
            shown.items(), key=lambda kv: (kv[1][3], kv[0])
        )
    )
    lies = tuple(
        PlayerLie(r["id"], r["content"], r["chapter"], tuple(sorted(r["told_to"])))
        for r in read(_LIES_QUERY)
    )
    return PlayerView(story_id, chapter, entries, lies)


def player_knowledge_about(
    driver: Driver, story_id: str, entity_id: str, chapter: int
) -> list[PlayerEntry]:
    """§7.3: Người chơi đã được biết điều gì về X. Lọc trên player_view, không truy vấn riêng."""
    view = player_view(driver, story_id, chapter)
    return [e for e in view.entries if e.id == entity_id or entity_id in e.about]
