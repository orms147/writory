from collections import Counter
from itertools import product

import pytest
from pydantic import ValidationError

from writory.pipeline.story_plan import StoryPlan, WindowShift, align_thread_windows


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


def test_protects_optional_and_validated():
    """D-61: id các nút có tên mà bí mật bảo vệ. Kế hoạch cũ không có trường này."""
    def secret(protects):
        return plan(secrets=[{"fact_id": "f", "reveal_from_chapter": 1, "reveal_to_chapter": 2,
                              "protects": protects}])

    assert StoryPlan.model_validate(secret(["ly_that"])).secret("f").protects == ["ly_that"]
    assert StoryPlan.model_validate(plan()).secret("f_lan_spy").protects == []
    for bad in (["ly_that", "ly_that"], ["Lý Thất"], [""]):
        with pytest.raises(ValidationError):
            StoryPlan.model_validate(secret(bad))


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


# --- mạch do bí mật trả lời: khoảng gỡ không bắt đầu trước khoảng lộ (D-135) ------------------------
# Hồi quy evals/results/2026-10-30-plan-thread-secret-window/notes.md: kế hoạch cho gỡ mạch trước khi
# bí mật chứa câu trả lời được phép lộ.


def _thread(tid: str, low: int | None, high: int | None, *answers: str) -> dict:
    return {"thread_id": tid, "resolve_from_chapter": low, "resolve_to_chapter": high,
            "answered_by": list(answers)}


def _secret(fid: str, low: int, high: int) -> dict:
    return {"fact_id": fid, "reveal_from_chapter": low, "reveal_to_chapter": high}


def test_answered_by_round_trips_and_old_plans_have_none():
    p = StoryPlan.model_validate(plan(must_resolve_threads=[_thread("t", 5, 6, "f_lan_spy")]))
    assert p.thread("t").answered_by == ["f_lan_spy"]
    assert StoryPlan.model_validate(p.model_dump(mode="json")) == p
    # Kế hoạch đã lưu trước D-135 (Postgres `story_plans`, truth_dump cũ): không có trường này.
    old = StoryPlan.model_validate(plan(must_resolve_threads=[
        {"thread_id": "t", "resolve_from_chapter": 5, "resolve_to_chapter": 6}, "t_legacy"]))
    assert [t.answered_by for t in old.must_resolve_threads] == [[], []]


@pytest.mark.parametrize("bad", [["f_lan_spy", "f_lan_spy"], ["có dấu cách"], [""]])
def test_answered_by_ids_are_well_formed_and_unique(bad):
    with pytest.raises(ValidationError):
        StoryPlan.model_validate(plan(must_resolve_threads=[_thread("t", 5, 6, *bad)]))


def test_plans_without_links_or_windows_are_left_alone():
    """Kế hoạch cũ không có khoảng gỡ hay không có `answered_by`: không kiểm, không dời (D-49)."""
    for threads in (["t_legacy"], [_thread("t", 1, 2)],  # không liên kết dù gỡ trước bí mật
                    [{"thread_id": "t", "answered_by": ["f_lan_spy"]}]):  # liên kết, không khoảng
        p = StoryPlan.model_validate(plan(must_resolve_threads=threads))
        assert p.answer_mismatches() == ()
        assert align_thread_windows(p, max_due_per_chapter=3) == (p, ())


def test_unknown_answer_id_is_left_for_the_setup_check():
    """Id không phải bí mật của kế hoạch: hàm dời bỏ qua; `pipeline.setup` báo lỗi (lượt sửa D-54)."""
    p = StoryPlan.model_validate(plan(must_resolve_threads=[_thread("t", 1, 2, "f_khong_co")]))
    assert p.answer_start(p.thread("t")) is None
    assert p.answer_mismatches() == ()
    assert align_thread_windows(p, max_due_per_chapter=3) == (p, ())


TU_TIEN_ACTS = [(1, 6), (7, 13), (14, 20), (21, 24)]
TU_TIEN_MILESTONES = [("turning_point", 1, 2), ("turning_point", 4, 6), ("turning_point", 9, 11),
                      ("turning_point", 12, 13), ("turning_point", 16, 17), ("climax", 20, 22),
                      ("ending", 24, 24)]


def _tu_tien() -> StoryPlan:
    """Kế hoạch dài tu-tiên của `evals/results/2026-10-29-run-long-after-tu-tien/truth_dump.json`,
    thêm `answered_by` mà đề `setup-11` đòi: "Ninh Tuyết Anh thật sự đại diện cho phe nào?" do bí
    mật `fact_su_gia_that` trả lời; "Vì sao Thẩm Mặc Ngôn bí mật đổi hướng thuyền?" do
    `fact_tham_mac_phan_bo`; "Hộp ngọc sẽ được dùng vào việc gì?" do `fact_hop_ngoc_dinh_vi`."""
    return StoryPlan.model_validate({
        "acts": [{"name": f"hồi {i}", "from_chapter": a, "to_chapter": b}
                 for i, (a, b) in enumerate(TU_TIEN_ACTS, 1)],
        "secrets": [_secret("fact_tham_mac_phan_bo", 6, 8), _secret("fact_su_gia_that", 11, 13),
                    _secret("fact_hop_ngoc_dinh_vi", 9, 11)],
        "must_resolve_threads": [
            _thread("thread_duong_den_dao", 1, 24),
            _thread("thread_ly_do_doi_huong", 3, 8, "fact_tham_mac_phan_bo"),
            _thread("thread_nguon_chuong", 5, 11),
            _thread("thread_lap_truong_su_gia", 7, 13, "fact_su_gia_that"),
            _thread("thread_ke_pha_la_ban", 8, 12),
            _thread("thread_doi_gia_giu_an", 14, 19),
            _thread("thread_so_phan_hop_ngoc", 16, 22, "fact_hop_ngoc_dinh_vi"),
        ],
        "milestones": [{"kind": k, "goal": f"mốc {i}", "from_chapter": a, "to_chapter": b}
                       for i, (k, a, b) in enumerate(TU_TIEN_MILESTONES, 1)],
    })


def test_tu_tien_threads_start_when_their_secret_may_be_revealed():
    p = _tu_tien()
    assert p.answer_mismatches() == ("thread_ly_do_doi_huong", "thread_lap_truong_su_gia")
    aligned, shifts = align_thread_windows(p, max_due_per_chapter=3)
    assert shifts == (
        WindowShift("thread_ly_do_doi_huong", (3, 8), (6, 8), ("fact_tham_mac_phan_bo",)),
        WindowShift("thread_lap_truong_su_gia", (7, 13), (11, 13), ("fact_su_gia_that",)),
    )
    assert not any(s.end_moved for s in shifts)
    windows = {t.thread_id: (t.resolve_from_chapter, t.resolve_to_chapter)
               for t in aligned.must_resolve_threads}
    assert windows["thread_lap_truong_su_gia"] == (11, 13)
    assert windows["thread_so_phan_hop_ngoc"] == (16, 22)  # đã sau khoảng lộ: giữ nguyên
    assert windows["thread_duong_den_dao"] == (1, 24)  # không liên kết: giữ nguyên
    assert aligned.answer_mismatches() == ()
    assert aligned.deadlines() == p.deadlines()  # chỉ dời chương đầu: nhịp không đổi
    # Mọi thứ khác của kế hoạch giữ nguyên.
    assert aligned.model_copy(update={"must_resolve_threads": p.must_resolve_threads}) == p
    assert align_thread_windows(aligned, max_due_per_chapter=3) == (aligned, ())


def _one_secret_plan(thread: tuple[int, int], secret: tuple[int, int], *,
                     extra_secrets: list[dict] | None = None) -> StoryPlan:
    return StoryPlan.model_validate(plan(  # hồi 1–2, 3–6: 6 chương
        secrets=[_secret("f_lan_spy", *secret), *(extra_secrets or [])],
        must_resolve_threads=[_thread("t", *thread, "f_lan_spy")]))


def test_thread_due_before_its_secret_opens_takes_the_secret_window():
    """Hạn gỡ xong trước cả chương đầu của khoảng lộ (không thể đúng cả hai): mạch nhận đúng khoảng lộ
    của bí mật, nên bí mật lộ lúc nào trong khoảng thì mạch vẫn gỡ kịp."""
    p = _one_secret_plan((1, 2), (3, 4))
    aligned, [shift] = align_thread_windows(p, max_due_per_chapter=3)
    assert shift == WindowShift("t", (1, 2), (3, 4), ("f_lan_spy",)) and shift.end_moved
    assert aligned.deadlines() == {4: 2}


def test_moved_deadline_skips_full_chapters_and_the_last_chapter_is_never_full():
    # Giới hạn 1: chương 4 đã có hạn của bí mật f_lan_spy, chương 5 của f_khac: mạch sang chương 6
    # (cuối); chương cuối không tính giới hạn (D-54), nên luôn dời được.
    p = _one_secret_plan((1, 2), (3, 4), extra_secrets=[_secret("f_khac", 5, 5)])
    aligned, [shift] = align_thread_windows(p, max_due_per_chapter=1)
    assert shift.after == (3, 6)
    assert aligned.deadlines() == {4: 1, 5: 1, 6: 1}
    # Giới hạn 2: chương 4 còn chỗ.
    assert align_thread_windows(p, max_due_per_chapter=2)[1][0].after == (3, 4)


def test_secret_in_the_last_chapter_moves_the_thread_there():
    aligned, [shift] = align_thread_windows(_one_secret_plan((2, 5), (6, 6)), max_due_per_chapter=1)
    assert shift.after == (6, 6) and aligned.total_chapters == 6


def test_thread_answered_by_several_secrets_waits_for_the_latest_one():
    p = StoryPlan.model_validate(plan(
        secrets=[_secret("f_lan_spy", 2, 3), _secret("f_khac", 4, 5)],
        must_resolve_threads=[_thread("t", 1, 6, "f_lan_spy", "f_khac")]))
    assert p.answer_start(p.thread("t")) == 4
    assert align_thread_windows(p, max_due_per_chapter=3)[1] == (
        WindowShift("t", (1, 6), (4, 6), ("f_lan_spy", "f_khac")),)


def test_two_threads_moved_to_the_same_chapter_respect_the_cap_together():
    p = StoryPlan.model_validate(plan(
        secrets=[_secret("f_lan_spy", 4, 4)],
        must_resolve_threads=[_thread("t1", 1, 2, "f_lan_spy"), _thread("t2", 1, 3, "f_lan_spy")]))
    aligned, shifts = align_thread_windows(p, max_due_per_chapter=2)
    assert [s.after for s in shifts] == [(4, 4), (4, 5)]  # chương 4: bí mật + t1 đã đủ 2
    assert aligned.deadlines() == {4: 2, 5: 1}


@pytest.mark.parametrize("cap", [1, 2])
def test_alignment_holds_for_every_window_pair_of_a_short_plan(cap):
    """Mọi cặp khoảng mạch–bí mật trên kế hoạch 6 chương: sau khi dời không còn lệch; khoảng vẫn trong
    truyện; chương đầu = max(chương đầu cũ, chương đầu khoảng lộ); hạn chỉ lùi về sau, và chỉ khi hạn
    cũ trước khoảng lộ; không chương nào trừ chương cuối bị đẩy quá giới hạn nhịp."""
    windows = [(a, b) for a in range(1, 7) for b in range(a, 7)]
    for (a, b), (r1, r2) in product(windows, windows):
        p = _one_secret_plan((a, b), (r1, r2))
        aligned, shifts = align_thread_windows(p, max_due_per_chapter=cap)
        t = aligned.thread("t")
        low, high = t.resolve_from_chapter, t.resolve_to_chapter
        assert aligned.answer_mismatches() == ()
        assert 1 <= low <= high <= aligned.total_chapters
        assert low == max(a, r1)
        assert (high == b) if b >= r1 else (high >= r2)
        assert len(shifts) == int(a < r1)
        before, after = Counter(p.deadlines()), Counter(aligned.deadlines())
        assert all(after[c] <= max(cap, before[c]) for c in after if c != aligned.total_chapters)
