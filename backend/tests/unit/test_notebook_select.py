"""Truy hồi sổ tay cho người kể khi truyện dài (design §6.6, D-59). Không mạng, không model thật.

G1: truy hồi chạy trên `PlayerView` SAU khi lọc; hàm không nhận gì khác, nên không chạm lớp truth.
Mã công khai (m1, l1...) lấy từ sổ tay đầy đủ, nên ổn định dù chỉ gửi một phần.
"""

import json

import pytest

from writory.config import CostLimits, load_config
from writory.graph import (
    PlayerEntry,
    PlayerLie,
    PlayerView,
    public_entries,
    public_lies,
    read_sample,
)
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM, render_context
from writory.pipeline.narrator import (
    NOT_KNOWN,
    BlockReason,
    ask_narrator_reply,
    build_messages,
    render_notebook,
)
from writory.pipeline.notebook import NotebookSelection, select_notebook
from writory.pipeline.story_plan import StoryPlan

CONFIG = load_config()
LIMITS = CONFIG.limits.narrator_notebook
SAMPLE = read_sample()

# Ngưỡng nhỏ để test không phải dựng hàng trăm mục.
SMALL = LIMITS.model_copy(update={"max_entries": 40, "max_chars": 6000, "recent_entries": 5,
                                  "keyword_entries": 4})


def entry(i: int, kind: str, text: str, *, chapter: int, about: tuple[str, ...] = (),
          aliases: tuple[str, ...] = (), quote: str | None = None) -> PlayerEntry:
    q = quote if quote is not None else f"Câu trên trang số {i}."
    return PlayerEntry(f"e{i}", kind, text, aliases, chapter, q, about, (q,))


def big_view(n_filler: int = 300, *, extra: tuple[PlayerEntry, ...] = (),
             lies: tuple[PlayerLie, ...] = ()) -> PlayerView:
    """Một sổ tay lớn: vài mục cũ ở chương 1 và `n_filler` mục không liên quan ở chương 2..40."""
    old = (
        entry(0, "Character", "Lão Gù", chapter=1, aliases=("thợ rèn",),
              quote="Cả phố chỉ gọi lão là Lão Gù."),
        entry(1, "Location", "lò rèn của Lão Gù", chapter=1, quote="Cuối phố là lò rèn."),
        entry(2, "Fact", "Mỗi sáng lò phát ra tiếng búa", chapter=1, about=("e0",),
              quote="Tiếng búa vang lên từ sớm."),
    )
    filler = tuple(
        entry(100 + i, "Event", f"Nhân vật phụ số {i} đi chợ mua hàng số {i}", chapter=2 + i % 39)
        for i in range(n_filler)
    )
    return PlayerView("s-big", 40, (*old, *extra, *filler), lies)


def ids_of(selection: NotebookSelection) -> set[str]:
    return {e.id for _, e in selection.entries}


# --- cấu hình --------------------------------------------------------------------------------


def test_config_has_notebook_thresholds():
    assert LIMITS.require("max_entries") > LIMITS.require("recent_entries") > 0
    assert LIMITS.require("max_chars") > 0 and LIMITS.require("keyword_entries") > 0


# --- sổ tay nhỏ: gửi nguyên ------------------------------------------------------------------


@pytest.mark.parametrize("chapter", [1, 3, 5])
def test_small_notebook_is_sent_whole(chapter):
    state = OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= chapter])
    view = player_view_of(state, chapter, story_id="s")
    sel = select_notebook("Lan là ai?", view, LIMITS)
    assert not sel.partial
    assert sel.entries == public_entries(view)
    assert sel.lies == public_lies(view)
    assert render_notebook(view, sel) == render_notebook(view)


# --- sổ tay lớn: cắt theo ngưỡng -------------------------------------------------------------


def test_large_notebook_is_cut_to_the_limits():
    view = big_view()
    sel = select_notebook("Hôm nay trời thế nào?", view, SMALL)
    assert sel.partial and sel.total_entries == len(view.entries)
    assert len(sel.entries) + len(sel.lies) <= SMALL.max_entries
    assert len(render_notebook(view, sel)) <= SMALL.max_chars


def test_context_is_smaller_than_the_full_notebook():
    view = big_view()
    sel = select_notebook("Lão Gù là ai?", view, SMALL)
    assert len(render_notebook(view, sel)) < len(render_notebook(view)) / 3


def test_old_entry_named_in_the_question_is_kept():
    view = big_view()
    sel = select_notebook("Lão Gù là ai?", view, SMALL)
    assert {"e0", "e1"} <= ids_of(sel)


def test_name_match_ignores_diacritics_and_case():
    view = big_view()
    sel = select_notebook("lo ren cua LAO GU nam o dau", view, SMALL)
    assert {"e0", "e1"} <= ids_of(sel)


def test_alias_the_player_knows_also_matches():
    view = big_view()
    sel = select_notebook("Người thợ rèn đó là ai?", view, SMALL)
    assert "e0" in ids_of(sel)


def test_neighbours_are_included_by_about_up_to_two_hops():
    # e2 nói về e0 (1 bước); e3 nói về e2 (2 bước); e4 nói về e3 (3 bước: không lấy).
    chain = (
        entry(3, "Event", "Chuyện bên lề thứ nhất", chapter=1, about=("e2",)),
        entry(4, "Event", "Chuyện bên lề thứ hai", chapter=1, about=("e3",)),
    )
    view = big_view(extra=chain)
    ids = ids_of(select_notebook("Lão Gù là ai?", view, SMALL))
    assert {"e0", "e2", "e3"} <= ids
    assert "e4" not in ids


def test_neighbour_link_works_in_both_directions():
    # Câu hỏi nhắc tên "Sổ Trận"; mục e7 (nhân vật) là thứ mà e8 nói về.
    extra = (entry(7, "Item", "Sổ Trận", chapter=3),
             entry(8, "Fact", "Ghi chép nằm trong đó rất kỹ", chapter=3, about=("e7",)),
             entry(9, "Character", "Người giữ sổ", chapter=3, about=()))
    view = big_view(extra=extra)
    ids = ids_of(select_notebook("Sổ Trận để làm gì?", view, SMALL))
    assert {"e7", "e8"} <= ids


def test_most_recent_entries_always_come_along():
    view = big_view()
    ordered = [e.id for _, e in public_entries(view)]
    sel = select_notebook("Lão Gù là ai?", view, SMALL)
    assert set(ordered[-SMALL.recent_entries:]) <= ids_of(sel)


def test_rare_word_in_the_text_finds_an_entry_without_a_name_match():
    extra = (entry(5, "Fact", "Chiếc chìa khóa đồng giấu dưới viên gạch lỏng", chapter=2),)
    view = big_view(extra=extra)
    sel = select_notebook("Cái gì giấu dưới viên gạch?", view, SMALL)
    assert "e5" in ids_of(sel)


def test_public_refs_stay_stable_when_only_part_is_sent():
    view = big_view()
    full = dict(public_entries(view))
    sel = select_notebook("Lão Gù là ai?", view, SMALL)
    assert sel.entries and all(full[ref] == e for ref, e in sel.entries)
    assert [r for r, _ in sel.entries] == sorted((r for r, _ in sel.entries),
                                                 key=lambda r: int(r[1:]))


def test_selection_never_invents_entries():
    view = big_view()
    sel = select_notebook("Lão Gù là ai?", view, SMALL)
    assert ids_of(sel) <= {e.id for e in view.entries}


def test_selection_is_deterministic():
    view = big_view()
    assert select_notebook("Lão Gù là ai?", view, SMALL) == select_notebook("Lão Gù là ai?", view,
                                                                           SMALL)


def test_lies_follow_the_question_and_recency():
    lies = tuple(PlayerLie(f"l{i}", f"Lời dối số {i} về chuyện {i}", 2 + i, ("Trần Văn Khải",))
                 for i in range(12))
    lies += (PlayerLie("old", "Thanh kiếm là của cha tôi", 1, ("Phạm Thị Lan",)),)
    view = big_view(lies=lies)
    sel = select_notebook("Tôi đã nói gì với Phạm Thị Lan?", view, SMALL)
    contents = {lie.content for _, lie in sel.lies}
    assert "Thanh kiếm là của cha tôi" in contents
    assert len(sel.lies) <= SMALL.recent_entries + SMALL.keyword_entries


def test_question_with_nothing_in_common_still_gets_the_recent_entries():
    view = big_view()
    sel = select_notebook("???", view, SMALL)
    assert len(sel.entries) >= SMALL.recent_entries


# --- G1 qua đường người kể -------------------------------------------------------------------


def metered(fake: FakeLLM) -> MeteredClient:
    return MeteredClient(fake, CostTracker(CostLimits(per_scene=1.0, per_chapter=1.0,
                                                      per_story=1.0)))


class Quota:
    async def take(self, story_id: str, chapter: int, limit: int) -> bool:
        return True


PLAN = StoryPlan.model_validate({
    "acts": [{"name": "mở đầu", "from_chapter": 1, "to_chapter": 60}], "secrets": [],
})
CFG = CONFIG.model_copy(update={
    "limits": CONFIG.limits.model_copy(update={"narrator_notebook": SMALL}),
    "models": CONFIG.models.model_copy(update={
        "roles": CONFIG.models.roles.model_copy(update={"narrator": "test/narrator"})}),
})


async def ask(question: str, view: PlayerView, reply: dict) -> tuple[FakeLLM, object]:
    fake = FakeLLM.scripted([json.dumps(reply, ensure_ascii=False)])
    out = await ask_narrator_reply(question, view, llm=metered(fake), config=CFG,
                                   truth_names={}, plan=PLAN, story_brief="", quota=Quota(),
                                   pages={})
    return fake, out


def ref_of(view: PlayerView, entry_id: str) -> str:
    return next(r for r, e in public_entries(view) if e.id == entry_id)


async def test_model_context_is_a_subset_of_the_player_view():
    view = big_view()
    fake, _ = await ask("Lão Gù là ai?", view, {"known": False, "answer": None, "entry_ids": []})
    [messages] = fake.calls
    context = render_context(messages)
    assert "Lão Gù" in context and "lò rèn của Lão Gù" in context
    # Phần xa câu hỏi không nằm trong context.
    assert "Nhân vật phụ số 150 đi chợ" not in context
    assert len(context) < len(render_notebook(view)) / 3
    # Không id lớp truth.
    for e in view.entries:
        assert f'"{e.id}"' not in context


async def test_answer_from_a_retrieved_old_entry_is_accepted():
    view = big_view()
    ref = ref_of(view, "e1")
    _, out = await ask("Lò rèn của Lão Gù ở đâu?", view,
                       {"known": True, "answer": "Ở cuối phố.", "entry_ids": [ref]})
    assert out.answer == "Ở cuối phố." and out.blocked is None
    assert ref in out.shown


async def test_citing_a_ref_that_was_not_sent_is_an_unknown_ref():
    """Mã có thật trong sổ tay đầy đủ nhưng không được gửi: model không thể dựa vào chữ nó chưa
    thấy, nên coi là mã sai."""
    view = big_view()
    unsent = ref_of(view, "e150")
    _, out = await ask("Lò rèn của Lão Gù ở đâu?", view,
                          {"known": True, "answer": "Ở cuối phố.", "entry_ids": [unsent]})
    assert unsent not in out.shown
    assert out.answer == NOT_KNOWN and out.blocked is BlockReason.UNKNOWN_REF


async def test_small_view_reply_reports_every_ref_as_shown():
    state = OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= 3])
    view = player_view_of(state, 3, story_id="s")
    _, out = await ask("Lão Gù chết ở đâu?", view, {"known": False, "answer": None, "entry_ids": []})
    assert set(out.shown) == {r for r, _ in public_entries(view)} | {
        r for r, _ in public_lies(view)}
    assert out.total == len(view.entries) + len(view.lies)


def test_build_messages_without_limits_is_the_old_behaviour():
    view = big_view(40)
    old = build_messages("Lão Gù là ai?", view)
    assert render_context(old).count("[m") == len(view.entries)


def test_few_but_very_long_entries_are_cut_by_characters():
    # 30 mục (dưới max_entries) nhưng mỗi mục ~600 ký tự: tổng vượt max_chars, nên vẫn phải cắt.
    long_quote = "Một đoạn rất dài trên trang. " * 20
    rows = tuple(entry(i, "Event", f"Sự việc thứ {i}", chapter=1 + i, quote=long_quote,
                       about=("e99",)) for i in range(30))  # đều là hàng xóm của "Lão Gù"
    named = entry(99, "Character", "Lão Gù", chapter=1, quote=long_quote)
    view = PlayerView("s-long", 40, (named, *rows), ())
    assert len(view.entries) < SMALL.max_entries
    assert len(render_notebook(view)) > SMALL.max_chars
    sel = select_notebook("Lão Gù là ai?", view, SMALL)
    assert sel.partial and "e99" in ids_of(sel)
    assert len(render_notebook(view, sel)) <= SMALL.max_chars + len(long_quote) * SMALL.recent_entries
    # Trần ký tự thật sự áp cho phần không bắt buộc: bỏ các mục gần đây (luôn kèm) thì còn trong trần.
    optional = [e for _, e in sel.entries if e.id != "e99"][:-SMALL.recent_entries]
    assert sum(len(e.quote or "") for e in optional) <= SMALL.max_chars
