"""Đề bài A trên truyện dài 24 chương do pipeline viết (`questions-long-ky-ao-2.yaml`; D-83): đề khoá theo
hash, mọi câu qua cùng bộ kiểm với đề truyện vừa (câu trích có trên trang, `graph_agrees` khớp đồ thị bộ
trích), oracle chấm đúng, và đề nghiêng về câu cần trí nhớ dài. Không mạng, không Neo4j."""

import asyncio
from collections import Counter

import pytest

from writory.config import load_config
from writory.pipeline.bench_a import RESULTS, RunOptions, run_bench
from writory.pipeline.bench_a_data import (
    DATA_DIR,
    check_question,
    derive,
    distance_bin,
    load_data,
    oracle_answer,
    score_answer,
    wrong_answer,
)
from writory.quality.bench_d import Store

QUESTIONS_FILE = "questions-long-ky-ao-2.yaml"
LONG = load_data(questions_file=QUESTIONS_FILE)
QS = LONG.questions.questions
NAMES = LONG.state_at(24).named_nodes()


def test_long_story_reads_all_24_chapters_and_pins_every_file():
    assert LONG.source == "evals/results/2026-10-29-run-long-after-ky-ao-2"
    assert LONG.chapters == tuple(range(1, 25))
    files = {"truth_dump.json", *(f"chapters/ch{n:02d}.md" for n in range(1, 25))}
    assert set(LONG.questions.run_sha256) == files
    assert LONG.state_at(24).protagonist_id() == "protagonist"


@pytest.mark.parametrize("question", QS, ids=[x.id for x in QS])
def test_every_question_checks_out_against_the_page_and_the_graph(question):
    assert check_question(question, LONG) == []


@pytest.mark.parametrize("question", QS, ids=[x.id for x in QS])
def test_oracle_answer_scores_correct_and_wrong_answer_does_not(question):
    assert score_answer(question, oracle_answer(question, NAMES), NAMES)["correct"] is True
    assert score_answer(question, wrong_answer(question, NAMES), NAMES)["correct"] is False


def test_question_set_is_approved_by_the_owner():
    """Như D-72: chủ dự án duyệt đáp án trước lần chạy thật (31/10/2026)."""
    assert LONG.questions.status == "CHỦ DỰ ÁN DUYỆT 31/10/2026"
    header = (DATA_DIR / QUESTIONS_FILE).read_text(encoding="utf-8").splitlines()[:8]
    assert any(line.startswith("# TRẠNG THÁI: CHỦ DỰ ÁN DUYỆT 31/10/2026") for line in header)


def test_question_set_leans_on_long_distances():
    assert 40 <= len(QS) <= 50
    by_group = Counter(x.group for x in QS)
    assert set(by_group) == {"item", "alive", "knows", "relation", "lie"}
    assert all(n >= 5 for n in by_group.values())
    assert set(Counter(distance_bin(x.distance) for x in QS)) == {"0", "1-2", "3+"}
    assert sum(x.distance >= 10 for x in QS) * 2 > len(QS)
    assert sum(x.distance >= 5 for x in QS) * 4 >= len(QS) * 3
    assert {x.answer.type for x in QS} == {"entities", "bool", "choice", "text"}
    assert any(x.inference for x in QS)
    assert any(x.graph_agrees for x in QS) and any(not x.graph_agrees for x in QS)


def test_each_secret_is_asked_before_and_after_its_reveal_on_the_page():
    """Ba bí mật lộ trên trang ở chương 7, 11, 16; đồ thị ghi KNOWS của nhân vật chính đúng các chương đó."""
    def asked(fact: str) -> dict:
        return {(x.answer.type, x.state_chapter): x.answer.gold for x in QS
                if (x.derive or {}).get("to") == fact and (x.derive or {}).get("from") == "protagonist"}

    assert asked("dinh_loc_giau_loi_di") == {("bool", 6): False, ("choice", 24): "chương 7"}
    assert asked("loi_di_la_duong_cuu") == {("bool", 10): False, ("choice", 24): "chương 11"}
    assert asked("khuong_dieu_phoi_vu_bat") == {
        ("bool", 15): False, ("choice", 24): "chương 16", ("entities", 24): ["ta_van"]}


def test_extracted_graph_records_the_map_coming_back_at_24_only_as_close_and_reopen():
    """Nền của item-05/06: ném bản đồ sang Tạ Vân rồi nhận lại ở ch24 không để lại HOLDS nào của Tạ Vân."""
    holds = LONG.state_at(24).edges_at("HOLDS", 24, target_id="ban_do_nep_gap", ever=True)
    assert {(e.source, e.valid_from_chapter, e.valid_to_chapter) for e in holds} == {
        ("protagonist", 0, 2), ("ta_van", 2, 22), ("protagonist", 22, 24), ("protagonist", 24, None)}
    spec = {"op": "edge_since", "type": "HOLDS", "from": "protagonist", "to": "ban_do_nep_gap"}
    assert derive(spec, LONG.state_at(23), 23) == "chương 22"
    assert derive(spec, LONG.state_at(24), 24) == "chương 24"


def test_full_story_oracle_answers_every_question(tmp_path):
    """Trên truyện do pipeline viết chỉ hệ `full` chắc 100% (docs/eval.md): mọi câu trả lời được từ trang."""
    opts = RunOptions(out=tmp_path / "out", dry_run=True, samples=1, systems=["full"])
    assert asyncio.run(run_bench(LONG, opts, config=load_config(), log=lambda _: None)) == 0
    rows = Store(opts.out).rows(RESULTS)
    assert len(rows) == len(QS) and all(r["correct"] for r in rows)
