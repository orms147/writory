"""Dữ liệu và bộ chấm của bài đo A (bộ nhớ; docs/eval.md "Bài A"; D-72, D-83).

- Đề khai trước ở evals/scenarios/memory/ (`questions*.yaml`, `run.yaml` dùng chung). Trường `story`
  của file đề chọn truyện: `sample-story` (truyện mẫu dựng tay, data/sample-story/) hoặc `run`
  (truyện do pipeline viết: thư mục kết quả `run_dir` của `pipeline.bench_run`, khoá theo
  `run_sha256`; D-83).
- Truyện mẫu: đáp án gốc kiểm lại từ đồ thị dựng tay: mỗi câu có `derive` tính lại đáp án từ
  `data/sample-story/graph.yaml` tại chương `as_of`; lệch là lỗi đề (`check_question`).
- Truyện do pipeline viết: đồ thị do bộ trích dựng, không phải đáp án. Đáp án gốc lấy từ trang; mỗi
  câu khai `graph_agrees` và code kiểm cờ đó với đồ thị (có `derive` thì derive == gold khi true,
  != gold khi false).
- Mỗi câu có `evidence`: câu trích nguyên văn từ chương <= ask_chapter, nên câu hỏi luôn trả lời
  được từ trang.
- Chấm bằng code, không dùng giám khảo LLM (D-72): tập thực thể, có/không, chọn một, nhóm từ khoá.
  Câu trả lời "không biết" tính riêng (kiêng cữ), không tính là đúng.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator

from writory.config import REPO_ROOT, ConfigError
from writory.graph import ChangePackage
from writory.graph.sample import DEFAULT_SAMPLE_DIR, read_sample
from writory.guard.state import EmptyState, GraphState, OverlayState
from writory.pipeline.bench_a_systems import (
    OPTIONAL_SYSTEMS,
    SYSTEMS,
    AliasIndex,
    contains_phrase,
    edge_key,
    flat,
)
from writory.pipeline.bench_e_story import (  # noqa: F401 — tên cũ vẫn dùng được từ đây
    CHOICES_HEADING,
    run_chapter_text,
    run_packages,
)
from writory.pipeline.bench_run import Price
from writory.quality.bench_d import _parse_yaml

DATA_DIR = REPO_ROOT / "evals" / "scenarios" / "memory"
GROUPS: tuple[str, ...] = ("item", "alive", "knows", "relation", "lie")
GROUP_LABEL = {
    "item": "đồ vật", "alive": "sống / chết", "knows": "ai biết gì",
    "relation": "quan hệ hiện tại", "lie": "lời nói dối",
}
# Khoảng cách = ask_chapter - fact_chapter, gom thành ba nhóm.
DISTANCE_BINS: tuple[str, ...] = ("0", "1-2", "3+")


def distance_bin(distance: int) -> str:
    return "0" if distance == 0 else "1-2" if distance <= 2 else "3+"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AnswerSpec(_Strict):
    type: Literal["entities", "bool", "choice", "text"]
    gold: Any
    options: tuple[str, ...] = ()
    aliases: Mapping[str, tuple[str, ...]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _shape(self) -> Self:
        gold = self.gold
        if self.type == "entities":
            if not (isinstance(gold, list) and gold and all(isinstance(g, str) for g in gold)):
                raise ValueError("entities: gold là danh sách id, không rỗng")
        elif self.type == "bool":
            if not isinstance(gold, bool):
                raise ValueError("bool: gold là true/false")
        elif self.type == "choice":
            if len(self.options) < 2 or gold not in self.options:
                raise ValueError("choice: cần >= 2 options và gold nằm trong options")
        elif not (isinstance(gold, list) and gold and all(
                isinstance(g, list) and g and all(isinstance(a, str) for a in g) for g in gold)):
            raise ValueError("text: gold là danh sách nhóm từ khoá, mỗi nhóm không rỗng")
        return self


class Evidence(_Strict):
    chapter: PositiveInt
    quote: str = Field(min_length=3)


class Question(_Strict):
    id: str = Field(pattern=r"^[a-z]+-\d{2}$")
    group: Literal["item", "alive", "knows", "relation", "lie"]
    fact_chapter: int = Field(ge=1)
    ask_chapter: int = Field(ge=1)
    as_of: int | None = Field(default=None, ge=1)
    inference: bool = False  # nối hai chi tiết trên trang; báo điểm tách riêng (D-72)
    # Đồ thị có cho đúng đáp án của trang không (D-83). Truyện mẫu: luôn true (đồ thị dựng tay là
    # đáp án). Truyện do pipeline viết: khai từng câu; `check_question` kiểm với đồ thị.
    graph_agrees: bool = True
    question: str = Field(min_length=5)
    answer: AnswerSpec
    derive: Mapping[str, Any] | None = None  # bỏ trống chỉ khi graph_agrees false: đồ thị không có gì để tính
    evidence: tuple[Evidence, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _shape(self) -> Self:
        if self.fact_chapter > self.ask_chapter:
            raise ValueError("fact_chapter không được sau ask_chapter")
        if self.as_of is not None and self.as_of > self.ask_chapter:
            raise ValueError("as_of không được sau ask_chapter (hệ trả lời chưa đọc tới đó)")
        if not self.id.startswith({"item": "item", "alive": "alive", "knows": "knows",
                                   "relation": "rel", "lie": "lie"}[self.group] + "-"):
            raise ValueError(f"id {self.id} không khớp nhóm {self.group}")
        if self.derive is None:
            if self.graph_agrees:
                raise ValueError("thiếu derive: graph_agrees true cần derive để kiểm với đồ thị")
        elif "op" not in self.derive:
            raise ValueError("derive thiếu op")
        return self

    @property
    def state_chapter(self) -> int:
        return self.as_of or self.ask_chapter

    @property
    def distance(self) -> int:
        return self.ask_chapter - self.fact_chapter


class QuestionsFile(_Strict):
    version: PositiveInt
    status: str
    story: Literal["sample-story", "run"]
    # story "run" (D-83): thư mục kết quả của pipeline.bench_run (tương đối thì tính từ gốc repo),
    # và sha256 của từng file đọc từ đó (đường dẫn tương đối trong run_dir), khoá đề theo đúng truyện.
    run_dir: str | None = None
    run_sha256: Mapping[str, str] = Field(default_factory=dict)
    questions: tuple[Question, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> Self:
        if self.story == "run":
            if not self.run_dir:
                raise ValueError("story: run cần run_dir (thư mục kết quả của pipeline.bench_run)")
            if not self.run_sha256:
                raise ValueError("story: run cần run_sha256 (hash các file đọc từ run_dir)")
        else:
            if self.run_dir is not None or self.run_sha256:
                raise ValueError("run_dir và run_sha256 chỉ dùng với story: run")
            loose = [q.id for q in self.questions if not q.graph_agrees]
            if loose:  # đồ thị dựng tay là đáp án: không có câu nào đồ thị "sai"
                raise ValueError(f"truyện mẫu: graph_agrees phải true: {', '.join(loose)}")
        ids = [q.id for q in self.questions]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            raise ValueError(f"id câu hỏi trùng: {', '.join(dupes)}")
        asked = [(q.ask_chapter, q.question) for q in self.questions]
        same = sorted({q.id for q in self.questions if asked.count((q.ask_chapter, q.question)) > 1})
        if same:  # model giả tìm câu hỏi theo (chương, chữ)
            raise ValueError(f"câu hỏi trùng chữ ở cùng chương hỏi: {', '.join(same)}")
        return self


class RagSettings(_Strict):
    top_k: PositiveInt
    chunk_chars: PositiveInt


class GraphSettings(_Strict):
    recent_chapter: bool  # hai hệ đồ thị có thấy chương N không (mọi hệ trừ `full` đều thấy)


class GraphQuotesSettings(_Strict):
    """Hệ đồ thị + câu trích (D-81). Cắt đoạn theo `rag.chunk_chars`, nên chỉ khác `rag` ở `top_k`."""

    enabled: bool  # false: không chạy khi bỏ trống --systems; chọn bằng --systems là lỗi
    top_k: PositiveInt


class RunFile(_Strict):
    version: PositiveInt
    samples: PositiveInt
    max_tokens_per_call: PositiveInt
    # Model trả lời lấy từ config/models.yaml vai `narrator` (cùng một model cho mọi hệ).
    prices: Mapping[str, Price] = Field(min_length=1)
    rag: RagSettings
    graph: GraphSettings
    graph_quotes: GraphQuotesSettings

    @property
    def systems(self) -> tuple[str, ...]:
        """Hệ chạy khi bỏ trống --systems: mọi hệ, trừ hệ tuỳ chọn đang tắt (OPTIONAL_SYSTEMS)."""
        enabled = {s: getattr(self, s).enabled for s in OPTIONAL_SYSTEMS}
        return tuple(s for s in SYSTEMS if enabled.get(s, True))


# --- đề ------------------------------------------------------------------------------------------


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as e:
        raise ConfigError(f"không đọc được {path}: {e}") from None


@dataclass(frozen=True)
class BenchData:
    questions: QuestionsFile
    run: RunFile
    story: Mapping[int, str]  # chương -> văn bản
    packages: tuple[tuple[int, ChangePackage], ...]  # (chương, gói thay đổi), gồm chương 0
    hashes: Mapping[str, str]
    source: str = "sample-story"  # nguồn truyện, ghi vào meta.json: "sample-story" hoặc run_dir

    @property
    def chapters(self) -> tuple[int, ...]:
        return tuple(sorted(self.story))

    def state_at(self, chapter: int) -> GraphState:
        """Đồ thị đã biết tới hết chương `chapter`: các gói chương 0..chapter phủ lên nền rỗng."""
        return OverlayState(EmptyState(), [pkg for n, pkg in self.packages if n <= chapter])

    def question(self, qid: str) -> Question:
        for q in self.questions.questions:
            if q.id == qid:
                return q
        raise KeyError(qid)


def load_data(data_dir: Path = DATA_DIR, *, sample_dir: Path | None = None,
              questions_file: str = "questions.yaml") -> BenchData:
    raw_q, raw_r = _read(data_dir / questions_file), _read(data_dir / "run.yaml")
    questions = _parse_yaml(questions_file, raw_q, QuestionsFile)
    run = _parse_yaml("run.yaml", raw_r, RunFile)
    hashes = {questions_file: sha256(raw_q), "run.yaml": sha256(raw_r)}
    if questions.story == "run":
        story, packages, files = _read_run(questions)
        source = str(questions.run_dir)
    else:
        root = sample_dir or DEFAULT_SAMPLE_DIR
        sample = read_sample(root)
        story = {c.number: c.text for c in sample.chapters if c.number >= 1}
        packages = tuple((c.number, c.package) for c in sample.chapters)
        files = {
            "sample-story/graph.yaml": sha256(_read(root / "graph.yaml")),
            **{f"sample-story/ch{n:02d}.md": sha256(_read(root / f"ch{n:02d}.md")) for n in story},
        }
        source = "sample-story"
    data = BenchData(questions, run, story, packages, {**hashes, **files}, source)
    problems = [p for q in questions.questions for p in check_question(q, data)]
    if problems:
        raise ConfigError("đề bài A sai:\n- " + "\n- ".join(problems))
    return data


# --- truyện do pipeline viết (D-83) -----------------------------------------------------------------
# Văn chương: `bench_e_story.run_chapter_text`, dùng chung với bài E (người kể đọc đoạn trên trang,
# D-143).


def _resolve_run_dir(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _read_run(questions: QuestionsFile
              ) -> tuple[dict[int, str], tuple[tuple[int, ChangePackage], ...], dict[str, str]]:
    """(văn từng chương, gói từng chương, hash các file) của `run_dir`. Hash phải khớp đúng
    `run_sha256`: đề viết cho đúng những byte đó."""
    assert questions.run_dir is not None
    root = _resolve_run_dir(questions.run_dir)
    raw_dump = _read(root / "truth_dump.json")
    try:
        dump = json.loads(raw_dump.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ConfigError(f"{root / 'truth_dump.json'} không phải JSON hợp lệ: {e}") from None
    packages = run_packages(dump)
    raw_chapters = {n: _read(root / "chapters" / f"ch{n:02d}.md") for n, _ in packages if n >= 1}
    try:
        story = {n: run_chapter_text(raw.decode("utf-8")) for n, raw in raw_chapters.items()}
    except UnicodeDecodeError as e:
        raise ConfigError(f"{root / 'chapters'}: chương không phải UTF-8: {e}") from None
    files = {"truth_dump.json": sha256(raw_dump),
             **{f"chapters/ch{n:02d}.md": sha256(raw) for n, raw in raw_chapters.items()}}
    pinned = dict(questions.run_sha256)
    wrong = sorted(f for f in files.keys() | pinned.keys() if files.get(f) != pinned.get(f))
    if wrong:
        raise ConfigError(f"{questions.run_dir}: hash khác `run_sha256` của đề (thiếu, thừa hoặc đã "
                          f"sửa sau khi khai đề): {', '.join(wrong)}")
    return story, packages, {f"run/{f}": h for f, h in files.items()}


# --- tính lại đáp án từ đồ thị --------------------------------------------------------------------


def _ids(edges: Sequence[Any], side: str) -> list[str]:
    return sorted({getattr(e, side) for e in edges})


def _text_of(state: GraphState, node: str) -> str:
    row = state.nodes([node]).get(node)
    if row is None:
        raise ValueError(f"không có nút {node}")
    return " ".join(str(row.props[k]) for k in ("description", "text", "content", "name")
                    if row.props.get(k))


def _single_edge(state: GraphState, edge_type: str, chapter: int, source: str, target: str) -> Any:
    found = state.edges_at(edge_type, chapter, source_id=source, target_id=target)
    if len(found) != 1:
        raise ValueError(f"cần đúng một cạnh {edge_type} {source}>{target} ở chương {chapter}, "
                         f"có {len(found)}")
    return found[0]


def derive(spec: Mapping[str, Any], state: GraphState, chapter: int) -> Any:
    """Đáp án theo đồ thị `state` ở cuối chương `chapter`. Danh sách id đã sắp, bool, chuỗi, hoặc
    (op node_text) True khi mọi nhóm từ khoá của spec đều có trong chữ của nút."""
    op = spec["op"]
    if op == "holders":
        return _ids(state.edges_at("HOLDS", chapter, target_id=spec["item"]), "source")
    if op == "held_by":
        return _ids(state.edges_at("HOLDS", chapter, source_id=spec["holder"]), "target")
    if op == "edge_exists":
        return bool(state.edges_at(spec["type"], chapter, source_id=spec["from"],
                                   target_id=spec["to"]))
    if op == "edge_sources":
        return _ids(state.edges_at(spec["type"], chapter, target_id=spec["to"]), "source")
    if op == "edge_targets":
        return _ids(state.edges_at(spec["type"], chapter, source_id=spec["from"]), "target")
    if op == "edge_sources_of_type":
        return _ids(state.edges_at(spec["type"], chapter), "source")
    if op == "handed_over":  # người giao cho `to`: cạnh HOLDS đóng đúng lúc cạnh của `to` mở
        edges = state.edges_at("HOLDS", chapter, target_id=spec["item"], ever=True)
        mine = min((e for e in edges if e.source == spec["to"]),
                   key=lambda e: e.valid_from_chapter)
        return sorted({e.source for e in edges if e.valid_to_chapter == mine.valid_from_chapter})
    if op == "relation_kind":
        return _single_edge(state, "RELATES_TO", chapter, spec["from"], spec["to"]).props["kind"]
    if op == "relation_is":
        return _single_edge(state, "RELATES_TO", chapter, spec["from"],
                            spec["to"]).props["kind"] == spec["kind"]
    if op == "alive":
        return not state.edges_at("DIED_IN", chapter, source_id=spec["character"])
    if op == "edge_prop":
        return [_single_edge(state, spec["type"], chapter, spec["from"],
                             spec["to"]).props[spec["prop"]]]
    if op == "edge_since":  # chương mà đồ thị ghi cạnh đang hiệu lực, dạng lựa chọn "chương N"
        edge = _single_edge(state, spec["type"], chapter, spec["from"], spec["to"])
        return f"chương {edge.valid_from_chapter}"
    if op == "resolve_alias":
        found = AliasIndex(state.named_nodes()).find(spec["alias"])
        if len(found) != 1:
            raise ValueError(f"biệt danh {spec['alias']!r} khớp {len(found)} nút")
        return found
    if op == "node_text":
        text = flat(_text_of(state, spec["node"]))
        return all(any(contains_phrase(text, alt) for alt in group) for group in spec["keywords"])
    raise ValueError(f"derive: op không biết: {op}")


def _chapter_texts_upto(data: BenchData, chapter: int) -> dict[int, str]:
    return {n: flat(t) for n, t in data.story.items() if n <= chapter}


_DERIVE_ID_KEYS = ("item", "holder", "from", "to", "character", "node")
_RESULT_SHAPE = {"entities": list, "bool": bool, "choice": str, "text": bool}


def _graph_problems(q: Question, result: Any) -> list[str]:
    """Đáp án gốc so với kết quả `derive` (đồ thị nói gì). Rỗng = đồ thị cho đúng đáp án."""
    a = q.answer
    pre = f"câu {q.id}:"
    if a.type == "entities":
        return [] if result == sorted(a.gold) else [f"{pre} gold {sorted(a.gold)} khác đồ thị {result}"]
    if a.type in ("bool", "choice"):
        return [] if result == a.gold else [f"{pre} gold {a.gold!r} khác đồ thị {result!r}"]
    assert q.derive is not None
    problems = [] if result is True else [f"{pre} từ khoá derive không có trong chữ của nút"]
    accepted = {flat(alt) for group in a.gold for alt in group}
    for group in q.derive["keywords"]:
        if not any(flat(g) in accepted for g in group):
            problems.append(f"{pre} gold không chấp nhận từ khoá của đồ thị: {group}")
    return problems


def check_question(q: Question, data: BenchData) -> list[str]:
    """Lỗi của một câu hỏi (rỗng = sạch): chương không có, câu trích không có trên trang, id thực thể
    không có trong đồ thị, `derive` trỏ tới nút không có, và cờ `graph_agrees` sai: true mà đáp án
    gốc lệch đồ thị, hoặc false mà đồ thị lại cho đúng đáp án (D-83)."""
    problems: list[str] = []
    pre = f"câu {q.id}:"
    if q.ask_chapter not in data.story:
        return [f"{pre} truyện không có chương {q.ask_chapter}"]
    texts = _chapter_texts_upto(data, q.ask_chapter)
    for ev in q.evidence:
        if ev.chapter > q.ask_chapter:
            problems.append(f"{pre} câu trích ở chương {ev.chapter} sau ask_chapter {q.ask_chapter}")
        elif flat(ev.quote) not in texts.get(ev.chapter, ""):
            problems.append(f"{pre} câu trích không có nguyên văn trong chương {ev.chapter}: "
                            f"{ev.quote!r}")
    names = data.state_at(q.ask_chapter).named_nodes()
    a = q.answer
    if a.type == "entities":
        unknown = sorted(set(a.gold) - set(names))
        if unknown:
            problems.append(f"{pre} id không có trong đồ thị: {unknown}")
        stray = sorted(set(a.aliases) - set(names))
        if stray:
            problems.append(f"{pre} aliases cho id không có: {stray}")
    if q.derive is None:  # graph_agrees false (Question đã kiểm): đồ thị không có gì để tính
        return problems
    state = data.state_at(q.state_chapter)
    ids = [q.derive[k] for k in _DERIVE_ID_KEYS if isinstance(q.derive.get(k), str)]
    absent = sorted(set(ids) - set(state.nodes(ids)))
    if absent:  # gõ sai id thì derive ra rỗng, trông như "đồ thị sai": chặn trước
        return [*problems, f"{pre} derive trỏ tới id không có nút trong đồ thị: {absent}"]
    try:
        result = derive(q.derive, state, q.state_chapter)
    except (ValueError, KeyError, LookupError) as e:
        return [*problems, f"{pre} derive lỗi: {type(e).__name__}: {e}"]
    if not isinstance(result, _RESULT_SHAPE[a.type]):
        return [*problems, f"{pre} derive trả {type(result).__name__}, không hợp answer.type {a.type}"]
    against = _graph_problems(q, result)
    if q.graph_agrees:
        problems += against
    elif not against:
        problems.append(f"{pre} graph_agrees: false nhưng đồ thị cho đúng đáp án ({result!r})")
    return problems


# --- chấm một câu trả lời -----------------------------------------------------------------------------

ABSTAIN_PHRASES = ("không biết", "không rõ", "không đủ thông tin", "không có thông tin",
                   "không thể xác định", "không thể biết", "chưa rõ", "không được nhắc",
                   "không được đề cập", "không thấy")
YES_WORDS = ("có", "đúng", "phải")
NO_WORDS = ("không", "chưa", "sai")


def is_abstain(answer: str) -> bool:
    head = flat(answer)[:60]
    return any(head.startswith(flat(p)) for p in ABSTAIN_PHRASES) or not head


def parse_bool(answer: str) -> bool | None:
    """Từ đầu tiên của câu trả lời; không nhận ra thì None (tính sai)."""
    words = flat(answer).split()
    if not words:
        return None
    if words[0] in YES_WORDS:
        return True
    if words[0] in NO_WORDS:
        return False
    return None


def parse_choice(answer: str, options: Sequence[str]) -> str | None:
    """Đúng một lựa chọn xuất hiện trong câu trả lời; không có hoặc nhiều hơn một thì None."""
    f = flat(answer)
    hits = [o for o in options if contains_phrase(f, o)]
    # "người quen" chứa "quen": nếu một lựa chọn là phần của lựa chọn khác, giữ lựa chọn dài nhất
    hits = [o for o in hits if not any(o != p and flat(o) in flat(p) for p in hits)]
    return hits[0] if len(hits) == 1 else None


def question_index(q: Question, names: Mapping[str, Sequence[str]]) -> AliasIndex:
    merged: dict[str, list[str]] = {k: list(v) for k, v in names.items()}
    for entity_id, extra in q.answer.aliases.items():
        merged.setdefault(entity_id, []).extend(extra)
    return AliasIndex(merged)


def score_answer(q: Question, answer: str, names: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """{'correct': bool, 'abstained': bool, 'parsed': ...}. Kiêng cữ không bao giờ đúng."""
    a = q.answer
    abstained = is_abstain(answer)
    if abstained:
        return {"correct": False, "abstained": True, "parsed": None}
    if a.type == "bool":
        parsed: Any = parse_bool(answer)
        return {"correct": parsed is a.gold, "abstained": False, "parsed": parsed}
    if a.type == "choice":
        parsed = parse_choice(answer, a.options)
        return {"correct": parsed == a.gold, "abstained": False, "parsed": parsed}
    if a.type == "text":
        f = flat(answer)
        parsed = [[alt for alt in group if contains_phrase(f, alt)] for group in a.gold]
        return {"correct": all(parsed), "abstained": False, "parsed": parsed}
    index = question_index(q, names)
    asked = set(index.find(q.question))  # thực thể đã nêu trong câu hỏi: nhắc lại không bị trừ
    found = [e for e in index.find(answer) if e in a.gold or e not in asked]
    return {"correct": sorted(found) == sorted(a.gold), "abstained": False,
            "parsed": sorted(found)}


# --- câu trả lời giả (oracle, null) -------------------------------------------------------------------


def oracle_answer(q: Question, names: Mapping[str, Sequence[str]]) -> str:
    """Câu trả lời đúng theo đáp án gốc, dạng người viết ra."""
    a = q.answer
    if a.type == "bool":
        return "Có" if a.gold else "Không"
    if a.type == "choice":
        return str(a.gold)
    if a.type == "text":
        return " ".join(group[0] for group in a.gold)
    return ", ".join(names[e][0] for e in a.gold)


def null_answer(_: Question) -> str:
    return "Không biết"


def wrong_answer(q: Question, names: Mapping[str, Sequence[str]]) -> str:
    """Câu trả lời chắc chắn sai (cùng dạng), cho test: hệ đoán sai bị tính sai chứ không phải kiêng."""
    a = q.answer
    if a.type == "bool":
        return "Không" if a.gold else "Có"
    if a.type == "choice":
        return next(o for o in a.options if o != a.gold)
    if a.type == "text":
        return "Một câu không liên quan gì tới câu hỏi"
    others = [n for n in names if n not in a.gold and n not in AliasIndex(names).find(q.question)]
    return names[others[0]][0] if others else "Một người lạ"



# --- điều kiện để một ngữ cảnh "đủ" trả lời (cho model giả oracle) ---------------------------------


def support_keys(spec: Mapping[str, Any], state: GraphState, chapter: int) -> set[str]:
    """Khoá `Context.facts` mà ngữ cảnh của hệ đồ thị phải có để trả lời câu có `derive` này.
    Cạnh: `edge_key`; trạng thái sống/chết: `status:<id>`; nút lời nói dối: `lie:<id>`; sự kiện:
    `node:<id>` (Event: khối sự kiện; Fact: dòng "đã biết" mang chữ của nó, D-144); thực thể được nối:
    `entity:<id>`; "không có cạnh nào": `complete:<id>`, chỉ có khi danh sách của thực thể không bị cắt
    bởi trần dòng (D-144)."""
    op = spec["op"]

    def keys_of(edges: Sequence[Any]) -> set[str]:
        return {edge_key(e) for e in edges}

    if op == "holders":
        return keys_of(state.edges_at("HOLDS", chapter, target_id=spec["item"]))
    if op == "held_by":
        return keys_of(state.edges_at("HOLDS", chapter, source_id=spec["holder"]))
    if op == "edge_exists":
        edges = state.edges_at(spec["type"], chapter, source_id=spec["from"], target_id=spec["to"])
        return keys_of(edges) or {f"complete:{spec['from']}"}
    if op == "edge_sources":
        return keys_of(state.edges_at(spec["type"], chapter, target_id=spec["to"]))
    if op == "edge_targets":
        return keys_of(state.edges_at(spec["type"], chapter, source_id=spec["from"]))
    if op == "edge_sources_of_type":
        labels = state.node_labels(sorted(state.named_nodes()))
        return {f"status:{n}" for n, label in labels.items() if label == "Character"}
    if op == "handed_over":
        return keys_of(state.edges_at("HOLDS", chapter, target_id=spec["item"], ever=True))
    if op in ("relation_kind", "relation_is", "edge_prop", "edge_since"):
        edge_type = spec["type"] if op in ("edge_prop", "edge_since") else "RELATES_TO"
        return keys_of(state.edges_at(edge_type, chapter, source_id=spec["from"],
                                      target_id=spec["to"]))
    if op == "alive":
        return {f"status:{spec['character']}"}
    if op == "resolve_alias":
        return {f"entity:{i}" for i in derive(spec, state, chapter)}
    if op == "node_text":
        label = state.node_labels([spec["node"]]).get(spec["node"])
        return {f"lie:{spec['node']}" if label == "Lie" else f"node:{spec['node']}"}
    raise ValueError(f"support_keys: op không biết: {op}")


def context_supports(q: Question, ctx: Any, data: BenchData) -> bool:
    """Ngữ cảnh có đủ chứng cứ để trả lời câu `q` không. Trang: mọi câu trích bằng chứng nằm trong
    chữ ngữ cảnh. Đồ thị: đủ khoá `facts` mà `derive` cần, và chỉ khi đồ thị cho đúng đáp án
    (`graph_agrees`; đồ thị sai thì khoá dẫn tới câu sai). Hai hệ đồ thị đủ khi một trong hai nguồn
    đủ (D-81, D-83): chữ của chúng có cả chương N, nên trần của chúng không dưới hệ "không bộ nhớ"."""
    def graph_ok() -> bool:
        if not q.graph_agrees or q.derive is None:
            return False
        return support_keys(q.derive, data.state_at(q.state_chapter), q.state_chapter) <= ctx.facts

    def page_ok() -> bool:
        flat_ctx = flat(ctx.text)
        return all(flat(ev.quote) in flat_ctx for ev in q.evidence)

    if ctx.system in ("graph", "graph_quotes"):
        return graph_ok() or page_ok()
    return page_ok()
