"""Người canh, phần kiểm bằng code (design §8 mục 1–2). Chạy trên OverlayState (không Neo4j);
tests/graph/test_guard_state_parity.py chứng minh OverlayState khớp Neo4j."""

import pytest

from writory.config import load_config
from writory.errors import ErrorCode, WritoryError
from writory.graph import ChangePackage, read_sample
from writory.guard import GuardKind, Severity, check_scene_package
from writory.guard.bench_b import SCENARIOS, load_scenarios, run, run_case
from writory.guard.state import EmptyState, OverlayState

SAMPLE = read_sample()
SCEN = load_scenarios(SCENARIOS)


def committed(through: int) -> OverlayState:
    return OverlayState(EmptyState(), [c.package for c in SAMPLE.chapters if c.number <= through])


def pkg(**data) -> ChangePackage:
    return ChangePackage.model_validate({"commit_id": "t", **data})


@pytest.mark.parametrize("case", SCEN.cases, ids=[c["id"] for c in SCEN.cases])
def test_bench_case_reports_exactly_expected_kinds(case):
    kinds = {issue.kind.value for issue in run_case(case, SCEN, SAMPLE)}
    assert kinds == set(case["expect"])


def test_bench_b_recall_is_total_and_no_false_positive():
    result = run(SCENARIOS)
    assert result.unexpected == 0
    for kind, row in result.by_kind.items():
        assert row.error_cases >= 2 and row.clean_cases >= 2, kind
        assert row.detected == row.error_cases, kind
        assert row.false_positive_cases == 0, kind


def test_every_kind_is_covered_by_bench():
    assert set(run(SCENARIOS).by_kind) == {k.value for k in GuardKind}


def test_early_reveal_blocks_others_rewrite():
    case = next(c for c in SCEN.cases if c["id"] == "err-early-reveal-on-page")
    [issue] = run_case(case, SCEN, SAMPLE)
    assert issue.severity is Severity.BLOCK
    assert "f_lan_killed_gu" in issue.ids
    dead = next(c for c in SCEN.cases if c["id"] == "err-dead-participates")
    assert {i.severity for i in run_case(dead, SCEN, SAMPLE)} == {Severity.REWRITE}


def test_at_most_one_names_both_edges():
    case = next(c for c in SCEN.cases if c["id"] == "err-two-holders")
    [issue] = run_case(case, SCEN, SAMPLE)
    assert "holds_sword_minh_2" in issue.ids
    assert "HOLDS:lan>sword@4" in issue.ids


def test_unset_relationship_threshold_is_config_error():
    guard = load_config().guard
    unset = guard.relationship.model_copy(update={"max_score_jump_without_event": None})
    cfg = guard.model_copy(update={"relationship": unset})
    with pytest.raises(WritoryError) as exc:
        check_scene_package(
            chapter=2, current=SAMPLE.chapters[2].package, earlier=[],
            committed=committed(1), plan=SCEN.plan, config=cfg,
        )
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert "guard.yaml" in str(exc.value)


def test_death_in_later_scene_does_not_affect_earlier_scene_actions():
    """Cảnh 1 hành động, cảnh 2 chết: kiểm cảnh 2 không được báo hành động của cảnh 1."""
    earlier = pkg(nodes=[{"id": "e_x", "label": "Event", "chapter": 4, "description": "x"}],
                  edges=[{"type": "PARTICIPATED_IN", "from": "khai", "to": "e_x",
                          "valid_from_chapter": 4}])
    current = pkg(edges=[{"type": "DIED_IN", "from": "khai", "to": "e_x",
                          "valid_from_chapter": 4}])
    issues = check_scene_package(
        chapter=4, current=current, earlier=[earlier], committed=committed(3),
        plan=SCEN.plan, config=SCEN.config,
    )
    assert issues == []


def _chapter_node(n: int) -> dict:
    return {"id": f"ch{n}", "label": "Chapter", "number": n}


def test_overdue_is_checked_on_the_last_scene_only_and_never_blocks():
    """Trễ hạn (D-49): mạch t_sealed_letter hạn gỡ 3–4 (khoảng trên nút, kế hoạch cũ) chưa gỡ ở
    cuối chương 4. Cảnh đầu chương chưa bị báo; cảnh cuối bị báo mức viết lại, không chặn
    người chơi, không bỏ cạnh nào khỏi gói."""
    kw = {"chapter": 4, "current": pkg(nodes=[_chapter_node(4)]), "earlier": [],
          "committed": committed(3), "plan": SCEN.plan, "config": SCEN.config}
    assert check_scene_package(**kw) == []
    [issue] = check_scene_package(**kw, last_scene=True)
    assert (issue.kind, issue.severity, issue.ids) == (GuardKind.OVERDUE_THREAD, Severity.REWRITE,
                                                       ())
    assert "t_sealed_letter" in issue.detail and "Lá thư niêm phong" in issue.detail


def test_overdue_uses_the_plan_window_and_counts_reveals_of_this_chapter():
    plan = SCEN.plan.model_validate({
        **SCEN.plan.model_dump(mode="json"),
        "must_resolve_threads": [{"thread_id": "t_sealed_letter", "resolve_from_chapter": 3,
                                  "resolve_to_chapter": 6}],
    })
    base = {"chapter": 6, "earlier": [], "committed": committed(4), "plan": plan,
            "config": SCEN.config, "last_scene": True}
    # Nền tới chương 4: f_lan_spy (khoảng lộ 5–6) chưa lộ; mạch theo khoảng của kế hoạch tới 6.
    issues = check_scene_package(current=pkg(nodes=[_chapter_node(6)]), **base)
    assert sorted(i.kind for i in issues) == [GuardKind.OVERDUE_SECRET, GuardKind.OVERDUE_THREAD]
    assert all(i.severity is Severity.REWRITE for i in issues)
    done = pkg(nodes=[_chapter_node(6)], edges=[
        {"type": "REVEALED_TO_PLAYER", "from": "f_lan_spy", "to": "ch6", "valid_from_chapter": 6,
         "quote": "Lan là người của Hội Hắc Kỳ."},
        {"type": "RESOLVED_IN", "from": "t_sealed_letter", "to": "ch6", "valid_from_chapter": 6}])
    assert check_scene_package(current=done, **base) == []
    # Hé lộ ở cảnh trước của cùng chương cũng tính.
    reveal, resolve = (e.model_dump(mode="json", by_alias=True) for e in done.edges)
    earlier = pkg(nodes=[_chapter_node(6)], edges=[reveal])
    later = pkg(edges=[resolve])
    assert check_scene_package(current=later, **(base | {"earlier": [earlier]})) == []


def test_item_held_by_character_located_elsewhere_is_not_flagged():
    """LOCATED_AT chỉ kiểm "tối đa một" cho Item; nhân vật ở đâu không thuộc bất biến này."""
    current = pkg(edges=[{"type": "LOCATED_AT", "from": "minh", "to": "mieu_ba",
                          "valid_from_chapter": 4}])
    assert check_scene_package(
        chapter=4, current=current, earlier=[], committed=committed(3),
        plan=SCEN.plan, config=SCEN.config,
    ) == []
