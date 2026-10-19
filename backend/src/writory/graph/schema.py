"""Nhãn nút, kiểu cạnh và ràng buộc. Mô tả: docs/graph-schema.md.

Nhãn và kiểu cạnh được ghép thẳng vào chuỗi Cypher (Cypher không nhận nhãn làm tham số
trong MERGE), nên chỉ nhận giá trị trong hai danh sách cố định dưới đây.
"""

from typing import Literal, get_args

from neo4j import Driver

NodeLabel = Literal[
    "Character", "Location", "Item", "Faction", "Event", "Fact", "Lie", "Thread", "Chapter"
]
EdgeType = Literal[
    "RELATES_TO",
    "LOCATED_AT",
    "HOLDS",
    "MEMBER_OF",
    "PARTICIPATED_IN",
    "DIED_IN",
    "KNOWS",
    "FEELS",
    "TOLD",
    "TOLD_TO",
    "ABOUT",
    "RESOLVED_IN",
    "REVEALED_TO_PLAYER",
]

NODE_LABELS: tuple[str, ...] = get_args(NodeLabel)

# Nút có tên. Người chơi chỉ thấy tên qua `known_as` trên cạnh hé lộ, không bao giờ thấy `name` (D-17).
NAMED_LABELS = frozenset({"Character", "Location", "Item", "Faction"})
EDGE_TYPES: tuple[str, ...] = get_args(EdgeType)

# Nhãn chung của mọi nút: khoá (story_id, id) là duy nhất trên toàn truyện, không theo nhãn.
ENTITY = "Entity"

# Thuộc tính do lớp graph/ tự đặt; dữ liệu đầu vào không được ghi đè.
RESERVED_PROPS = frozenset(
    {"story_id", "id", "commit_id", "closed_by_commit", "valid_from_chapter", "valid_to_chapter"}
)


def schema_statements() -> list[str]:
    stmts = [
        f"CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (n:{ENTITY}) "
        + "REQUIRE (n.story_id, n.id) IS UNIQUE",
        f"CREATE INDEX entity_story IF NOT EXISTS FOR (n:{ENTITY}) ON (n.story_id)",
        f"CREATE INDEX entity_commit IF NOT EXISTS FOR (n:{ENTITY}) ON (n.story_id, n.commit_id)",
    ]
    for t in EDGE_TYPES:
        stmts.append(
            f"CREATE CONSTRAINT rel_{t.lower()}_key IF NOT EXISTS "
            f"FOR ()-[r:{t}]-() REQUIRE (r.story_id, r.id) IS UNIQUE"
        )
    return stmts


def ensure_schema(driver: Driver) -> None:
    """Tạo ràng buộc và index. Chạy lại an toàn (IF NOT EXISTS)."""
    for stmt in schema_statements():
        driver.execute_query(stmt)
