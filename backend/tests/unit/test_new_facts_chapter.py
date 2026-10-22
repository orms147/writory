"""Fact mới trong đường đi một chương (D-93): ghi vào gói, thấy được ở cảnh sau, dò lộ G2, trần mỗi
chương, tắt được bằng config; cùng ngữ cảnh người viết và gói gộp theo chương."""

import json
from dataclasses import replace

from tests.pipeline_fixtures import (
    EXTRACT_2,
    SCENE_1,
    SCENE_2,
    SUMMARY,
    MemoryStore,
    calls_of,
    choices_reply,
    extract_reply,
    outline_reply,
    writer_context_ch4,
)
from tests.unit.test_pipeline_chapter import run
from writory.config import load_config
from writory.errors import ErrorCode
from writory.graph import ChangePackage, EdgeSpec, NodeSpec
from writory.graph.context import FactInfo, Knower, Text, cap_page_facts
from writory.pipeline.chapter import chapter_node, config_problems, merge_scene_packages

Q_RUMOUR = "Cô bảo cả phố đồn anh là người thân nhất của Lão Gù"
FACT_RUMOUR = {"ref": "new_1", "text": "Cả phố đồn Minh là người thân nhất của Lão Gù",
               "quote": Q_RUMOUR}
Q_LOCK = "Cửa gác vẫn cài then từ bên trong"
FACT_LOCK = {"ref": "new_1", "text": "Cửa gác vẫn cài then từ bên trong", "quote": Q_LOCK}


def _edge(**kw):
    base = {"kind": None, "score": None, "how": None, "told_by": None, "quote": None,
            "known_as": None, "role": None}
    return base | kw


def fact_edges(ref="new_1", quote=Q_RUMOUR):
    return [_edge(type="ABOUT", source=ref, target="minh"),
            _edge(type="KNOWS", source="minh", target=ref, how="chứng kiến", quote=quote),
            _edge(type="KNOWS", source="lan", target=ref, how="tự biết")]


def script(first, second=None):
    return [outline_reply(), SCENE_1, first, outline_reply(), SCENE_2,
            second or EXTRACT_2, SUMMARY, choices_reply()]


async def test_a_new_fact_is_committed_revealed_and_seen_by_the_next_scene(tmp_path):
    first = extract_reply(fact_edges(), new_facts=[FACT_RUMOUR])
    _, outcome, llm, store = await run(script(first), tmp_path)

    [(_, _, package)] = store.commits
    [node] = [n for n in package.nodes if n.label == "Fact"]
    assert node.id == "fact_c4s1_1" and node.props["text"] == FACT_RUMOUR["text"]
    ids = {e.id for e in package.edges}
    assert {"ABOUT:fact_c4s1_1>minh@4", "KNOWS:minh>fact_c4s1_1@4",
            "REVEALED_TO_PLAYER:fact_c4s1_1>ch4@4"} <= ids
    # Cảnh 2 thấy Fact mới trong danh mục của bộ trích và trong tên của đề.
    second_extract = calls_of(llm, "extract")[1][-1].content
    assert "fact_c4s1_1" in second_extract and FACT_RUMOUR["text"] in second_extract
    assert outcome.scenes[0].rejected == ()


async def test_the_extractor_is_told_how_many_new_facts_it_may_write(tmp_path):
    _, _, llm, _ = await run(script(extract_reply()), tmp_path)
    cap = load_config().limits.facts.max_new_per_chapter
    assert f"tối đa {cap} sự thật mới" in calls_of(llm, "extract")[0][-1].content


async def test_a_new_fact_that_leaks_a_secret_is_dropped_by_the_leak_check(tmp_path, monkeypatch):
    """G2 trên chữ Fact mới: văn cảnh không vi phạm (hai vế ở hai câu), nhưng Fact gộp cả hai thành
    một câu "Lan là người của Hội Hắc Kỳ", đúng bí mật chưa tới khoảng lộ."""
    page = (SCENE_1 + "\n\nLan rót trà. Minh nhắc tới người của Hội Hắc Kỳ. Có kẻ bàn chuyện gián "
            "điệp ngoài bến.")
    leak = {"ref": "new_1", "text": "Lan là người của Hội Hắc Kỳ",
            "quote": "Minh nhắc tới người của Hội Hắc Kỳ."}
    edges = [_edge(type="ABOUT", source="new_1", target="lan"),
             _edge(type="KNOWS", source="minh", target="new_1", how="chứng kiến",
                   quote="Minh nhắc tới người của Hội Hắc Kỳ.")]
    s = [outline_reply(), page, extract_reply(edges, new_facts=[leak]), outline_reply(), SCENE_2,
         EXTRACT_2, SUMMARY, choices_reply()]
    _, outcome, _, store = await run(s, tmp_path)

    [(_, _, package)] = store.commits
    assert [n for n in package.nodes if n.label == "Fact"] == []
    assert not [e for e in package.edges if "fact_c4s1_1" in (e.source, e.target)]
    assert any("G2" in why for _, why in outcome.scenes[0].rejected)


async def test_the_cap_is_per_chapter_not_per_scene(tmp_path):
    first = extract_reply(fact_edges(), new_facts=[FACT_RUMOUR])
    both = json.loads(EXTRACT_2)  # cảnh 2 vẫn phải hé lộ gã lái đò cho bước tạo lựa chọn
    both["edges"] += fact_edges(quote=Q_LOCK)
    both["new_facts"] = [FACT_LOCK]
    second = json.dumps(both, ensure_ascii=False)
    _, outcome, _, store = await run(script(first, second), tmp_path,
                                     limits={"facts": {"max_new_per_chapter": 1}})
    [(_, _, package)] = store.commits
    assert [n.id for n in package.nodes if n.label == "Fact"] == ["fact_c4s1_1"]
    assert any("trần" in why for _, why in outcome.scenes[1].rejected)


async def test_zero_cap_turns_the_feature_off(tmp_path):
    first = extract_reply(fact_edges(), new_facts=[FACT_RUMOUR])
    _, outcome, llm, store = await run(script(first), tmp_path,
                                       limits={"facts": {"max_new_per_chapter": 0}})
    [(_, _, package)] = store.commits
    assert [n for n in package.nodes if n.label == "Fact"] == []
    assert "không ghi (new_facts để rỗng)" in calls_of(llm, "extract")[0][-1].content
    assert outcome.scenes[0].rejected


def test_merge_keeps_the_nodes_of_every_scene_once():
    fact = NodeSpec(id="fact_c4s1_1", label="Fact", props={"text": "Một điều trên trang"})
    edge = EdgeSpec.model_validate({"type": "ABOUT", "from": "fact_c4s1_1", "to": "minh",
                                    "valid_from_chapter": 4})
    first = ChangePackage(commit_id="x", nodes=[fact], edges=[edge])
    second = ChangePackage(commit_id="x", nodes=[])
    merged = merge_scene_packages("c", chapter_node(4), [first, second])
    assert [n.id for n in merged.nodes] == ["ch4", "fact_c4s1_1"] and len(merged.edges) == 1


def _fact(fid, since):
    return FactInfo(fid, f"Điều {fid}", (Knower("minh", Text("Minh", False), since, None),), False)


def test_writer_context_keeps_every_initial_fact_and_only_the_latest_page_facts():
    """Fact của thế giới khởi tạo (có người biết từ chương 0) luôn giữ; Fact sinh từ trang chỉ giữ
    `keep` cái mới nhất, để đồ thị phình không làm đề phình theo."""
    base = [_fact("f_a", 0), _fact("f_b", 0)]
    page = [_fact(f"p{i}", i) for i in range(1, 6)]
    kept = cap_page_facts(tuple(base + page), keep=2)
    assert [f.id for f in kept] == ["f_a", "f_b", "p4", "p5"]
    assert cap_page_facts(tuple(base + page), keep=None) == tuple(base + page)
    ctx = replace(writer_context_ch4("s", ["minh"]), known_facts=tuple(base + page))
    assert len(cap_page_facts(ctx.known_facts, keep=3)) == 5


def test_config_ships_the_limits_and_requires_them_when_on():
    repo = load_config()
    f = repo.limits.facts
    assert f.max_new_per_chapter and f.text_max_chars and f.writer_max_page_facts
    assert 0 < f.duplicate_overlap <= 1 and 0 < f.grounded_min <= 1
    assert config_problems(repo) == []
    unset = f.model_copy(update={"text_max_chars": None})
    config = repo.model_copy(update={"limits": repo.limits.model_copy(update={"facts": unset})})
    assert [p.code for p in config_problems(config)] == [ErrorCode.CONFIG_LIMIT_NOT_SET]
    off = unset.model_copy(update={"max_new_per_chapter": 0})
    config = repo.model_copy(update={"limits": repo.limits.model_copy(update={"facts": off})})
    assert config_problems(config) == []


class _FactsStore(MemoryStore):
    """Kho trả ngữ cảnh người viết có 5 Fact sinh từ trang (biết từ chương 1 tới 5)."""

    def writer_context(self, as_of_chapter, present_ids, plan, *, max_neighbors):
        ctx = super().writer_context(as_of_chapter, present_ids, plan, max_neighbors=max_neighbors)
        page = tuple(_fact(f"p{i}", i) for i in range(1, 6))
        return replace(ctx, known_facts=(*ctx.known_facts, *page))


async def test_the_writer_context_of_a_chapter_keeps_only_the_latest_page_facts(tmp_path):
    _, _, llm, _ = await run(script(extract_reply()), tmp_path, store=_FactsStore(),
                             limits={"facts": {"writer_max_page_facts": 2}})
    writers = calls_of(llm, "writer")
    assert writers  # chương chạy được tới bước viết
    for call in writers:
        text = call[-1].content
        assert "Điều p5" in text and "Điều p4" in text and "Điều p3" not in text
