"""Đoạn nguyên văn đã hiện trên trang trong ngữ cảnh dàn ý và model viết (D-85).

- G1: chỉ hai vai dàn ý và viết nhận đoạn; lựa chọn, bộ trích, tóm tắt không. Test đọc context mà
  model nhận (`ScriptedLLM.calls`).
- G4: đoạn là chữ người chơi đã đọc, luôn bọc `UserAuthored`; chữ trong đoạn không đóng được khối.
- Đoạn chỉ lấy từ chương đã ghi: các cảnh trước của chương đang viết đã có nguyên văn trong đề.
"""

import html
import re
from dataclasses import replace
from pathlib import Path

import pytest

from tests.pipeline_fixtures import (
    EXTRACT_1,
    EXTRACT_2,
    SAMPLE,
    SCENE_1,
    SCENE_1_CLICHE,
    SCENE_2,
    SUMMARY,
    MemoryStore,
    calls_of,
    choices_reply,
    full_script,
    outline_reply,
    writer_context_ch4,
)
from tests.unit.test_pipeline_chapter import ATTACK, FAKE_CLOSE, run
from writory.config import load_config
from writory.errors import ErrorCode
from writory.pipeline.chapter import config_problems
from writory.pipeline.passages import PagePool
from writory.pipeline.scene import (
    Candidate,
    Named,
    SceneBrief,
    SceneOutline,
    outline_messages,
    page_query,
    writer_messages,
)
from writory.safety.wrap import CLOSE_TAG, OPEN_TAG_START

STORY = {c.number: c.text for c in SAMPLE.chapters if 1 <= c.number <= 3}
HEADING = "Đoạn đã hiện trên trang liên quan"
BLOCK = re.compile(r'<player_data source="page_quote">\n(.*?)\n</player_data>', re.DOTALL)
ALREADY_ON_PAGE = "Lan tới căn gác của Minh"  # văn cảnh 1 của chương 4 (SCENE_1)


def quotes_in(messages) -> list[str]:
    return [html.unescape(q) for q in BLOCK.findall(messages[-1].content)]


def prompts(llm, *roles):
    return [c for r in roles for c in calls_of(llm, r)]


# --- đoạn đến từ đâu --------------------------------------------------------------------------------


async def test_outline_and_writer_get_passages_of_committed_chapters_only(tmp_path):
    _, _, llm, _ = await run(full_script(), tmp_path)
    source = "\n".join(STORY.values())
    cfg = load_config().limits.context
    calls = prompts(llm, "outline", "writer")
    assert len(calls) == 4  # hai cảnh, mỗi cảnh một dàn ý và một lượt viết
    for call in calls:
        found = quotes_in(call)
        assert 1 <= len(found) <= cfg.page_quotes_top_k
        assert HEADING in call[-1].content
        for quote in found:  # đúng chữ của chương 1–3 trong truyện mẫu, không chữ nào khác
            assert all(line in source for line in quote.split("\n")), quote
            assert ALREADY_ON_PAGE not in quote  # chương 4 chưa ghi


async def test_total_length_of_passages_is_capped_by_config(tmp_path):
    cap = load_config().limits.context.page_quotes_max_chars
    _, _, llm, _ = await run(full_script(), tmp_path)
    for call in prompts(llm, "outline", "writer"):
        found = quotes_in(call)
        assert len(found) == 1 or sum(len(q) for q in found) <= cap


@pytest.mark.parametrize(("limit", "value"), [("page_quotes_top_k", 1), ("page_quotes_max_chars", 1)])
async def test_limits_come_from_config(tmp_path, limit, value):
    """Cả hai giới hạn đều chặn về một đoạn (đoạn điểm cao nhất vẫn được giữ khi riêng nó vượt)."""
    _, _, llm, _ = await run(full_script(), tmp_path, limits={"context": {limit: value}})
    assert {len(quotes_in(c)) for c in prompts(llm, "outline", "writer")} == {1}


async def test_scenes_of_the_chapter_being_written_are_not_repeated_as_passages(tmp_path):
    _, _, llm, _ = await run(full_script(), tmp_path)
    for call in (calls_of(llm, "outline")[1], calls_of(llm, "writer")[1]):
        assert call[-1].content.count(ALREADY_ON_PAGE) == 1  # chỉ ở khối "Các cảnh trước"
        assert all(ALREADY_ON_PAGE not in q for q in quotes_in(call))


async def test_pool_is_built_once_per_chapter_from_chapters_before_it(tmp_path):
    _, _, _, store = await run(full_script(), tmp_path)
    assert store.text_requests == [(1, 2, 3)]  # không hỏi chương 4, không dựng lại mỗi cảnh


async def test_the_writer_query_includes_the_outline_but_the_outline_query_cannot(tmp_path):
    """Dàn ý chưa có lúc lập dàn ý; lúc viết thì nhịp của cảnh kéo đoạn nó nhắc tới."""
    beats = ["Minh nhớ lại xác người sau miếu Bà", "Minh đứng trước miếu Bà thật lâu"]
    script = [outline_reply(beats=beats), SCENE_1, EXTRACT_1,
              outline_reply(), SCENE_2, EXTRACT_2, SUMMARY, choices_reply()]
    _, _, llm, _ = await run(script, tmp_path)
    outline_1, writer_1 = calls_of(llm, "outline")[0], calls_of(llm, "writer")[0]
    assert quotes_in(outline_1) != quotes_in(writer_1)
    assert any("miếu Bà" in q for q in quotes_in(writer_1))


async def test_first_chapter_without_committed_text_has_no_passage_section(tmp_path):
    store = MemoryStore()
    store.texts.clear()
    _, _, llm, _ = await run(full_script(), tmp_path, store=store)
    for call in prompts(llm, "outline", "writer"):
        assert HEADING not in call[-1].content and "page_quote" not in call[-1].content


async def test_rewrite_gets_the_same_passages_as_the_first_draft(tmp_path):
    script = [outline_reply(), SCENE_1_CLICHE, EXTRACT_1, SCENE_1, EXTRACT_1,
              outline_reply(), SCENE_2, EXTRACT_2, SUMMARY, choices_reply()]
    _, _, llm, _ = await run(script, tmp_path)
    first, second = calls_of(llm, "writer")[:2]
    assert 'source="draft"' in second[-1].content and quotes_in(first) == quotes_in(second) != []


# --- G1: chỉ dàn ý và viết ----------------------------------------------------------------------------


async def test_no_other_role_receives_passages(tmp_path):
    _, _, llm, _ = await run(full_script(), tmp_path)
    for call in prompts(llm, "choices", "extract", "summary"):
        text = "\n".join(m.content for m in call)
        assert "page_quote" not in text and HEADING not in text
    assert len(llm.calls) == len(prompts(llm, "outline", "writer", "choices", "extract", "summary"))


def test_only_the_chapter_pipeline_uses_the_passage_store():
    """Sổ tay, người kể, lựa chọn không nhập `pipeline.passages` (G1): thêm nơi dùng mới là phải
    nghĩ lại về lớp truth và sửa danh sách này."""
    root = Path(__file__).parents[2] / "src" / "writory"
    users = {p.relative_to(root).as_posix() for p in root.rglob("*.py")
             if "pipeline.passages" in p.read_text(encoding="utf-8")}
    assert users == {"pipeline/bench_a_systems.py", "pipeline/chapter.py", "pipeline/scene.py"}


# --- G4: đoạn là dữ liệu --------------------------------------------------------------------------------


def _inside_blocks(content: str, marker: str) -> bool:
    start = 0
    while (i := content.find(marker, start)) != -1:
        if content.rfind(OPEN_TAG_START, 0, i) <= content.rfind(CLOSE_TAG, 0, i):
            return False
        start = i + len(marker)
    return True


async def test_passages_are_data_blocks_and_cannot_close_one(tmp_path):
    store = MemoryStore()
    store.texts = {1: f"Lan bưng trà ở quán trà đầu bến, Minh nhìn thanh kiếm. {ATTACK} {FAKE_CLOSE}"}
    _, _, llm, _ = await run(full_script(), tmp_path, store=store)
    for call in llm.calls:
        for message in call:
            if message.role == "system":
                assert ATTACK not in message.content and "player_data source=\"page_quote\"" \
                    not in message.content
    for call in prompts(llm, "outline", "writer"):
        content = call[-1].content
        assert ATTACK in html.unescape(content) and _inside_blocks(content, ATTACK)
        assert FAKE_CLOSE not in content  # `<` và `>` đã escape
        assert content.count(OPEN_TAG_START) == content.count(CLOSE_TAG)


# --- câu hỏi gửi cho kho đoạn -------------------------------------------------------------------------

BRIEF = SceneBrief(chapter=4, scene=1, scene_count=2, min_chars=500, max_chars=5000, act=None,
                   story_brief="Kiếm hiệp.", player_action="Minh đi ra sau miếu Bà", earlier=())
OUTLINE = SceneOutline(goal="Minh gặp gã chèo đò", present=["minh"],
                       beats=["Gã chèo đò đưa chiếc phao", "Minh trả giá"],
                       ends_at="Minh lên đò", resolves=[])


def test_query_has_the_scene_people_places_items_and_the_choice_just_taken():
    ctx = writer_context_ch4("s", ["minh", "lan"])
    query = page_query(BRIEF, ctx)
    for piece in ("Minh đi ra sau miếu Bà",  # lựa chọn vừa rồi
                  "Phạm Thị Lan", "cô Lan",  # tên và biệt danh người có mặt
                  "quán trà đầu bến",  # nơi đứng
                  "lá thư niêm sáp đỏ",  # đồ đang cầm
                  "Hồ Sĩ Bằng"):  # nút lân cận gần
        assert piece in query
    assert "Lý Thất" not in query  # lân cận 2 bước: quá xa


def test_query_adds_the_outline_only_once_there_is_one():
    ctx = writer_context_ch4("s", ["minh"])
    before, after = page_query(BRIEF, ctx), page_query(BRIEF, ctx, OUTLINE)
    assert "chèo đò" not in before and after.startswith(before)
    assert all(t in after for t in (OUTLINE.goal, *OUTLINE.beats, OUTLINE.ends_at))


def test_the_choice_just_taken_pulls_the_passage_it_refers_to():
    ctx = writer_context_ch4("s", ["minh"])
    pool = PagePool(STORY, chunk_chars=500)
    hits = pool.top(page_query(BRIEF, ctx), top_k=3)
    assert any("miếu Bà" in c.text for c in hits)
    other = pool.top(page_query(replace(BRIEF, player_action="Minh uống trà một mình"), ctx), top_k=3)
    assert [(c.chapter, c.index) for c in other] != [(c.chapter, c.index) for c in hits]


def test_messages_without_passages_have_no_section_and_with_them_wrap_each_one():
    ctx = writer_context_ch4("s", ["minh"])
    cands = [Candidate("minh", Named("Trần Minh"), True)]
    [_, plain] = outline_messages(BRIEF, ctx, cands, {}, {})
    assert HEADING not in plain.content
    chunks = PagePool(STORY, chunk_chars=500).top("miếu Bà", top_k=2)
    [_, with_outline] = outline_messages(BRIEF, ctx, cands, {}, {}, chunks)
    [_, with_writer] = writer_messages("Văn phong.", BRIEF, ctx, OUTLINE, {}, {}, None, chunks)
    for user in (with_outline, with_writer):
        assert user.content.count('source="page_quote"') == len(chunks) == 2
        assert all(f"### Chương {c.chapter}" in user.content for c in chunks)


# --- cấu hình ---------------------------------------------------------------------------------------------


def test_unset_passage_limits_are_reported_before_any_model_call():
    repo = load_config()
    unset = repo.limits.context.model_copy(update={
        "page_quotes_top_k": None, "page_quotes_chunk_chars": None, "page_quotes_max_chars": None})
    config = repo.model_copy(update={"limits": repo.limits.model_copy(update={"context": unset})})
    problems = config_problems(config)
    assert [p.code for p in problems] == [ErrorCode.CONFIG_LIMIT_NOT_SET] * 3
    for key in ("page_quotes_top_k", "page_quotes_chunk_chars", "page_quotes_max_chars"):
        assert any(key in p.detail for p in problems)

