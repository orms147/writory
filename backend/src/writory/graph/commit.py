"""Áp và gỡ gói thay đổi theo commit_id (D-6). Mỗi thao tác là một transaction Neo4j:
lỗi ở bất kỳ bước nào thì không còn gì được ghi.

- Nút và cạnh mới mang `commit_id`; MERGE theo khoá (story_id, id) nên áp lại cùng gói là an toàn.
- Đóng cạnh ghi `closed_by_commit`, để gỡ commit thì mở lại được.
- Nút đã tồn tại không bị sửa: thay đổi trạng thái đi qua cạnh mới hoặc đóng cạnh cũ.
"""

from dataclasses import dataclass
from itertools import groupby

from neo4j import Driver, ManagedTransaction
from neo4j.exceptions import ConstraintError

from writory.graph.package import ChangePackage, CloseSpec
from writory.graph.schema import EDGE_TYPES, ENTITY, NAMED_LABELS, NODE_LABELS
from writory.graph.story import require_story_id


class GraphWriteError(Exception):
    """Lỗi ghi đồ thị. Đã rollback, đồ thị giữ nguyên như trước."""


class MissingEntityError(GraphWriteError):
    """Gói tham chiếu id không có trong truyện (G11: chỉ tham chiếu id đã có)."""


class CommitConflictError(GraphWriteError):
    """Gói đụng dữ liệu của commit khác."""


class InvalidPackageError(GraphWriteError):
    """Gói đúng schema nhưng sai quy tắc cần biết nhãn nút (ví dụ thiếu `known_as`, D-17)."""


@dataclass(frozen=True)
class StorySnapshot:
    node_count: int
    edge_count: int
    nodes: tuple[tuple, ...]
    edges: tuple[tuple, ...]


def apply_package(driver: Driver, story_id: str, package: ChangePackage) -> None:
    require_story_id(story_id)
    try:
        with driver.session() as session:
            session.execute_write(_apply_tx, story_id, package)
    except ConstraintError as exc:
        raise CommitConflictError(f"id đã thuộc về dữ liệu khác: {exc.message}") from exc


def _apply_tx(tx: ManagedTransaction, story_id: str, pkg: ChangePackage) -> None:
    cid = pkg.commit_id
    for label, group in groupby(sorted(pkg.nodes, key=lambda n: n.label), key=lambda n: n.label):
        assert label in NODE_LABELS
        rows = [{"id": n.id, "props": {k: v for k, v in n.props.items() if v is not None}}
                for n in group]
        records = tx.run(
            f"""
            UNWIND $rows AS row
            MERGE (n:{ENTITY} {{story_id: $story_id, id: row.id}})
            ON CREATE SET n:{label}, n += row.props, n.commit_id = $commit_id
            RETURN row.id AS id, n.commit_id AS commit_id, '{label}' IN labels(n) AS label_ok
            """,
            rows=rows, story_id=story_id, commit_id=cid,
        ).data()
        clash = [r["id"] for r in records if r["commit_id"] != cid or not r["label_ok"]]
        if clash:
            raise CommitConflictError(f"nút đã có từ commit khác: {clash}")

    endpoints = sorted({e.source for e in pkg.edges} | {e.target for e in pkg.edges})
    if endpoints:
        found = {
            r["id"]: r
            for r in tx.run(
                f"""
                UNWIND $ids AS id
                MATCH (n:{ENTITY} {{story_id: $story_id, id: id}})
                RETURN id, labels(n) AS labels, coalesce(n.is_protagonist, false) AS protagonist
                """,
                ids=endpoints, story_id=story_id,
            ).data()
        }
        missing = [i for i in endpoints if i not in found]
        if missing:
            raise MissingEntityError(f"id không có trong truyện: {missing}")
        for e in pkg.edges:
            if needs_known_as(e.type, found[e.source], found[e.target]) and "known_as" not in e.props:
                raise InvalidPackageError(f"cạnh {e.id} hé lộ nút có tên nhưng thiếu `known_as`")

    for etype, group in groupby(sorted(pkg.edges, key=lambda e: e.type), key=lambda e: e.type):
        assert etype in EDGE_TYPES
        rows = [
            {"id": e.id, "source": e.source, "target": e.target,
             "vf": e.valid_from_chapter, "vt": e.valid_to_chapter,
             "props": {k: v for k, v in e.props.items() if v is not None}}
            for e in group
        ]
        records = tx.run(
            f"""
            UNWIND $rows AS row
            MATCH (a:{ENTITY} {{story_id: $story_id, id: row.source}})
            MATCH (b:{ENTITY} {{story_id: $story_id, id: row.target}})
            MERGE (a)-[r:{etype} {{story_id: $story_id, id: row.id}}]->(b)
            ON CREATE SET r += row.props, r.commit_id = $commit_id,
                          r.valid_from_chapter = row.vf, r.valid_to_chapter = row.vt
            RETURN row.id AS id, r.commit_id AS commit_id
            """,
            rows=rows, story_id=story_id, commit_id=cid,
        ).data()
        clash = [r["id"] for r in records if r["commit_id"] != cid]
        if clash:
            raise CommitConflictError(f"cạnh đã có từ commit khác: {clash}")

    for close in pkg.close:
        _close_edge(tx, story_id, cid, close)


def needs_known_as(edge_type: str, source: dict, target: dict) -> bool:
    """Cạnh làm người chơi biết một nút có tên thì phải nói người chơi biết nó dưới tên nào (D-17).
    `source`/`target`: dict có `labels` và `protagonist`."""
    if edge_type == "REVEALED_TO_PLAYER":
        return bool(NAMED_LABELS & set(source["labels"]))
    if edge_type == "KNOWS":
        return source["protagonist"] and bool(NAMED_LABELS & set(target["labels"]))
    return False


def _close_edge(tx: ManagedTransaction, story_id: str, cid: str, close: CloseSpec) -> None:
    assert close.type in EDGE_TYPES
    rec = tx.run(
        f"""
        MATCH ()-[r:{close.type} {{story_id: $story_id, id: $id}}]->()
        RETURN r.valid_from_chapter AS vf, r.valid_to_chapter AS vt,
               r.closed_by_commit AS closed_by
        """,
        story_id=story_id, id=close.id,
    ).single()
    if rec is None:
        raise MissingEntityError(f"không có cạnh {close.type} id={close.id} để đóng")
    if rec["closed_by"] == cid:
        return  # áp lại cùng gói
    if rec["vt"] is not None:
        raise CommitConflictError(f"cạnh {close.id} đã đóng ở chương {rec['vt']}")
    if close.valid_to_chapter <= rec["vf"]:
        raise CommitConflictError(
            f"cạnh {close.id} mở từ chương {rec['vf']}, không đóng ở chương {close.valid_to_chapter}"
        )
    tx.run(
        f"""
        MATCH ()-[r:{close.type} {{story_id: $story_id, id: $id}}]->()
        SET r.valid_to_chapter = $vt, r.closed_by_commit = $commit_id
        """,
        story_id=story_id, id=close.id, vt=close.valid_to_chapter, commit_id=cid,
    )


def delete_commit(driver: Driver, story_id: str, commit_id: str) -> None:
    """Gỡ một commit: xoá nút/cạnh nó tạo, mở lại cạnh nó đóng.
    Chỉ gỡ được commit mới nhất chạm tới các nút đó; có commit sau dựa vào thì báo lỗi."""
    require_story_id(story_id)
    with driver.session() as session:
        session.execute_write(_delete_commit_tx, story_id, commit_id)


def _delete_commit_tx(tx: ManagedTransaction, story_id: str, cid: str) -> None:
    # Cạnh của commit khác gắn vào nút của commit này, hoặc cạnh của commit này đã bị commit khác đóng.
    dependents = tx.run(
        f"""
        CALL () {{
          MATCH (:{ENTITY} {{story_id: $story_id, commit_id: $cid}})-[r]-()
          WHERE r.commit_id <> $cid
          RETURN r
          UNION
          MATCH (:{ENTITY} {{story_id: $story_id}})-[r]->()
          WHERE r.commit_id = $cid AND r.closed_by_commit IS NOT NULL
                AND r.closed_by_commit <> $cid
          RETURN r
        }}
        RETURN count(r) AS c
        """,
        story_id=story_id, cid=cid,
    ).single(strict=True)["c"]
    if dependents:
        raise CommitConflictError(f"commit {cid} có {dependents} cạnh của commit sau dựa vào")
    tx.run(
        f"""
        MATCH (:{ENTITY} {{story_id: $story_id}})-[r]->()
        WHERE r.closed_by_commit = $cid
        REMOVE r.valid_to_chapter, r.closed_by_commit
        """,
        story_id=story_id, cid=cid,
    )
    tx.run(
        f"""
        MATCH (:{ENTITY} {{story_id: $story_id}})-[r]->()
        WHERE r.commit_id = $cid
        DELETE r
        """,
        story_id=story_id, cid=cid,
    )
    tx.run(
        f"MATCH (n:{ENTITY} {{story_id: $story_id, commit_id: $cid}}) DETACH DELETE n",
        story_id=story_id, cid=cid,
    )


def delete_story(driver: Driver, story_id: str) -> None:
    """Xoá toàn bộ một truyện (chỉ truyện đó)."""
    require_story_id(story_id)
    driver.execute_query(
        f"MATCH (n:{ENTITY} {{story_id: $story_id}}) DETACH DELETE n",
        parameters_={"story_id": story_id},
    )


def story_snapshot(driver: Driver, story_id: str) -> StorySnapshot:
    """Toàn bộ nút và cạnh của một truyện, sắp xếp ổn định. Dùng để so trước/sau."""
    require_story_id(story_id)
    nodes = driver.execute_query(
        f"""
        MATCH (n:{ENTITY} {{story_id: $story_id}})
        RETURN n.id AS id, labels(n) AS labels, properties(n) AS props
        """,
        parameters_={"story_id": story_id},
    ).records
    edges = driver.execute_query(
        f"""
        MATCH (a:{ENTITY} {{story_id: $story_id}})-[r]->(b)
        RETURN type(r) AS type, a.id AS source, b.id AS target, properties(r) AS props
        """,
        parameters_={"story_id": story_id},
    ).records
    node_rows = tuple(sorted(
        (r["id"], tuple(sorted(r["labels"])), tuple(sorted(r["props"].items(), key=str)))
        for r in nodes
    ))
    edge_rows = tuple(sorted(
        (r["type"], r["source"], r["target"], tuple(sorted(r["props"].items(), key=str)))
        for r in edges
    ))
    return StorySnapshot(len(node_rows), len(edge_rows), node_rows, edge_rows)
