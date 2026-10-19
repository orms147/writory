"""Truy vấn lớp sự thật (`truth`) theo chương. Chỉ cho AI viết truyện và người canh dùng;
mọi đường ra cho người chơi đi qua `player_view` (G1).

"Ở chương N" nghĩa là trạng thái ở cuối chương N: cạnh có hiệu lực khi
valid_from_chapter <= N và (valid_to_chapter rỗng hoặc > N).
"""

import unicodedata
from dataclasses import dataclass

from neo4j import Driver, RoutingControl

from writory.graph.schema import EDGE_TYPES, ENTITY, RESERVED_PROPS
from writory.graph.story import require_chapter, require_story_id

# Điều kiện "cạnh r còn hiệu lực ở chương $chapter", dùng chung cho mọi truy vấn.
VALID_AT = "r.valid_from_chapter <= $chapter AND (r.valid_to_chapter IS NULL OR r.valid_to_chapter > $chapter)"


class GraphIntegrityError(Exception):
    """Đồ thị vi phạm bất biến (ví dụ một đồ vật có hai người giữ cùng lúc). Là lỗi ghi, không phải lỗi đọc."""


def _at_most_one(rows, what: str):
    if len(rows) > 1:
        raise GraphIntegrityError(f"{what}: {len(rows)} cạnh cùng hiệu lực, cần tối đa 1")
    return rows[0] if rows else None


@dataclass(frozen=True)
class EntityRef:
    id: str
    name: str


@dataclass(frozen=True)
class Knowledge:
    since_chapter: int
    how: str | None


@dataclass(frozen=True)
class LieInfo:
    id: str
    content: str
    chapter: int
    told_to: tuple[str, ...]


@dataclass(frozen=True)
class ThreadInfo:
    id: str
    description: str
    planted_chapter: int
    due_to_chapter: int


@dataclass(frozen=True)
class Relation:
    kind: str
    score: int
    since_chapter: int


@dataclass(frozen=True)
class EdgeRow:
    id: str
    type: str
    source: str
    target: str
    valid_from_chapter: int
    valid_to_chapter: int | None
    props: dict


def _read(driver: Driver, query: str, story_id: str, chapter: int | None = None, **params):
    require_story_id(story_id)
    if chapter is not None:
        require_chapter(chapter)
    return driver.execute_query(
        query,
        parameters_={"story_id": story_id, "chapter": chapter, **params},
        routing_=RoutingControl.READ,
    ).records


def item_holder(driver: Driver, story_id: str, item_id: str, chapter: int) -> EntityRef | None:
    """§7.3: Ai đang giữ đồ vật ở chương N."""
    rows = _read(
        driver,
        f"""
        MATCH (c:{ENTITY}:Character {{story_id: $story_id}})-[r:HOLDS]->
              (:{ENTITY}:Item {{story_id: $story_id, id: $item_id}})
        WHERE {VALID_AT}
        RETURN c.id AS id, c.name AS name
        """,
        story_id, chapter, item_id=item_id,
    )
    row = _at_most_one(rows, f"người giữ {item_id} ở chương {chapter}")
    return EntityRef(row["id"], row["name"]) if row else None


def knows(
    driver: Driver, story_id: str, character_id: str, target_id: str, chapter: int
) -> Knowledge | None:
    """§7.3: Nhân vật có biết sự thật/lời nói dối/sự kiện không, từ chương nào, bằng cách nào."""
    rows = _read(
        driver,
        f"""
        MATCH (:{ENTITY}:Character {{story_id: $story_id, id: $character_id}})-[r:KNOWS]->
              (:{ENTITY} {{story_id: $story_id, id: $target_id}})
        WHERE {VALID_AT}
        RETURN r.valid_from_chapter AS since, r.how AS how
        ORDER BY since LIMIT 1
        """,
        story_id, chapter, character_id=character_id, target_id=target_id,
    )
    return Knowledge(rows[0]["since"], rows[0]["how"]) if rows else None


def undiscovered_lies(
    driver: Driver, story_id: str, speaker_id: str, chapter: int
) -> list[LieInfo]:
    """§7.3: Lời nói dối của một nhân vật chưa bị ai khác phát hiện ở chương N, đã nói với ai.
    "Bị phát hiện" = có nhân vật khác người nói KNOWS nút Lie."""
    rows = _read(
        driver,
        f"""
        MATCH (s:{ENTITY}:Character {{story_id: $story_id, id: $speaker_id}})-[r:TOLD]->
              (l:{ENTITY}:Lie {{story_id: $story_id}})-[:TOLD_TO]->
              (h:{ENTITY}:Character {{story_id: $story_id}})
        WHERE {VALID_AT}
          AND NOT EXISTS {{
            MATCH (k:{ENTITY}:Character {{story_id: $story_id}})-[d:KNOWS]->(l)
            WHERE k <> s AND d.valid_from_chapter <= $chapter
          }}
        RETURN l.id AS id, l.content AS content, l.chapter AS chapter, collect(h.id) AS told_to
        ORDER BY chapter, id
        """,
        story_id, chapter, speaker_id=speaker_id,
    )
    return [LieInfo(r["id"], r["content"], r["chapter"], tuple(sorted(r["told_to"]))) for r in rows]


def overdue_threads(driver: Driver, story_id: str, chapter: int) -> list[ThreadInfo]:
    """§7.3: Mạch đang mở ở chương N và đã quá khoảng chương dự kiến gỡ."""
    rows = _read(
        driver,
        f"""
        MATCH (t:{ENTITY}:Thread {{story_id: $story_id}})
        WHERE t.planted_chapter <= $chapter AND t.due_to_chapter < $chapter
          AND NOT EXISTS {{
            MATCH (t)-[r:RESOLVED_IN]->(:{ENTITY}:Chapter {{story_id: $story_id}})
            WHERE r.valid_from_chapter <= $chapter
          }}
        RETURN t.id AS id, t.description AS description,
               t.planted_chapter AS planted, t.due_to_chapter AS due_to
        ORDER BY due_to, id
        """,
        story_id, chapter,
    )
    return [ThreadInfo(r["id"], r["description"], r["planted"], r["due_to"]) for r in rows]


def relationship(
    driver: Driver, story_id: str, from_id: str, to_id: str, chapter: int
) -> Relation | None:
    """B là gì của A ở chương N (cạnh RELATES_TO có hướng A → B)."""
    rows = _read(
        driver,
        f"""
        MATCH (:{ENTITY}:Character {{story_id: $story_id, id: $from_id}})-[r:RELATES_TO]->
              (:{ENTITY}:Character {{story_id: $story_id, id: $to_id}})
        WHERE {VALID_AT}
        RETURN r.kind AS kind, r.score AS score, r.valid_from_chapter AS since
        """,
        story_id, chapter, from_id=from_id, to_id=to_id,
    )
    row = _at_most_one(rows, f"quan hệ {from_id}→{to_id} ở chương {chapter}")
    return Relation(row["kind"], row["score"], row["since"]) if row else None


def is_alive(driver: Driver, story_id: str, character_id: str, chapter: int) -> bool:
    rows = _read(
        driver,
        f"""
        MATCH (c:{ENTITY}:Character {{story_id: $story_id, id: $character_id}})
        RETURN NOT EXISTS {{
          MATCH (c)-[r:DIED_IN]->(:{ENTITY}:Event {{story_id: $story_id}})
          WHERE r.valid_from_chapter <= $chapter
        }} AS alive
        """,
        story_id, chapter, character_id=character_id,
    )
    if not rows:
        raise LookupError(f"không có nhân vật {character_id}")
    return rows[0]["alive"]


def _norm_name(s: str) -> str:
    return " ".join(unicodedata.normalize("NFC", s).casefold().split())


def find_characters(driver: Driver, story_id: str, name: str) -> list[EntityRef]:
    """Tìm nhân vật theo tên đầy đủ hoặc biệt danh, khớp nguyên cụm (không khớp một phần như họ)."""
    rows = _read(
        driver,
        f"""
        MATCH (c:{ENTITY}:Character {{story_id: $story_id}})
        RETURN c.id AS id, c.name AS name, coalesce(c.aliases, []) AS aliases
        """,
        story_id,
    )
    want = _norm_name(name)
    return [
        EntityRef(r["id"], r["name"])
        for r in rows
        if want in {_norm_name(n) for n in [r["name"], *r["aliases"]]}
    ]


def protagonist_id(driver: Driver, story_id: str) -> str:
    rows = _read(
        driver,
        f"MATCH (c:{ENTITY}:Character {{story_id: $story_id, is_protagonist: true}}) RETURN c.id AS id",
        story_id,
    )
    if len(rows) != 1:
        raise LookupError(f"truyện {story_id} có {len(rows)} nhân vật chính, cần đúng 1")
    return rows[0]["id"]


def edges_at(
    driver: Driver,
    story_id: str,
    edge_type: str,
    chapter: int,
    *,
    source_id: str | None = None,
    target_id: str | None = None,
) -> list[EdgeRow]:
    """Cạnh một kiểu còn hiệu lực ở chương N, kèm id. Cho người canh kiểm trước khi ghi.
    `props` chỉ gồm thuộc tính của truyện, không gồm thuộc tính do lớp graph/ đặt."""
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"kiểu cạnh không hợp lệ: {edge_type!r}")
    rows = _read(
        driver,
        f"""
        MATCH (a:{ENTITY} {{story_id: $story_id}})-[r:{edge_type}]->(b:{ENTITY} {{story_id: $story_id}})
        WHERE r.story_id = $story_id AND {VALID_AT}
          AND ($source_id IS NULL OR a.id = $source_id)
          AND ($target_id IS NULL OR b.id = $target_id)
        RETURN r.id AS id, a.id AS source, b.id AS target, r.valid_from_chapter AS vf,
               r.valid_to_chapter AS vt, properties(r) AS props
        ORDER BY id
        """,
        story_id, chapter, source_id=source_id, target_id=target_id,
    )
    return [
        EdgeRow(
            r["id"], edge_type, r["source"], r["target"], r["vf"], r["vt"],
            {k: v for k, v in r["props"].items() if k not in RESERVED_PROPS},
        )
        for r in rows
    ]


def node_labels(driver: Driver, story_id: str, ids: list[str]) -> dict[str, str]:
    """Nhãn loại (không tính nhãn chung Entity) của các nút có trong truyện; id không có thì bỏ."""
    rows = _read(
        driver,
        f"""
        UNWIND $ids AS id
        MATCH (n:{ENTITY} {{story_id: $story_id, id: id}})
        RETURN id, [l IN labels(n) WHERE l <> '{ENTITY}'][0] AS label
        """,
        story_id, ids=list(ids),
    )
    return {r["id"]: r["label"] for r in rows}
