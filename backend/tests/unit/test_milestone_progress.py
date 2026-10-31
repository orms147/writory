"""Mốc cốt truyện đã diễn ra (D-116): dấu nằm ở thuộc tính nút `Chapter`, ghi cùng gói chương (D-6),
câu trích kiểm lại ở bước ghi (G3), và báo cáo so kế hoạch với kết quả."""

from writory.graph import ChangePackage, NodeSpec
from writory.graph.package import quote_problems
from writory.guard.plan import MilestoneProgress, PlanProgress
from writory.pipeline.bench_run import plan_vs_result
from writory.pipeline.chapter import merge_scene_packages
from writory.pipeline.extract import MilestoneMark

CHAPTER = NodeSpec(id="ch4", label="Chapter", props={"number": 4})
SCENE = ChangePackage(commit_id="s1")


def test_merge_writes_the_marks_on_the_chapter_node_in_order():
    package = merge_scene_packages(
        "c", CHAPTER, [SCENE, SCENE],
        milestones=[MilestoneMark(2, "câu hai"), MilestoneMark(1, "câu một")])
    [node] = [n for n in package.nodes if n.id == "ch4"]
    assert node.props == {"number": 4, "milestones": [2, 1], "milestone_quotes": ["câu hai", "câu một"]}


def test_merge_keeps_the_first_mark_of_a_milestone_marked_twice():
    package = merge_scene_packages(
        "c", CHAPTER, [SCENE],
        milestones=[MilestoneMark(2, "lần một"), MilestoneMark(2, "lần hai")])
    assert package.nodes[0].props["milestone_quotes"] == ["lần một"]


def test_merge_without_marks_leaves_the_chapter_node_exactly_as_before():
    package = merge_scene_packages("c", CHAPTER, [SCENE])
    assert package.nodes[0] == CHAPTER and "milestones" not in package.nodes[0].props


def _package(**props):
    return ChangePackage(commit_id="c", nodes=[NodeSpec(id="ch4", label="Chapter", props={
        "number": 4, **props})])


def test_commit_time_check_accepts_a_quote_that_is_on_the_page():
    pkg = _package(milestones=[1], milestone_quotes=["Minh bước xuống bậc thang đá"])
    assert quote_problems(pkg, ["Cánh cửa mở. Minh bước xuống bậc thang đá."], protagonist="") == []


def test_commit_time_check_rejects_a_quote_that_is_not_on_the_page():
    pkg = _package(milestones=[1], milestone_quotes=["câu bịa"])
    [problem] = quote_problems(pkg, ["Cánh cửa mở."], protagonist="")
    assert "mốc" in problem and "câu bịa" in problem


def test_commit_time_check_rejects_marks_without_a_matching_quote():
    for props in ({"milestones": [1, 2], "milestone_quotes": ["a b c d e"]},
                  {"milestones": [1]}):
        problems = quote_problems(_package(**props), ["a b c d e"], protagonist="")
        assert problems and all("mốc" in p for p in problems), props


def test_a_chapter_without_marks_has_no_milestone_problem():
    assert quote_problems(_package(), ["x"], protagonist="") == []


def test_report_lists_each_milestone_with_its_window_and_the_chapter_it_happened_in():
    progress = PlanProgress(
        chapter=6, total_chapters=12, secrets=(), threads=(), milestones=(
            MilestoneProgress(1, "turning_point", "mô tả bí mật", 3, 5, 2),    # sớm
            MilestoneProgress(2, "turning_point", "mô tả", 3, 5, 4),           # đúng khoảng
            MilestoneProgress(3, "climax", "mô tả", 4, 5, 6),                  # muộn
            MilestoneProgress(4, "climax", "mô tả", 5, 6, None),               # chưa tới/quá hạn
            MilestoneProgress(5, "climax", "mô tả", 8, 9, None),               # chưa tới
        ))
    got = plan_vs_result(progress)["milestones"]
    assert got == [
        {"n": 1, "window": [3, 5], "done_chapter": 2, "status": "early"},
        {"n": 2, "window": [3, 5], "done_chapter": 4, "status": "on_time"},
        {"n": 3, "window": [4, 5], "done_chapter": 6, "status": "late"},
        {"n": 4, "window": [5, 6], "done_chapter": None, "status": "missed"},
        {"n": 5, "window": [8, 9], "done_chapter": None, "status": "pending"},
    ]
    assert "mô tả" not in str(got)  # file chung không mang chữ lớp truth


def test_the_ending_is_reported_as_untracked_not_missed():
    """Bộ trích không theo dõi mốc kết (`pacing._pending_milestones`), nên mốc kết không có dấu là
    `untracked`, kể cả khi truyện đã tới chương cuối; mốc khác quá hạn vẫn là `missed`."""
    from writory.pipeline import bench_run

    def report(chapter: int) -> dict:
        return plan_vs_result(PlanProgress(chapter, 12, (), (), (
            MilestoneProgress(1, "climax", "x", 9, 11, None),
            MilestoneProgress(2, "ending", "y", 12, 12, None))))

    assert [m["status"] for m in report(12)["milestones"]] == ["missed", "untracked"]
    assert [m["status"] for m in report(6)["milestones"]] == ["pending", "untracked"]
    lines = "\n".join(bench_run._plan_lines({"plan_vs_result": report(12), "story_finished": True}))
    assert "| 2 | 12–12 | — | không theo dõi (mốc kết) |" in lines


def test_plan_vs_result_lists_the_candidate_chapter_only_for_an_unconfirmed_early_climax():
    from writory.guard.plan import MilestoneProgress, PlanProgress
    from writory.pipeline.bench_run import plan_vs_result

    progress = PlanProgress(7, 12, (), (), (
        MilestoneProgress(1, "turning_point", "x", 3, 5, 4),
        MilestoneProgress(2, "climax", "y", 9, 11, None, 7),
        MilestoneProgress(3, "climax", "z", 10, 11, None)))
    got = plan_vs_result(progress)["milestones"]
    assert got[0] == {"n": 1, "window": [3, 5], "done_chapter": 4, "status": "on_time"}
    assert got[1] == {"n": 2, "window": [9, 11], "done_chapter": None, "status": "pending",
                      "candidate_chapter": 7}
    assert "candidate_chapter" not in got[2]
