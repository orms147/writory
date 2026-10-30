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

# Nhãn hai đầu hợp lệ của từng kiểu cạnh (docs/graph-schema.md, bảng Cạnh): (nhãn nguồn, nhãn đích),
# None = nhãn nào cũng được. MỘT bảng cho khởi tạo (`pipeline/setup.py`, thu hẹp cho chương 0) và bộ
# trích (`pipeline/extract.py`), để kiểu cạnh mới không lọt lại: psab-b1 (D-128) bộ trích ghi HOLDS từ
# nhân vật tới một Fact, ngữ cảnh viết đọc tên của Fact rồi sập. Phần kiểm thật là `endpoint_problem`.
EDGE_ENDPOINTS: dict[str, tuple[frozenset[str] | None, frozenset[str] | None]] = {
    "RELATES_TO": (frozenset({"Character"}), frozenset({"Character"})),
    "LOCATED_AT": (frozenset({"Character", "Item"}), frozenset({"Location"})),
    "HOLDS": (frozenset({"Character"}), frozenset({"Item"})),
    "MEMBER_OF": (frozenset({"Character"}), frozenset({"Faction"})),
    "PARTICIPATED_IN": (frozenset({"Character"}), frozenset({"Event"})),
    "DIED_IN": (frozenset({"Character"}), frozenset({"Event"})),
    "KNOWS": (frozenset({"Character"}), frozenset({"Fact", "Lie", "Event"})),
    "FEELS": (frozenset({"Character"}), None),
    "TOLD": (frozenset({"Character"}), frozenset({"Lie"})),
    "TOLD_TO": (frozenset({"Lie"}), frozenset({"Character"})),
    "ABOUT": (frozenset({"Fact", "Event", "Lie"}), None),
    "RESOLVED_IN": (frozenset({"Thread"}), frozenset({"Chapter"})),
    "REVEALED_TO_PLAYER": (None, frozenset({"Chapter"})),
}
assert set(EDGE_ENDPOINTS) == set(EDGE_TYPES)


def endpoint_problem(etype: str, source_label: str, target_label: str) -> str | None:
    """Lý do cạnh `etype` không nối được nhãn nguồn với nhãn đích, hoặc None nếu hợp lệ. Chỉ nêu kiểu cạnh
    và nhãn, không chữ của truyện."""
    sources, targets = EDGE_ENDPOINTS[etype]
    if (sources is not None and source_label not in sources) or (
            targets is not None and target_label not in targets):
        def side(labels: frozenset[str] | None) -> str:
            return "nhãn nào cũng được" if labels is None else " hoặc ".join(sorted(labels))
        return (f"{etype} nối {source_label} → {target_label}, bảng chỉ cho {side(sources)} → "
                f"{side(targets)}")
    return None


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
