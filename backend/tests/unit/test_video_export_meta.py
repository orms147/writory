"""Bộ xuất kịch bản video chọn nhà cung cấp theo config (D-140): model của vai `video` và `moderate`."""

import json

import pytest

from tests.pipeline_fixtures import make_config
from tests.unit.test_video_export import args, source
from writory.export import video
from writory.llm.fake import FakeLLM

META = "meta/muse-wonder-1.0"
META_MODELS = {"roles": {"video": META, "moderate": META},
               "prices": {META: {"in": 4.0, "cached_in": 0.2, "out": 20.0}}}


@pytest.fixture(autouse=True)
def no_keys_in_the_environment(monkeypatch):
    for name in ("OPENROUTER_API_KEY", "META_API_KEY"):
        monkeypatch.delenv(name, raising=False)


async def test_script_json_names_the_provider_of_the_models_it_used(tmp_path):
    make_config(tmp_path, models=META_MODELS)
    assert await video.run(args(tmp_path, "--dry-run"), source=source()) == video.EXIT_OK
    meta = json.loads((tmp_path / "out" / "script.json").read_text(encoding="utf-8"))["meta"]
    assert meta["provider"] == "meta" and meta["model"] == META


async def test_a_sheets_only_export_has_no_provider_because_it_calls_no_model(tmp_path):
    make_config(tmp_path)
    assert await video.run(args(tmp_path, "--sheets-only"), source=source()) == video.EXIT_OK
    assert json.loads((tmp_path / "out" / "script.json").read_text(encoding="utf-8"))["meta"]["provider"] is None


async def test_the_real_run_asks_the_shared_factory_for_the_video_and_moderation_models(monkeypatch, tmp_path):
    make_config(tmp_path, models=META_MODELS)
    seen = {}

    def factory(config, env_file, **kw):
        seen.update(models=sorted(kw["models"]), deadline=kw["deadline_s"], env_file=env_file)
        return FakeLLM([])

    monkeypatch.setattr("writory.llm.provider.bench_llm", factory)
    await video.run(args(tmp_path, "--budget", "0.1", "--env-file", str(tmp_path / "e.env")), source=source())
    assert seen["models"] == [META, META]      # vai video và vai moderate
    assert seen["env_file"] == tmp_path / "e.env" and seen["deadline"] is not None
