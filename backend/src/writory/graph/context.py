"""Ngữ cảnh lớp `truth` cho model viết (design §6.2 bước 1, D-28).

Model viết được thấy sự thật, kể cả bí mật, để giữ truyện nhất quán và biết điều gì
KHÔNG được để lộ. Ngữ cảnh này không bao giờ đi tới đường ra cho người chơi; đường đó dùng
`player_view` (G1).

`as_of_chapter` là chương đã commit cuối (lấy từ `writory.db.current_chapter`); ngữ cảnh mô tả
trạng thái cuối chương đó, dùng để viết chương `as_of_chapter + 1`.

Nút mang `user_authored: true` có chữ do người chơi viết; khi render, chữ đó luôn được bọc
bằng `UserAuthored` (G4).
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from neo4j import Driver, RoutingControl

from writory.graph.queries import VALID_AT
from writory.graph.schema import ENTITY
from writory.graph.story import require_chapter, require_story_id
from writory.safety.wrap import UserAuthored

SecretStatus = Literal["not_yet", "in_window", "overdue", "revealed"]


class PlanSecret(Protocol):
    fact_id: str
    reveal_from_chapter: int
    reveal_to_chapter: int


class PlanLike(Protocol):
    """Phần của `story_plan` mà ngữ cảnh cần. `pipeline.story_plan.StoryPlan` khớp giao thức này."""

    @property
    def secrets(self) -> Sequence[PlanSecret]: ...


@dataclass(frozen=True)
class CharacterInfo:
    id: str
    name: str
    aliases: tuple[str, ...]
    alive: bool
    location: str | None
    holds: tuple[str, ...]
    user_authored: bool


@dataclass(frozen=True)
class RelationInfo:
    source: str
    target: str
    kind: str
    score: int
    since_chapter: int


@dataclass(frozen=True)
class Knower:
    id: str
    name: str
    since_chapter: int
    how: str | None


@dataclass(frozen=True)
class FactInfo:
    id: str
    text: str
    known_by: tuple[Knower, ...]
    user_authored: bool


@dataclass(frozen=True)
class LieInfo:
    id: str
    content: str
    speaker_id: str
    speaker_name: str
    told_to: tuple[str, ...]  # tên người nghe
    chapter: int
    user_authored: bool


@dataclass(frozen=True)
class SecretInfo:
    fact_id: str
    text: str
    reveal_from_chapter: int
    reveal_to_chapter: int
    status: SecretStatus
    revealed_chapter: int | None


@dataclass(frozen=True)
class NeighborInfo:
    id: str
    kind: str
    text: str
    aliases: tuple[str, ...]
    hops: int
    alive: bool | None  # chỉ cho Character
    user_authored: bool


@dataclass(frozen=True)
class ThreadInfo:
    id: str
    description: str
    planted_chapter: int
    due_from_chapter: int
    due_to_chapter: int
    overdue: bool


@dataclass(frozen=True)
class WriterContext:
    story_id: str
    as_of_chapter: int
    writing_chapter: int
    present: tuple[CharacterInfo, ...]
    relations: tuple[RelationInfo, ...]
    known_facts: tuple[FactInfo, ...]
    open_lies: tuple[LieInfo, ...]
    secrets: tuple[SecretInfo, ...]
    neighbors: tuple[NeighborInfo, ...]
    open_threads: tuple[ThreadInfo, ...]


# Chữ hiện của một nút theo nhãn (lớp truth: dùng `name` thật).
_TEXT = "coalesce(n.name, n.text, n.description, n.content, n.id)"
_KIND = "[l IN labels(n) WHERE l <> 'Entity'][0]"


def _status(secret: PlanSecret, writing: int, revealed: int | None) -> SecretStatus:
    if revealed is not None:
        return "revealed"
    if writing < secret.reveal_from_chapter:
        return "not_yet"
    if writing <= secret.reveal_to_chapter:
        return "in_window"
    return "overdue"


def writer_context(
    driver: Driver,
    story_id: str,
    as_of_chapter: int,
    present_ids: Sequence[str],
    plan: PlanLike | None,
    *,
    max_neighbors: int | None = None,
) -> WriterContext:
    """`max_neighbors`: lấy từ `limits.context.writer_max_neighbors` (None = không giới hạn)."""
    require_story_id(story_id)
    require_chapter(as_of_chapter)
    present = list(dict.fromkeys(present_ids))
    params = {"story_id": story_id, "chapter": as_of_chapter, "present": present}

    def read(query: str, **extra):
        return driver.execute_query(
            query, parameters_={**params, **extra}, routing_=RoutingControl.READ
        ).records

    chars = read(f"""
        MATCH (n:{ENTITY}:Character {{story_id: $story_id}}) WHERE n.id IN $present
        OPTIONAL MATCH (n)-[r:LOCATED_AT]->(loc:{ENTITY} {{story_id: $story_id}}) WHERE {VALID_AT}
        WITH n, collect(loc) AS locs
        OPTIONAL MATCH (n)-[r:HOLDS]->(item:{ENTITY} {{story_id: $story_id}}) WHERE {VALID_AT}
        WITH n, locs, collect(item) AS items
        RETURN n.id AS id, n.name AS name, coalesce(n.aliases, []) AS aliases,
               [x IN locs | {{id: x.id, name: x.name}}] AS locs,
               [x IN items | {{id: x.id, name: x.name}}] AS items,
               coalesce(n.user_authored, false) AS ua,
               NOT EXISTS {{
                 MATCH (n)-[d:DIED_IN]->(:{ENTITY} {{story_id: $story_id}})
                 WHERE d.valid_from_chapter <= $chapter
               }} AS alive
        """)
    found = {r["id"] for r in chars}
    missing = [i for i in present if i not in found]
    if missing:
        raise LookupError(f"không có nhân vật trong truyện: {missing}")
    order = {cid: i for i, cid in enumerate(present)}
    present_info = tuple(sorted(
        (CharacterInfo(r["id"], r["name"], tuple(r["aliases"]), r["alive"],
                       r["locs"][0]["name"] if r["locs"] else None,
                       tuple(sorted(x["name"] for x in r["items"])), r["ua"]) for r in chars),
        key=lambda c: order[c.id],
    ))
    # Nút đã nằm ở phần sự thật thì không lặp lại trong phần gợi ý.
    shown = {x["id"] for r in chars for x in r["locs"] + r["items"]}

    relations = tuple(
        RelationInfo(r["s"], r["t"], r["kind"], r["score"], r["since"])
        for r in read(f"""
            MATCH (a:{ENTITY}:Character {{story_id: $story_id}})-[r:RELATES_TO]->
                  (b:{ENTITY}:Character {{story_id: $story_id}})
            WHERE a.id IN $present AND b.id IN $present AND {VALID_AT}
            RETURN a.id AS s, b.id AS t, r.kind AS kind, r.score AS score,
                   r.valid_from_chapter AS since
            ORDER BY s, t
            """)
    )

    facts = tuple(
        FactInfo(
            r["id"], r["text"],
            tuple(Knower(k["id"], k["name"], k["since"], k["how"])
                  for k in sorted(r["knowers"], key=lambda k: (k["since"], k["id"]))),
            r["ua"],
        )
        for r in read(f"""
            MATCH (p:{ENTITY}:Character {{story_id: $story_id}})-[r:KNOWS]->
                  (f:{ENTITY}:Fact {{story_id: $story_id}})
            WHERE p.id IN $present AND r.valid_from_chapter <= $chapter
            WITH DISTINCT f
            MATCH (k:{ENTITY}:Character {{story_id: $story_id}})-[r:KNOWS]->(f)
            WHERE r.valid_from_chapter <= $chapter
            RETURN f.id AS id, f.text AS text, coalesce(f.user_authored, false) AS ua,
                   collect({{id: k.id, name: k.name, since: r.valid_from_chapter, how: r.how}})
                     AS knowers
            ORDER BY id
            """)
    )

    lies = tuple(
        LieInfo(r["id"], r["content"], r["speaker_id"], r["speaker_name"],
                tuple(sorted(r["told_to"])), r["chapter"], r["ua"])
        for r in read(f"""
            MATCH (s:{ENTITY}:Character {{story_id: $story_id}})-[r:TOLD]->
                  (l:{ENTITY}:Lie {{story_id: $story_id}})-[:TOLD_TO]->
                  (h:{ENTITY}:Character {{story_id: $story_id}})
            WHERE {VALID_AT}
              AND NOT EXISTS {{
                MATCH (k:{ENTITY}:Character {{story_id: $story_id}})-[d:KNOWS]->(l)
                WHERE k <> s AND d.valid_from_chapter <= $chapter
              }}
            WITH s, l, collect(h) AS hearers
            WHERE s.id IN $present OR any(h IN hearers WHERE h.id IN $present)
            RETURN l.id AS id, l.content AS content, l.chapter AS chapter,
                   s.id AS speaker_id, s.name AS speaker_name,
                   [h IN hearers | h.name] AS told_to,
                   coalesce(l.user_authored, false) AS ua
            ORDER BY chapter, id
            """)
    )

    secrets: tuple[SecretInfo, ...] = ()
    if plan is not None and plan.secrets:
        ids = [s.fact_id for s in plan.secrets]
        rows = {
            r["id"]: r
            for r in read(f"""
                MATCH (f:{ENTITY}:Fact {{story_id: $story_id}}) WHERE f.id IN $ids
                OPTIONAL MATCH (f)-[r:REVEALED_TO_PLAYER]->(:{ENTITY}:Chapter {{story_id: $story_id}})
                WHERE r.valid_from_chapter <= $chapter
                RETURN f.id AS id, f.text AS text, min(r.valid_from_chapter) AS revealed
                """, ids=ids)
        }
        unknown = [i for i in ids if i not in rows]
        if unknown:
            raise LookupError(f"story_plan nhắc tới Fact không có trong đồ thị: {unknown}")
        secrets = tuple(
            SecretInfo(s.fact_id, rows[s.fact_id]["text"], s.reveal_from_chapter,
                       s.reveal_to_chapter,
                       _status(s, as_of_chapter + 1, rows[s.fact_id]["revealed"]),
                       rows[s.fact_id]["revealed"])
            for s in plan.secrets
        )

    shown |= {f.id for f in facts} | {lie.id for lie in lies}
    limit = "" if max_neighbors is None else "LIMIT $limit"
    neighbors = tuple(
        NeighborInfo(r["id"], r["kind"], r["text"], tuple(r["aliases"]), r["hops"],
                     r["alive"], r["ua"])
        for r in read(f"""
            MATCH (p:{ENTITY} {{story_id: $story_id}}) WHERE p.id IN $present
            MATCH path = (p)-[rels*1..2]-(n:{ENTITY} {{story_id: $story_id}})
            WHERE NOT n.id IN $present AND NOT n.id IN $shown
              AND all(r IN rels WHERE type(r) <> 'REVEALED_TO_PLAYER' AND {VALID_AT})
              AND all(x IN nodes(path) WHERE NOT x:Chapter)
            WITH n, min(length(path)) AS hops
            RETURN n.id AS id, {_KIND} AS kind, {_TEXT} AS text,
                   coalesce(n.aliases, []) AS aliases, hops,
                   coalesce(n.user_authored, false) AS ua,
                   CASE WHEN n:Character THEN NOT EXISTS {{
                     MATCH (n)-[d:DIED_IN]->(:{ENTITY} {{story_id: $story_id}})
                     WHERE d.valid_from_chapter <= $chapter
                   }} END AS alive
            ORDER BY hops, id
            {limit}
            """, limit=max_neighbors, shown=sorted(shown))
    )

    threads = tuple(
        ThreadInfo(r["id"], r["description"], r["planted"], r["due_from"], r["due_to"],
                   r["due_to"] < as_of_chapter)
        for r in read(f"""
            MATCH (t:{ENTITY}:Thread {{story_id: $story_id}})
            WHERE t.planted_chapter <= $chapter
              AND NOT EXISTS {{
                MATCH (t)-[r:RESOLVED_IN]->(:{ENTITY}:Chapter {{story_id: $story_id}})
                WHERE r.valid_from_chapter <= $chapter
              }}
            RETURN t.id AS id, t.description AS description, t.planted_chapter AS planted,
                   t.due_from_chapter AS due_from, t.due_to_chapter AS due_to
            ORDER BY due_to, id
            """)
    )

    return WriterContext(
        story_id, as_of_chapter, as_of_chapter + 1, present_info, relations, facts, lies,
        secrets, neighbors, threads,
    )


# --- render -----------------------------------------------------------------------------

_DATA_LABEL = "story_data"


class _Parts:
    """Gom chữ hệ thống thành khối str; chữ người chơi thành UserAuthored riêng (G4)."""

    def __init__(self) -> None:
        self.parts: list[str | UserAuthored] = []
        self._buf: list[str] = []

    def line(self, *pieces: str | tuple[str, bool]) -> None:
        """Mỗi mảnh là str (chữ hệ thống) hoặc (chữ, user_authored)."""
        current = ""
        for piece in pieces:
            text, ua = piece if isinstance(piece, tuple) else (piece, False)
            if ua:
                self._buf.append(current)
                current = ""
                self._flush()
                self.parts.append(UserAuthored(text, label=_DATA_LABEL))
            else:
                current += text
        self._buf.append(current)

    def _flush(self) -> None:
        text = "\n".join(self._buf).strip("\n")
        if text:
            self.parts.append(text)
        self._buf = []

    def done(self) -> list[str | UserAuthored]:
        self._flush()
        return self.parts


def _name(c: CharacterInfo | NeighborInfo) -> list[str | tuple[str, bool]]:
    pieces: list[str | tuple[str, bool]] = [(c.name if isinstance(c, CharacterInfo) else c.text,
                                            c.user_authored)]
    if c.aliases:
        pieces.append(" (" + ", ".join(c.aliases) + ")")
    return pieces


def render_writer_context(ctx: WriterContext) -> list[str | UserAuthored]:
    """Chữ cho prompt model viết, hai phần: sự thật cần tôn trọng, rồi gợi ý có thể nhắc tới
    (design §13). Trả danh sách phần để đưa vào `user_message(*parts)`; không đưa vào system."""
    out = _Parts()
    names = {c.id: c for c in ctx.present}

    out.line(f"## Sự thật cần tôn trọng (trạng thái cuối chương {ctx.as_of_chapter}, "
             f"đang viết chương {ctx.writing_chapter})")
    out.line("### Nhân vật có mặt")
    for c in ctx.present:
        state = "còn sống" if c.alive else "ĐÃ CHẾT"
        extra = f"; ở: {c.location}" if c.location else ""
        extra += f"; đang giữ: {', '.join(c.holds)}" if c.holds else "; không giữ đồ vật nào"
        out.line("- ", *_name(c), f" — {state}{extra}")

    if ctx.relations:
        out.line("### Quan hệ hiện tại giữa người có mặt")
        for r in ctx.relations:
            out.line("- ", (names[r.source].name, names[r.source].user_authored), " → ",
                     (names[r.target].name, names[r.target].user_authored),
                     f": {r.kind} ({r.score}), từ chương {r.since_chapter}")

    if ctx.known_facts:
        out.line("### Điều người có mặt biết (chỉ những người được liệt kê là biết)")
        for f in ctx.known_facts:
            who = "; ".join(
                f"{k.name} (từ chương {k.since_chapter}{', ' + k.how if k.how else ''})"
                for k in f.known_by
            )
            out.line("- ", (f.text, f.user_authored), f" — biết: {who}")

    if ctx.open_lies:
        out.line("### Lời nói dối chưa bị phát hiện (người nghe vẫn tin là thật)")
        for lie in ctx.open_lies:
            speaker = names.get(lie.speaker_id)
            out.line("- ", (lie.speaker_name, bool(speaker and speaker.user_authored)),
                     f" nói với {', '.join(lie.told_to)} (chương {lie.chapter}): ",
                     (lie.content, lie.user_authored))

    if ctx.secrets:
        out.line("### Bí mật và khoảng lộ")
        for s in ctx.secrets:
            if s.status == "revealed":
                out.line(f"- Đã lộ cho người đọc ở chương {s.revealed_chapter}: {s.text}")
            elif s.status == "not_yet":
                out.line(f"- KHÔNG để lộ: {s.text} (dự kiến lộ chương "
                         f"{s.reveal_from_chapter}–{s.reveal_to_chapter})")
            elif s.status == "in_window":
                out.line(f"- Chỉ lộ nếu cảnh dẫn tới một cách hợp lý: {s.text} "
                         f"(khoảng lộ chương {s.reveal_from_chapter}–{s.reveal_to_chapter})")
            else:
                out.line(f"- Đã quá khoảng lộ (chương {s.reveal_from_chapter}–"
                         f"{s.reveal_to_chapter}), nên tìm cách hé lộ hợp lý: {s.text}")

    dead = [n for n in ctx.neighbors if n.alive is False]
    if dead:
        out.line("### Nhân vật liên quan đã chết (không được xuất hiện hay hành động)")
        for n in dead:
            out.line("- ", *_name(n), " — đã chết")

    out.line("")
    out.line("## Gợi ý có thể nhắc tới")
    alive_neighbors = [n for n in ctx.neighbors if n.alive is not False]
    if alive_neighbors:
        out.line("### Người, vật, sự việc liên quan")
        for n in alive_neighbors:
            out.line("- ", *_name(n), f" [{n.kind}, cách {n.hops} bước]")
    if ctx.open_threads:
        out.line("### Mạch đang mở")
        for t in ctx.open_threads:
            due = f"dự kiến gỡ chương {t.due_from_chapter}–{t.due_to_chapter}"
            flag = " — QUÁ HẠN, nên gỡ" if t.overdue else ""
            out.line(f"- {t.description} (gieo ở chương {t.planted_chapter}; {due}){flag}")
    return out.done()
