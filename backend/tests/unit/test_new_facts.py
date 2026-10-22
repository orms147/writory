"""Nút Fact mới do bộ trích tạo sau chương 0 (D-93): chỉ từ trang, có câu trích nguyên văn (G3), id do
code sinh, đã hé lộ cho người chơi, có trần mỗi chương, chống trùng với Fact đã có, chữ người chơi
bị đánh dấu `user_authored` (G4). Không tạo được bí mật: bí mật chỉ đến từ khởi tạo."""

import json

import pytest

from writory.llm.fake import FakeLLM
from writory.pipeline.extract import (
    SYSTEM_PROMPT,
    Entity,
    ExtractedEdge,
    ExtractOutput,
    FactRules,
    NewFact,
    extract_changes,
    to_package,
)

TEXT = ("Tôi nhìn Trần Mặc. Hắn nói: Cho ta mượn Thẻ Định Phong đến hết chuyến qua đá trôi. "
        "Tôi đáp: Ta cho ngươi mượn. Vân Chi kịp nắm lấy cánh tay ông lão bị vấp ở phiến thứ hai.")
Q_LOAN = "Cho ta mượn Thẻ Định Phong đến hết chuyến qua đá trôi."
Q_RESCUE = "Vân Chi kịp nắm lấy cánh tay ông lão bị vấp ở phiến thứ hai."
ENTITIES = [
    Entity("protagonist", "Character", "Phó Cảnh Hành", user_authored=True),
    Entity("tran_mac", "Character", "Trần Mặc"),
    Entity("tao_van_chi", "Character", "Tào Vân Chi", ("Vân Chi",)),
    Entity("thep_dinh_phong", "Item", "Thẻ Định Phong"),
    Entity("ch4", "Chapter", "Chương 4"),
    Entity("fact_old", "Fact", "Thẻ Định Phong chỉ lối qua những luồng khí ở vùng đá trôi"),
]
RULES = FactRules(max_new=3, max_chars=160, scene=1, duplicate_overlap=0.7, grounded_min=0.6)


def edge(**kw) -> ExtractedEdge:
    base = {"kind": None, "score": None, "how": None, "told_by": None, "quote": None,
            "known_as": None, "role": None}
    return ExtractedEdge(**(base | kw))


def about(ref, target):
    return edge(type="ABOUT", source=ref, target=target)


def knows(who, ref, quote=None, how="chứng kiến"):
    return edge(type="KNOWS", source=who, target=ref, how=how, quote=quote)


def loan(ref="new_1", text="Trần Mặc mượn Thẻ Định Phong đến hết chuyến qua đá trôi", quote=Q_LOAN):
    return NewFact(ref=ref, text=text, quote=quote)


def good_edges(ref="new_1"):
    return [about(ref, "tran_mac"), about(ref, "thep_dinh_phong"), knows("protagonist", ref, Q_LOAN)]


def run(new_facts, edges, *, rules=RULES, entities=ENTITIES, text=TEXT, open_edges=()):
    out = ExtractOutput(edges=edges, close=[], new_facts=new_facts)
    return to_package(out, chapter=4, commit_id="c", protagonist_id="protagonist",
                      chapter_text=text, entities=entities, open_edges=list(open_edges),
                      fact_rules=rules)


def reasons(rejected) -> str:
    return " | ".join(r for _, r in rejected)


def test_a_new_fact_becomes_a_node_with_about_knows_and_a_reveal():
    pkg, rejected = run([loan()], good_edges())
    assert rejected == []
    [node] = pkg.nodes
    assert node.id == "fact_c4s1_1" and node.label == "Fact"
    assert node.props["text"] == "Trần Mặc mượn Thẻ Định Phong đến hết chuyến qua đá trôi"
    by_id = {e.id: e for e in pkg.edges}
    assert set(by_id) == {
        "ABOUT:fact_c4s1_1>tran_mac@4", "ABOUT:fact_c4s1_1>thep_dinh_phong@4",
        "KNOWS:protagonist>fact_c4s1_1@4", "REVEALED_TO_PLAYER:fact_c4s1_1>ch4@4"}
    assert by_id["REVEALED_TO_PLAYER:fact_c4s1_1>ch4@4"].props["quote"] == Q_LOAN


def test_the_model_never_picks_the_id():
    """`ref` chỉ là nhãn tạm dạng new_<số>; model đặt ref trùng id có sẵn thì Fact bị bỏ."""
    pkg, rejected = run([loan(ref="fact_old")], good_edges("fact_old"))
    assert pkg.nodes == [] and "ref" in reasons(rejected)


def test_quote_must_be_verbatim_in_the_scene():
    """G3: Fact mới không có câu trích thật trên trang thì không tồn tại, kéo theo các cạnh của nó."""
    pkg, rejected = run([loan(quote="Hắn đòi cả thanh kiếm của tôi.")], good_edges())
    assert pkg.nodes == [] and pkg.edges == []
    assert "câu trích" in reasons(rejected) and "G3" in reasons(rejected)


def test_a_fact_needs_an_about_and_a_knows():
    pkg, rejected = run([loan()], [knows("protagonist", "new_1", Q_LOAN)])
    assert pkg.nodes == [] and pkg.edges == [] and "ABOUT" in reasons(rejected)
    pkg, rejected = run([loan()], [about("new_1", "tran_mac")])
    assert pkg.nodes == [] and pkg.edges == [] and "KNOWS" in reasons(rejected)


def test_the_protagonist_knowing_a_new_fact_still_needs_the_quote():
    pkg, rejected = run([loan()], [about("new_1", "tran_mac"), knows("protagonist", "new_1")])
    assert pkg.nodes == [] and "câu trích" in reasons(rejected)
    # Người khác biết thì không cần câu trích riêng.
    pkg, _ = run([loan()], [about("new_1", "tran_mac"), knows("tran_mac", "new_1")])
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]


@pytest.mark.parametrize("text", [
    "x" * 161,  # quá dài
    "ngắn",  # quá ngắn
    "Trần Mặc mượn\nThẻ Định Phong",  # nhiều dòng
    "",
])
def test_text_must_be_one_short_line(text):
    pkg, rejected = run([loan(text=text)], good_edges())
    assert pkg.nodes == [] and pkg.edges == [] and rejected


def test_text_must_come_from_the_page():
    """Không thêm điều trang chưa nói: chữ Fact phải phần lớn nằm trên trang."""
    pkg, rejected = run([loan(text="Hội Hắc Kỳ ngầm cài gián điệp vào đoàn thương nhân miền biên")],
                        good_edges())
    assert pkg.nodes == [] and "trang" in reasons(rejected)


def test_cap_per_chapter_drops_the_extras_and_their_edges():
    facts = [loan(), NewFact(ref="new_2", text="Vân Chi nắm lấy cánh tay ông lão bị vấp",
                             quote=Q_RESCUE)]
    edges = [*good_edges(), about("new_2", "tao_van_chi"), knows("protagonist", "new_2", Q_RESCUE)]
    pkg, rejected = run(facts, edges, rules=FactRules(1, 160, 1, 0.7, 0.6))
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]
    assert not any("new_2" in e.source or "new_2" in e.target for e in pkg.edges)
    assert "trần" in reasons(rejected)


def test_zero_cap_or_no_rules_means_the_feature_is_off():
    for rules in (None, FactRules(0, 160, 1, 0.7, 0.6)):
        pkg, rejected = run([loan()], good_edges(), rules=rules)
        assert pkg.nodes == [] and pkg.edges == [] and rejected


def test_duplicate_of_an_existing_fact_is_remapped_not_created():
    """Trùng Fact đã có: không tạo nút, KNOWS chuyển sang Fact cũ, ABOUT bỏ (Fact cũ có ABOUT riêng)."""
    dup = NewFact(ref="new_1", text="Thẻ Định Phong chỉ lối qua những luồng khí ở vùng đá trôi",
                  quote="Cho ta mượn Thẻ Định Phong đến hết chuyến qua đá trôi.")
    pkg, rejected = run([dup], [about("new_1", "thep_dinh_phong"),
                                knows("protagonist", "new_1", Q_LOAN)])
    assert pkg.nodes == []
    assert [e.id for e in pkg.edges] == ["KNOWS:protagonist>fact_old@4"]
    assert "trùng" in reasons(rejected)


def test_two_new_facts_that_say_the_same_thing_become_one():
    a = loan()
    b = NewFact(ref="new_2", text="Trần Mặc mượn Thẻ Định Phong đến hết chuyến qua đá trôi.",
                quote=Q_LOAN)
    pkg, _ = run([a, b], [*good_edges(), knows("tran_mac", "new_2")])
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]
    assert "KNOWS:tran_mac>fact_c4s1_1@4" in {e.id for e in pkg.edges}


def test_text_that_copies_player_words_is_marked_user_authored():
    """G4: Fact chép tên người chơi viết thì mang `user_authored` để vào đề và sổ tay qua khối dữ liệu."""
    text = "Phó Cảnh Hành cho Trần Mặc mượn Thẻ Định Phong đến hết chuyến qua đá trôi"
    ents = [*ENTITIES]
    text_page = TEXT + " Phó Cảnh Hành gật đầu."
    pkg, _ = run([loan(text=text)], good_edges(), entities=ents, text=text_page)
    assert pkg.nodes[0].props["user_authored"] is True
    pkg, _ = run([loan()], good_edges())
    assert "user_authored" not in pkg.nodes[0].props or pkg.nodes[0].props["user_authored"] is False


def test_edges_to_an_unknown_ref_are_rejected():
    pkg, rejected = run([], [about("new_9", "tran_mac")])
    assert pkg.edges == [] and "id không có trong danh mục" in reasons(rejected)


def test_ids_do_not_collide_with_existing_nodes():
    ents = [*ENTITIES, Entity("fact_c4s1_1", "Fact", "Một điều hoàn toàn khác về Hội Lưu Dân")]
    pkg, _ = run([loan()], good_edges(), entities=ents)
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_2"]


def test_new_facts_cannot_be_secrets_or_hidden_entities():
    """ABOUT/KNOWS chỉ trỏ tới thực thể trong danh mục; một ref không thể làm đích REVEALED_TO_PLAYER hay
    RESOLVED_IN do model ghi (đường duy nhất để hé lộ là cạnh tự thêm kèm câu trích của Fact)."""
    sneaky = edge(type="RESOLVED_IN", source="new_1", target="ch4", quote=Q_LOAN)
    pkg, rejected = run([loan()], [*good_edges(), sneaky])
    assert "RESOLVED_IN" not in {e.type for e in pkg.edges}
    assert rejected


async def test_extract_changes_passes_the_rules_and_the_prompt_mentions_new_facts():
    reply = json.dumps({"edges": [e.model_dump() for e in good_edges()], "close": [],
                        "new_facts": [loan().model_dump()]}, ensure_ascii=False)
    result = await extract_changes(
        FakeLLM.scripted([reply]), "m", chapter=4, chapter_id="ch4", commit_id="c",
        protagonist_id="protagonist", chapter_text=TEXT, entities=ENTITIES, open_edges=[],
        fact_rules=RULES)
    assert [n.id for n in result.package.nodes] == ["fact_c4s1_1"]


def test_prompt_explains_new_facts():
    for phrase in ("new_facts", "ref", "ABOUT", "KNOWS", "tối đa", "REVEALED_TO_PLAYER"):
        assert phrase in SYSTEM_PROMPT, phrase


def test_output_without_new_facts_still_parses():
    """Trả lời cũ (chưa có trường này) vẫn hợp lệ: trường bắt buộc trong schema gửi model, nhưng parse
    chịu thiếu để fixture và model cũ không hỏng."""
    out = ExtractOutput.model_validate_json('{"edges": [], "close": []}')
    assert out.new_facts == []

