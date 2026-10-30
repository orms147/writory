"""bench_run chạy bằng model Meta (D-140): nhà cung cấp theo config, giá lấy từ config, meta.json ghi provider và model.
Model giả, kho trong bộ nhớ, không mạng."""

import hashlib
import json

import httpx
import pytest

from tests.pipeline_fixtures import OverlayStore, make_config
from tests.unit.test_pipeline_bench_run import make_run, scenario_for
from writory.config import REPO_CONFIG_DIR, REPO_ROOT, load_config
from writory.llm.meta import MetaClient
from writory.llm.openrouter import OpenRouterClient
from writory.pipeline import bench_run

META = "meta/muse-wonder-1.0"
META_DIR = REPO_ROOT / "evals" / "config" / "meta"
META_MODELS = {
    "roles": {role: META for role in ("outline", "extract", "choices", "narrator", "classify", "setup", "summary",
                                       "moderate", "video", "overreach")},
    "writer_tiers": [{"id": "standard", "label": "Tiêu chuẩn", "model": META, "eval_result": "x", "reasoning": "none"}],
    "prices": {META: {"in": 4.0, "cached_in": 0.2, "out": 20.0}},
}


@pytest.fixture(autouse=True)
def no_keys_in_the_environment(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "META_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def meta_config(tmp_path):
    return make_config(tmp_path, models=META_MODELS, quality={"narration": {"person": "first"}})


def sha(path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


async def written_meta(tmp_path, config):
    run, _, _, out = make_run(tmp_path, config=config, scenario=scenario_for(config), store=OverlayStore("s"),
                              chapters=1)
    assert await run.run() == bench_run.EXIT_OK
    return json.loads((out / "meta.json").read_text(encoding="utf-8"))


async def test_the_meta_json_of_a_run_names_the_provider_and_the_models(tmp_path):
    meta = await written_meta(tmp_path, meta_config(tmp_path))
    assert meta["provider"] == "meta" and meta["models"]["setup"]["model"] == META
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    plain = await written_meta(plain_dir, make_config(plain_dir, quality={"narration": {"person": "first"}}))
    assert plain["provider"] == "openrouter"


def test_the_price_of_a_model_the_scenario_does_not_list_comes_from_config_models(tmp_path):
    config = meta_config(tmp_path)
    scenario = scenario_for(config)
    bare = type(scenario).model_validate(scenario.model_dump(mode="json", by_alias=True) | {
        "prices": {"other/model": {"in": 1.0, "out": 1.0}}})
    assert bench_run.run_problems(config, bare) == []
    table = bench_run.price_table(config, bare)
    assert table[META].input == 4.0 and table[META].output == 20.0 and "other/model" in table
    # Đề ghi đè giá của config (đề khai trước khi chạy).
    pinned = type(scenario).model_validate(scenario.model_dump(mode="json", by_alias=True) | {
        "prices": {META: {"in": 9.0, "out": 9.0}}})
    assert bench_run.price_table(config, pinned)[META].input == 9.0


def test_a_model_with_no_price_anywhere_is_still_reported_before_the_first_call(tmp_path):
    config = make_config(tmp_path, models={**META_MODELS, "prices": {}}, quality={"narration": {"person": "first"}})
    scenario = scenario_for(config)
    bare = type(scenario).model_validate(scenario.model_dump(mode="json", by_alias=True) | {
        "prices": {"other/model": {"in": 1.0, "out": 1.0}}})
    assert any(META in p and "prices" in p for p in bench_run.run_problems(config, bare))


def test_the_config_hash_covers_the_files_that_are_in_effect_so_a_meta_run_hashes_the_meta_models():
    hashed = bench_run.config_sha256(META_DIR)
    assert hashed["models.yaml"] == sha(META_DIR / "models.yaml") != bench_run.config_sha256(REPO_CONFIG_DIR)["models.yaml"]
    assert hashed["limits.yaml"] == sha(REPO_CONFIG_DIR / "limits.yaml")
    assert set(bench_run.config_sha256(REPO_CONFIG_DIR)) == set(hashed)


def test_the_real_client_follows_the_config_the_run_was_started_with(tmp_path):
    env = tmp_path / ".env"
    env.write_text("META_API_KEY=m\nOPENROUTER_API_KEY=o\n", encoding="utf-8")
    http = httpx.AsyncClient()
    meta = bench_run.real_llm(load_config(META_DIR), env, http=http, deadline_s=30)
    openrouter = bench_run.real_llm(load_config(), env, http=http, deadline_s=30)
    assert isinstance(meta, MetaClient) and isinstance(openrouter, OpenRouterClient)
