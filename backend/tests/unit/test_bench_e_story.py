"""Nguồn truyện của bài E (D-60): truyện mẫu, truyện do pipeline viết, và sổ tay đệm cho nhóm
câu hỏi sổ tay lớn. Không mạng, không model."""

import json
import shutil

import pytest

from writory.config import REPO_ROOT, ConfigError
from writory.graph import PlayerView, public_entries
from writory.guard.state import EmptyState, OverlayState, player_view_of
from writory.pipeline.bench_e_story import (
    PadSpec,
    load_run_story,
    load_sample_story,
    pad_view,
)
from writory.pipeline.setup import story_brief
from writory.pipeline.story_plan import StoryPlan

RUN_DIR = REPO_ROOT / "evals" / "results" / "2026-10-20-run-tu-tien-1"


def view_of(story, chapter: int) -> PlayerView:
    state = OverlayState(EmptyState(), story.packages_upto(chapter))
    return player_view_of(state, chapter, story_id="s")


# --- truyện mẫu -------------------------------------------------------------------------------


def test_sample_story_has_chapters_one_to_five_and_a_chapter_zero_package():
    story = load_sample_story()
    assert story.kind == "sample"
    assert story.chapters == (1, 2, 3, 4, 5)
    assert next(n for n, _ in story.packages) == 0
    assert story.plan is None and story.brief is None  # do plan.yaml khai
    assert "sample-story/graph.yaml" in story.hashes


# --- truyện do pipeline viết ------------------------------------------------------------------


def test_run_story_reads_packages_plan_and_rebuilds_the_brief():
    story = load_run_story(RUN_DIR)
    assert story.kind == "run"
    assert story.chapters == (1, 2, 3, 4, 5, 6)
    assert isinstance(story.plan, StoryPlan) and story.plan.secrets
    # Cùng chữ bước khởi tạo đã đưa vào bộ dò lộ lúc chạy (bench_run: story_brief(...)).
    assert story.brief and "Nhân vật chính:" in story.brief and "Bối cảnh:" in story.brief
    assert set(story.hashes) >= {"run/truth_dump.json", "run/setup.json", "run/meta.json"}


def test_run_story_brief_is_exactly_what_the_pipeline_function_returns():
    from writory.pipeline.setup import CharacterOption, PlotOption, SettingOption, StoryChoices

    story = load_run_story(RUN_DIR)
    setup = json.loads((RUN_DIR / "setup.json").read_text(encoding="utf-8"))
    meta = json.loads((RUN_DIR / "meta.json").read_text(encoding="utf-8"))
    c = meta["scenario"]["content"]
    choices = StoryChoices(tags=c["tags"], length_level=c["length_level"], pov=c["pov"],
                           naming=c["naming"])

    def pick(step, cls):
        return cls(**setup[step]["options"][setup[step]["picked"]])

    want = story_brief(choices, pick("settings", SettingOption), pick("plots", PlotOption),
                       pick("characters", CharacterOption))
    assert story.brief == want


def test_run_story_player_view_is_non_empty_and_grows():
    story = load_run_story(RUN_DIR)
    sizes = [len(view_of(story, n).entries) for n in story.chapters]
    assert sizes[0] > 0 and sizes == sorted(sizes)


def test_run_story_view_hides_what_the_plan_calls_secret():
    story = load_run_story(RUN_DIR)
    shown = {e.id for e in view_of(story, 2).entries}
    assert "f_doan_khac_tao_phu_gia" not in shown  # bí mật chưa tới khoảng lộ


@pytest.mark.parametrize("break_it", ["truth_dump.json", "setup.json", "meta.json"])
def test_missing_run_file_is_a_config_error(tmp_path, break_it):
    dst = tmp_path / "run"
    shutil.copytree(RUN_DIR, dst)
    (dst / break_it).unlink()
    with pytest.raises(ConfigError, match=break_it):
        load_run_story(dst)


def test_run_dir_without_packages_is_a_config_error(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(RUN_DIR, dst)
    dump = json.loads((dst / "truth_dump.json").read_text(encoding="utf-8"))
    del dump["packages"]
    (dst / "truth_dump.json").write_text(json.dumps(dump), encoding="utf-8")
    with pytest.raises(ConfigError, match="packages"):
        load_run_story(dst)


def test_run_story_hash_changes_when_the_dump_changes(tmp_path):
    dst = tmp_path / "run"
    shutil.copytree(RUN_DIR, dst)
    before = load_run_story(dst).hashes["run/truth_dump.json"]
    path = dst / "truth_dump.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert load_run_story(dst).hashes["run/truth_dump.json"] != before


# --- sổ tay đệm -------------------------------------------------------------------------------


SPEC = PadSpec(count=300, seed=7)


def test_pad_adds_exactly_count_entries_and_keeps_the_real_ones():
    view = view_of(load_sample_story(), 5)
    padded = pad_view(view, SPEC)
    assert len(padded.entries) == len(view.entries) + SPEC.count
    assert set(view.entries) <= set(padded.entries) and padded.lies == view.lies
    assert (padded.story_id, padded.chapter) == (view.story_id, view.chapter)


def test_pad_is_deterministic_and_seed_dependent():
    view = view_of(load_sample_story(), 5)
    assert pad_view(view, SPEC) == pad_view(view, SPEC)
    assert pad_view(view, SPEC) != pad_view(view, PadSpec(count=300, seed=8))


def test_pad_entries_are_unique_and_dont_repeat_real_text():
    view = view_of(load_sample_story(), 5)
    padded = pad_view(view, PadSpec(count=900, seed=1))
    texts = [e.text for e in padded.entries]
    assert len(set(texts)) == len(texts)
    assert len({e.id for e in padded.entries}) == len(padded.entries)


def test_pad_chapters_stay_inside_the_story_and_ids_are_marked():
    view = view_of(load_sample_story(), 3)
    extra = [e for e in pad_view(view, SPEC).entries if e.id.startswith("pad-")]
    assert len(extra) == SPEC.count
    assert all(1 <= e.since_chapter <= 3 for e in extra)


def test_pad_mixes_kinds_and_links_facts_to_padded_characters_only():
    view = view_of(load_sample_story(), 5)
    extra = [e for e in pad_view(view, SPEC).entries if e.id.startswith("pad-")]
    assert {e.kind for e in extra} >= {"Character", "Location", "Item", "Fact", "Event"}
    ids = {e.id for e in extra}
    linked = [e for e in extra if e.about]
    assert linked and all(set(e.about) <= ids for e in linked)


def test_pad_has_words_that_look_like_the_real_story_to_make_retrieval_work():
    view = view_of(load_sample_story(), 5)
    text = " ".join(e.text for e in pad_view(view, SPEC).entries if e.id.startswith("pad-"))
    for word in ("lò rèn", "thanh kiếm", "quán trà"):
        assert word in text


def test_refs_of_real_entries_shift_but_every_ref_still_resolves():
    view = view_of(load_sample_story(), 5)
    padded = pad_view(view, SPEC)
    refs = dict(public_entries(padded))
    assert len(refs) == len(padded.entries)
    assert {e.id for e in view.entries} <= {e.id for e in refs.values()}


def test_pad_spec_rejects_nonsense():
    with pytest.raises(ValueError):
        PadSpec(count=0, seed=1)
    with pytest.raises(ValueError):
        PadSpec(count=10, seed=1, extra="x")  # type: ignore[call-arg]

