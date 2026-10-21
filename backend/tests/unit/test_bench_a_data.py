"""Bài đo A (bộ nhớ), phần đề và bộ chấm (D-72). Không mạng, không Neo4j: đồ thị truyện mẫu ở
chương N dựng bằng OverlayState từ các gói dựng tay."""

import shutil
from collections import Counter
from pathlib import Path

import pytest
import yaml

from writory.config import ConfigError
from writory.pipeline.bench_a_data import (
    DATA_DIR,
    DISTANCE_BINS,
    GROUPS,
    check_question,
    derive,
    distance_bin,
    is_abstain,
    load_data,
    null_answer,
    oracle_answer,
    parse_bool,
    parse_choice,
    score_answer,
    wrong_answer,
)

DATA = load_data()
QUESTIONS = DATA.questions.questions
NAMES = DATA.state_at(5).named_nodes()


def question(qid: str):
    return DATA.question(qid)


# --- đề ----------------------------------------------------------------------------------------


def test_every_group_has_questions_at_several_distances():
    by_group = Counter(q.group for q in QUESTIONS)
    assert set(by_group) == set(GROUPS)
    assert all(n >= 5 for n in by_group.values())
    for group in GROUPS:
        bins = {distance_bin(q.distance) for q in QUESTIONS if q.group == group}
        assert len(bins) >= 2, group
    assert {distance_bin(q.distance) for q in QUESTIONS} == set(DISTANCE_BINS)


def test_question_set_is_marked_approved_by_the_owner():
    assert "CHỦ DỰ ÁN DUYỆT" in DATA.questions.status and "CHỜ" not in DATA.questions.status
    header = (DATA_DIR / "questions.yaml").read_text(encoding="utf-8").splitlines()[:6]
    assert any("CHỦ DỰ ÁN DUYỆT 21/10/2026" in line for line in header)


def test_relation_questions_ask_from_minhs_side_and_knows_06_is_inference():
    """Chủ dự án duyệt 21/10/2026: câu quan hệ hỏi theo chiều của Minh (Lan coi Minh là "con mồi" ở
    lớp sự thật, ngoài bốn lựa chọn); knows-06 cần nối thư ký tên với gã lái đò nên tách riêng."""
    rel = [q for q in QUESTIONS if q.derive.get("op") == "relation_kind"]
    assert rel and all("Minh coi Lan là gì?" in q.question for q in rel)
    assert {q.id for q in QUESTIONS if q.inference} == {"knows-06"}


def test_all_answer_types_are_used():
    assert {q.answer.type for q in QUESTIONS} == {"entities", "bool", "choice", "text"}


@pytest.mark.parametrize("q", QUESTIONS, ids=[q.id for q in QUESTIONS])
def test_gold_matches_graph_and_evidence_is_on_the_page(q):
    assert check_question(q, DATA) == []


def test_every_question_can_be_answered_from_the_pages_alone():
    """Câu trích bằng chứng nằm trong chương <= ask_chapter, và ask_chapter là chương cuối hệ trả lời
    được đọc: không câu nào cần điều chỉ có ở lớp sự thật."""
    for q in QUESTIONS:
        assert q.evidence and all(ev.chapter <= q.ask_chapter for ev in q.evidence), q.id


def test_bad_gold_is_caught_against_the_graph():
    bad = question("item-05").model_copy(update={
        "answer": question("item-05").answer.model_copy(update={"gold": ["lan"]})})
    assert any("khác đồ thị" in p for p in check_question(bad, DATA))


def test_invented_quote_is_caught():
    q = question("item-05")
    ev = q.evidence[0].model_copy(update={"quote": "Lan giấu thanh kiếm dưới giường Minh."})
    bad = q.model_copy(update={"evidence": (ev,)})
    assert any("không có nguyên văn" in p for p in check_question(bad, DATA))


def test_quote_from_a_later_chapter_is_caught():
    q = question("item-02")  # hỏi ở chương 2
    ev = q.evidence[0].model_copy(update={"chapter": 5})
    bad = q.model_copy(update={"evidence": (ev,)})
    assert any("sau ask_chapter" in p for p in check_question(bad, DATA))


def test_as_of_after_ask_chapter_is_rejected():
    q = question("item-02")
    with pytest.raises(ValueError, match="as_of"):
        type(q).model_validate({**q.model_dump(), "as_of": 4})


def test_load_data_reports_bad_question_file(tmp_path: Path):
    shutil.copytree(DATA_DIR, tmp_path / "memory")
    path = tmp_path / "memory" / "questions.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["questions"][0]["answer"]["gold"] = ["lan"]
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="item-01"):
        load_data(tmp_path / "memory")


def test_duplicate_ids_are_rejected(tmp_path: Path):
    shutil.copytree(DATA_DIR, tmp_path / "memory")
    path = tmp_path / "memory" / "questions.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    raw["questions"].append(raw["questions"][0])
    path.write_text(yaml.safe_dump(raw, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="trùng"):
        load_data(tmp_path / "memory")


def test_graph_state_follows_the_chapter_cut():
    """Cạnh đóng ở chương sau không được hiện ở chương trước: nền của mọi câu hỏi."""
    holders = {n: derive({"op": "holders", "item": "sword"}, DATA.state_at(n), n)
               for n in range(1, 6)}
    assert holders == {1: ["gu"], 2: ["minh"], 3: ["minh"], 4: ["lan"], 5: ["minh"]}


# --- bộ chấm ------------------------------------------------------------------------------------


@pytest.mark.parametrize("q", QUESTIONS, ids=[q.id for q in QUESTIONS])
def test_oracle_answer_scores_correct_and_wrong_answer_scores_wrong(q):
    assert score_answer(q, oracle_answer(q, NAMES), NAMES)["correct"] is True
    verdict = score_answer(q, wrong_answer(q, NAMES), NAMES)
    assert verdict["correct"] is False and verdict["abstained"] is False
    null = score_answer(q, null_answer(q), NAMES)
    assert null == {"correct": False, "abstained": True, "parsed": None}


def test_entity_answer_must_match_the_set_exactly():
    q = question("item-08")  # {Thanh Sương, thư niêm sáp đỏ, thư Hội Hắc Kỳ}
    full = "Thanh Sương, lá thư niêm sáp đỏ của Lão Gù và xấp thư của Hội Hắc Kỳ"
    assert score_answer(q, full, NAMES)["correct"] is True
    assert score_answer(q, "Thanh Sương và lá thư niêm sáp đỏ", NAMES)["correct"] is False
    # thừa một thực thể (Lan) cũng sai
    assert score_answer(q, full + ", và Lan", NAMES)["correct"] is False


def test_entity_named_in_the_question_is_not_an_extra():
    q = question("item-08")  # câu hỏi nêu Minh; "Minh giữ Thanh Sương..." không bị trừ
    answer = "Minh giữ Thanh Sương, lá thư niêm sáp đỏ và thư của Hội Hắc Kỳ"
    assert score_answer(q, answer, NAMES)["correct"] is True


def test_entity_alias_resolves_to_longest_name_not_a_part():
    # "Lan" nằm trong "Phạm Thị Lan": cả hai chỉ một người; "Hội Hắc Kỳ" không bị tách ra
    q = question("lie-02")
    assert score_answer(q, "Phạm Thị Lan", NAMES)["correct"] is True
    assert score_answer(q, "cô Lan", NAMES)["correct"] is True


def test_minh_the_pronoun_is_not_minh_the_character():
    """Không bỏ dấu khi so tên: "mình" (đại từ) không phải "Minh"."""
    q = question("item-01")  # đáp án: Lão Gù
    assert score_answer(q, "Lão Gù tự giữ lấy mình", NAMES)["correct"] is True


@pytest.mark.parametrize(("text", "expected"), [
    ("Có", True), ("có.", True), ("Có, Minh đã biết", True), ("Đúng", True),
    ("Không", False), ("Không, Minh chưa biết", False), ("Chưa", False),
    ("Minh có biết", None), ("", None),
])
def test_parse_bool(text, expected):
    assert parse_bool(text) is expected


@pytest.mark.parametrize("text", [
    "Không biết", "không rõ", "Không đủ thông tin để trả lời", "Chưa rõ", "", "  ",
    "Không thể xác định từ đoạn văn",
])
def test_abstentions(text):
    assert is_abstain(text)


def test_no_alone_is_not_an_abstention():
    assert not is_abstain("Không")
    assert not is_abstain("Không, Lan chưa biết")


def test_choice_needs_exactly_one_option():
    options = ["người quen", "bạn", "yêu", "thù"]
    assert parse_choice("yêu", options) == "yêu"
    assert parse_choice("Họ đang yêu nhau", options) == "yêu"
    assert parse_choice("bạn bè", options) == "bạn"
    assert parse_choice("bạn hoặc yêu", options) is None
    assert parse_choice("không rõ", options) is None
    assert parse_choice("người quen", options) == "người quen"


def test_text_answer_needs_every_keyword_group():
    q = question("lie-03")
    assert score_answer(q, "Rằng đêm đó anh ở nhà", NAMES)["correct"] is True
    assert score_answer(q, "Rằng anh đã ra phố", NAMES)["correct"] is False


def test_abstaining_is_never_correct_even_for_a_false_answer():
    q = question("item-04")  # đáp án gốc: Không
    assert score_answer(q, "Không", NAMES)["correct"] is True
    assert score_answer(q, "Không biết", NAMES) == {
        "correct": False, "abstained": True, "parsed": None}


def test_distance_bins():
    assert [distance_bin(d) for d in (0, 1, 2, 3, 4)] == ["0", "1-2", "1-2", "3+", "3+"]
