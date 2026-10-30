"""D-99: ba cách trình bày khác của khối đồ thị trong ngữ cảnh bài A (`style`), để đo A/B. Cùng sự
thật, cùng khoá `facts`, chỉ khác chữ và thứ tự dòng. Không mạng, không model."""

import asyncio
import re
from pathlib import Path

import pytest

from writory.config import ConfigError, load_config
from writory.pipeline import bench_a_systems as systems
from writory.pipeline.bench_a import (
    ContextBuilder,
    RunOptions,
    check_options,
    main,
    run_bench,
)
from writory.pipeline.bench_a_data import load_data
from writory.pipeline.bench_a_systems import GRAPH_STYLES, GraphReader, build_graph_context
from writory.pipeline.passages import flat
from writory.quality.bench_d import Store

CFG = load_config()
FACTS = "questions-ky-ao-vua-1-facts.yaml"
DATA = load_data(questions_file=FACTS)
Q = {q.id: q for q in DATA.questions.questions}


def graph(qid: str, style: str = "base"):
    q = Q[qid]
    return build_graph_context(DATA.state_at(q.ask_chapter), q.question, q.ask_chapter,
                               story=DATA.story, style=style)


def know_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if "Mảnh Khiếp Tàn Thiên theo một giao ước" in line]


# --- chung --------------------------------------------------------------------------------------


def test_styles_are_base_plus_three_named_variants():
    assert GRAPH_STYLES == ("base", "natural", "relevance", "no_item_place")


def test_base_is_the_default_and_unchanged():
    assert graph("knows-05").text == build_graph_context(
        DATA.state_at(9), Q["knows-05"].question, 9, story=DATA.story).text


def test_unknown_style_is_refused():
    with pytest.raises(ValueError, match="style"):
        graph("knows-05", "xyz")


@pytest.mark.parametrize("style", GRAPH_STYLES[1:])
def test_variants_say_the_same_facts_as_base(style, monkeypatch):
    """Cùng khoá `facts` ở các câu mà biến thể không bỏ dòng nào (khác `no_item_place`). Trần ký tự của
    cả ngữ cảnh gỡ ra: chữ mỗi biến thể dài ngắn khác nhau nên sát trần thì một khối vừa ở biến thể này
    mà không vừa ở biến thể kia (đã thấy sau D-144, khi dòng cuối của khối không còn bị cắt)."""
    monkeypatch.setattr("writory.pipeline.bench_a_systems.GRAPH_CHARS_CAP", 10**6)
    for qid in Q:
        base, other = graph(qid), graph(qid, style)
        if style == "no_item_place":
            assert other.facts <= base.facts, qid
        else:
            assert other.facts == base.facts, qid


@pytest.mark.parametrize("style", GRAPH_STYLES[1:])
def test_variants_never_show_a_later_chapter(style):
    later = {n: [flat(p) for p in DATA.story[n].split("\n\n") if len(p.strip()) > 40
                 and not p.startswith("#")] for n in DATA.story}
    for q in DATA.questions.questions:
        text = flat(graph(q.id, style).text)
        for n, paragraphs in later.items():
            if n > q.ask_chapter:
                assert not [p for p in paragraphs if p in text], (q.id, style, n)


# --- natural: cách biết bằng câu thường -------------------------------------------------------------


def test_natural_drops_the_how_label_and_names_the_subject():
    text = graph("knows-05", "natural").text
    assert "Phó Cảnh Hành tự suy ra: Gia tộc Phó từng cất giữ Mảnh Khiếp Tàn Thiên" in text
    assert "cách biết:" not in text and "Đã biết:" not in text


def test_natural_keeps_the_teller_for_things_told():
    text = graph("knows-05", "natural").text
    assert "Phó Cảnh Hành được Trần Mặc kể rằng: Trần Mặc nói rằng hắn biết một lối an toàn" in text


def test_natural_has_one_line_per_known_fact_like_base():
    base = graph("knows-05").text.count("Đã biết:")
    natural = graph("knows-05", "natural").text
    verbs = ("tự suy ra:", "chứng kiến:", "vốn đã biết:", "tự làm:", "kể rằng:")
    assert sum(natural.count(v) for v in verbs) >= base - 1  # trừ dòng lời nói dối, nếu có


def test_natural_lie_lines_keep_the_lie_text():
    base, natural = graph("lie-05" if "lie-05" in Q else "knows-05"), graph(
        "lie-05" if "lie-05" in Q else "knows-05", "natural")
    for m in re.findall(r"«([^»]+)»", base.text):
        assert m in natural.text


# --- relevance: dòng khớp câu hỏi lên đầu -----------------------------------------------------------

MARKER = "giao ước với những người dựng nên Điện Tàn Tinh.; cách biết: suy ra"


def known_lines(text: str, entity: str = "Phó Cảnh Hành") -> list[str]:
    """Các dòng "Đã biết" (không phải lời nói dối) trong khối của một thực thể."""
    block = text.split(f"## {entity}", 1)[1].split("\n\n", 1)[0]
    return [ln for ln in block.splitlines() if ln.startswith("- Đã biết:")]


def test_relevance_moves_the_matching_known_line_into_the_first_four_of_its_group():
    base, rel = known_lines(graph("knows-05").text), known_lines(
        graph("knows-05", "relevance").text)
    assert any(MARKER in ln for ln in rel[:4]) and not any(MARKER in ln for ln in base[:4])
    assert rel[:4] != base[:4]


def test_relevance_keeps_every_other_line_in_its_original_order():
    base, rel = known_lines(graph("knows-05").text), known_lines(
        graph("knows-05", "relevance").text)
    assert sorted(base) == sorted(rel) and len(rel) > 4
    assert rel[4:] == [ln for ln in base if ln not in rel[:4]]


def test_relevance_only_reorders_when_no_cap_cuts_lines(monkeypatch):
    """Không trần dòng và ký tự: cùng độ dài, cùng tập dòng, chỉ khác thứ tự. Khi trần dòng của một
    khối cắt giữa nhóm "đã biết", dòng khớp được đưa lên đầu thì sống sót thay cho dòng cuối nhóm:
    đó là hệ quả đo được của biến thể, không phải lỗi."""
    monkeypatch.setattr(systems, "LINES_PER_ENTITY_CAP", 10**6)
    monkeypatch.setattr(systems, "GRAPH_CHARS_CAP", 10**9)
    for qid in Q:
        base, rel = graph(qid), graph(qid, "relevance")
        assert len(rel.text) == len(base.text), qid
        assert sorted(rel.text.splitlines()) == sorted(base.text.splitlines()), qid


def test_relevance_is_a_noop_when_no_line_matches_the_question():
    nothing = "zzz qqq xxx?"
    base = build_graph_context(DATA.state_at(9), nothing, 9, story=DATA.story)
    rel = build_graph_context(DATA.state_at(9), nothing, 9, story=DATA.story, style="relevance")
    assert rel.text == base.text


# --- no_item_place: bỏ dòng vị trí đồ vật đã có Fact nói về nó -----------------------------------------


def items(chapter: int) -> tuple[list[str], list[str]]:
    """Tên đồ vật có Fact `ABOUT` nó, và đồ vật không có (ở trạng thái sau `chapter`)."""
    reader = GraphReader(DATA.state_at(chapter), chapter)
    named = [i for i in reader._names if reader.label_of(i) == "Item"]
    with_fact = [reader._names[i][0] for i in named if reader.edges("ABOUT", target=i)]
    without = [reader._names[i][0] for i in named if not reader.edges("ABOUT", target=i)]
    return with_fact, without


def place_lines(text: str, name: str) -> list[str]:
    block = text.split(f"## {name}", 1)[1].split("\n\n", 1)[0]
    return [ln for ln in block.splitlines() if ln.startswith("- Ở ")]


def asked_about(name: str, style: str, chapter: int = 10) -> str:
    return build_graph_context(DATA.state_at(chapter), f"Ở đâu có {name}?", chapter,
                               story=DATA.story, style=style).text


def test_no_item_place_drops_the_place_of_an_item_a_fact_is_about():
    with_fact, _ = items(10)
    assert with_fact
    for name in with_fact:
        assert place_lines(asked_about(name, "base"), name), name
        assert not place_lines(asked_about(name, "no_item_place"), name), name


def test_no_item_place_keeps_the_place_of_an_item_nobody_wrote_a_fact_about():
    _, without = items(10)
    assert without
    for name in without:
        base = place_lines(asked_about(name, "base"), name)
        assert base and base == place_lines(asked_about(name, "no_item_place"), name), name


def blocks(text: str) -> dict[str, str]:
    return {part.splitlines()[0]: part for part in text.split("\n\n") if part.startswith("## ")}


def test_no_item_place_leaves_characters_and_places_alone():
    seen = 0
    for qid in Q:
        base, trimmed = blocks(graph(qid).text), blocks(graph(qid, "no_item_place").text)
        for heading in base.keys() & trimmed.keys():
            if "(nhân vật)" in heading or "(nơi chốn)" in heading:
                assert base[heading] == trimmed[heading], (qid, heading)
                seen += 1
    assert seen > 10


# --- bài A mang kiểu trình bày theo cờ --------------------------------------------------------------


def test_builder_applies_style_to_graph_and_graph_quotes_only():
    q = Q["knows-05"]
    base = ContextBuilder(DATA, DATA.state_at, {})
    nat = ContextBuilder(DATA, DATA.state_at, {}, graph_style="natural")
    for system in ("graph", "graph_quotes"):
        assert base.build(system, q).text != nat.build(system, q).text
    for system in ("none", "rag", "full"):
        assert base.build(system, q).text == nat.build(system, q).text


def test_cli_flag_validates_and_meta_records_the_style(tmp_path: Path, capsys):
    out = tmp_path / "o"
    code = main(["run", "--dry-run", "--out", str(out), "--samples", "1", "--systems", "graph",
                 "--questions", "knows-05", "--questions-file", FACTS, "--graph-style", "natural"])
    assert code == 0
    meta = Store(out).read_meta()
    assert meta["runs"][-1]["graph_style"] == "natural"
    assert meta["fingerprint"]["graph_style"] == "natural"
    assert main(["run", "--dry-run", "--out", str(tmp_path / "x"), "--graph-style", "xyz"]) != 0
    capsys.readouterr()


def test_default_style_is_base_and_a_changed_style_does_not_resume_old_results(tmp_path: Path):
    out = tmp_path / "o"
    opts = RunOptions(out=out, dry_run=True, samples=1, systems=["graph"], question_ids=["knows-05"])
    assert asyncio.run(run_bench(DATA, opts, config=CFG, log=lambda _: None)) == 0
    assert Store(out).read_meta()["fingerprint"]["graph_style"] == "base"
    again = RunOptions(out=out, dry_run=True, samples=1, systems=["graph"],
                       question_ids=["knows-05"], graph_style="relevance")
    with pytest.raises(ConfigError, match="graph_style"):
        asyncio.run(run_bench(DATA, again, config=CFG, log=lambda _: None))


def test_bad_style_is_rejected_before_anything_runs(tmp_path: Path):
    with pytest.raises(ConfigError, match="graph-style"):
        check_options(RunOptions(out=tmp_path, graph_style="xyz"))
