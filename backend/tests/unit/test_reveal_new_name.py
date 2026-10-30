"""Hé lộ lần hai dưới tên chính (D-136, D-17): nút có tên người chơi đã biết dưới một tên khác (biệt
danh trước), nay trang nói ra tên chính lớp truth (tên thật sau). Bộ trích được ghi thêm một cạnh
`REVEALED_TO_PLAYER` (`extract-10`), code tự hé lộ tên chính có nguyên văn trên trang; cả hai cùng một
luật (`safety.reveal.new_name_problem`). Không nhận: tên người chơi đã biết, biệt danh hay chức danh
khác (sổ tay đổi tên hiện liên tục), nút đã hé lộ ở chính chương này (mỗi nút một cạnh hé lộ mỗi
chương), nút có tên đang được kế hoạch bảo vệ mà bí mật chưa có trong player_view (D-61). Không mạng,
không model."""

import json

import pytest

from tests.pipeline_fixtures import (
    EXTRACT_1,
    EXTRACT_2,
    SAMPLE,
    SCENE_1,
    SCENE_2,
    SUMMARY,
    MemoryStore,
    _refs,
    choices_reply,
    extract_reply,
    outline_reply,
)
from tests.pipeline_fixtures import PLAN as SAMPLE_PLAN
from tests.unit.test_pipeline_chapter import kinds, request, run
from writory.graph import ChangePackage, PlayerEntry, PlayerView
from writory.graph.package import quote_in_text
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline import bench_c
from writory.pipeline.bench_run import reject_reason
from writory.pipeline.extract import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    Entity,
    ExtractedEdge,
    ExtractOutput,
    OpenEdge,
    build_messages,
    to_package,
)
from writory.pipeline.story_plan import StoryPlan
from writory.safety.reveal import auto_reveals, new_name_problem
from writory.safety.wrap import OPEN_TAG_START

NICK = "gã lái đò mặt sẹo"
REAL = "Lý Thất"
NAMES = {"ly_that": (REAL, NICK), "lan": ("Phạm Thị Lan", "Lan", "cô Lan"),
         "minh": ("Trần Minh", "Minh")}
SIGNED = "Cuối thư ký tên Lý Thất."


def _entry(node_id: str, text: str, *aliases: str) -> PlayerEntry:
    return PlayerEntry(id=node_id, kind="Character", text=text, aliases=aliases, since_chapter=4,
                       quote=None, about=())


VIEW = PlayerView("s", 5, (_entry("ly_that", NICK), _entry("lan", "Phạm Thị Lan"),
                           _entry("minh", "Trần Minh")), ())


def _auto(text: str, *, view: PlayerView = VIEW, no_new_name=()):
    return auto_reveals(text, chapter=5, chapter_id="ch5", names=NAMES, view=view, skip={"minh"},
                        no_new_name=no_new_name)


# --- luật chung -----------------------------------------------------------------------------------


@pytest.mark.parametrize(("known_as", "shown", "locked", "reason"), [
    (REAL, (NICK,), (), None),
    ("lý thất", (NICK,), (), None),  # cùng khoá so tên của bộ dò lộ
    (REAL, (NICK, REAL), (), "người chơi đã biết nút này dưới tên đó"),
    ("Gã lái đò mặt sẹo", (REAL, NICK), (), "người chơi đã biết nút này dưới tên đó"),
    ("Thất ca", (NICK,), (), "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)"),
    (REAL, (NICK,), ("ly_that",), "tên mới của nút có tên đang được bảo vệ (D-61)"),
])
def test_new_name_problem(known_as, shown, locked, reason):
    assert new_name_problem(known_as, "ly_that", names=NAMES, shown=shown, locked=locked) == reason


def test_an_alias_is_not_a_second_name():
    """Biệt danh hay chức danh lớp truth ("Lan", "cô Lan") không thay tên hiện của nút; tên của nút
    khác cũng không."""
    for alias in ("Lan", "cô Lan"):
        assert new_name_problem(alias, "lan", names=NAMES, shown=("Phạm Thị Lan",), locked=()) == (
            "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)")
    assert new_name_problem("Phạm Thị Lan", "ly_that", names=NAMES, shown=(NICK,), locked=()) == (
        "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)")


def test_every_reason_is_counted_by_the_bench():
    reasons = ["người chơi đã biết nút này dưới tên đó",
               "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)",
               "tên mới của nút có tên đang được bảo vệ (D-61)",
               "đã hé lộ ở chương này: tên mới ghi ở chương sau (D-136)"]
    assert [reject_reason(r) for r in reasons] == reasons


# --- tự hé lộ (code) ----------------------------------------------------------------------------


def test_the_real_name_on_the_page_is_auto_revealed_for_a_known_node():
    text = f"Minh mở thư. {SIGNED} Anh lặng người."
    [edge] = _auto(text)
    assert (edge.type, edge.source, edge.target, edge.valid_from_chapter) == (
        "REVEALED_TO_PLAYER", "ly_that", "ch5", 5)
    assert edge.props == {"quote": "Cuối thư ký tên Lý Thất", "known_as": REAL}
    assert quote_in_text(edge.props["quote"], text)


@pytest.mark.parametrize("text", [
    "Gã lái đò mặt sẹo buộc thuyền.",  # tên người chơi đã biết
    "Phạm Thị Lan rót trà.",  # tên chính người chơi đã biết
    "Cô Lan rót trà.",  # biệt danh, không phải tên chính
])
def test_names_the_player_knows_and_aliases_are_not_revealed_again(text):
    assert _auto(text) == []


def test_locked_nodes_keep_their_name():
    """Bí mật chưa có trong player_view bảo vệ nút (đường người chơi, D-61), hay nút đã hé lộ ở
    chương này: không thêm tên."""
    assert _auto(SIGNED, no_new_name={"ly_that"}) == []


def test_first_reveals_are_unchanged():
    view = PlayerView("s", 5, (_entry("minh", "Trần Minh"),), ())
    assert [(e.source, e.props["known_as"]) for e in _auto(f"Cô Lan rót trà. {SIGNED}", view=view)
            ] == [("lan", "Cô Lan"), ("ly_that", REAL)]


def test_the_new_name_becomes_the_shown_name_and_the_old_one_an_alias():
    """D-17, D-132: chữ hiện là tên của lần hé lộ mới nhất."""
    base = OverlayState(EmptyState(), [SAMPLE.chapters[n].package for n in range(5)])
    view4 = player_view_of(base, 5)
    [ly4] = [e for e in view4.entries if e.id == "ly_that"]
    assert (ly4.text, ly4.aliases) == (NICK, ())
    edges = auto_reveals(SIGNED, chapter=5, chapter_id="ch5", names=base.named_nodes(),
                         view=view4, skip={"minh"}, no_new_name=())
    pkg = ChangePackage.model_validate({
        "commit_id": "c5", "nodes": [{"id": "ch5", "label": "Chapter", "number": 5}],
        "edges": [e.model_dump(by_alias=True) for e in edges]})
    [ly5] = [e for e in player_view_of(OverlayState(base, [pkg]), 5).entries if e.id == "ly_that"]
    assert (ly5.text, ly5.aliases) == (REAL, (NICK,))


# --- bộ trích -----------------------------------------------------------------------------------


def _reveal(node: str, known_as: str, quote: str, target: str = "ch5") -> ExtractedEdge:
    return ExtractedEdge(type="REVEALED_TO_PLAYER", source=node, target=target, kind=None,
                         score=None, how=None, told_by=None, quote=quote, known_as=known_as,
                         role=None)


ENTITIES = [Entity("minh", "Character", "Trần Minh", ("Minh",)),
            Entity("ly_that", "Character", REAL, (NICK,)),
            Entity("lan", "Character", "Phạm Thị Lan", ("Lan", "cô Lan")),
            Entity("ch5", "Chapter", "Chương 5")]
EARLIER = [OpenEdge("REVEALED_TO_PLAYER:ly_that>ch4@4", "REVEALED_TO_PLAYER", "ly_that", "ch4",
                    known_as=NICK),
           OpenEdge("REVEALED_TO_PLAYER:lan>ch1@1", "REVEALED_TO_PLAYER", "lan", "ch1",
                    known_as="Phạm Thị Lan")]
PAGE = f"Minh mở thư. {SIGNED} Cô Lan không về. Gã lái đò mặt sẹo đã đi."


def _package(*edges: ExtractedEdge, open_edges=EARLIER, locked=()):
    return to_package(ExtractOutput(edges=list(edges), close=[], new_facts=[], milestones=[]),
                      chapter=5, commit_id="c5", protagonist_id="minh", chapter_text=PAGE,
                      entities=ENTITIES, open_edges=list(open_edges), locked=locked)


def test_the_extractor_may_record_the_real_name_of_a_known_node():
    package, rejected = _package(_reveal("ly_that", REAL, "Cuối thư ký tên Lý Thất"))
    assert rejected == []
    [edge] = package.edges
    assert edge.props == {"quote": "Cuối thư ký tên Lý Thất", "known_as": REAL}


@pytest.mark.parametrize(("edge", "reason"), [
    (_reveal("ly_that", "Gã lái đò mặt sẹo", "Gã lái đò mặt sẹo đã đi"),
     "người chơi đã biết nút này dưới tên đó"),
    (_reveal("lan", "Cô Lan", "Cô Lan không về"),
     "hé lộ lần hai chỉ nhận tên chính lớp truth của nút (D-17)"),
])
def test_the_extractor_may_not_re_reveal_a_known_name_or_an_alias(edge, reason):
    package, rejected = _package(edge)
    assert package.edges == [] and [why for _, why in rejected] == [reason]


def test_a_node_the_plan_still_protects_gets_no_new_name():
    package, rejected = _package(_reveal("ly_that", REAL, "Cuối thư ký tên Lý Thất"),
                                 locked={"ly_that"})
    assert package.edges == []
    assert rejected == [("REVEALED_TO_PLAYER ly_that→ch5",
                         "tên mới của nút có tên đang được bảo vệ (D-61)")]


def test_a_node_revealed_earlier_in_this_chapter_waits_for_the_next_one():
    """Cùng id cạnh (kiểu, từ, tới, chương): cảnh sau đè cảnh trước khi gộp, mất tên cũ."""
    same = [*EARLIER, OpenEdge("REVEALED_TO_PLAYER:ly_that>ch5@5", "REVEALED_TO_PLAYER", "ly_that",
                               "ch5", known_as=NICK)]
    package, rejected = _package(_reveal("ly_that", REAL, "Cuối thư ký tên Lý Thất"),
                                 open_edges=same)
    assert package.edges == []
    assert [why for _, why in rejected] == ["đã hé lộ ở chương này: tên mới ghi ở chương sau (D-136)"]


def test_a_first_reveal_of_a_locked_node_is_unchanged():
    """D-61 không đổi: lần hé lộ đầu theo luật cũ (bộ dò lộ của cảnh quyết tên trên trang)."""
    package, rejected = _package(_reveal("ly_that", "Gã lái đò mặt sẹo", "Gã lái đò mặt sẹo đã đi"),
                                 open_edges=EARLIER[1:], locked={"ly_that"})
    assert rejected == [] and len(package.edges) == 1


def test_the_sample_story_gold_second_reveal_passes():
    """Truyện mẫu dựng tay ghi Lý Thất ở chương 5 (D-17): đáp án của bài C qua được luật mới."""
    entities, open_edges = bench_c.gold_state(SAMPLE, 5)
    [ly] = [o for o in open_edges if o.type == "REVEALED_TO_PLAYER" and o.source == "ly_that"]
    assert ly.known_as == NICK
    gold = bench_c.gold_package(SAMPLE, 5)
    [edge] = [e for e in gold.edges if e.type == "REVEALED_TO_PLAYER" and e.source == "ly_that"]
    out = ExtractedEdge(type=edge.type, source=edge.source, target=edge.target, kind=None,
                        score=None, how=None, told_by=None, quote=edge.props["quote"],
                        known_as=edge.props["known_as"], role=None)
    text = SAMPLE.chapters[5].text
    package, rejected = to_package(
        ExtractOutput(edges=[out], close=[], new_facts=[], milestones=[]), chapter=5,
        commit_id="c5", protagonist_id=SAMPLE.protagonist, chapter_text=text, entities=entities,
        open_edges=open_edges)
    assert rejected == [] and [e.props["known_as"] for e in package.edges] == [REAL]


# --- đề bộ trích (extract-10) -------------------------------------------------------------------


def test_the_prompt_lists_the_names_the_player_knows():
    messages = build_messages(chapter=5, chapter_id="ch5", protagonist_id="minh", chapter_text=PAGE,
                              entities=ENTITIES, open_edges=EARLIER)
    user = messages[-1].content
    assert f"REVEALED_TO_PLAYER | ly_that → ch4 | người chơi biết là: {NICK}" in user
    assert PROMPT_VERSION == "extract-10"
    assert "tên chính" in SYSTEM_PROMPT and "Đã hé lộ ở chương trước thì không ghi lại." not in (
        SYSTEM_PROMPT)


def test_a_known_name_the_player_wrote_is_data_in_the_prompt():
    """G4: tên người chơi viết (nhân vật chính, `user_authored`) vào đề trong khối dữ liệu."""
    entities = [Entity("minh", "Character", "Kẻ <b>Lạ</b>", user_authored=True), *ENTITIES[1:]]
    edges = [OpenEdge("REVEALED_TO_PLAYER:minh>ch0@0", "REVEALED_TO_PLAYER", "minh", "ch0",
                      known_as="Kẻ <b>Lạ</b>")]
    user = build_messages(chapter=5, chapter_id="ch5", protagonist_id="minh", chapter_text=PAGE,
                          entities=entities, open_edges=edges)[-1].content
    assert "<b>" not in user
    assert (f'minh → ch0 | người chơi biết là:\n\n{OPEN_TAG_START} source="known_as">\n'
            "Kẻ &lt;b&gt;Lạ&lt;/b&gt;\n") in user


# --- đường đi một chương ------------------------------------------------------------------------

LETTER = f"{SIGNED} Minh nhớ tới gã lái đò mặt sẹo buộc thuyền trước quán trà hôm trước."
REVEAL_REAL = {"type": "REVEALED_TO_PLAYER", "source": "ly_that", "target": "ch5",
               "quote": "Cuối thư ký tên Lý Thất.", "known_as": REAL}


def _req():
    return request(commit_id="c-ch5")


def _choices_ch5(messages) -> str:
    """Lựa chọn cuối chương 5: tham chiếu nhân vật bằng tên sổ tay đang hiện (đã đổi sang "Lý Thất")."""
    refs = _refs(messages)
    none = {"tone": None, "lie_content": None, "listeners": [], "feeling": None}
    return json.dumps({"choices": [
        none | {"kind": "action", "text": "Xuống bến tìm Lý Thất.", "about": [refs[REAL]]},
        none | {"kind": "dialogue", "text": "Hỏi Lan về lá thư.", "tone": "truth",
                "listeners": [refs["Phạm Thị Lan"]], "about": [refs["Phạm Thị Lan"]]},
        none | {"kind": "inner", "text": "Thầm nghĩ Lan biết nhiều hơn cô nói.",
                "about": [refs["Phạm Thị Lan"]], "feeling": "nghi ngờ"},
    ]}, ensure_ascii=False)


def _protecting_ly_that() -> StoryPlan:
    data = SAMPLE_PLAN.model_dump()
    next(s for s in data["secrets"] if s["fact_id"] == "f_lan_spy")["protects"] = ["ly_that"]
    return StoryPlan.model_validate(data)


async def test_the_real_name_recorded_by_the_extractor_lets_the_scene_through(tmp_path):
    """Truyện mẫu chương 5: người chơi biết "gã lái đò mặt sẹo" từ chương 4. Tên thật "Lý Thất" bị
    giấu sau biệt danh (luật a của D-61): trang nói ra mà bộ trích ghi tên mới thì cảnh qua bộ dò lộ,
    sổ tay hiện tên thật, biệt danh thành tên khác."""
    text = f"{LETTER}\n\n{SCENE_1}"
    script = [outline_reply(), text, extract_reply([REVEAL_REAL]), outline_reply(), SCENE_2,
              extract_reply(), SUMMARY, _choices_ch5]
    events, outcome, _, store = await run(script, tmp_path, store=MemoryStore(through=4),
                                          req=_req())
    assert kinds(events) == ["scene_ready", "scene_ready", "chapter_committed", "choices_ready"]
    assert all(i.source != "leak" for r in outcome.reviews for i in r.issues)
    [ly] = [e for e in store.player_view(5).entries if e.id == "ly_that"]
    assert (ly.text, ly.aliases) == (REAL, (NICK,))


async def test_a_protected_real_name_is_not_recorded_and_the_scene_is_blocked(tmp_path):
    """Bí mật f_lan_spy (khoảng lộ 5–6, chưa hé lộ) bảo vệ ly_that: bộ trích ghi tên mới thì bị bỏ,
    tên thật còn bị cấm, cảnh bị chặn như trước (D-61)."""
    text = f"{LETTER}\n\n{SCENE_1}"
    script = [outline_reply(), text, extract_reply([REVEAL_REAL]), text,
              extract_reply([REVEAL_REAL])]
    events, outcome, _, _ = await run(script, tmp_path, store=MemoryStore(through=4), req=_req(),
                                      plan=_protecting_ly_that())
    assert kinds(events) == ["scene_blocked"]
    assert all(("REVEALED_TO_PLAYER ly_that→ch5", "tên mới của nút có tên đang được bảo vệ (D-61)")
               in r.rejected for r in outcome.reviews)


async def test_a_non_secret_real_name_on_the_page_is_auto_revealed(tmp_path):
    """Truyện mẫu chương 4: người chơi biết "Lão Gù"; tên thật "Hồ Sĩ Bằng" đã có trong một câu trích
    (chương 1) nên không bị cấm. Trang nêu tên thật mà bộ trích không ghi: code tự hé lộ tên mới."""
    line ="Minh nghĩ tới Hồ Sĩ Bằng."
    script = [outline_reply(), f"{line} {SCENE_1}", EXTRACT_1, outline_reply(), SCENE_2, EXTRACT_2,
              SUMMARY, choices_reply()]
    events, _, _, store = await run(script, tmp_path)
    assert kinds(events) == ["scene_ready", "scene_ready", "chapter_committed", "choices_ready"]
    [(_, _, package)] = store.commits
    [edge] = [e for e in package.edges if e.type == "REVEALED_TO_PLAYER" and e.source == "gu"]
    assert edge.props == {"quote": "Minh nghĩ tới Hồ Sĩ Bằng", "known_as": "Hồ Sĩ Bằng"}
