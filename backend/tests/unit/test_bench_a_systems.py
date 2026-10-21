"""Bài đo A: năm hệ dựng đúng ngữ cảnh (D-72, D-73). Không mạng, không Neo4j."""

from collections.abc import Sequence
from pathlib import Path

import pytest

from writory.guard.state import EdgeRow, GraphState
from writory.pipeline import bench_a, bench_a_data, bench_a_systems
from writory.pipeline.bench_a import ContextBuilder
from writory.pipeline.bench_a_data import context_supports, load_data
from writory.pipeline.bench_a_systems import (
    AliasIndex,
    Bm25Index,
    build_graph_context,
    chunk_chapter,
    context_full,
    context_none,
    context_rag,
    context_rolling,
    flat,
    tokens,
)

DATA = load_data()
STORY = DATA.story
QUESTIONS = DATA.questions.questions
SUMMARIES = {k: f"TÓM-TẮT-GIẢ-{k}" for k in range(1, 6)}
BUILDER = ContextBuilder(DATA, DATA.state_at, SUMMARIES)


def later_paragraphs(chapter: int) -> list[str]:
    """Đoạn văn (đã chuẩn hoá) của mọi chương SAU `chapter`: không hệ nào được chứa chúng."""
    return [flat(p) for n in STORY if n > chapter
            for p in STORY[n].split("\n\n") if len(p.strip()) > 40 and not p.startswith("#")]


# --- chuẩn hoá và nối tên -----------------------------------------------------------------------


def test_flat_keeps_vietnamese_diacritics_and_drops_punctuation():
    assert flat("Thanh  Sương, —lão nói!") == "thanh sương lão nói"
    assert flat("Minh") != flat("mình")


def test_alias_index_prefers_longer_names_and_reports_each_entity_once():
    index = AliasIndex({"lan": ["Phạm Thị Lan", "Lan", "cô Lan"], "minh": ["Trần Minh", "Minh"],
                        "kiem": ["Thanh Sương", "thanh kiếm"]})
    assert index.find("Phạm Thị Lan gặp Minh, Lan cười, cô Lan đi") == ["lan", "minh"]
    assert index.find("thanh kiếm Thanh Sương") == ["kiem"]
    assert index.find("Lanh lợi") == []  # khớp trọn từ, không khớp một phần
    assert index.find("mình tôi") == []


# --- BM25 -----------------------------------------------------------------------------------------


def test_tokens_include_syllable_pairs_and_drop_function_words():
    out = tokens("Lão Gù là thợ rèn")
    assert "lão" in out and "gù" in out and "lão_gù" in out and "là" not in out


def test_chunks_keep_chapter_order_and_skip_the_heading():
    chunks = chunk_chapter(3, STORY[3], chunk_chars=500)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert all(c.chapter == 3 for c in chunks) and not any(c.text.startswith("#") for c in chunks)
    assert "".join(flat(c.text) for c in chunks).replace(" ", "") != ""
    assert sum(len(c.text) for c in chunks) >= len(STORY[3]) * 0.8


def test_bm25_finds_the_paragraph_that_names_the_place():
    chunks = [c for n in (1, 2, 3, 4) for c in chunk_chapter(n, STORY[n], chunk_chars=500)]
    top = Bm25Index(chunks).top("Lão Gù được tìm thấy đã chết ở đâu? miếu Bà", 2)
    assert any("nằm sấp sau miếu Bà" in c.text for c in top)


def test_bm25_ignores_unrelated_query_and_is_deterministic():
    chunks = chunk_chapter(1, STORY[1], chunk_chars=300)
    index = Bm25Index(chunks)
    assert index.top("zzz qqq", 3) == []
    assert index.top("Lão Gù thanh kiếm", 3) == index.top("Lão Gù thanh kiếm", 3)


# --- ngữ cảnh từng hệ -------------------------------------------------------------------------------


def test_none_sees_only_the_latest_chapter():
    ctx = context_none(STORY, 3)
    assert "[Chương 3]" in ctx.text and "[Chương 2]" not in ctx.text
    assert "miếu Bà" in ctx.text and "gầm giường trống trơn" not in ctx.text


def test_full_sees_every_chapter_up_to_n_and_none_after():
    ctx = context_full(STORY, 3)
    assert [f"[Chương {n}]" in ctx.text for n in range(1, 6)] == [True, True, True, False, False]


def test_rolling_has_summaries_of_older_chapters_plus_the_latest_text():
    texts = BUILDER.rolling_text(2)
    ctx = context_rolling(STORY, 3, texts)
    assert "Chương 1: TÓM-TẮT-GIẢ-1" in ctx.text and "Chương 2: TÓM-TẮT-GIẢ-2" in ctx.text
    assert "[Chương 3]" in ctx.text and "TÓM-TẮT-GIẢ-3" not in ctx.text
    assert "nằm sấp sau miếu Bà" in ctx.text  # chương 3 nguyên văn
    assert "Ta giao nó cho mày" not in ctx.text  # chương 2 chỉ còn bản tóm tắt


def test_rolling_at_chapter_one_has_no_summary_section():
    ctx = context_rolling(STORY, 1, {})
    assert "Tóm tắt" not in ctx.text and "[Chương 1]" in ctx.text


def test_rolling_without_a_needed_summary_fails_loudly():
    builder = ContextBuilder(DATA, DATA.state_at, {1: "x"})
    q = DATA.question("item-06")  # hỏi ở chương 5: cần tóm tắt 1..4
    with pytest.raises(KeyError, match="thiếu tóm tắt"):
        builder.build("rolling", q)


def test_rag_retrieves_only_from_older_chapters_and_adds_the_latest_whole():
    ctx = context_rag(STORY, 5, "Ai đã giao thanh kiếm Thanh Sương cho Minh?", top_k=3,
                      chunk_chars=500)
    retrieved = ctx.detail["retrieved"]
    assert retrieved and all(chapter < 5 for chapter, _ in retrieved)
    assert len(retrieved) <= 3 and "[Chương 5]" in ctx.text
    assert "[Các đoạn liên quan trong chương trước]" in ctx.text


def test_rag_at_chapter_one_has_nothing_older_to_retrieve():
    ctx = context_rag(STORY, 1, "Lão Gù là ai?", top_k=3, chunk_chars=500)
    assert ctx.detail["retrieved"] == [] and ctx.detail["pool"] == 0
    assert "[Các đoạn liên quan" not in ctx.text


@pytest.mark.parametrize("system", bench_a_systems.SYSTEMS)
def test_no_system_ever_sees_a_later_chapter(system):
    """Ngữ cảnh của câu hỏi ở chương N không chứa đoạn văn nào của chương sau N."""
    for q in QUESTIONS:
        text = flat(BUILDER.build(system, q).text)
        leaked = [p[:50] for p in later_paragraphs(q.ask_chapter) if p in text]
        assert leaked == [], (q.id, system)


# --- hệ đồ thị -----------------------------------------------------------------------------------------


def test_graph_context_shows_the_window_of_each_fact_up_to_the_asked_chapter():
    q = DATA.question("item-03")  # chương 3: Thanh Sương đã sang tay Minh từ cuối chương 2
    text = BUILDER.build("graph", q).text
    assert "Trần Minh giữ Thanh Sương (đúng từ cuối chương 2 tới nay)" in text
    assert "Hồ Sĩ Bằng giữ Thanh Sương (đúng từ cuối chương 1 tới cuối chương 1)" in text
    assert "Phạm Thị Lan giữ" not in text  # cạnh mở ở chương 4: chưa tồn tại ở chương 3


def test_graph_context_edge_closed_in_the_asked_chapter_ends_the_chapter_before():
    """Cạnh đóng ở chương N (valid_to = N) đúng tới hết chương N-1, không phải tới nay."""
    text = BUILDER.build("graph", DATA.question("item-02")).text  # hỏi ở chương 2
    assert "Hồ Sĩ Bằng giữ Thanh Sương (đúng từ cuối chương 1 tới cuối chương 1)" in text
    assert "Trần Minh giữ Thanh Sương (đúng từ cuối chương 2 tới nay)" in text
    rel = BUILDER.build("graph", DATA.question("rel-03")).text  # chương 3: quan hệ "bạn" đóng ở 3
    assert "bạn (mức 50) (đúng từ cuối chương 2 tới cuối chương 2)" in rel
    assert "yêu (mức 80) (đúng từ cuối chương 3 tới nay)" in rel


def test_graph_context_does_not_leak_a_later_close_into_an_earlier_chapter():
    """Nền đầy đủ (như Neo4j: cạnh đã có cả cửa sổ đóng ở chương sau) và nền cắt tới chương N cho
    CÙNG ngữ cảnh: cạnh đóng ở chương sau N vẫn "tới nay"."""
    full = DATA.state_at(5)
    for q in QUESTIONS:
        a = build_graph_context(full, q.question, q.ask_chapter, story=STORY)
        b = build_graph_context(DATA.state_at(q.ask_chapter), q.question, q.ask_chapter,
                                story=STORY)
        assert a.text == b.text and a.facts == b.facts, q.id


def test_graph_context_roster_lists_who_is_dead_without_naming_anyone():
    q = DATA.question("alive-06")  # "nhân vật nào đã chết": câu hỏi không nêu tên ai
    text = BUILDER.build("graph", q).text
    assert "Hồ Sĩ Bằng: ĐÃ CHẾT (từ cuối chương 3)" in text
    assert "Phạm Thị Lan: còn sống" in text
    early = BUILDER.build("graph", DATA.question("alive-01")).text  # chương 2: chưa ai chết
    assert "ĐÃ CHẾT" not in early


def test_graph_context_without_a_named_entity_falls_back_to_the_protagonist():
    ctx = build_graph_context(DATA.state_at(3), "Chuyện gì đã xảy ra?", 3, story=STORY)
    assert ctx.detail["linked"] == ["minh"]


def test_graph_context_is_capped_and_keys_only_cover_what_fits(monkeypatch):
    monkeypatch.setattr(bench_a_systems, "GRAPH_CHARS_CAP", 400)
    q = DATA.question("item-08")
    ctx = build_graph_context(DATA.state_at(5), q.question, 5, story=None)
    assert ctx.detail["graph_chars"] <= 400
    assert not context_supports(q, ctx, DATA)  # bị cắt thì oracle không còn đủ chứng cứ


def test_graph_recent_chapter_can_be_switched_off():
    q = DATA.question("item-05")
    with_page = build_graph_context(DATA.state_at(5), q.question, 5, story=STORY, recent=True)
    without = build_graph_context(DATA.state_at(5), q.question, 5, story=STORY, recent=False)
    assert "[Chương 5]" in with_page.text and "[Chương 5]" not in without.text


def test_graph_competitor_has_enough_facts_for_every_question():
    """Chứng cứ mà `derive` cần đều nằm trong khoá của ngữ cảnh đồ thị: nền của "oracle = 100%"."""
    missing = [q.id for q in QUESTIONS if not context_supports(q, BUILDER.build("graph", q), DATA)]
    assert missing == []


def test_oracle_support_depends_on_the_context_not_the_system_name():
    q = DATA.question("item-06")  # cách 3 chương
    assert context_supports(q, BUILDER.build("full", q), DATA)
    assert not context_supports(q, BUILDER.build("none", q), DATA)
    assert not context_supports(q, BUILDER.build("rolling", q), DATA)  # tóm tắt giả không có trích dẫn


# --- hệ đồ thị chỉ đọc qua lớp graph/ (G10) -----------------------------------------------------------


class SpyState:
    """Chỉ lộ đúng các phương thức của `GraphState`: gọi gì khác là AttributeError."""

    def __init__(self, inner: GraphState) -> None:
        self._inner = inner
        self.used: set[str] = set()

    def edges_at(self, edge_type: str, chapter: int, *, source_id: str | None = None,
                 target_id: str | None = None, ever: bool = False) -> list[EdgeRow]:
        self.used.add("edges_at")
        return self._inner.edges_at(edge_type, chapter, source_id=source_id,
                                    target_id=target_id, ever=ever)

    def node_labels(self, ids: Sequence[str]):
        self.used.add("node_labels")
        return self._inner.node_labels(ids)

    def nodes(self, ids: Sequence[str]):
        self.used.add("nodes")
        return self._inner.nodes(ids)

    def named_nodes(self):
        self.used.add("named_nodes")
        return self._inner.named_nodes()

    def protagonist_id(self) -> str:
        self.used.add("protagonist_id")
        return self._inner.protagonist_id()


def test_graph_system_reads_only_through_the_graph_state_protocol():
    spy = SpyState(DATA.state_at(5))
    for q in QUESTIONS:
        build_graph_context(spy, q.question, q.ask_chapter, story=STORY)  # type: ignore[arg-type]
    assert {"edges_at", "named_nodes", "nodes", "node_labels"} <= spy.used


def test_graph_system_modules_contain_no_cypher_or_driver_code():
    root = Path(bench_a_systems.__file__).parent
    for name in ("bench_a_systems.py", "bench_a_data.py", "bench_a.py"):
        source = (root / name).read_text(encoding="utf-8")
        for forbidden in ("MATCH ", "MERGE ", "session.run", "execute_query", "CREATE (",
                          "import neo4j", "from neo4j import Driver"):
            assert forbidden not in source, (name, forbidden)
    # đường Neo4j của bài chạy thật nạp muộn và đi qua Neo4jState (graph/), không qua Cypher riêng
    assert "Neo4jState" in (root / "bench_a.py").read_text(encoding="utf-8")


def test_runner_builds_contexts_through_the_injected_graph_state():
    spy = SpyState(DATA.state_at(5))
    builder = ContextBuilder(DATA, lambda _n: spy, SUMMARIES)  # type: ignore[arg-type]
    builder.build("graph", DATA.question("item-05"))
    assert spy.used
    spy.used.clear()
    builder.build("none", DATA.question("item-05"))
    builder.build("full", DATA.question("item-05"))
    builder.build("rag", DATA.question("item-05"))
    builder.build("rolling", DATA.question("item-05"))
    assert spy.used == set()  # bốn hệ còn lại không đụng tới đồ thị


def test_data_module_exposes_group_names_used_by_the_report():
    assert set(bench_a_data.GROUP_LABEL) == set(bench_a_data.GROUPS)
    assert set(bench_a_systems.SYSTEM_LABELS) == set(bench_a.SYSTEMS)
