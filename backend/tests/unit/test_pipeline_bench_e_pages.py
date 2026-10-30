"""Bài đo E với người kể đọc đoạn trên trang (D-143, đề `narrator-4`). Không mạng, model giả.

Người kể nhận văn đã hiện của truyện (`Story.pages`) như khi chơi; lộ ở câu cuối vẫn phải bằng 0.
"""

from pathlib import Path

import pytest

from writory.config import ConfigError, load_config
from writory.graph.sample import read_sample
from writory.pipeline import bench_e as be
from writory.pipeline.bench_a_data import run_chapter_text
from writory.pipeline.bench_e_story import load_run_story, load_sample_story
from writory.pipeline.narrator import (
    PAGES_PROMPT_VERSION,
    NarratorOutput,
    NarratorReply,
    build_messages,
    prompt_version,
    select_passages,
)
from writory.pipeline.notebook import select_notebook

CONFIG = load_config()  # đề mặc định của repo: bật đoạn trên trang
DATA = be.load_data(questions_file="questions-v2.yaml")
RUN = be.load_data(questions_file="questions-tu-tien-1.yaml", plan_file="plan-tu-tien-1.yaml")


def opts(tmp_path: Path, **kw) -> be.RunOptions:
    base = {"out": tmp_path / "out", "dry_run": True, "samples": 1, "concurrency": 4}
    return be.RunOptions(**(base | kw))


async def run(tmp_path: Path, data=DATA, **kw):
    narrator = kw.pop("narrator", None)
    o = opts(tmp_path, **kw)
    code = await be.run_bench(data, o, config=CONFIG, narrator=narrator, log=lambda _: None)
    store = be.Store(o.out)
    return code, store, be.compute_report(data, store)


def test_repo_config_turns_the_pages_on():
    assert prompt_version(CONFIG) == PAGES_PROMPT_VERSION
    assert CONFIG.limits.narrator_pages.top_k > 0


def test_sample_story_pages_are_the_chapter_files_and_are_hashed():
    story = load_sample_story()
    assert story.pages == {c.number: c.text for c in read_sample().chapters if c.number >= 1}
    assert {f"sample-story/ch{n:02d}.md" for n in range(1, 6)} <= set(story.hashes)


def test_run_story_pages_are_the_prose_of_each_chapter_file_and_are_hashed():
    run_dir = Path(be._resolve_run_dir(RUN.plan.run_dir))
    story = load_run_story(run_dir)
    assert sorted(story.pages) == list(story.chapters)
    for n, text in story.pages.items():
        raw = (run_dir / "chapters" / f"ch{n:02d}.md").read_text(encoding="utf-8")
        assert text == run_chapter_text(raw)
        assert f"run/chapters/ch{n:02d}.md" in story.hashes


@pytest.mark.parametrize("data", [DATA, RUN], ids=["mau-v2", "tu-tien-1"])
async def test_oracle_dry_run_with_pages_records_them_and_leaks_nothing(tmp_path, data):
    code, store, report = await run(tmp_path, data=data)
    assert code == be.EXIT_OK
    assert report["final_leaks"] == 0 and report["n_errors"] == 0
    rows = store.rows(be.RESULTS)
    assert report["pages"]["rows_with"] > 0
    assert all(r["prompt_chars"] > 0 for r in rows if r["raw"] is not None)
    meta = store.read_meta()
    assert meta["fingerprint"]["narrator_prompt"] == PAGES_PROMPT_VERSION
    assert meta["fingerprint"]["narrator_pages"]["top_k"] == CONFIG.limits.narrator_pages.top_k
    summary = (store.root / "summary.md").read_text(encoding="utf-8")
    assert f"đề `{PAGES_PROMPT_VERSION}`" in summary and "Đoạn trên trang (D-143)" in summary
    assert "Lộ ở câu cuối: 0" in summary


@pytest.mark.parametrize("data", [DATA, RUN], ids=["mau-v2", "tu-tien-1"])
async def test_leaker_with_pages_never_reaches_the_player(tmp_path, data):
    code, store, report = await run(tmp_path, data=data, fake="leaker")
    rows = store.rows(be.RESULTS)
    assert code == be.EXIT_OK and rows
    assert all(r["final"] == be.NOT_KNOWN for r in rows)
    assert report["final_leaks"] == 0


async def test_bench_sends_the_production_narrator_4_context(tmp_path):
    q = DATA.question("c4-f-xac-nhan-ten")
    narrator = be.FakeNarrator(DATA, be.oracle_reply)
    await run(tmp_path, narrator=narrator, question_ids=[q.id])
    [messages] = narrator.calls
    view, text = DATA.state_for(q).view, DATA.texts[q.id]
    assert messages == build_messages(
        text, view, select_notebook(text, view, CONFIG.limits.narrator_notebook),
        select_passages(text, view, DATA.pages, CONFIG.limits.narrator_pages))


async def test_the_judge_is_refused_while_it_cannot_see_the_pages(tmp_path):
    with pytest.raises(ConfigError, match="D-143"):
        await run(tmp_path, judge=True)


def test_an_unlocked_answer_grounded_by_a_passage_counts():
    """Loại a: dẫn một đoạn có đủ `expect_terms` là dẫn đúng, như dẫn mục căn cứ."""
    q = next(x for x in DATA.questions.questions if x.type == "a" and x.expect_terms)
    state = DATA.state_for(q)
    text = DATA.texts[q.id]
    passages = select_passages(text, state.view, DATA.pages, CONFIG.limits.narrator_pages)
    good = [(r, c) for r, c in passages if all(be.contains(c.text, t) for t in q.expect_terms)]
    if not good:
        pytest.skip("BM25 không kéo được đoạn có đủ cụm cho câu này")
    ref, _ = good[0]
    answer = " ".join(q.expect_terms)
    reply = NarratorReply(answer, NarratorOutput(known=True, answer=answer, entry_ids=[ref]),
                          None, passages=passages)
    row = be.score_reply(q, text, state, reply, DATA)
    assert row["grounded_by_page"] is True and row["verdict"] == "correct"
    wrong = NarratorReply(answer, NarratorOutput(known=True, answer=answer, entry_ids=["m999"]),
                          None, passages=passages)
    assert be.score_reply(q, text, state, wrong, DATA)["verdict"] == "wrong_grounds"


async def test_final_leaks_say_whether_the_term_is_on_a_page_already_read(tmp_path):
    """Bộ chấm vẫn đếm mọi lần trúng là lộ (mã thoát 4); cờ `on_page` chỉ giúp đọc tay: chuỗi có
    trên trang người chơi đã đọc thì nhiều khả năng là bộ trích bỏ sót, không phải lộ thật."""
    def slips(data, q, state, shown):
        return {"known": True, "answer": "Có lẽ Lan đã ra tay với lão.",
                "entry_ids": [state.by_truth_id["e_gu_death"]]}

    code, store, report = await run(tmp_path, narrator=be.FakeNarrator(DATA, slips),
                                    question_ids=["c3-b-ai-giet-gu"])
    assert code == be.EXIT_LEAK and report["final_leaks"] == 1
    [row] = store.rows(be.RESULTS)
    assert row["final_leaks"] and all(h["on_page"] is False for h in row["final_leaks"])
    assert report["final_leaks_on_page_only"] == 0


def test_on_page_needs_every_part_of_a_group():
    page = "Lão Gù ngồi bên bếp lò nguội. Lan rót trà."
    assert be.on_page("Lão Gù", page) and be.on_page("Lão Gù + Lan", page)
    assert not be.on_page("Lão Gù + gián điệp", page)
