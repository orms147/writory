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


def test_the_config_hash_covers_the_merged_config_so_a_meta_run_hashes_both_sources():
    from writory.config import config_bytes

    repo, meta = bench_run.config_sha256(REPO_CONFIG_DIR), bench_run.config_sha256(META_DIR)
    assert set(repo) == set(meta)
    assert meta["models.yaml"] == sha_bytes(config_bytes(META_DIR, "models.yaml")) != repo["models.yaml"]
    assert meta["limits.yaml"] == sha_bytes(config_bytes(META_DIR, "limits.yaml")) != repo["limits.yaml"]
    assert meta["quality.yaml"] == repo["quality.yaml"] == sha(REPO_CONFIG_DIR / "quality.yaml")
    assert config_bytes(META_DIR, "limits.yaml").startswith((REPO_CONFIG_DIR / "limits.yaml").read_bytes())


def sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw.replace(b"\n", b"\n")).hexdigest()


def test_the_real_client_follows_the_config_the_run_was_started_with(tmp_path):
    env = tmp_path / ".env"
    env.write_text("META_API_KEY=m\nOPENROUTER_API_KEY=o\n", encoding="utf-8")
    http = httpx.AsyncClient()
    meta = bench_run.real_llm(load_config(META_DIR), env, http=http, deadline_s=30)
    openrouter = bench_run.real_llm(load_config(), env, http=http, deadline_s=30)
    assert isinstance(meta, MetaClient) and isinstance(openrouter, OpenRouterClient)


# --- bài A và E: giá lấy từ config khi run.yaml không khai -----------------------------------------


def test_bench_a_and_e_need_no_meta_price_in_their_run_yaml_when_the_config_has_it(tmp_path):
    from writory.pipeline import bench_a, bench_e
    from writory.pipeline.bench_a_data import load_data as load_a

    config = meta_config(tmp_path)
    assert not [p for p in bench_a.run_problems(config, load_a()) if "prices" in p]
    assert not [p for p in bench_e.run_problems(config, bench_e.load_data()) if "prices" in p]
    (tmp_path / "bare").mkdir()
    bare = make_config(tmp_path / "bare", models={**META_MODELS, "prices": {}})
    assert any("prices" in p for p in bench_a.run_problems(bare, load_a()))
    assert any("prices" in p for p in bench_e.run_problems(bare, bench_e.load_data()))


async def test_calls_jsonl_keeps_the_reasoning_tokens_of_a_call_when_the_provider_reports_them(tmp_path):
    from writory.llm.base import ChatResult, LLMClient, Message, Usage
    from writory.pipeline.bench_run import BudgetedClient, Price, StepTracker
    from writory.quality.bench_d import Budget

    class Inner(LLMClient):
        def __init__(self, reasoning):
            self.reasoning = reasoning

        async def chat(self, model, messages, *, response_schema=None, extra=None):
            return ChatResult(text="x", usage=Usage(prompt_tokens=1, completion_tokens=9, cost_usd=0.001,
                                                    reasoning_tokens=self.reasoning))

        async def stream(self, model, messages):
            raise NotImplementedError
            yield

    rows: list[dict] = []
    config = meta_config(tmp_path)
    for reasoning in (7, None):
        client = BudgetedClient(Inner(reasoning), budget=Budget("t", 1.0), prices={META: Price(input=4, output=20)},
                                max_tokens=100, tracker=StepTracker(config.limits.cost_usd), record=rows.append)
        await client.chat(META, [Message(role="user", content="x")])
    assert [r["reasoning_tokens"] for r in rows] == [7, None]
