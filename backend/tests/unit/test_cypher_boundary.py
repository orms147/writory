"""G10: mọi Cypher đi qua lớp `graph/` (D-106). Quét mã nguồn ngoài `graph/` tìm dấu hiệu Cypher
hay lời gọi chạy truy vấn của driver neo4j.

Chọn mẫu để ít báo oan:
- Mệnh đề Cypher kèm dấu ngoặc của mẫu nút: `MATCH (`, `MERGE (`, `CREATE (`, và `DETACH DELETE`.
  SQL của `db/` viết `CREATE TABLE`, `INSERT INTO`, `DELETE FROM`, không có ngoặc ngay sau từ khoá.
- Mẫu cạnh có kiểu viết hoa: `)-[r:KNOWS]`, `)<-[:TOLD`. Regex của `quality/` có `)-[ \\t]`, không
  có `\\w*:` theo sau nên không trúng.
- Lời gọi chạy truy vấn của driver: `.session(`, `.execute_query(`, `.execute_read(`,
  `.execute_write(`, `.begin_transaction(`, và `.run(` trên `tx`/`session`. Không cấm `.run(` nói
  chung vì `asyncio.run`, `subprocess.run`, `runner.run` có ở nhiều nơi.
- Không cấm `from neo4j import ...`: kiểu `Driver`, lớp lỗi và `GraphDatabase.driver(...)` (tạo
  kết nối ở `api/app.py` và lệnh đo) không chạy Cypher.

Ngoại lệ: không có. Thêm ngoại lệ thì ghi đường dẫn, lý do và quyết định ở `ALLOWED`.
"""

import re
from pathlib import Path

import writory

SRC = Path(writory.__file__).parent

PATTERNS = {
    "mệnh đề MATCH": re.compile(r"\b(?:OPTIONAL\s+)?MATCH\s*\("),
    "mệnh đề MERGE": re.compile(r"\bMERGE\s*\("),
    "mệnh đề CREATE": re.compile(r"\bCREATE\s*\("),
    "DETACH DELETE": re.compile(r"\bDETACH\s+DELETE\b"),
    "mẫu cạnh": re.compile(r"\)<?-\[\w*:[A-Z_]"),
    "driver.session": re.compile(r"\.session\("),
    "execute_query": re.compile(r"\.execute_(?:query|read|write)\("),
    "begin_transaction": re.compile(r"\.begin_transaction\("),
    "tx.run": re.compile(r"\b(?:tx|session)\.run\("),
}

# (đường dẫn tương đối với writory/, tên mẫu) → lý do (D-106). Giữ tối thiểu.
ALLOWED: dict[tuple[str, str], str] = {}


def _hits(text: str) -> list[str]:
    return [name for name, rx in PATTERNS.items() if rx.search(text)]


def test_no_cypher_outside_graph_layer():
    found = []
    for path in sorted(SRC.rglob("*.py")):
        rel = path.relative_to(SRC).as_posix()
        if rel.startswith("graph/"):
            continue
        for name in _hits(path.read_text(encoding="utf-8")):
            if (rel, name) not in ALLOWED:
                found.append(f"{rel}: {name}")
    assert found == [], "Cypher hay lời gọi driver ngoài graph/ (G10):\n" + "\n".join(found)


def test_scan_reaches_the_whole_package():
    """Đối chứng: quét thấy các module ngoài graph/, và mẫu bắt được Cypher thật của graph/."""
    outside = {p.relative_to(SRC).parts[0] for p in SRC.rglob("*.py")} - {"graph"}
    assert {"api", "db", "pipeline", "guard", "safety"} <= outside
    graph_hits = {name for p in (SRC / "graph").rglob("*.py")
                  for name in _hits(p.read_text(encoding="utf-8"))}
    assert {"mệnh đề MATCH", "mệnh đề MERGE", "mẫu cạnh", "tx.run",
            "execute_query", "driver.session"} <= graph_hits


def test_patterns_do_not_flag_sql_or_ordinary_run_calls():
    benign = [
        "CREATE TABLE IF NOT EXISTS stories (id text)",
        "DELETE FROM stories WHERE id = %s",
        "INSERT INTO chapters (story_id) VALUES (%s)",
        "asyncio.run(main())", "subprocess.run(['git'])", "await runner.run(questions)",
        r're.compile(r"(?m)^([ \t]*)-[ \t]*(?=\S)")',
        "from neo4j import Driver, GraphDatabase",
        "driver = GraphDatabase.driver(uri, auth=auth)",
    ]
    for line in benign:
        assert _hits(line) == [], line


def test_patterns_flag_cypher_and_driver_calls():
    bad = {
        "MATCH (n:Entity {story_id: $story_id})": "mệnh đề MATCH",
        "OPTIONAL MATCH (a)-[:KNOWS]->(b)": "mệnh đề MATCH",
        "MERGE (n:Entity {id: $id})": "mệnh đề MERGE",
        "CREATE (n:Fact)": "mệnh đề CREATE",
        "MATCH (n) DETACH DELETE n": "DETACH DELETE",
        "(a)-[r:REVEALED_TO_PLAYER]->(c)": "mẫu cạnh",
        "with driver.session() as s:": "driver.session",
        "driver.execute_query(q)": "execute_query",
        "tx.run(q, story_id=sid)": "tx.run",
    }
    for text, name in bad.items():
        assert name in _hits(text), text
