"""Tự hé lộ tên trang vừa nêu, và tên người chơi thấy phải đúng nút (safety/reveal.py, D-62).
Cùng hồi quy tu-tien-3: luật tên của bộ dò lộ chỉ cấm tên bí mật (D-61). Không mạng, không model."""

import json
from pathlib import Path

import pytest

from writory.graph import ChangePackage, PlayerView
from writory.graph.package import quote_in_text
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.setup import PROTAGONIST_ID
from writory.pipeline.story_plan import StoryPlan
from writory.safety.leak import check_leaks, leak_names, protected_ids
from writory.safety.reveal import auto_reveals, known_as_conflicts

# --- hồi quy tu-tien-3 -------------------------------------------------------------------------
# evals/results/2026-10-20-run-tu-tien-3/: chương 1 cảnh 1 bị chặn cả hai lần bấm thử lại
# (`SCENE_LEAK_BLOCKED`, chỉ `leak:name`) vì các tên giới thiệu bình thường dưới đây. Fixture: kế
# hoạch, gói chương 0 và thiết lập truyện của lần chạy đó.

TT3 = json.loads((Path(__file__).parents[1] / "fixtures" / "leak" / "run-tu-tien-3-ch0.json")
                 .read_text(encoding="utf-8"))
TT3_PLAN = StoryPlan.model_validate(TT3["plan"])
TT3_BRIEF = TT3["story_brief"]
BLOCKED_IN_RUN = ("Đoàn Khương", "Diệp Tĩnh Lan", "sân Vấn Kiếm", "kho kiếm cụ", "chấp sự Lương",
                  "phòng chấp sự")  # notes.md của lần chạy, mục "Tên bị cấm"
S_DOAN = "Đoàn Khương chặn ngang lối lên sân Vấn Kiếm, tay đặt trên chuôi kiếm"
S_LAN = "Sau lưng hắn, Diệp Tĩnh Lan khẽ lắc đầu"
S_KHO = "Tôi nhớ lại lúc sáng ở kho kiếm cụ, khi chấp sự Lương còn dặn từng món phải ghi sổ"
S_PHONG = "Cửa phòng chấp sự được phát hiện khóa từ bên trong"  # cũng là chữ của một Fact
TT3_SCENE = (f"{S_DOAN}. {S_LAN}.\n\n- Đoàn sư huynh, để nàng nói hết đã. - Tĩnh Lan nói.\n\n"
             f"{S_KHO}. {S_PHONG}.")


def tt3_state() -> OverlayState:
    return OverlayState(EmptyState(), [ChangePackage.model_validate(TT3["package"])])


def tt3_reveals(text: str = TT3_SCENE, view: PlayerView | None = None, skip=None):
    state = tt3_state()
    view = view or player_view_of(state, 1)
    return auto_reveals(text, chapter=1, chapter_id="ch1", names=state.named_nodes(), view=view,
                        skip={PROTAGONIST_ID} if skip is None else skip, no_new_name=())


def test_tu_tien_3_scene_names_are_not_blocked():
    """Hồi quy: các tên này không được kế hoạch bảo vệ và chưa nút nào được biết qua biệt danh,
    nên không phải tên bí mật (D-61). Trước đây chặn cả cảnh."""
    assert all(name in TT3_SCENE for name in BLOCKED_IN_RUN)
    state = tt3_state()
    view = player_view_of(state, 1)
    assert view.entries == ()  # chương 0: người chơi chưa biết gì (D-38)
    for scope in ("scene", "player_path"):
        assert check_leaks(TT3_SCENE, view=view, truth_names=leak_names(state), plan=TT3_PLAN,
                           story_brief=TT3_BRIEF, scope=scope) == []


def test_tu_tien_3_names_are_auto_revealed_with_their_sentence():
    edges = tt3_reveals()
    got = {e.source: (e.props["known_as"], e.props["quote"]) for e in edges}
    assert got == {
        "doan_khuong": ("Đoàn Khương", S_DOAN),  # ưu tiên tên hơn biệt danh "Đoàn sư huynh"
        "san_van_kiem": ("sân Vấn Kiếm", S_DOAN),
        "diep_tinh_lan": ("Diệp Tĩnh Lan", S_LAN),
        "kho_kiem_cu": ("kho kiếm cụ", S_KHO),
        "luong_khac": ("chấp sự Lương", S_KHO),
        "phong_chap_su": ("phòng chấp sự", S_PHONG),
    }
    for e in edges:  # G3, D-17, D-21: câu trích nguyên văn, known_as nằm trong câu trích
        assert (e.type, e.target, e.valid_from_chapter) == ("REVEALED_TO_PLAYER", "ch1", 1)
        assert quote_in_text(e.props["quote"], TT3_SCENE)
        assert quote_in_text(e.props["known_as"], e.props["quote"])
    assert [e.source for e in edges] == sorted(got, key=lambda i: TT3_SCENE.index(got[i][0]))


def test_after_auto_reveal_the_names_are_seen_by_the_notebook_and_detector():
    state = tt3_state()
    package = ChangePackage(commit_id="c1", edges=tt3_reveals())
    after = OverlayState(state, [package])
    view = player_view_of(after, 1)
    assert {e.text for e in view.entries} == {"Đoàn Khương", "sân Vấn Kiếm", "Diệp Tĩnh Lan",
                                              "kho kiếm cụ", "chấp sự Lương", "phòng chấp sự"}
    for scope in ("scene", "player_path"):
        assert check_leaks(TT3_SCENE, view=view, truth_names=leak_names(after), plan=TT3_PLAN,
                           story_brief=TT3_BRIEF, scope=scope) == []


# --- không đụng gì ngoài nút có tên chưa hé lộ ---------------------------------------------------


def test_protagonist_thread_and_fact_are_never_auto_revealed():
    state = tt3_state()
    labels = state.node_labels([n["id"] for n in TT3["package"]["nodes"]])
    facts = [n["props"]["text"] for n in TT3["package"]["nodes"] if n["label"] == "Fact"]
    threads = [n["props"]["description"] for n in TT3["package"]["nodes"]
               if n["label"] == "Thread"]
    text = " ".join(["Phó Minh Nghi bước ra hiên.", *facts, *threads])
    sources = {e.source for e in tt3_reveals(text)}
    assert PROTAGONIST_ID not in sources
    assert {labels[s] for s in sources} <= {"Character", "Location", "Item", "Faction"}
    assert "luong_khac" in sources  # tên trong chữ của Fact vẫn là tên trên trang


def test_already_revealed_and_protected_nodes_are_skipped():
    state = tt3_state()
    first = ChangePackage(commit_id="c1", edges=tt3_reveals(S_DOAN + "."))
    view = player_view_of(OverlayState(state, [first]), 1)
    assert {e.id for e in view.entries} == {"doan_khuong", "san_van_kiem"}
    again = tt3_reveals(view=view)
    assert {"doan_khuong", "san_van_kiem"}.isdisjoint(e.source for e in again)
    protected = {e.source for e in tt3_reveals(skip={PROTAGONIST_ID, "diep_tinh_lan"})}
    assert "diep_tinh_lan" not in protected and "doan_khuong" in protected


def test_pipeline_skip_set_is_the_plan_protects_in_scene_scope():
    plan = StoryPlan.model_validate({**TT3["plan"], "secrets": [
        {**s, "protects": ["diep_tinh_lan"]} for s in TT3["plan"]["secrets"]]})
    view = player_view_of(tt3_state(), 1)
    assert protected_ids(plan, view, "scene") == {"diep_tinh_lan"}
    assert protected_ids(plan, player_view_of(tt3_state(), 3), "scene") == set()  # trong khoảng lộ


NAMES = {
    PROTAGONIST_ID: ("Phó Minh Nghi",),
    "minh": ("Minh",),
    "lan": ("Phạm Thị Lan", "Lan"),
    "dong_linh_mach": ("Động Linh Mạch",),
    "a": ("Đoàn Khương", "Đoàn sư huynh"),
    "b": ("Đoàn Tử Hư", "Đoàn sư huynh"),
}


def reveal(text: str, names=NAMES) -> dict[str, str]:
    view = PlayerView("s", 1, (), ())
    return {e.source: e.props["known_as"]
            for e in auto_reveals(text, chapter=1, chapter_id="ch1", names=names, view=view,
                                  skip={PROTAGONIST_ID}, no_new_name=())}


@pytest.mark.parametrize("text", [
    "Một tiếng chấn động linh mạch vang lên dưới chân núi.",  # tên ghép từ từ thường (D-52)
    "Bà cụ bán hoa lan ngoài chợ.",  # tên một từ phải viết hoa, khớp đúng
    "Phó Minh Nghi gật đầu.",  # "Minh" nằm trong tên dài hơn của nút khác
    "Đoàn sư huynh tới rồi.",  # biệt danh của hai nút: mơ hồ
    "Mọi người gọi hắn là Lanh.",  # không theo ranh giới từ
])
def test_strict_matching_reveals_nothing_by_mistake(text):
    assert reveal(text) == {}


def test_strict_matching_still_reveals_real_mentions():
    assert reveal("Minh gật đầu. Lan rót trà. Động Linh Mạch rung lên.") == {
        "minh": "Minh", "lan": "Lan", "dong_linh_mach": "Động Linh Mạch"}
    assert reveal("Chiều đó động Linh Mạch rung lên.") == {"dong_linh_mach": "động Linh Mạch"}


def test_long_sentence_quote_is_cut_at_word_boundaries_and_stays_verbatim():
    filler = " ".join(["mưa"] * 80)
    text = f"Ngoài hiên {filler} rồi Đoàn Khương bước vào giữa sân và {filler} mãi không dứt."
    [edge] = auto_reveals(text, chapter=2, chapter_id="ch2", names={"a": ("Đoàn Khương",)},
                          view=PlayerView("s", 2, (), ()), skip=(), no_new_name=())
    quote = edge.props["quote"]
    assert quote_in_text(quote, text) and "Đoàn Khương" in quote
    assert len(quote) <= 200
    assert quote.split()[0] == "mưa" and quote.split()[-1] in ("mưa", "và")


# --- known_as gán nhầm nút ---------------------------------------------------------------------

RUN1_NAMES = {"doan_khac": ("Đoàn Khắc",), "van_tinh_bach": ("Vạn Tinh Bách", "Vạn sư huynh")}


def test_known_as_conflicts_names_the_other_node():
    """Hồi quy tu-tien-1 chương 5: known_as "Vạn Tinh Bách" bị gắn lên `doan_khac`."""
    assert known_as_conflicts("Vạn Tinh Bách", "doan_khac", RUN1_NAMES) == ["van_tinh_bach"]
    assert known_as_conflicts("van tinh  BACH", "doan_khac", RUN1_NAMES) == ["van_tinh_bach"]
    assert known_as_conflicts("Vạn Tinh Bách", "van_tinh_bach", RUN1_NAMES) == []
    assert known_as_conflicts("gã áo xám", "doan_khac", RUN1_NAMES) == []
