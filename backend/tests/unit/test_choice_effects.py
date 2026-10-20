"""Tác động của lựa chọn vào đồ thị (design §6.2 bước 6, §6.3; D-55): hàm thuần dựng gói phần mở
đầu của chương kế. Không model, không Neo4j."""

from writory.graph import ChangePackage
from writory.graph.package import chapter_rule_problems
from writory.pipeline.choices import Choice, LieEffect, choice_effects

CHAPTER = 4
ME = "minh"


def lie_choice(*, listeners=("lan",), about=("sword",), content="Thanh Sương ở chỗ cai Khải"):
    return Choice(
        id="choice-abc123def456", kind="dialogue", tone="lie", text="Nói với Lan là kiếm đã gửi.",
        listeners=tuple(listeners), about=tuple(about), lie=LieEffect(content, tuple(listeners)),
        feeling=None,
    )


def inner_choice(*, about=("lan",), feeling="nghi ngờ"):
    return Choice(
        id="choice-inner0000001", kind="inner", tone=None, text="Thầm nghĩ Lan biết nhiều hơn.",
        listeners=(), about=tuple(about), lie=None, feeling=feeling,
    )


def plain(kind, tone=None, **kw):
    base = {"id": "choice-plain0000001", "kind": kind, "tone": tone, "text": "x", "listeners": (),
            "about": (), "lie": None, "feeling": None}
    return Choice(**(base | kw))


def effects(choice, **kw) -> ChangePackage:
    return choice_effects(choice, chapter=CHAPTER, protagonist=ME, **kw)


def by_type(package: ChangePackage, edge_type: str):
    return [e for e in package.edges if e.type == edge_type]


# --- lời nói dối ------------------------------------------------------------------------------


def test_lie_becomes_a_lie_node_with_told_told_to_and_about_edges():
    pkg = effects(lie_choice(listeners=("lan", "gu"), about=("sword", "lan")))

    [node] = pkg.nodes
    assert (node.id, node.label) == ("lie:choice-abc123def456", "Lie")
    assert node.props == {"chapter": CHAPTER, "content": "Thanh Sương ở chỗ cai Khải"}
    [told] = by_type(pkg, "TOLD")
    assert (told.source, told.target) == (ME, node.id)
    assert sorted(e.target for e in by_type(pkg, "TOLD_TO")) == ["gu", "lan"]
    assert all(e.source == node.id for e in by_type(pkg, "TOLD_TO"))
    assert sorted(e.target for e in by_type(pkg, "ABOUT")) == ["lan", "sword"]
    assert all(e.source == node.id for e in by_type(pkg, "ABOUT"))
    assert pkg.close == []


def test_every_edge_opens_in_the_chapter_being_written_and_none_is_pre_closed():
    """D-21: gói chương N chỉ mở cạnh ở N, không đặt sẵn ngày đóng."""
    for choice in (lie_choice(), inner_choice()):
        pkg = effects(choice, open_feels={"lan": "FEELS:minh>lan@2"})
        assert pkg.edges
        assert chapter_rule_problems(pkg, CHAPTER) == []


def test_protagonist_is_never_his_own_hearer():
    pkg = effects(lie_choice(listeners=(ME, "lan")))
    assert [e.target for e in by_type(pkg, "TOLD_TO")] == ["lan"]


def test_dead_hearers_are_dropped():
    pkg = effects(lie_choice(listeners=("lan", "gu")), dead={"gu"})
    assert [e.target for e in by_type(pkg, "TOLD_TO")] == ["lan"]


def test_a_lie_nobody_alive_can_hear_writes_nothing():
    assert effects(lie_choice(listeners=("gu",)), dead={"gu"}) == ChangePackage(commit_id="header")
    assert effects(lie_choice(listeners=(ME,))) == ChangePackage(commit_id="header")


def test_lie_without_about_has_no_about_edge():
    assert by_type(effects(lie_choice(about=())), "ABOUT") == []


def test_same_choice_gives_the_same_package():
    """Chương ghi lỗi rồi viết lại: id nút và cạnh không đổi theo lần gọi."""
    assert effects(lie_choice()) == effects(lie_choice())


# --- nội tâm ----------------------------------------------------------------------------------


def test_inner_choice_becomes_feels_edges_from_the_protagonist():
    pkg = effects(inner_choice(about=("lan", "sword")))

    assert pkg.nodes == []
    assert sorted((e.source, e.target) for e in pkg.edges) == [(ME, "lan"), (ME, "sword")]
    assert {e.type for e in pkg.edges} == {"FEELS"}
    assert {e.props["feeling"] for e in pkg.edges} == {"nghi ngờ"}
    assert {e.id for e in pkg.edges} == {"FEELS:minh>lan@4", "FEELS:minh>sword@4"}


def test_new_feeling_about_the_same_target_closes_the_old_one():
    """"Đổi trạng thái = đóng cạnh cũ + tạo cạnh mới" (graph-schema)."""
    pkg = effects(inner_choice(about=("lan", "sword")), open_feels={"lan": "FEELS:minh>lan@2"})

    [close] = pkg.close
    assert (close.type, close.id, close.valid_to_chapter) == ("FEELS", "FEELS:minh>lan@2", CHAPTER)
    assert chapter_rule_problems(pkg, CHAPTER) == []


def test_open_feels_about_other_targets_are_left_alone():
    assert effects(inner_choice(about=("lan",)), open_feels={"sword": "FEELS:minh>sword@2"}
                   ).close == []


# --- không có chỗ trong đồ thị ----------------------------------------------------------------


def test_truth_silence_and_action_choices_write_nothing():
    """graph-schema không có chỗ cho "nói thật" hay "im lặng" (D-55): chỉ chữ đi vào đề chương."""
    for choice in (plain("dialogue", "truth", listeners=("lan",)),
                   plain("dialogue", "silence", listeners=("lan",)),
                   plain("action", about=("sword",))):
        assert effects(choice) == ChangePackage(commit_id="header")
