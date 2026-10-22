"""Ước tính chi phí chương tới (design §10, D-87): trung vị chi phí thật các chương đã ghi của chính
truyện đó; chưa có chương nào thì số mặc định trong config. Không Docker: nhật ký chi phí trong bộ nhớ
(SQL thật ở tests/graph/test_ui_api.py)."""

import shutil
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from tests.api_fixtures import MemoryCostLedger
from tests.unit.test_api_stories import build
from tests.unit.test_api_ui import build as build_ui
from writory.api import deps
from writory.config import REPO_CONFIG_DIR, ConfigError, load_config
from writory.db import CostEntry
from writory.llm.cost import ChapterEstimate, estimate_chapter_cost

CFG = load_config()
DEFAULT = CFG.limits.chapter_estimate.default_usd


# --- phép tính thuần ----------------------------------------------------------------------------


def test_median_of_the_stories_own_chapters():
    got = estimate_chapter_cost([0.012, 0.007, 0.010], default_usd=0.5)
    assert got == ChapterEstimate(usd=0.010, source="story_median", chapters_used=3)


def test_median_of_an_even_number_averages_the_middle_two():
    got = estimate_chapter_cost([0.004, 0.020, 0.008, 0.010], default_usd=0.5)
    assert got.usd == pytest.approx(0.009) and got.chapters_used == 4


def test_one_outlier_chapter_does_not_move_the_estimate():
    """Lý do chọn trung vị, không phải trung bình: một chương viết lại nhiều lần tốn gấp mấy lần."""
    got = estimate_chapter_cost([0.008, 0.009, 0.010, 0.011, 0.300], default_usd=0.5)
    assert got.usd == pytest.approx(0.010)


def test_story_without_chapters_uses_the_config_default():
    assert estimate_chapter_cost([], default_usd=0.01) == ChapterEstimate(
        usd=0.01, source="default", chapters_used=0)


def test_no_default_and_no_chapters_gives_no_number_rather_than_zero():
    got = estimate_chapter_cost([], default_usd=None)
    assert got == ChapterEstimate(usd=None, source="default", chapters_used=0)


def test_the_stories_own_chapters_win_even_if_there_is_no_default():
    assert estimate_chapter_cost([0.02], default_usd=None).source == "story_median"


# --- config -------------------------------------------------------------------------------------


def test_default_lives_in_limits_yaml_as_a_provisional_number():
    assert DEFAULT is not None and 0 < DEFAULT < CFG.limits.cost_usd.per_chapter
    text = (REPO_CONFIG_DIR / "limits.yaml").read_text(encoding="utf-8")
    assert "chapter_estimate" in text and "D-87" in text


def test_default_must_not_be_negative(tmp_path: Path):
    target = tmp_path / "config"
    shutil.copytree(REPO_CONFIG_DIR, target)
    path = target / "limits.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["chapter_estimate"]["default_usd"] = -0.01
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
    with pytest.raises(ConfigError, match="chapter_estimate"):
        load_config(target)


def test_public_config_exposes_the_default_for_screens_without_a_story():
    with TestClient(build_ui()) as client:
        body = client.get("/config/public").json()
    assert body["chapter_estimate_default_usd"] == DEFAULT


def test_public_config_default_is_null_when_unset():
    cfg = CFG.model_copy(update={"limits": CFG.limits.model_copy(update={
        "chapter_estimate": CFG.limits.chapter_estimate.model_copy(update={"default_usd": None})})})
    with TestClient(build_ui(config=cfg)) as client:
        assert client.get("/config/public").json()["chapter_estimate_default_usd"] is None


# --- endpoint -----------------------------------------------------------------------------------


def seed(ledger: MemoryCostLedger, story: str, costs: dict[int, float], *, role="writer") -> None:
    for chapter, usd in costs.items():
        ledger.record(CostEntry(role, "m", 1, 1, usd), story_id=story, chapter=chapter)


def estimate(client: TestClient, story: str = "s1"):
    return client.get(f"/stories/{story}/estimate")


def test_endpoint_gives_the_median_the_next_chapter_and_how_many_chapters_it_used():
    app = build(chapter=4)
    ledger = MemoryCostLedger()
    seed(ledger, "s1", {1: 0.010, 2: 0.007, 3: 0.012, 4: 0.020})
    app.dependency_overrides[deps.get_cost_ledger] = lambda: ledger
    with TestClient(app) as client:
        resp = estimate(client)
    assert resp.status_code == 200
    assert resp.json() == {"chapter": 5, "usd": pytest.approx(0.011), "source": "story_median",
                           "chapters_used": 4}


def test_endpoint_sums_every_call_of_a_chapter_before_taking_the_median():
    app = build(chapter=2)
    ledger = MemoryCostLedger()
    for role, usd in (("outline", 0.002), ("writer", 0.004), ("extract", 0.003)):
        seed(ledger, "s1", {1: usd}, role=role)  # chương 1: 0,009
    seed(ledger, "s1", {2: 0.011})
    app.dependency_overrides[deps.get_cost_ledger] = lambda: ledger
    with TestClient(app) as client:
        body = estimate(client).json()
    assert body["usd"] == pytest.approx(0.010) and body["chapters_used"] == 2


def test_endpoint_ignores_player_side_roles_setup_chapter_zero_and_other_stories():
    app = build(chapter=2)
    ledger = MemoryCostLedger()
    seed(ledger, "s1", {1: 0.010, 2: 0.010})
    seed(ledger, "s1", {1: 0.9, 2: 0.9}, role="narrator")  # hỏi người kể không phải viết chương
    seed(ledger, "s1", {1: 0.9}, role="classify")
    seed(ledger, "s1", {0: 0.9}, role="setup")
    seed(ledger, "s1", {0: 0.9})  # chương 0 không phải chương viết
    seed(ledger, "s2", {1: 0.9, 2: 0.9})
    app.dependency_overrides[deps.get_cost_ledger] = lambda: ledger
    with TestClient(app) as client:
        body = estimate(client).json()
    assert body["usd"] == pytest.approx(0.010) and body["chapters_used"] == 2


def test_endpoint_falls_back_to_the_default_for_a_story_with_no_written_chapter():
    app = build(chapter=0)
    with TestClient(app) as client:
        body = estimate(client).json()
    assert body == {"chapter": 1, "usd": DEFAULT, "source": "default", "chapters_used": 0}


def test_endpoint_without_any_number_says_so():
    cfg = CFG.model_copy(update={"limits": CFG.limits.model_copy(update={
        "chapter_estimate": CFG.limits.chapter_estimate.model_copy(update={"default_usd": None})})})
    app = build(chapter=0)
    app.state.config = cfg
    with TestClient(app) as client:
        body = estimate(client).json()
    assert body == {"chapter": 1, "usd": None, "source": "default", "chapters_used": 0}


def test_endpoint_of_someone_elses_or_missing_story_is_404():
    with TestClient(build()) as client:
        assert estimate(client, "khong-co").status_code == 404


def test_endpoint_exposes_nothing_but_the_four_fields():
    """G1/G7: không model, không giá, không chi phí từng vai, không id."""
    app = build(chapter=1)
    ledger = MemoryCostLedger()
    seed(ledger, "s1", {1: 0.010})
    app.dependency_overrides[deps.get_cost_ledger] = lambda: ledger
    with TestClient(app) as client:
        body = estimate(client).json()
    assert set(body) == {"chapter", "usd", "source", "chapters_used"}
