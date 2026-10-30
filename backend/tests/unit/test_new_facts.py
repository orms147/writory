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
    OpenEdge,
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
        fact_rules=RULES, locked=())
    assert [n.id for n in result.package.nodes] == ["fact_c4s1_1"]


def test_prompt_explains_new_facts():
    for phrase in ("new_facts", "ref", "ABOUT", "KNOWS", "tối đa", "REVEALED_TO_PLAYER"):
        assert phrase in SYSTEM_PROMPT, phrase


def test_output_without_new_facts_still_parses():
    """Trả lời cũ (chưa có trường này) vẫn hợp lệ: trường bắt buộc trong schema gửi model, nhưng parse
    chịu thiếu để fixture và model cũ không hỏng."""
    out = ExtractOutput.model_validate_json('{"edges": [], "close": []}')
    assert out.new_facts == []



def test_orphan_facts_are_the_new_facts_no_knows_edge_points_to():
    from writory.graph import ChangePackage, EdgeSpec, NodeSpec
    from writory.pipeline.extract import orphan_facts

    def e(kind, a, b):
        return EdgeSpec.model_validate({"type": kind, "from": a, "to": b, "valid_from_chapter": 4})

    nodes = [NodeSpec(id=i, label="Fact", props={"text": f"Điều {i} trên trang"})
             for i in ("fact_c4s1_1", "fact_c4s1_2", "fact_c4s1_3")]
    pkg = ChangePackage(commit_id="c", nodes=nodes, edges=[
        e("KNOWS", "protagonist", "fact_c4s1_1"),
        e("ABOUT", "fact_c4s1_2", "tran_mac"),  # ABOUT đi ra khỏi Fact, không tính là có người biết
        e("ABOUT", "fact_c4s1_1", "fact_c4s1_3")])  # cạnh khác kiểu trỏ tới Fact cũng không tính
    assert orphan_facts(pkg) == {"fact_c4s1_2", "fact_c4s1_3"}


# --- chống trùng chặt hơn (D-95): cùng việc về cùng thực thể, kể cả bí mật đã lộ ------------------------

OLD_TEXT = "Lưu Tố Nguyệt đã bí mật đưa một số người sống sót khỏi khu chợ trước khi các tiên môn tới"
PAGE = "Lưu Tố Nguyệt đưa người sống sót khỏi khu chợ. Tôi nhìn dấu chân trên nền chợ."
RESTATE = "Lưu Tố Nguyệt đưa người sống sót khỏi khu chợ"
RESTATE_QUOTE = "Lưu Tố Nguyệt đưa người sống sót khỏi khu chợ."
RULES95 = FactRules(max_new=3, max_chars=160, scene=1, duplicate_overlap=0.7, grounded_min=0.6,
                    related_overlap=0.65)
ENTS95 = [
    Entity("protagonist", "Character", "Phó Cảnh Hành", user_authored=True),
    Entity("luu_tu_nguyet", "Character", "Lưu Tố Nguyệt"),
    Entity("tran_mac", "Character", "Trần Mặc"),
    Entity("ch4", "Chapter", "Chương 4"),
    Entity("fact_nguyet", "Fact", OLD_TEXT),
]
ABOUT_OLD = OpenEdge("a1", "ABOUT", "fact_nguyet", "luu_tu_nguyet")


def run95(facts, edges, *, entities=ENTS95, open_edges=(ABOUT_OLD,), text=PAGE):
    out = ExtractOutput(edges=edges, close=[], new_facts=facts)
    return to_package(out, chapter=4, commit_id="c", protagonist_id="protagonist",
                      chapter_text=text, entities=entities, open_edges=list(open_edges),
                      fact_rules=RULES95)


def restated(about_target):
    fact = NewFact(ref="new_1", text=RESTATE, quote=RESTATE_QUOTE)
    return [fact], [about("new_1", about_target), knows("protagonist", "new_1", RESTATE_QUOTE)]


def test_a_restatement_of_an_existing_fact_about_the_same_entity_is_a_duplicate():
    """Hồi quy D-93: "Những người dự đấu giá được đưa khỏi khu chợ…" nói lại bí mật đã lộ về Lưu Tố
    Nguyệt mà Jaccard (dưới 0,7) không bắt. Cùng việc (hệ số trùng cao) về cùng thực thể thì là một."""
    facts, edges = restated("luu_tu_nguyet")
    pkg, rejected = run95(facts, edges)
    assert pkg.nodes == [] and "KNOWS:protagonist>fact_nguyet@4" in {e.id for e in pkg.edges}
    assert "trùng Fact fact_nguyet" in reasons(rejected)


def test_the_same_words_about_another_entity_is_not_a_duplicate():
    """Chỉ trùng chữ mà nói về thực thể khác thì là chuyện khác (hai Fact dùng chung vài từ)."""
    facts, edges = restated("tran_mac")
    pkg, _ = run95(facts, edges)
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]


def test_low_overlap_about_the_same_entity_is_not_a_duplicate():
    other = NewFact(ref="new_1", text="Lưu Tố Nguyệt giữ một chiếc đèn lưu quang bên mình",
                    quote="Lưu Tố Nguyệt giữ một chiếc đèn lưu quang bên mình.")
    page = PAGE + " Lưu Tố Nguyệt giữ một chiếc đèn lưu quang bên mình."
    edges = [about("new_1", "luu_tu_nguyet"), knows("protagonist", "new_1", other.quote)]
    pkg, _ = run95([other], edges, text=page)
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]


def test_two_new_facts_restating_each_other_about_the_same_entity_become_one():
    ents = [e for e in ENTS95 if e.id != "fact_nguyet"]
    a = NewFact(ref="new_1", text=RESTATE, quote=RESTATE_QUOTE)
    b = NewFact(ref="new_2", text="Lưu Tố Nguyệt đưa người sống sót khỏi khu chợ trước các tiên môn",
                quote=RESTATE_QUOTE)
    edges = [about("new_1", "luu_tu_nguyet"), knows("protagonist", "new_1", RESTATE_QUOTE),
             about("new_2", "luu_tu_nguyet"), knows("tran_mac", "new_2")]
    pkg, _ = run95([a, b], edges, entities=ents, open_edges=[])
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]
    assert "KNOWS:tran_mac>fact_c4s1_1@4" in {e.id for e in pkg.edges}


def test_the_prompt_keeps_new_facts_to_what_happened_with_examples_both_ways():
    from writory.pipeline.extract import PROMPT_VERSION
    assert PROMPT_VERSION == "extract-11"
    for phrase in ("KHÔNG ghi", "ý định", "quyết định", "cảm nghĩ", "Ví dụ ĐÚNG", "Ví dụ SAI",
                   "dù diễn đạt khác"):
        assert phrase in SYSTEM_PROMPT, phrase


def test_a_short_fact_wholly_inside_a_longer_one_about_the_same_entity_is_a_duplicate():
    """Hệ số trùng tính trên Fact mới: câu ngắn nằm trọn trong câu dài là bản nói lại."""
    short = NewFact(ref="new_1", text="Lưu Tố Nguyệt đưa người sống sót",
                    quote="Lưu Tố Nguyệt đưa người sống sót khỏi khu chợ.")
    edges = [about("new_1", "luu_tu_nguyet"),
             knows("protagonist", "new_1", "Lưu Tố Nguyệt đưa người sống sót khỏi khu chợ.")]
    pkg, _ = run95([short], edges)
    assert pkg.nodes == [] and "KNOWS:protagonist>fact_nguyet@4" in {e.id for e in pkg.edges}


def test_a_more_specific_fact_that_contains_the_old_one_is_not_a_duplicate():
    """Replay D-95: "Trần Mặc đổi dấu vết lấy lời hứa… không bị lục xét hay bắt khai" chứa trọn
    "Trần Mặc bán tin cho Huyền Kính" nhưng thêm chính điều câu hỏi cần (điều khoản). Hệ số trùng tính
    trên Fact MỚI (phần nằm trong Fact cũ), nên Fact cụ thể hơn được giữ."""
    new_text = OLD_TEXT + ", Hội Lưu Dân canh lối kín sau dãy lều suốt đêm"  # chứa trọn Fact cũ
    page = PAGE + " " + new_text + "."
    fact = NewFact(ref="new_1", text=new_text, quote=new_text + ".")
    edges = [about("new_1", "luu_tu_nguyet"), knows("protagonist", "new_1", new_text + ".")]
    pkg, _ = run95([fact], edges, text=page)
    assert [n.id for n in pkg.nodes] == ["fact_c4s1_1"]


def test_knows_already_open_is_not_written_again_when_a_duplicate_is_remapped():
    """Replay D-95: dùng lại id Fact cũ cho bản nói lại sinh KNOWS thứ hai cùng cặp; đồ thị có hai cạnh
    KNOWS đang hiệu lực giữa cùng hai nút làm truy vấn một-cạnh (`derive`) hỏng."""
    facts, edges = restated("luu_tu_nguyet")
    open_knows = OpenEdge("k1", "KNOWS", "protagonist", "fact_nguyet")
    pkg, rejected = run95(facts, edges, open_edges=(ABOUT_OLD, open_knows))
    assert pkg.nodes == [] and pkg.edges == []
    assert "đã có KNOWS" in reasons(rejected)


def test_the_internal_protagonist_id_never_reaches_the_fact_text():
    """Replay D-95 bản cuối: model chép id nội bộ vào chữ Fact ("Protagonist kéo một đứa trẻ…"), sổ tay
    sẽ hiện chữ tiếng Anh. Code đổi id đó thành "nhân vật chính" (chỉ khi id không phải một phần tên)."""
    text = "Protagonist mượn Thẻ Định Phong đến hết chuyến qua đá trôi, theo lời Trần Mặc"
    page = TEXT + " Tôi mượn Thẻ Định Phong đến hết chuyến qua đá trôi, theo lời Trần Mặc."
    pkg, _ = run([loan(text=text, quote=Q_LOAN)], good_edges(), text=page)
    assert pkg.nodes[0].props["text"].startswith("Nhân vật chính mượn Thẻ Định Phong")
    assert "rotagonist" not in pkg.nodes[0].props["text"]


def test_an_id_that_is_part_of_the_protagonists_name_is_left_alone():
    """Truyện mẫu dùng id `minh` cho nhân vật tên Minh: đó là tên thật, không đổi."""
    ents = [Entity("minh", "Character", "Trần Minh", user_authored=True),
            Entity("tran_mac", "Character", "Trần Mặc"),
            Entity("thep_dinh_phong", "Item", "Thẻ Định Phong"), Entity("ch4", "Chapter", "Chương 4")]
    text = "Minh mượn Thẻ Định Phong đến hết chuyến qua đá trôi cho Trần Mặc"
    edges = [about("new_1", "tran_mac"), knows("minh", "new_1", Q_LOAN)]
    out = ExtractOutput(edges=edges, close=[], new_facts=[loan(text=text, quote=Q_LOAN)])
    pkg, _ = to_package(out, chapter=4, commit_id="c", protagonist_id="minh", chapter_text=TEXT,
                        entities=ents, open_edges=[], fact_rules=RULES)
    assert pkg.nodes[0].props["text"].startswith("Minh mượn")
