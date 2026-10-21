"""G2: dò lộ bí mật trên chữ sắp hiện cho người chơi. Bằng code, không gọi model.

Luật tên (D-61): chỉ cấm tên bí mật, (a) tên thật bị giấu sau biệt danh và (b) tên trong
`Secret.protects` của bí mật còn hiệu lực. `scope` nói bí mật nào còn hiệu lực: `scene` theo khoảng
lộ, `player_path` mọi bí mật chưa có trong player_view."""

import json
import logging
import unicodedata
from pathlib import Path

import pytest

from tests.pipeline_fixtures import SETUP_PC_NAME, setup_chapter_0
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, PlayerEntry, PlayerView, read_sample
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.setup import PROTAGONIST_ID
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import (
    LeakKind,
    check_leaks,
    ensure_no_leak,
    leak_names,
    protected_ids,
    strip_diacritics,
)

SAMPLE = read_sample()
PLAN = StoryPlan.model_validate({
    "acts": [{"name": "mở đầu", "from_chapter": 1, "to_chapter": 12}],
    "secrets": [
        {"fact_id": "f_gu_old_hac_ky", "reveal_from_chapter": 2, "reveal_to_chapter": 3,
         "leak_terms": [["Lão Gù", "Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6,
         "leak_terms": [["Lan", "gián điệp"], ["Lan", "người của Hội Hắc Kỳ"]]},
        {"fact_id": "f_lan_killed_gu", "reveal_from_chapter": 7, "reveal_to_chapter": 9,
         "leak_terms": [["Lan", "giết", "Lão Gù"]]},
    ],
})


def through(chapter: int) -> OverlayState:
    return OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= chapter])


def leaks(text: str, chapter: int, plan: StoryPlan = PLAN, state: OverlayState | None = None,
          brief: str = "", scope: str = "scene"):
    state = state or through(chapter)
    return check_leaks(
        text, view=player_view_of(state, chapter), truth_names=state.named_nodes(), plan=plan,
        story_brief=brief, scope=scope,
    )


def with_protects(plan: StoryPlan, **protects: list[str]) -> StoryPlan:
    """Bản sao kế hoạch, thêm `protects` cho các bí mật theo fact_id."""
    data = plan.model_dump()
    for s in data["secrets"]:
        s["protects"] = protects.get(s["fact_id"], s["protects"])
    return StoryPlan.model_validate(data)


# --- scope bắt buộc -----------------------------------------------------------------------------


def test_scope_has_no_default():
    view = player_view_of(through(4), 4)
    with pytest.raises(TypeError):
        check_leaks("Minh rót trà.", view=view, truth_names={}, plan=PLAN,  # type: ignore[call-arg]
                    story_brief="")
    with pytest.raises(TypeError):
        ensure_no_leak("Minh rót trà.", view=view, truth_names={}, plan=PLAN,  # type: ignore[call-arg]
                       story_brief="")
    with pytest.raises(ValueError, match="scope"):
        check_leaks("Minh rót trà.", view=view, truth_names={}, plan=PLAN, story_brief="",
                    scope="chapter")  # type: ignore[arg-type]


# --- (a) tên thật bị giấu sau biệt danh ------------------------------------------------------


@pytest.mark.parametrize("scope", ["scene", "player_path"])
def test_real_name_behind_a_nickname_is_a_leak(scope):
    """Truyện mẫu chương 4: người chơi biết "gã lái đò mặt sẹo", chưa biết đó là Lý Thất."""
    [hit] = leaks("Gã lái đò mặt sẹo, tức Lý Thất, buộc thuyền trước quán.", 4, scope=scope)
    assert (hit.kind, hit.term) == (LeakKind.NAME, "Lý Thất")


def test_real_name_after_reveal_is_fine():
    assert leaks("Cuối thư ký tên Lý Thất.", 5) == []
    assert leaks("Cuối thư ký tên Lý Thất.", 5, scope="player_path") == []


def test_name_without_diacritics_or_case_is_caught():
    assert [h.term for h in leaks("tuc ly that, nguoi cua hoi", 4)] == ["Lý Thất"]


def test_common_noun_alias_is_never_forbidden():
    # "thanh kiếm" là biệt danh trong lớp truth của Thanh Sương, nhưng không có tên riêng nào.
    assert leaks("Minh lau thanh kiếm.", 1) == []


def test_name_said_in_reveal_quote_counts_as_known():
    # ch01: "Tên thật của lão là Hồ Sĩ Bằng, nhưng cả phố chỉ gọi lão là Lão Gù" (known_as: Lão Gù).
    assert leaks("Hồ Sĩ Bằng ngồi bên bếp lò nguội.", 1) == []


def _known_as(node_id: str, known_as: str, quote: str) -> ChangePackage:
    return ChangePackage.model_validate({
        "commit_id": "c1", "nodes": [{"id": "ch1", "label": "Chapter", "number": 1}],
        "edges": [{"type": "REVEALED_TO_PLAYER", "from": node_id, "to": "ch1",
                   "valid_from_chapter": 1, "quote": quote, "known_as": known_as}],
    })


def _world(*nodes: tuple[str, str, list[str]]) -> OverlayState:
    return OverlayState(EmptyState(), [ChangePackage.model_validate({"commit_id": "c0", "nodes": [
        {"id": i, "label": "Character", "props": {"name": name, "aliases": aliases}}
        for i, name, aliases in nodes]})])


@pytest.mark.parametrize(("known", "text"), [
    ("Tĩnh Lan", "Diệp Tĩnh Lan khẽ cười."),  # tên đầy đủ chứa tên đã hé lộ
    ("Đoàn sư huynh", "Đoàn Khương bước tới."),  # chung họ với tên đã hé lộ
])
def test_fuller_form_of_a_revealed_name_is_not_hidden(known, text):
    base = _world(("diep_tinh_lan", "Diệp Tĩnh Lan", ["Tĩnh Lan"]),
                  ("doan_khuong", "Đoàn Khương", ["Đoàn sư huynh"]))
    node = "diep_tinh_lan" if "Lan" in known else "doan_khuong"
    state = OverlayState(base, [_known_as(node, known, f"{known} đứng ở cửa")])
    plan = StoryPlan.model_validate({"acts": [{"name": "a", "from_chapter": 1, "to_chapter": 3}]})
    assert leaks(text, 1, plan=plan, state=state) == []


def test_unrelated_real_name_behind_a_title_is_hidden():
    base = _world(("gu", "Hồ Sĩ Bằng", ["Lão Gù"]))
    state = OverlayState(base, [_known_as("gu", "Lão Gù", "Lão Gù ngồi bên lò")])
    plan = StoryPlan.model_validate({"acts": [{"name": "a", "from_chapter": 1, "to_chapter": 3}]})
    assert [h.term for h in leaks("Hồ Sĩ Bằng gật đầu.", 1, plan=plan, state=state)] == [
        "Hồ Sĩ Bằng"]


# --- tên lớp truth không bí mật (D-61) -------------------------------------------------------


@pytest.mark.parametrize("scope", ["scene", "player_path"])
def test_unprotected_truth_name_is_not_a_secret(scope):
    """Trước D-61 mọi tên chưa có trong player_view đều bị cấm. Giờ trang được nêu tên đó; code tự
    hé lộ nút (safety/reveal.py)."""
    assert leaks("Họ là người của Hội Hắc Kỳ.", 1, scope=scope) == []


# --- (b) tên được kế hoạch bảo vệ ------------------------------------------------------------
# Thế giới nhỏ: người áo đen là Lâm Hắc Y (bí mật lộ ở chương 3–4). Nút chưa từng được hé lộ, nên
# chỉ luật (b) cấm tên đó.

MASK_PLAN = StoryPlan.model_validate({
    "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
    "secrets": [{"fact_id": "f_mask", "reveal_from_chapter": 3, "reveal_to_chapter": 4,
                 "leak_terms": [["người áo đen", "Lâm Hắc Y"]], "protects": ["hac_y"]}],
})
MASK_TEXT = "Lâm Hắc Y đứng ở đầu bến."


def mask_world(revealed_at: int | None = None) -> OverlayState:
    nodes = [
        {"id": PROTAGONIST_ID, "label": "Character",
         "props": {"name": "Kỷ Trầm Uyên", "is_protagonist": True, "user_authored": True}},
        {"id": "hac_y", "label": "Character",
         "props": {"name": "Lâm Hắc Y", "aliases": ["người áo đen"]}},
        {"id": "f_mask", "label": "Fact", "props": {"text": "Người áo đen là Lâm Hắc Y"}},
    ]
    packages = [ChangePackage.model_validate({"commit_id": "c0", "nodes": nodes})]
    if revealed_at is not None:
        packages.append(ChangePackage.model_validate({
            "commit_id": f"c{revealed_at}",
            "nodes": [{"id": f"ch{revealed_at}", "label": "Chapter", "number": revealed_at}],
            "edges": [{"type": "REVEALED_TO_PLAYER", "from": "f_mask", "to": f"ch{revealed_at}",
                       "valid_from_chapter": revealed_at, "quote": "hắn đã ở đó từ đầu"}],
        }))
    return OverlayState(EmptyState(), packages)


def mask_hits(text: str, chapter: int, scope: str, *, plan: StoryPlan = MASK_PLAN,
              revealed_at: int | None = None):
    state = mask_world(revealed_at)
    return check_leaks(text, view=player_view_of(state, chapter), truth_names=leak_names(state),
                       plan=plan, story_brief="", scope=scope)


def test_protected_name_is_blocked_before_its_secret_window():
    [hit] = mask_hits(MASK_TEXT, 1, "scene")
    assert (hit.kind, hit.term) == (LeakKind.NAME, "Lâm Hắc Y")
    unprotected = with_protects(MASK_PLAN, f_mask=[])
    assert mask_hits(MASK_TEXT, 1, "scene", plan=unprotected) == []


def test_lowercase_alias_of_a_protected_node_is_never_forbidden():
    assert mask_hits("Người áo đen đứng ở đầu bến.", 1, "scene") == []


def test_protected_name_is_allowed_in_scene_inside_the_window():
    assert mask_hits(MASK_TEXT, 3, "scene") == []


def test_player_path_blocks_protected_name_until_the_secret_is_in_player_view():
    """Trong khoảng lộ mà cảnh chưa hé lộ: người kể và lựa chọn vẫn không được nói tên đó."""
    assert [h.term for h in mask_hits(MASK_TEXT, 3, "player_path")] == ["Lâm Hắc Y"]
    assert [h.term for h in mask_hits(MASK_TEXT, 6, "player_path")] == ["Lâm Hắc Y"]
    assert mask_hits(MASK_TEXT, 3, "player_path", revealed_at=3) == []


def test_revealed_secret_no_longer_protects_in_any_scope():
    state = mask_world(revealed_at=2)
    view = player_view_of(state, 2)
    for scope in ("scene", "player_path"):
        assert protected_ids(MASK_PLAN, view, scope) == set()
    assert protected_ids(MASK_PLAN, player_view_of(mask_world(), 2), "scene") == {"hac_y"}


# --- bí mật theo story_plan ----------------------------------------------------------------


def test_secret_before_window_is_a_leak():
    [hit] = leaks("Minh không ngờ Lan là gián điệp.", 4)
    assert hit.kind is LeakKind.SECRET
    assert hit.excerpt == "Lan là gián điệp"


def test_secret_without_diacritics_is_caught():
    assert [h.kind for h in leaks("Minh khong ngo Lan la gian diep.", 4)] == [LeakKind.SECRET]


def test_secret_inside_window_is_fine_in_a_scene():
    assert leaks("Lan là gián điệp.", 5, state=through(4)) == []


def test_player_path_catches_a_secret_past_its_window_start_that_was_never_revealed():
    """Hồi quy tu-tien-1 (D-60): khoảng lộ 3–6, chưa hề hé lộ. Từ chương 3 người kể nói được bí mật
    mà bộ dò không bắt, vì `leak_terms` chỉ áp trước `reveal_from_chapter`."""
    text = "Tôi biết Đoàn Khắc làm giả phù âm."
    for chapter in (3, 4, 6):
        assert run1_hits(text, brief="", chapter=chapter, scope="scene") == []
        assert [h.kind for h in run1_hits(text, brief="", chapter=chapter,
                                          scope="player_path")] == [LeakKind.SECRET]


def test_player_path_still_frees_a_secret_once_it_is_in_player_view():
    # Truyện mẫu chương 5: f_lan_spy đã hé lộ.
    assert leaks("Lan là gián điệp.", 5, scope="player_path") == []
    assert leaks("Lan là gián điệp.", 4, scope="player_path")


def test_secret_phrases_in_different_sentences_do_not_hit():
    assert leaks("Lan rót trà. Ngoài chợ người ta đồn có gián điệp.", 4) == []


def test_common_noun_lan_is_not_the_character():
    # "lan" (hoa lan) viết thường: tên một từ so có phân biệt hoa thường.
    assert leaks("Ông lão bán hoa lan kể chuyện gián điệp thời chiến.", 4) == []


def test_spy_word_alone_is_fine():
    assert leaks("Gián điệp là nghề nguy hiểm.", 4) == []


def test_secret_revealed_early_by_choice_is_no_longer_secret():
    """Lộ sớm hợp lệ (by_choice, D-22): từ đó chữ nói về bí mật không còn là lộ."""
    early = ChangePackage.model_validate({
        "commit_id": "c4",
        "nodes": [{"id": "ch4", "label": "Chapter", "number": 4}],
        "edges": [{"type": "REVEALED_TO_PLAYER", "from": "f_lan_spy", "to": "ch4",
                   "valid_from_chapter": 4, "quote": "Lan là gián điệp.", "by_choice": "c3"}],
    })
    for scope in ("scene", "player_path"):
        assert leaks("Lan là gián điệp.", 4, state=OverlayState(through(3), [early]),
                     scope=scope) == []


def test_secret_without_leak_terms_warns(caplog):
    plan = StoryPlan.model_validate({
        "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 9}],
        "secrets": [{"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6}],
    })
    with caplog.at_level(logging.WARNING, logger="writory.safety.leak"):
        leaks("Trời mưa.", 4, plan)
    assert "f_lan_spy" in caplog.text
    assert "leak_terms" in caplog.text


# --- vị trí, chuẩn hoá ---------------------------------------------------------------------


def test_positions_refer_to_nfc_text():
    text = unicodedata.normalize("NFD", "Ở bến, Lý Thất cười.")
    [hit] = leaks(text, 4)
    nfc = unicodedata.normalize("NFC", text)
    assert nfc[hit.start : hit.end] == hit.excerpt == "Lý Thất"


def test_strip_diacritics_keeps_length_and_case():
    s = "Đêm Lão Gù chết, ĐỒNG hồ điểm"
    out = strip_diacritics(s)
    assert len(out) == len(s)
    assert out == "Dem Lao Gu chet, DONG ho diem"


# --- văn sạch của truyện mẫu ---------------------------------------------------------------


@pytest.mark.parametrize("chapter", [c for c in SAMPLE.chapters if c.text],
                         ids=lambda c: f"ch{c.number}")
def test_hand_written_sample_chapter_has_no_leak(chapter):
    assert leaks(chapter.text, chapter.number) == []


# --- chặn và báo lỗi (G12) -----------------------------------------------------------------


def test_leak_reads_only_player_view():
    """Một định nghĩa "người chơi biết gì" (G1, D-16): bộ dò không đọc cạnh, chỉ đọc PlayerView.
    Một PlayerView có "Lý Thất" ở chương 4 thì tên đó không còn bị cấm."""
    view = player_view_of(through(4), 4)
    entry = PlayerEntry("ly_that", "Character", "Lý Thất", (), 4, "Lý Thất", (), ("Lý Thất",))
    patched = PlayerView(view.story_id, 4, (*view.entries, entry), view.lies)
    text = "Lý Thất cười."
    names = through(4).named_nodes()
    assert check_leaks(text, view=view, truth_names=names, plan=PLAN, story_brief="",
                       scope="scene")
    assert check_leaks(text, view=patched, truth_names=names, plan=PLAN, story_brief="",
                       scope="scene") == []


def test_ensure_no_leak_blocks_without_revealing_the_secret():
    with pytest.raises(WritoryError) as exc:
        ensure_no_leak("Minh không ngờ Lan là gián điệp.", view=player_view_of(through(4), 4),
                       truth_names=through(4).named_nodes(), plan=PLAN, story_brief="",
                       scope="scene")
    err = exc.value
    assert err.code is ErrorCode.SCENE_LEAK_BLOCKED
    shown = json.dumps(err.player_payload(), ensure_ascii=False) + str(err)
    for secret in ("gián điệp", "f_lan_spy", "Lý Thất"):
        assert secret not in shown


def test_ensure_no_leak_passes_clean_text():
    ensure_no_leak("Minh rót trà.", view=player_view_of(through(4), 4),
                   truth_names=through(4).named_nodes(), plan=PLAN, story_brief="",
                   scope="player_path")


# --- tên do người chơi viết (D-48) -----------------------------------------------------------

_PC_NAME = SETUP_PC_NAME


def setup_world(*, protagonist_aliases: tuple[str, ...] = ()) -> tuple[OverlayState, StoryPlan]:
    package, plan = setup_chapter_0(protagonist_aliases=protagonist_aliases)
    return OverlayState(EmptyState(), [package]), plan


def test_leak_names_spare_only_the_name_the_player_wrote():
    state, _ = setup_world(protagonist_aliases=("Vân Nhi",))
    names = leak_names(state)
    assert names[PROTAGONIST_ID] == ("Vân Nhi",)  # chỉ miễn `name`; biệt danh vẫn bị dò
    assert names["to_nguyet_hoa"] == ("Tô Nguyệt Hoa", "Nguyệt Hoa", "cô gái áo lam")
    assert {k: v for k, v in names.items() if k != PROTAGONIST_ID} == {
        k: v for k, v in state.named_nodes().items() if k != PROTAGONIST_ID}
    plain, _ = setup_world()
    assert PROTAGONIST_ID not in leak_names(plain)


def test_player_written_name_is_not_a_leak_before_any_reveal():
    state, plan = setup_world()
    view = player_view_of(state, 1)
    assert [e.id for e in view.entries] == [PROTAGONIST_ID]  # chương 0: chỉ nhân vật chính (D-74)
    text = f"{_PC_NAME} đẩy cửa lò rèn bước ra sân."
    for scope in ("scene", "player_path"):
        assert check_leaks(text, view=view, truth_names=leak_names(state), plan=plan,
                           story_brief="", scope=scope) == []


def test_unrevealed_names_are_secret_only_when_the_plan_protects_them():
    """D-61: tên lớp truth chưa hé lộ không còn bị cấm, trừ khi kế hoạch bảo vệ nó. Bảo vệ nhân vật
    chính thì chỉ biệt danh bị cấm, tên người chơi chọn thì không bao giờ (D-48)."""
    state, plan = setup_world(protagonist_aliases=("Vân Nhi",))
    text = f"{_PC_NAME} nhìn Tô Nguyệt Hoa gọi Vân Nhi lại."

    def terms(p: StoryPlan) -> set[str]:
        return {h.term for h in check_leaks(text, view=player_view_of(state, 1), plan=p,
                                            truth_names=leak_names(state), story_brief="",
                                            scope="scene")}

    assert terms(plan) == set()
    protected = with_protects(plan, f_nguyet_hoa_huyet_y=["to_nguyet_hoa", PROTAGONIST_ID])
    assert {"Tô Nguyệt Hoa", "Vân Nhi"} <= terms(protected)
    assert _PC_NAME not in terms(protected)


# --- chữ người chơi đã đọc lúc khởi tạo (D-52) ------------------------------------------------
# Bối cảnh, hướng truyện và nhân vật chính đã hiện cho người chơi lúc khởi tạo (G1, D-37); thiết lập
# truyện (`setup.story_brief`, lưu ở `stories.brief`) gom đúng chữ đó. Tên có trong đó không còn là
# bí mật đối với người chơi, kể cả tên được bảo vệ. Nhóm `leak_terms` của bí mật thì vẫn dò như cũ.

RUN1_NAMES = {"Huyền Sát Tông", "Tín Vật Huyền Nguyệt", "Động Linh Mạch"}  # notes.md mục 4
RUN1_BRIEF = (Path(__file__).parents[1] / "fixtures" / "leak" / "run-tu-tien-1-brief.txt"
              ).read_text(encoding="utf-8")
RUN1_SCENE = ("Người bên ngoài sẽ rơi vào tay Huyền Sát Tông. Bàn tay tôi khép lại quanh Tín Vật "
              "Huyền Nguyệt. Phía động linh mạch, một đoạn phù văn tắt hẳn.")


def run1_world(protects: tuple[str, ...] = ()) -> tuple[OverlayState, StoryPlan]:
    """Thế giới thu nhỏ của lần chạy tu-tien-1 ở chương 0: người chơi chưa biết gì (D-38)."""
    def node(i, label, name, **props):
        return {"id": i, "label": label, "props": {"name": name, **props}}

    package = ChangePackage.model_validate({"commit_id": "c0", "nodes": [
        node(PROTAGONIST_ID, "Character", "Kỷ Trầm Uyên", is_protagonist=True, user_authored=True),
        node("doan_khac", "Character", "Đoàn Khắc"),
        node("huyen_sat_tong", "Faction", "Huyền Sát Tông"),
        node("tinh_vat_huyen_nguyet", "Item", "Tín Vật Huyền Nguyệt", aliases=["tín vật"]),
        node("dong_linh_mach", "Location", "Động Linh Mạch"),
        {"id": "f_doan_khac_tao_phu_gia", "label": "Fact",
         "props": {"text": "Đoàn Khắc làm giả phù âm"}},
    ]})
    plan = StoryPlan.model_validate({
        "acts": [{"name": "a", "from_chapter": 1, "to_chapter": 6}],
        "secrets": [{"fact_id": "f_doan_khac_tao_phu_gia", "reveal_from_chapter": 3,
                     "reveal_to_chapter": 6, "leak_terms": [["Đoàn Khắc", "làm giả phù âm"]],
                     "protects": list(protects)}],
    })
    return OverlayState(EmptyState(), [package]), plan


def run1_hits(text: str, brief: str, *, chapter: int = 1, scope: str = "scene",
              protects: tuple[str, ...] = ()) -> list:
    state, plan = run1_world(protects)
    return check_leaks(text, view=player_view_of(state, chapter), truth_names=leak_names(state),
                       plan=plan, story_brief=brief, scope=scope)


def test_run1_names_are_not_secret_with_or_without_setup_text():
    """Hồi quy tu-tien-1 (notes.md mục 4): chương 1 bị viết lại vì ba tên này. Chúng không được kế
    hoạch bảo vệ và chưa từng hé lộ dưới biệt danh, nên không phải tên bí mật (D-61)."""
    assert run1_hits(RUN1_SCENE, brief="") == []
    assert run1_hits(RUN1_SCENE, brief=RUN1_BRIEF) == []


def test_protected_names_in_setup_text_the_player_read_are_not_secret():
    """D-52 giữ nguyên cho tên được bảo vệ: tên đã hiện cho người chơi lúc khởi tạo là chữ đã thấy.
    Thiết lập thật của lần chạy không có ba tên này (chỉ "tín vật", "linh mạch" viết thường)."""
    protects = ("huyen_sat_tong", "tinh_vat_huyen_nguyet", "dong_linh_mach")
    # Bộ dò so cụm nhiều từ không phân biệt hoa thường, nên "động linh mạch" cũng trúng (D-52).
    assert {h.term for h in run1_hits(RUN1_SCENE, brief="", protects=protects)} == RUN1_NAMES
    assert {h.term for h in run1_hits(RUN1_SCENE, brief=RUN1_BRIEF,
                                      protects=protects)} == RUN1_NAMES
    brief = ("Bối cảnh: Cô Phong bị Huyền Sát Tông vây. Sư huynh trao cho bạn Tín Vật Huyền "
             "Nguyệt rồi biến mất về phía Động Linh Mạch.")
    assert run1_hits(RUN1_SCENE, brief=brief, protects=protects) == []


def test_setup_text_never_unlocks_secret_leak_terms():
    """Chữ khởi tạo chỉ tính cho tên. Bí mật theo kế hoạch vẫn dò theo `leak_terms` (D-26), kể cả
    khi thiết lập truyện có đủ các cụm (người chơi tự gõ vào quá khứ nhân vật chính chẳng hạn)."""
    hits = run1_hits("Tôi biết Đoàn Khắc làm giả phù âm.",
                     brief="Quá khứ: nghi Đoàn Khắc làm giả phù âm.")
    assert [h.kind for h in hits] == [LeakKind.SECRET]
    assert leaks("Minh không ngờ Lan là gián điệp.", 4, brief="Lan là gián điệp.")


def test_protagonist_name_in_setup_text_counts_as_seen_but_new_words_do_not():
    """D-52 đổi một phần D-48: thiết lập truyện có tên nhân vật chính, nên từ của tên đó là chữ đã
    thấy. Biệt danh được bảo vệ chỉ gồm các từ ấy không còn bị cấm; biệt danh có từ mới vẫn bị cấm."""
    package, plan = setup_chapter_0(protagonist_aliases=("Thanh Vân", "Vân Nhi"))
    plan = with_protects(plan, f_nguyet_hoa_huyet_y=[PROTAGONIST_ID])
    brief = f"Nhân vật chính: {_PC_NAME}. Quá khứ: con một thợ rèn."
    text = "Có người gọi Thanh Vân, rồi gọi Vân Nhi."

    def terms(pkg: ChangePackage, b: str) -> set[str]:
        state = OverlayState(EmptyState(), [pkg])
        return {h.term for h in check_leaks(text, view=player_view_of(state, 1), plan=plan,
                                            truth_names=leak_names(state), story_brief=b,
                                            scope="scene")}

    # Gói chưa hé lộ nhân vật chính (như truyện chạy trước D-74): thiết lập truyện là chữ đã thấy.
    data = package.model_dump(mode="json", by_alias=True)
    data["edges"] = [e for e in data["edges"] if e["type"] != "REVEALED_TO_PLAYER"]
    unrevealed = ChangePackage.model_validate(data)
    assert terms(unrevealed, "") == {"Thanh Vân", "Vân Nhi"}
    assert terms(unrevealed, brief) == {"Vân Nhi"}
    # D-74: nhân vật chính hé lộ ở chương 0 nên tên đó nằm sẵn trong player_view, dù không có brief.
    assert terms(package, "") == {"Vân Nhi"}
    assert terms(package, brief) == {"Vân Nhi"}


def test_setup_text_counts_only_the_names_it_contains():
    """Tên bí mật vẫn bị cấm dù thiết lập truyện có chữ khác (D-26, D-48 giữ nguyên)."""
    hits = leaks("Gã lái đò, tức Lý Thất, buộc thuyền.", 4, brief="Kiếm hiệp, phố Bến Sương.")
    assert [h.term for h in hits] == ["Lý Thất"]
