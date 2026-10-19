"""Truyện mẫu dựng tay ở data/sample-story/: đọc, kiểm, nạp vào Neo4j (mỗi chương một commit)."""

from dataclasses import dataclass
from pathlib import Path

import yaml
from neo4j import Driver

from writory.graph.commit import apply_package
from writory.graph.package import ChangePackage, quote_in_text

DEFAULT_SAMPLE_DIR = Path(__file__).resolve().parents[4] / "data" / "sample-story"


@dataclass
class SampleChapter:
    number: int
    text: str
    package: ChangePackage


@dataclass
class SampleStory:
    title: str
    protagonist: str
    chapters: list[SampleChapter]


def read_sample(path: Path | None = None) -> SampleStory:
    root = path or DEFAULT_SAMPLE_DIR
    raw = yaml.safe_load((root / "graph.yaml").read_text(encoding="utf-8"))
    chapters = [
        SampleChapter(
            number=ch["number"],
            text=(root / ch["file"]).read_text(encoding="utf-8"),
            package=ChangePackage.model_validate(
                {k: ch.get(k) or [] for k in ("nodes", "edges", "close")}
                | {"commit_id": ch["commit_id"]}
            ),
        )
        for ch in raw["chapters"]
    ]
    return SampleStory(raw["story"]["title"], raw["story"]["protagonist"], chapters)


def validate_sample(sample: SampleStory) -> list[str]:
    """Kiểm truyện mẫu không cần Neo4j. Trả danh sách lỗi (rỗng = sạch).

    - Câu trích của REVEALED_TO_PLAYER và KNOWS của nhân vật chính có nguyên văn trong chương (G3).
    - Cạnh chỉ trỏ tới nút đã khai ở chương này hoặc trước.
    - `close` chỉ trỏ tới cạnh đã có, cùng kiểu.
    """
    problems: list[str] = []
    nodes: set[str] = set()
    edges: dict[str, str] = {}
    for ch in sample.chapters:
        pkg = ch.package
        nodes |= {n.id for n in pkg.nodes}
        for e in pkg.edges:
            for end in (e.source, e.target):
                if end not in nodes:
                    problems.append(f"chương {ch.number}: cạnh {e.id} trỏ tới nút chưa khai {end}")
            needs_quote = e.type == "REVEALED_TO_PLAYER" or (
                e.type == "KNOWS" and e.source == sample.protagonist
            )
            if needs_quote:
                quote = e.props.get("quote")
                if not isinstance(quote, str) or not quote_in_text(quote, ch.text):
                    problems.append(
                        f"chương {ch.number}: cạnh {e.id} có câu trích không nằm trong chương: {quote!r}"
                    )
            if e.valid_from_chapter > ch.number:
                problems.append(f"chương {ch.number}: cạnh {e.id} bắt đầu ở chương sau")
        edges |= {e.id: e.type for e in pkg.edges}
        for c in pkg.close:
            if edges.get(c.id) != c.type:
                problems.append(f"chương {ch.number}: close {c.type} {c.id} không có cạnh tương ứng")
    return problems


def load_sample_story(driver: Driver, story_id: str, path: Path | None = None) -> SampleStory:
    """Nạp truyện mẫu vào `story_id`, áp lần lượt từng chương. Chạy lại an toàn."""
    sample = read_sample(path)
    problems = validate_sample(sample)
    if problems:
        raise ValueError("truyện mẫu không hợp lệ:\n" + "\n".join(problems))
    for ch in sample.chapters:
        apply_package(driver, story_id, ch.package)
    return sample
