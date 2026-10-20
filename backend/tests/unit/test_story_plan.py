import pytest
from pydantic import ValidationError

from writory.pipeline.story_plan import StoryPlan


def plan(**overrides) -> dict:
    data = {
        "acts": [
            {"name": "mở đầu", "from_chapter": 1, "to_chapter": 2},
            {"name": "phát triển", "from_chapter": 3, "to_chapter": 6},
        ],
        "secrets": [{"fact_id": "f_lan_spy", "reveal_from_chapter": 5, "reveal_to_chapter": 6}],
        "must_resolve_threads": ["t_who_killed"],
    }
    return data | overrides


def test_valid_plan_and_secret_lookup():
    p = StoryPlan.model_validate(plan())
    assert p.secret("f_lan_spy").reveal_from_chapter == 5
    assert p.secret("f_unknown") is None


@pytest.mark.parametrize(
    "bad",
    [
        {"acts": []},
        {"acts": [{"name": "x", "from_chapter": 3, "to_chapter": 2}]},
        {"acts": [{"name": "a", "from_chapter": 1, "to_chapter": 3},
                  {"name": "b", "from_chapter": 3, "to_chapter": 5}]},  # chồng chương 3
        {"acts": [{"name": "b", "from_chapter": 4, "to_chapter": 5},
                  {"name": "a", "from_chapter": 1, "to_chapter": 3}]},  # sai thứ tự
        {"secrets": [{"fact_id": "f", "reveal_from_chapter": 6, "reveal_to_chapter": 5}]},
        {"secrets": [{"fact_id": "f", "reveal_from_chapter": 1, "reveal_to_chapter": 2},
                     {"fact_id": "f", "reveal_from_chapter": 3, "reveal_to_chapter": 4}]},
        {"secrets": [{"fact_id": "có dấu cách", "reveal_from_chapter": 1, "reveal_to_chapter": 2}]},
        {"must_resolve_threads": ["t", "t"]},
        {"extra_field": 1},
    ],
)
def test_invalid_plan_rejected(bad):
    with pytest.raises(ValidationError):
        StoryPlan.model_validate(plan(**bad))


def test_leak_terms_optional_and_validated():
    ok = StoryPlan.model_validate(plan(secrets=[{
        "fact_id": "f", "reveal_from_chapter": 1, "reveal_to_chapter": 2,
        "leak_terms": [["Lan", "gián điệp"]],
    }]))
    assert ok.secret("f").leak_terms == [["Lan", "gián điệp"]]
    assert StoryPlan.model_validate(plan()).secret("f_lan_spy").leak_terms == []
    for bad in ([[]], [["Lan", "  "]], [["Lan", "Lan"]]):
        with pytest.raises(ValidationError):
            StoryPlan.model_validate(plan(secrets=[{
                "fact_id": "f", "reveal_from_chapter": 1, "reveal_to_chapter": 2,
                "leak_terms": bad,
            }]))


# --- khoảng gỡ mạch và mốc (D-49) ------------------------------------------------------------


def milestones(total: int = 6) -> list[dict]:
    """Một mốc kết thúc trong mỗi hồi của `plan()` (hồi 1–2, 3–6); mốc kết ở chương cuối."""
    return [
        {"kind": "turning_point", "goal": "Minh biết Lão Gù chết", "from_chapter": 1,
         "to_chapter": 2},
        {"kind": "climax", "goal": "Minh đối mặt Lan", "from_chapter": 4, "to_chapter": 5},
        {"kind": "ending", "goal": "Minh chọn ở lại phố Bến Sương", "from_chapter": total,
         "to_chapter": total},
    ]


def test_legacy_thread_ids_still_load_without_a_window():
    """Kế hoạch cũ trong Postgres (D-44) và fixture: `must_resolve_threads` là danh sách id."""
    p = StoryPlan.model_validate(plan(must_resolve_threads=["t_who_killed", "t_sealed_letter"]))
    assert p.thread_ids == ("t_who_killed", "t_sealed_letter")
    assert p.thread("t_who_killed").resolve_to_chapter is None
    assert p.milestones == []
    # Đọc lại bản đã lưu theo dạng mới: không đổi gì.
    assert StoryPlan.model_validate(p.model_dump(mode="json")) == p


def test_thread_window_and_milestones_round_trip():
    p = StoryPlan.model_validate(plan(
        must_resolve_threads=[{"thread_id": "t_who_killed", "resolve_from_chapter": 4,
                               "resolve_to_chapter": 5}],
        milestones=milestones(),
    ))
    assert p.thread("t_who_killed").resolve_to_chapter == 5
    assert p.thread("t_khong_co") is None
    assert [m.kind for m in p.milestones] == ["turning_point", "climax", "ending"]
    assert StoryPlan.model_validate(p.model_dump(mode="json")) == p


@pytest.mark.parametrize(
    "bad",
    [
        # khoảng ngoài tổng số chương (6)
        {"secrets": [{"fact_id": "f", "reveal_from_chapter": 5, "reveal_to_chapter": 7}]},
        {"must_resolve_threads": [{"thread_id": "t", "resolve_from_chapter": 5,
                                   "resolve_to_chapter": 7}]},
        {"must_resolve_threads": [{"thread_id": "t", "resolve_from_chapter": 5,
                                   "resolve_to_chapter": 4}]},
        {"must_resolve_threads": [{"thread_id": "t", "resolve_from_chapter": 5}]},  # nửa khoảng
        {"must_resolve_threads": [{"thread_id": "t"}, "t"]},  # trùng id
        {"milestones": [*milestones()[:2], {"kind": "ending", "goal": "x", "from_chapter": 7,
                                             "to_chapter": 7}]},
        # mốc kết không nằm trọn ở chương cuối, không có mốc kết, hai mốc kết
        {"milestones": [*milestones()[:2], {"kind": "ending", "goal": "x", "from_chapter": 5,
                                             "to_chapter": 6}]},
        {"milestones": milestones()[:2]},
        {"milestones": [*milestones(), milestones()[-1]]},
        # hồi 1 (chương 1–2) không có mốc nào kết thúc trong hồi
        {"milestones": milestones()[1:]},
        {"milestones": [milestones()[0] | {"goal": "   "}, *milestones()[1:]]},
        {"milestones": [milestones()[0] | {"kind": "khac"}, *milestones()[1:]]},
    ],
)
def test_invalid_windows_and_milestones_rejected(bad):
    with pytest.raises(ValidationError):
        StoryPlan.model_validate(plan(**bad))


def test_deadlines_per_chapter_count_secrets_threads_and_milestones():
    p = StoryPlan.model_validate(plan(
        must_resolve_threads=[{"thread_id": "t_who_killed", "resolve_from_chapter": 4,
                               "resolve_to_chapter": 6}, "t_legacy"],
        milestones=milestones(),
    ))
    # Bí mật f_lan_spy hạn 6, mạch hạn 6, mốc hạn 2, 5, 6; mạch cũ không có khoảng thì không đếm.
    assert p.deadlines() == {2: 1, 5: 1, 6: 3}
