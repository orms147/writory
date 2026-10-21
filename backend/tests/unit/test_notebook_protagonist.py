"""Nhân vật chính trong sổ tay (D-74): có mục từ chương 0, và người kể biết mục đó chính là người
chơi nên trả lời được "tôi tên là gì". Chỉ FakeLLM, không mạng.

G1: context chỉ có chữ của `player_view`. G4: tên là chữ người chơi, luôn nằm trong khối dữ liệu.
"""

import json
from collections import Counter

import pytest

from tests.pipeline_fixtures import setup_chapter_0
from writory.config import CostLimits, load_config
from writory.graph import PlayerEntry, PlayerView, public_entries, read_sample
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM, render_context
from writory.pipeline.narrator import (
    NOT_KNOWN,
    PROTAGONIST_LABEL,
    SYSTEM_PROMPT,
    ask_narrator_reply,
    render_notebook,
)
from writory.pipeline.notebook import select_notebook
from writory.pipeline.setup import PROTAGONIST_ID
from writory.safety.leak import check_leaks, leak_names
from writory.safety.wrap import OPEN_TAG_START

CONFIG = load_config()
CFG = CONFIG.model_copy(update={"models": CONFIG.models.model_copy(update={
    "roles": CONFIG.models.roles.model_copy(update={"narrator": "test/narrator"})})})
SAMPLE = read_sample()


class Quota:
    async def take(self, story_id: str, chapter: int, limit: int) -> bool:
        return True


def metered(fake: FakeLLM) -> MeteredClient:
    return MeteredClient(fake, CostTracker(CostLimits(per_scene=1.0, per_chapter=1.0,
                                                      per_story=1.0)))


def world():
    package, plan = setup_chapter_0()
    state = OverlayState(EmptyState(), [package])
    return state, plan, player_view_of(state, 0, story_id="s")


def sample_view(chapter: int) -> PlayerView:
    state = OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= chapter])
    return player_view_of(state, chapter, story_id="s")


def ref_of(view: PlayerView, entry_id: str) -> str:
    return next(r for r, e in public_entries(view) if e.id == entry_id)


async def ask(question: str, view: PlayerView, state, plan, reply: dict):
    fake = FakeLLM.scripted([json.dumps(reply, ensure_ascii=False)])
    out = await ask_narrator_reply(question, view, llm=metered(fake), config=CFG,
                                   truth_names=leak_names(state), plan=plan, story_brief="",
                                   quota=Quota())
    return fake, out


# --- cờ nhân vật chính trong player_view -------------------------------------------------------


def test_entry_knows_when_it_is_the_protagonist():
    view = sample_view(1)
    flags = {e.id: e.is_protagonist for e in view.entries}
    assert flags["minh"] is True
    assert [i for i, f in flags.items() if f] == ["minh"]


def test_view_at_chapter_0_is_the_protagonist_alone():
    _, _, view = world()
    [entry] = view.entries
    assert entry.id == PROTAGONIST_ID and entry.is_protagonist and view.lies == ()


def test_is_protagonist_defaults_to_false_for_hand_built_entries():
    entry = PlayerEntry("x", "Character", "Ai đó", (), 1, "q", (), ("q",))
    assert entry.is_protagonist is False


# --- sổ tay cho model ---------------------------------------------------------------------------


def test_only_the_protagonist_line_carries_the_player_label():
    _, _, view = world()
    text = render_notebook(view)
    assert PROTAGONIST_LABEL in text and text.count(PROTAGONIST_LABEL) == 1
    big = sample_view(5)
    lines = [ln for ln in render_notebook(big).split("\n") if PROTAGONIST_LABEL in ln]
    assert len(lines) == 1 and "Trần Minh" in lines[0]


def test_label_does_not_change_public_refs_or_other_lines():
    view = sample_view(5)
    lines = render_notebook(view).split("\n")
    plain = [ln for ln in lines if PROTAGONIST_LABEL not in ln]
    assert len(plain) == len(lines) - 1
    refs = [r for r, _ in public_entries(view)]
    assert refs == [f"m{i}" for i in range(1, len(refs) + 1)]


def test_system_prompt_tells_the_model_who_toi_is():
    assert PROTAGONIST_LABEL in SYSTEM_PROMPT
    assert "tôi" in SYSTEM_PROMPT


def test_retrieval_always_keeps_the_protagonist_entry():
    from tests.unit.test_notebook_select import SMALL, big_view, entry

    me = entry(7, "Character", "Lục Vân", chapter=1, quote="Lục Vân bước ra khỏi cổng.")
    me = PlayerEntry(me.id, me.kind, me.text, me.aliases, me.since_chapter, me.quote, me.about,
                     me.quotes, is_protagonist=True)
    view = big_view(extra=(me,))
    sel = select_notebook("Hôm nay trời thế nào?", view, SMALL)
    assert sel.partial and "e7" in {e.id for _, e in sel.entries}


# --- người kể -----------------------------------------------------------------------------------


async def test_narrator_answers_what_my_name_is_at_chapter_0():
    state, plan, view = world()
    name = view.entries[0].text
    fake, out = await ask("Tôi tên là gì?", view, state, plan,
                          {"known": True, "answer": f"Bạn tên là {name}.",
                           "entry_ids": [ref_of(view, PROTAGONIST_ID)]})
    assert len(fake.calls) == 1  # sổ tay không còn rỗng nên model được gọi
    assert out.blocked is None and out.answer == f"Bạn tên là {name}."


async def test_context_marks_the_protagonist_and_keeps_the_name_inside_a_data_block():
    state, plan, view = world()
    name = view.entries[0].text
    fake, _ = await ask("Tôi tên là gì?", view, state, plan,
                        {"known": False, "answer": None, "entry_ids": []})
    [messages] = fake.calls
    system = next(m.content for m in messages if m.role == "system")
    user = next(m.content for m in messages if m.role == "user")
    assert name not in system  # G4: chữ người chơi không vào vai system
    block = user[user.index(OPEN_TAG_START):]
    assert name in block and PROTAGONIST_LABEL in block
    notebook_block = user.split('source="notebook">')[1].split("</player_data>")[0]
    assert name in notebook_block


async def test_context_at_chapter_0_has_nothing_else_of_the_world():
    """G1: ngoài nhân vật chính, không tên hay chữ nào của lớp truth đi vào context."""
    state, plan, view = world()
    fake, _ = await ask("Tôi tên là gì?", view, state, plan,
                        {"known": False, "answer": None, "entry_ids": []})
    context = render_context(fake.calls[0])
    for nid, names in leak_names(state).items():
        if nid == PROTAGONIST_ID:
            continue
        for n in names:
            assert n not in context, (nid, n)


async def test_answer_naming_the_protagonist_is_not_a_leak():
    state, plan, view = world()
    name = view.entries[0].text
    assert check_leaks(f"Bạn tên là {name}.", view=view, truth_names=leak_names(state),
                       plan=plan, story_brief="", scope="player_path") == []


async def test_not_known_is_still_returned_for_other_questions_at_chapter_0():
    state, plan, view = world()
    fake, out = await ask("Ai là kẻ thù của tôi?", view, state, plan,
                          {"known": False, "answer": None, "entry_ids": []})
    assert out.answer == NOT_KNOWN and len(fake.calls) == 1


@pytest.mark.parametrize("chapter", [1, 3, 5])
def test_other_entries_of_the_sample_are_unchanged_by_the_flag(chapter):
    view = sample_view(chapter)
    flagged = Counter(e.is_protagonist for e in view.entries)
    assert flagged[True] == 1 and flagged[False] == len(view.entries) - 1
