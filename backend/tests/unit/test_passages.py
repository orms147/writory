"""Kho đoạn trên trang dùng chung (D-85): BM25 và chia đoạn của bài đo A (hệ `graph_quotes`) và
của sản phẩm (ngữ cảnh dàn ý, ngữ cảnh viết) là MỘT code.

Giá trị vàng dưới đây lấy từ chính code của bài A trước khi tách, trên truyện mẫu: bài A phải ra
đúng kết quả cũ.
"""

import pytest

from writory.graph import read_sample
from writory.pipeline import bench_a_systems as bench
from writory.pipeline import passages

SAMPLE = read_sample()
STORY = {c.number: c.text for c in SAMPLE.chapters if c.number >= 1}
CHUNK = 500


def pairs(hits) -> list[tuple[int, int]]:
    return [(c.chapter, c.index) for c in hits]


# --- bài A và sản phẩm dùng cùng một code ---------------------------------------------------------


@pytest.mark.parametrize("name", ["flat", "tokens", "Chunk", "chunk_chapter", "Bm25Index",
                                  "STOPWORDS"])
def test_bench_a_reuses_the_shared_implementation(name):
    assert getattr(bench, name) is getattr(passages, name)


# --- giá trị vàng của bài A -------------------------------------------------------------------------


def test_tokens_golden():
    assert passages.tokens("Lão Gù giao Thanh Sương cho Minh ở lò rèn?") == [
        "lão", "gù", "giao", "thanh", "sương", "minh", "lò", "rèn", "lão_gù", "gù_giao",
        "giao_thanh", "thanh_sương", "sương_minh", "minh_lò", "lò_rèn"]


def test_chunking_golden():
    got = [(c.chapter, c.index, len(c.text))
           for ch in STORY for c in passages.chunk_chapter(ch, STORY[ch], chunk_chars=CHUNK)]
    assert got == [(1, 0, 545), (1, 1, 603), (1, 2, 844), (1, 3, 93), (2, 0, 509), (2, 1, 642),
                   (2, 2, 499), (3, 0, 535), (3, 1, 614), (3, 2, 515), (4, 0, 590), (4, 1, 524),
                   (4, 2, 303), (5, 0, 555), (5, 1, 572), (5, 2, 507)]


@pytest.mark.parametrize(("question", "expected"), [
    ("Lão Gù giao thanh kiếm cho ai?", [(2, 0), (4, 0), (4, 1)]),
    ("Lan đưa gói trà cho Minh", [(2, 1), (2, 2), (4, 1)]),
    ("Ai chết sau miếu Bà?", [(2, 0), (3, 0), (3, 1)]),
    ("quán trà đầu bến", [(1, 0), (1, 2), (4, 2)]),
    ("xyz không có", []),
])
def test_bench_a_retrieve_golden(question, expected):
    hits, pool = bench.retrieve(STORY, [1, 2, 3, 4], question, top_k=3, chunk_chars=CHUNK)
    assert pairs(hits) == expected and pool == 13


def test_bm25_scores_golden():
    chunks = [c for ch in STORY for c in passages.chunk_chapter(ch, STORY[ch], chunk_chars=CHUNK)]
    scores = passages.Bm25Index(chunks).scores("Lão Gù giao thanh kiếm cho ai?")
    assert [round(x, 4) for x in scores] == [
        0.0, 2.7192, 1.6871, 0.8711, 3.2246, 0.8142, 1.2325, 0.551, 2.4107, 0.6661, 3.3405,
        4.4001, 1.2699, 1.0952, 2.9156, 2.917]


# --- kho đoạn cho sản phẩm -----------------------------------------------------------------------------


def pool(through: int = 4) -> passages.PagePool:
    return passages.PagePool({c: STORY[c] for c in range(1, through + 1)}, chunk_chars=CHUNK)


def pool_chunks():
    return [c for ch in range(1, 5) for c in passages.chunk_chapter(ch, STORY[ch], chunk_chars=CHUNK)]


def test_pool_gives_the_same_hits_as_bench_a_retrieve():
    question = "Lão Gù giao thanh kiếm cho ai?"
    want, _ = bench.retrieve(STORY, [1, 2, 3, 4], question, top_k=3, chunk_chars=CHUNK)
    assert pairs(pool().top(question, top_k=3)) == pairs(want)


def test_hits_come_back_in_story_order():
    hits = pool().top("Ai chết sau miếu Bà?", top_k=3)
    assert pairs(hits) == sorted(pairs(hits))


def test_max_chars_drops_the_lowest_ranked_passages_first():
    question = "Lão Gù giao thanh kiếm cho ai?"
    full = pool().top(question, top_k=3)
    assert len(full) == 3
    best = pool().top(question, top_k=1)[0]
    cap = len(best.text) + 10  # chỉ đủ chỗ cho đoạn điểm cao nhất
    capped = pool().top(question, top_k=3, max_chars=cap)
    assert pairs(capped) == [(best.chapter, best.index)]
    assert sum(len(c.text) for c in capped) <= cap


def test_max_chars_never_skips_a_passage_to_fit_a_lower_ranked_one():
    """Bỏ từ đoạn điểm thấp nhất lên: đoạn hạng 2 không vừa thì đoạn hạng 3 cũng không được lọt vào,
    dù ngắn hơn."""
    question = "Ai chết sau miếu Bà?"
    ranked = passages.Bm25Index(pool_chunks()).top(question, 3)
    assert len(ranked[1].text) > len(ranked[2].text)  # điều kiện của bài: hạng 2 dài hơn hạng 3
    cap = len(ranked[0].text) + len(ranked[2].text)  # vừa hạng 1 + hạng 3, không vừa hạng 1 + 2
    assert len(ranked[0].text) + len(ranked[1].text) > cap
    assert pairs(pool().top(question, top_k=3, max_chars=cap)) == [
        (ranked[0].chapter, ranked[0].index)]


def test_no_overlap_with_the_query_gives_nothing():
    assert pool().top("xyz không có", top_k=3) == []


def test_pool_only_contains_the_chapters_it_was_given():
    only_two = passages.PagePool({2: STORY[2]}, chunk_chars=CHUNK)
    assert {c.chapter for c in only_two.top("Lão Gù giao thanh kiếm", top_k=5)} == {2}
    assert passages.PagePool({}, chunk_chars=CHUNK).top("Lão Gù", top_k=3) == []


def test_pool_is_deterministic():
    assert pool().top("quán trà đầu bến", top_k=3) == pool().top("quán trà đầu bến", top_k=3)


def test_pool_size_is_reported():
    assert pool().size == 13 and passages.PagePool({}, chunk_chars=CHUNK).size == 0


# --- câu mở chương (D-110) -------------------------------------------------------------------------


def test_opening_takes_the_first_sentences_of_the_first_paragraph_up_to_the_limit():
    from writory.pipeline.passages import opening_of

    text = ("Tôi siết ấn trong lòng bàn tay. Cạnh ấn cấn vào da, lạnh ngắt. Ba người đứng đối "
            "diện.\n\n- Ngươi là ai?")
    assert opening_of(text, 80) == "Tôi siết ấn trong lòng bàn tay. Cạnh ấn cấn vào da, lạnh ngắt."
    assert opening_of(text, 40) == "Tôi siết ấn trong lòng bàn tay."


def test_opening_clips_a_first_sentence_that_is_longer_than_the_limit_at_a_word():
    from writory.pipeline.passages import opening_of

    assert opening_of("một hai ba bốn năm sáu bảy tám chín mười.", 20) == "một hai ba bốn năm…"


def test_opening_skips_headings_scene_breaks_and_blank_lines_and_keeps_a_dialogue_opening():
    from writory.pipeline.passages import opening_of

    text = "# Chương 3\n\n* * *\n\nĐoàn Khương khuỵu xuống giữa đường.\n\nTôi chộp."
    assert opening_of(text, 90) == "Đoàn Khương khuỵu xuống giữa đường."
    assert opening_of("- Các người đã định tội ta.\n\nGiọng tôi vang.", 90) == (
        "- Các người đã định tội ta.")


def test_opening_of_empty_text_is_none():
    from writory.pipeline.passages import opening_of

    assert opening_of("", 90) is None
    assert opening_of("# Chương 1\n\n* * *", 90) is None
