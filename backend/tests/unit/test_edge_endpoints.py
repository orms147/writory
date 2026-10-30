"""Bảng đầu mút của cạnh: MỘT bảng cho khởi tạo và bộ trích (docs/graph-schema.md, mục Cạnh). Hồi quy từ
psab-b1: bộ trích ghi `HOLDS` từ nhân vật tới một Fact do chính nó tạo ở chương trước, ngữ cảnh viết đọc
tên của Fact (không có) rồi sập, truyện kẹt ở chương sau. Không mạng, không Neo4j."""

from writory.graph.package import EdgeSpec, NodeSpec
from writory.graph.sample import read_sample
from writory.graph.schema import EDGE_ENDPOINTS, EDGE_TYPES, NAMED_LABELS, endpoint_problem
from writory.pipeline.bench_run import reject_reason
from writory.pipeline.extract import (
    Entity,
    ExtractedEdge,
    ExtractOutput,
    OpenEdge,
    to_package,
)
from writory.pipeline.setup import _ENDPOINTS as SETUP_ENDPOINTS


def test_the_table_has_a_rule_for_every_edge_type_and_nothing_else():
    assert set(EDGE_ENDPOINTS) == set(EDGE_TYPES)


def test_endpoint_problem_follows_the_table_in_graph_schema_md():
    ok = [("HOLDS", "Character", "Item"), ("LOCATED_AT", "Item", "Location"),
          ("LOCATED_AT", "Character", "Location"), ("MEMBER_OF", "Character", "Faction"),
          ("RELATES_TO", "Character", "Character"), ("KNOWS", "Character", "Fact"),
          ("KNOWS", "Character", "Lie"), ("KNOWS", "Character", "Event"),
          ("KNOWS", "Character", "Location"),  # known_as (D-17), xem D-128
          ("ABOUT", "Fact", "Thread"), ("ABOUT", "Lie", "Character"),
          ("RESOLVED_IN", "Thread", "Chapter"), ("REVEALED_TO_PLAYER", "Location", "Chapter"),
          ("TOLD", "Character", "Lie"), ("TOLD_TO", "Lie", "Character"),
          ("FEELS", "Character", "Fact"), ("DIED_IN", "Character", "Event"),
          ("PARTICIPATED_IN", "Character", "Event")]
    for etype, source, target in ok:
        assert endpoint_problem(etype, source, target) is None, (etype, source, target)
    bad = [("HOLDS", "Character", "Fact"), ("HOLDS", "Item", "Item"),
           ("LOCATED_AT", "Character", "Character"), ("LOCATED_AT", "Fact", "Location"),
           ("MEMBER_OF", "Character", "Location"), ("RELATES_TO", "Character", "Faction"),
           ("KNOWS", "Character", "Thread"), ("KNOWS", "Fact", "Fact"),
           ("ABOUT", "Character", "Fact"), ("RESOLVED_IN", "Fact", "Chapter"),
           ("RESOLVED_IN", "Thread", "Fact"), ("REVEALED_TO_PLAYER", "Fact", "Fact"),
           ("TOLD", "Character", "Fact"), ("DIED_IN", "Character", "Location"),
           ("FEELS", "Fact", "Fact")]
    for etype, source, target in bad:
        assert endpoint_problem(etype, source, target), (etype, source, target)


def test_the_problem_text_names_the_edge_and_the_labels_but_no_node_text():
    text = endpoint_problem("HOLDS", "Character", "Fact")
    assert text and "HOLDS" in text and "Character" in text and "Fact" in text and "Item" in text


def test_setup_endpoints_are_the_shared_table_narrowed_for_chapter_0_never_wider():
    for etype, (sources, targets) in SETUP_ENDPOINTS.items():
        wide_sources, wide_targets = EDGE_ENDPOINTS[etype]
        assert wide_sources is None or sources <= wide_sources, etype
        assert wide_targets is None or targets <= wide_targets, etype
    # Bốn kiểu cạnh model được khai tự do ở chương 0 dùng đúng bảng chung, không hẹp hơn.
    for etype in ("RELATES_TO", "LOCATED_AT", "HOLDS", "MEMBER_OF"):
        assert SETUP_ENDPOINTS[etype] == EDGE_ENDPOINTS[etype]


def test_every_edge_of_the_sample_story_obeys_the_table():
    sample = read_sample()
    labels = {n.id: n.label for ch in sample.chapters for n in ch.package.nodes}
    wrong = [(e.type, e.source, e.target) for ch in sample.chapters for e in ch.package.edges
             if endpoint_problem(e.type, labels[e.source], labels[e.target])]
    assert wrong == []


# --- bộ trích: ca psab-b1 ---------------------------------------------------------------------------

TEXT = "Phụng Yên cầm tờ giấy mà Thảo đưa, và nhận ra đó là chữ viết của cha mình."


def entities() -> list[Entity]:
    return [
        Entity("protagonist", "Character", "Thảo", user_authored=True),
        Entity("phung_yen", "Character", "Phụng Yên"),
        Entity("to_giay", "Item", "Tờ giấy"),
        Entity("cang", "Location", "Bến cảng"),
        Entity("hoi", "Faction", "Hội Cầu"),
        Entity("fact_c10s1_1", "Fact", "Phụng Yên giấu tờ giấy dưới ván cầu"),  # Fact chương 10
        Entity("ch11", "Chapter", "chương 11"),
    ]


def edge(etype: str, source: str, target: str, **extra) -> ExtractedEdge:
    base = {"type": etype, "source": source, "target": target, "kind": None, "score": None,
            "how": None, "told_by": None, "quote": None, "known_as": None, "role": None}
    return ExtractedEdge.model_validate(base | extra)


def extract(*edges: ExtractedEdge, open_edges: list[OpenEdge] | None = None):
    output = ExtractOutput(edges=list(edges), close=[], new_facts=[], milestones=[])
    return to_package(output, chapter=11, commit_id="c11", protagonist_id="protagonist",
                      chapter_text=TEXT, entities=entities(), open_edges=open_edges or [])


def kinds(package) -> list[tuple[str, str, str]]:
    return [(e.type, e.source, e.target) for e in package.edges]


def test_holds_to_a_fact_made_in_an_earlier_chapter_is_rejected_not_written():
    package, rejected = extract(edge("HOLDS", "phung_yen", "fact_c10s1_1"))
    assert kinds(package) == []
    [(desc, why)] = rejected
    assert "HOLDS" in desc and why.startswith("đầu mút sai loại nút")


def test_a_valid_holds_is_still_written():
    package, rejected = extract(edge("HOLDS", "phung_yen", "to_giay"))
    assert ("HOLDS", "phung_yen", "to_giay") in kinds(package) and rejected == []


def test_every_wrong_endpoint_the_model_can_write_is_rejected_with_the_same_reason():
    wrong = [edge("LOCATED_AT", "phung_yen", "protagonist"), edge("MEMBER_OF", "phung_yen", "cang"),
             edge("RELATES_TO", "phung_yen", "hoi"), edge("KNOWS", "phung_yen", "ch11"),
             edge("ABOUT", "phung_yen", "to_giay"), edge("TOLD", "phung_yen", "fact_c10s1_1"),
             edge("RESOLVED_IN", "fact_c10s1_1", "ch11", quote="Phụng Yên cầm tờ giấy")]
    package, rejected = extract(*wrong)
    assert kinds(package) == [] or all(e.type in ("REVEALED_TO_PLAYER",) for e in package.edges)
    assert len(rejected) == len(wrong)
    assert all(why.startswith("đầu mút sai loại nút") for _, why in rejected)


def test_the_bench_groups_the_new_reason_under_its_own_name():
    assert reject_reason("đầu mút sai loại nút: HOLDS Character → Fact") == "đầu mút sai loại nút"


def test_a_package_the_model_could_not_make_is_not_the_only_defence():
    # Gói dựng tay (không qua bộ trích) vẫn có thể mang cạnh sai: bảng dùng chung nên kiểm ở đâu
    # cũng ra cùng kết quả.
    spec = EdgeSpec.model_validate({"type": "HOLDS", "from": "phung_yen", "to": "fact_c10s1_1",
                                    "valid_from_chapter": 11})
    node = NodeSpec(id="fact_c10s1_1", label="Fact", props={"text": "x"})
    assert endpoint_problem(spec.type, "Character", node.label)
    assert NAMED_LABELS >= {"Character", "Location", "Item", "Faction"}
