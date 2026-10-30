"""Bài đo A: sáu hệ dựng đúng ngữ cảnh (D-72, D-73, D-81). Không mạng, không Neo4j."""

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
    context_graph_quotes,
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


@pytest.mark.parametrize("system", ["graph", "graph_quotes"])
def test_graph_competitor_has_enough_facts_for_every_question(system):
    """Chứng cứ mà `derive` cần đều nằm trong khoá của ngữ cảnh đồ thị: nền của "oracle = 100%"."""
    missing = [q.id for q in QUESTIONS if not context_supports(q, BUILDER.build(system, q), DATA)]
    assert missing == []


def test_lie_06_and_07_graph_context_carries_lans_knows_edge():
    """Điều tra lần đo lan-1: cạnh KNOWS lan>l_sword_father (chương 4) CÓ trong ngữ cảnh đồ thị, ở
    cả khối của Lan lẫn khối lời nói dối. "Không" ở lie-06/07 không do phần đọc đồ thị."""
    for qid in ("lie-06", "lie-07"):
        ctx = BUILDER.build("graph", DATA.question(qid))
        assert "edge:KNOWS:lan>l_sword_father@4" in ctx.facts, qid
        assert ("Đã biết đó là lời nói dối: «Thanh kiếm là của cha Minh để lại»; cách biết: suy ra "
                "(đúng từ cuối chương 4 tới nay)") in ctx.text, qid
        assert ("những người ngoài người nói đã biết đó là lời dối: Phạm Thị Lan "
                "(từ cuối chương 4)") in ctx.text, qid


# --- hệ đồ thị + câu trích (D-81) -------------------------------------------------------------------


def graph_only(q) -> str:
    return build_graph_context(DATA.state_at(q.ask_chapter), q.question, q.ask_chapter,
                               story=STORY, recent=False).text


def test_graph_quotes_is_the_graph_context_plus_a_few_passages_plus_chapter_n():
    run = DATA.run
    for q in QUESTIONS:
        graph = BUILDER.build("graph", q)
        ctx = BUILDER.build("graph_quotes", q)
        assert ctx.system == "graph_quotes" and ctx.facts == graph.facts, q.id
        assert ctx.text.startswith(graph_only(q)), q.id  # đúng phần đồ thị của hệ `graph`
        assert ctx.text.endswith(f"[Chương {q.ask_chapter}]\n{STORY[q.ask_chapter].strip()}"), q.id
        retrieved = ctx.detail["retrieved"]
        assert len(retrieved) <= run.graph_quotes.top_k, q.id
        assert all(chapter < q.ask_chapter for chapter, _ in retrieved), q.id  # chương N đã có
        rag = context_rag(STORY, q.ask_chapter, q.question, top_k=run.graph_quotes.top_k,
                          chunk_chars=run.rag.chunk_chars)
        assert retrieved == rag.detail["retrieved"], q.id  # cùng BM25, cùng cách cắt đoạn


def test_graph_quotes_reads_fewer_passages_than_rag():
    assert DATA.run.graph_quotes.top_k < DATA.run.rag.top_k


def test_graph_quotes_brings_back_the_page_lines_the_graph_has_no_edge_for():
    """Lỗi của hệ đồ thị ở lan-1: chi tiết chỉ có trong chữ (alive-07: lời cai Khải) và điều phủ
    định (rel-08, rel-09: cùng họ Trần nhưng không họ hàng). Câu trích nằm ở chương cũ hơn N."""
    for qid in ("alive-07", "rel-08", "rel-09"):
        q = DATA.question(qid)
        [evidence] = q.evidence
        assert evidence.chapter < q.ask_chapter, qid
        assert flat(evidence.quote) not in flat(BUILDER.build("graph", q).text), qid
        assert flat(evidence.quote) in flat(BUILDER.build("graph_quotes", q).text), qid


def test_graph_quotes_at_chapter_one_has_nothing_older_to_retrieve():
    ctx = context_graph_quotes(DATA.state_at(1), "Lão Gù là ai?", 1, story=STORY, top_k=2,
                               chunk_chars=500)
    assert ctx.detail["retrieved"] == [] and ctx.detail["pool"] == 0
    assert "[Đoạn trên trang" not in ctx.text and "[Chương 1]" in ctx.text


def test_graph_quotes_without_chapter_n_searches_chapter_n_too():
    q = DATA.question("item-10")  # chứng cứ ở chính chương 5
    ctx = context_graph_quotes(DATA.state_at(5), q.question, 5, story=STORY, top_k=2,
                               chunk_chars=500, recent=False)
    assert "[Chương 5]" not in ctx.text
    assert any(chapter == 5 for chapter, _ in ctx.detail["retrieved"])


def test_graph_quotes_oracle_falls_back_to_page_evidence_when_the_graph_part_is_cut(monkeypatch):
    """Oracle của hệ lai: đủ khi phần đồ thị đủ khoá HOẶC câu trích trên trang có trong ngữ cảnh."""
    monkeypatch.setattr(bench_a_systems, "GRAPH_CHARS_CAP", 400)
    builder = ContextBuilder(DATA, DATA.state_at, SUMMARIES)
    found = DATA.question("rel-08")  # câu trích chương 1 được BM25 tìm lại
    missed = DATA.question("lie-07")  # câu trích chương 4 không vào top_k
    assert not context_supports(found, builder.build("graph", found), DATA)
    assert context_supports(found, builder.build("graph_quotes", found), DATA)
    assert not context_supports(missed, builder.build("graph_quotes", missed), DATA)


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
    builder.build("graph_quotes", DATA.question("item-05"))
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


# --- truyện dài: trần dòng mỗi nhân vật và câu trả lời ở chữ Fact (D-144) ------------------------------

import types

from writory.graph import ChangePackage
from writory.guard.state import EmptyState, OverlayState
from writory.pipeline.bench_a_data import support_keys
from writory.pipeline.bench_a_systems import LINES_PER_ENTITY_CAP, edge_key

ODD_WORDS = [f"vật{chr(97 + i // 26)}{chr(97 + i % 26)}" for i in range(80)]


def long_story_state(facts: int = 66, last_chapter: int = 22) -> OverlayState:
    """Lan biết `facts` điều, mỗi điều một chữ lạ riêng, rải đều qua các chương 1..`last_chapter`."""
    nodes = [{"id": "lan", "label": "Character", "props": {"name": "Lan"}}]
    edges = []
    for i in range(facts):
        nodes.append({"id": f"f{i}", "label": "Fact",
                      "props": {"text": f"Lan nhìn thấy {ODD_WORDS[i]} trong hộc tủ."}})
        edges.append({"type": "KNOWS", "from": "lan", "to": f"f{i}",
                      "valid_from_chapter": 1 + i * last_chapter // facts, "props": {"how": "chứng kiến"}})
    package = ChangePackage.model_validate({"commit_id": "c0", "nodes": nodes, "edges": edges})
    return OverlayState(EmptyState(), [package])


def known_keys_in(ctx) -> set[str]:
    return {k for k in ctx.facts if k.startswith("edge:KNOWS:lan>")}


def shown(ctx, i: int) -> bool:
    return ODD_WORDS[i] in ctx.text


def test_a_cut_line_is_never_claimed_as_seen():
    """D-144: khoá `facts` chỉ gồm dòng thật sự nằm trong chữ. Nhân vật biết 66 điều, trần 40 dòng:
    số khoá KNOWS bằng số điều có chữ trong ngữ cảnh, không hơn."""
    state = long_story_state()
    ctx = build_graph_context(state, "Lan biết gì?", 22, story=None)
    visible = [i for i in range(66) if shown(ctx, i)]
    assert 0 < len(visible) <= LINES_PER_ENTITY_CAP - 1  # một dòng dành cho tình trạng
    assert len(known_keys_in(ctx)) == len(visible)
    for i in range(66):
        key = next(edge_key(e) for e in state.edges_at("KNOWS", 22, source_id="lan", target_id=f"f{i}"))
        assert (key in ctx.facts) == shown(ctx, i), i


def test_when_over_the_cap_the_newest_lines_are_kept_and_a_relevant_old_one_is_pulled_back():
    state = long_story_state()
    plain = build_graph_context(state, "Lan biết gì?", 22, story=None)
    assert shown(plain, 65) and shown(plain, 64) and not shown(plain, 0)  # gần đây ở lại
    asked = build_graph_context(state, f"Lan có thấy {ODD_WORDS[3]} không?", 22, story=None)
    assert shown(asked, 3) and shown(asked, 65)  # câu hỏi kéo một dòng cũ về, vẫn giữ dòng mới
    assert (edge_key(next(iter(state.edges_at("KNOWS", 22, source_id="lan", target_id="f3"))))
            in asked.facts)


def test_selected_lines_keep_story_order_and_the_status_line_stays_first():
    ctx = build_graph_context(long_story_state(), f"Lan có thấy {ODD_WORDS[3]} không?", 22, story=None)
    block = ctx.text.split("## Lan (nhân vật)")[1].split("\n\n")[0].splitlines()
    assert block[1].startswith("- Tình trạng cuối chương 22")
    order = [i for line in block for i in range(66) if ODD_WORDS[i] in line]
    assert order == sorted(order) and len(block) - 1 <= LINES_PER_ENTITY_CAP


def test_under_the_cap_nothing_is_dropped_and_every_line_is_claimed():
    state = long_story_state(facts=30, last_chapter=10)
    ctx = build_graph_context(state, "Lan biết gì?", 10, story=None)
    assert all(shown(ctx, i) for i in range(30)) and len(known_keys_in(ctx)) == 30
    assert "complete:lan" in ctx.facts


def test_a_cut_block_cannot_prove_that_an_edge_does_not_exist():
    """Danh sách bị cắt thì không chứng minh được "không có cạnh": khoá `complete:` chỉ có khi đủ."""
    cut = build_graph_context(long_story_state(), "Lan biết gì?", 22, story=None)
    assert "complete:lan" not in cut.facts and "entity:lan" in cut.facts
    spec = {"op": "edge_exists", "type": "KNOWS", "from": "lan", "to": "nobody"}
    assert support_keys(spec, long_story_state(), 22) == {"complete:lan"}
    assert not support_keys(spec, long_story_state(), 22) <= cut.facts


def fake_question(spec: dict, state) -> tuple[types.SimpleNamespace, types.SimpleNamespace]:
    # Bằng chứng trên trang cố ý không có trong ngữ cảnh: chỉ đồ thị mới có thể làm câu này đủ chứng cứ.
    nowhere = types.SimpleNamespace(quote="một câu không bao giờ nằm trong ngữ cảnh đồ thị")
    q = types.SimpleNamespace(graph_agrees=True, derive=spec, state_chapter=22, evidence=(nowhere,))
    data = types.SimpleNamespace(state_at=lambda chapter: state)
    return q, data


def test_an_answer_that_lives_in_a_fact_text_counts_as_in_the_graph_when_that_text_is_shown():
    """D-144: `node_text` của một Fact cần khoá `node:<id>`, mà trước đây chỉ khối Event sinh ra nó."""
    state = long_story_state()
    spec = {"op": "node_text", "node": "f65"}
    assert support_keys(spec, state, 22) == {"node:f65"}
    q, data = fake_question(spec, state)
    shown_ctx = build_graph_context(state, "Lan biết gì?", 22, story=None)
    assert "node:f65" in shown_ctx.facts and context_supports(q, shown_ctx, data)
    # Dòng của Fact bị cắt thì chữ không có trong ngữ cảnh, nên không thể tính là có.
    q0, data0 = fake_question({"op": "node_text", "node": "f0"}, state)
    assert not shown(shown_ctx, 0) and "node:f0" not in shown_ctx.facts
    assert not context_supports(q0, shown_ctx, data0)
    # Hỏi đúng điều đó thì dòng được kéo về và đủ chứng cứ.
    asked = build_graph_context(state, f"Lan có thấy {ODD_WORDS[0]} không?", 22, story=None)
    assert context_supports(q0, asked, data0)


def test_the_event_and_lie_keys_are_unchanged():
    spec = {"op": "node_text", "node": "f1"}
    assert support_keys(spec, long_story_state(), 22) == {"node:f1"}
