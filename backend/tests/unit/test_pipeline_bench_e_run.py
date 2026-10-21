"""Bài E trên truyện do pipeline viết (D-60): kế hoạch, thiết lập truyện và sổ tay lấy từ thư mục
kết quả của `bench_run`. Không mạng, không model thật."""

import json
import shutil
from pathlib import Path

import pytest
import yaml

pytest.importorskip("anthropic")

from writory.config import REPO_ROOT, ConfigError, load_config
from writory.graph import public_entries
from writory.pipeline import bench_e as be
from writory.pipeline.narrator import NOT_KNOWN
from writory.pipeline.story_plan import Secret, StoryPlan

CONFIG = load_config()
RUN_DIR = REPO_ROOT / "evals" / "results" / "2026-10-20-run-tu-tien-1"
FILES = {"questions_file": "questions-tu-tien-1.yaml", "plan_file": "plan-tu-tien-1.yaml"}
DATA = be.load_data(**FILES)


async def run(tmp_path: Path, data=DATA, **kw):
    logs: list[str] = []
    o = be.RunOptions(**({"out": tmp_path / "out", "dry_run": True, "samples": 1,
                          "concurrency": 4} | kw))
    code = await be.run_bench(data, o, config=CONFIG, log=logs.append)
    store = be.Store(o.out)
    return code, store, be.compute_report(data, store)


def copy_data(tmp_path: Path) -> Path:
    dst = tmp_path / "data"
    shutil.copytree(be.DATA_DIR, dst)
    return dst


def edit(path: Path, fn) -> None:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    fn(doc)
    path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")


# --- nguồn truyện ------------------------------------------------------------------------------


def test_story_comes_from_the_run_directory_not_the_sample():
    assert DATA.story.kind == "run"
    assert sorted(DATA.states) == [1, 2, 3, 4, 5, 6]
    assert DATA.story_brief == DATA.story.brief and "Nhân vật chính:" in DATA.story_brief
    assert {"run/truth_dump.json", "run/setup.json", "run/meta.json"} <= set(DATA.hashes)
    assert "sample-story/graph.yaml" not in DATA.hashes


def test_runtime_plan_is_the_one_the_model_set_during_setup():
    dump = json.loads((RUN_DIR / "truth_dump.json").read_text(encoding="utf-8"))
    assert DATA.story_plan == StoryPlan.model_validate(dump["plan"])
    ids = {s.fact_id for s in DATA.story_plan.secrets}
    assert {"f_doan_khac_tao_phu_gia", "f_doan_khac_muon_mac_ca"} <= ids


def test_scorer_sees_every_truth_name_of_the_run_story():
    names = {n[0] for n in DATA.scorer.names.values()}
    assert {"Đoàn Khắc", "Tào Minh Liệt", "Nguyên Tuệ Lâm"} <= names


def test_questions_are_declared_for_every_chapter_with_both_known_and_hidden():
    for chapter in range(1, 7):
        types = {q.type for q in DATA.questions.questions if q.chapter == chapter}
        assert types - {"a"}, chapter
    assert {q.type for q in DATA.questions.questions} == set(be.TYPES)


def test_grounds_resolve_to_public_refs_in_the_run_notebook():
    q = DATA.question("t5-a-tin-vat-mo-gi")
    [ref] = DATA.expected_refs[q.id]
    entries = dict(public_entries(DATA.states[5].view))
    assert "chốt phụ" in entries[ref].text


def test_secrets_are_not_in_the_notebook_of_any_chapter():
    for chapter, state in DATA.states.items():
        shown = " ".join(e.text for e in state.view.entries).lower()
        assert "làm giả phù âm" not in shown and "đoàn khắc" not in shown, chapter


# --- bộ chấm chặt hơn bộ dò lộ lúc chạy --------------------------------------------------------


def _runtime(text: str, state, scope: str):
    return be.check_leaks(text, view=state.view, truth_names=state.truth_names,
                          plan=DATA.story_plan, story_brief=DATA.story_brief, scope=scope)


def test_traitor_secrets_stay_secret_on_the_narrator_path_after_their_planned_window():
    """D-60 ghi lỗ: hai bí mật của kế hoạch (khoảng lộ 3-6, 4-6) chưa hề hé lộ, mà bộ dò lộ chỉ áp
    `leak_terms` trước `reveal_from_chapter`, nên từ chương 3-4 người kể nói ra được. Từ D-61 người
    kể dò mọi bí mật chưa có trong player_view (`player_path`); văn cảnh (`scene`) vẫn theo khoảng
    lộ, vì cảnh được phép hé lộ trong khoảng."""
    for chapter in (4, 5, 6):  # f_doan_khac_muon_mac_ca: khoảng lộ 4-6
        state = DATA.states[chapter]
        own = "Đoàn Khắc muốn thương lượng với Bạch Lộc Cốc."  # nhóm leak_terms model đã đặt
        assert "secret" in {h.kind.value for h in _runtime(own, state, "player_path")}, chapter
        assert "secret" not in {h.kind.value for h in _runtime(own, state, "scene")}, chapter


def test_scorer_keeps_traitor_secrets_secret_beyond_the_plan_terms():
    """Bộ chấm vẫn chặt hơn lớp chạy thật: nhóm chỉ của bộ chấm bắt cách nói không có trong
    `leak_terms` của kế hoạch (tên sai "Vạn Tinh Bách" mà bộ trích gắn cho nút ở chương 5)."""
    state, text = DATA.states[6], "Vạn Tinh Bách đã thương lượng với Bạch Lộc Cốc về đường lui."
    assert _runtime(text, state, "player_path") == []  # lọt lớp chặn lúc chạy
    assert DATA.scorer.leaks(text, state)  # bộ chấm bắt


def test_scorer_catches_the_real_name_even_though_its_node_was_revealed_under_another_name():
    # Nút `doan_khac` bị hé lộ dưới tên "Vạn Tinh Bách" (xem plan-tu-tien-1.yaml).
    state = DATA.states[5]
    assert DATA.scorer.leaks("Người trao tín vật tên thật là Đoàn Khắc.", state)


def test_plain_notebook_facts_are_not_flagged():
    for chapter, state in DATA.states.items():
        for ref, text in state.entries.items():
            assert DATA.scorer.leaks(text, state) == [], (chapter, ref)


def test_extra_secret_window_beyond_the_story_extends_the_scorer_plan_only():
    plan = DATA.plan.scorer_plan(DATA.story_plan)
    total = DATA.story_plan.total_chapters
    assert max(s.reveal_to_chapter for s in DATA.story_plan.secrets) <= total
    assert max(s.reveal_to_chapter for s in plan.secrets) > total  # chỉ kế hoạch của bộ chấm
    assert "f_phu_am_bi_doi" in {s.fact_id for s in plan.secrets}
    assert plan.total_chapters == total


def test_scorer_plan_without_extra_windows_is_unchanged():
    base = DATA.story_plan
    plain = be.PlanFile(version=1, run_dir="x", score=be.ScoreExtras())
    assert plain.scorer_plan(base) == base
    assert isinstance(Secret, type)


# --- khai đúng nguồn ---------------------------------------------------------------------------


def test_run_dir_plan_may_not_also_declare_plan_or_story_brief(tmp_path):
    data_dir = copy_data(tmp_path)
    edit(data_dir / "plan-tu-tien-1.yaml", lambda d: d.update(story_brief="x"))
    with pytest.raises(ConfigError, match="run_dir"):
        be.load_data(data_dir, **FILES)


def test_sample_plan_must_declare_plan_and_brief(tmp_path):
    data_dir = copy_data(tmp_path)
    edit(data_dir / "plan.yaml", lambda d: d.pop("plan"))
    with pytest.raises(ConfigError, match="plan"):
        be.load_data(data_dir)


def test_missing_run_directory_is_a_config_error(tmp_path):
    data_dir = copy_data(tmp_path)
    edit(data_dir / "plan-tu-tien-1.yaml", lambda d: d.update(run_dir="evals/results/khong-co"))
    with pytest.raises(ConfigError, match="truth_dump.json"):
        be.load_data(data_dir, **FILES)


def test_question_for_a_chapter_the_run_never_reached_is_rejected(tmp_path):
    data_dir = copy_data(tmp_path)

    def late(doc):
        doc["questions"].append({"id": "t9-b-x", "chapter": 9, "type": "b", "text": "Ai?"})
        doc["counts"]["b"] += 1

    edit(data_dir / "questions-tu-tien-1.yaml", late)
    with pytest.raises(ConfigError, match="chương 9"):
        be.load_data(data_dir, **FILES)


# --- chạy khô ----------------------------------------------------------------------------------


async def test_oracle_dry_run_on_the_run_story_is_clean(tmp_path):
    code, store, report = await run(tmp_path)
    assert code == be.EXIT_OK and report["final_leaks"] == 0 and report["raw_leaks"] == 0
    assert all(r["ok"] for r in store.rows(be.RESULTS))
    assert report["by_type"]["a"]["n"] == DATA.questions.counts["a"]


async def test_leaker_cannot_reach_the_player_on_the_run_story(tmp_path):
    code, store, report = await run(tmp_path, fake="leaker")
    assert code == be.EXIT_OK and report["final_leaks"] == 0
    assert report["raw_leaks"] > 0  # chữ của kẻ lộ thật sự là lộ với bộ chấm: test không rỗng
    assert all(r["final"] == NOT_KNOWN for r in store.rows(be.RESULTS))


async def test_summary_names_the_run_directory_and_files(tmp_path):
    _, store, report = await run(tmp_path)
    text = be.build_summary(DATA, store, report)
    assert "2026-10-20-run-tu-tien-1" in text and "questions-tu-tien-1.yaml" in text
    assert "truyện mẫu graph.yaml" not in text
    meta = store.read_meta()
    assert meta["story"] == {"kind": "run", "run_dir": "evals/results/2026-10-20-run-tu-tien-1"}


async def test_changed_run_dump_refuses_to_resume(tmp_path):
    data_dir = copy_data(tmp_path)
    run_dir = tmp_path / "run"
    shutil.copytree(RUN_DIR, run_dir)
    edit(data_dir / "plan-tu-tien-1.yaml", lambda d: d.update(run_dir=str(run_dir)))
    data = be.load_data(data_dir, **FILES)
    await run(tmp_path, data=data, question_ids=["t1-b-ai-lam-lech-lenh"])
    dump = run_dir / "truth_dump.json"
    dump.write_text(dump.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="data_sha256"):
        await run(tmp_path, data=be.load_data(data_dir, **FILES),
                  question_ids=["t1-b-ai-lam-lech-lenh"])


def test_cli_plan_for_the_run_story(capsys):
    argv = ["plan", "--questions-file", FILES["questions_file"], "--plan-file", FILES["plan_file"]]
    assert be.main(argv) == be.EXIT_OK
    assert str(len(DATA.questions.questions)) in capsys.readouterr().out


def test_real_name_rule_spares_names_the_player_already_read_in_the_notebook():
    # "Thanh Hư Môn" là nút chưa hé lộ, nhưng tên nằm trong chữ của một mục sổ tay (chương 2).
    state = DATA.states[2]
    assert DATA.scorer.leaks("Nhóm đệ tử Thanh Hư Môn đang mắc kẹt bên ngoài.", state) == []


def test_real_name_rule_still_catches_names_nobody_has_shown():
    state = DATA.states[5]
    for text in ("Tào Minh Liệt đứng gần đó.", "nguyên tuệ lâm đã tới."):
        assert DATA.scorer.leaks(text, state), text
