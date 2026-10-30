"""Cấu hình bộ đo dùng model Meta (D-140): tiền tố `meta/`, thư mục config chỉ chứa phần khác `config/`, và sản
phẩm cho người chơi từ chối model Meta. Không mạng."""

import shutil
from pathlib import Path

import httpx
import pytest
import yaml
from pydantic import SecretStr

from tests.pipeline_fixtures import make_config
from writory.api.app import create_app
from writory.config import (
    REPO_CONFIG_DIR,
    REPO_ROOT,
    ConfigError,
    ModelPrice,
    config_bytes,
    config_sources,
    is_meta_model,
    load_config,
    product_model_problems,
)
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import Message
from writory.llm.openrouter import OpenRouterClient

META_CONFIG_DIR = REPO_ROOT / "evals" / "config" / "meta"
MODEL = "meta/muse-wonder-1.0"


def test_only_the_exact_meta_prefix_marks_a_meta_model():
    assert is_meta_model(MODEL) and not is_meta_model("meta-llama/llama-4") and not is_meta_model(None)
    assert not is_meta_model("openai/gpt-6-luna") and not is_meta_model("")


def test_a_price_may_carry_a_cached_input_rate_and_defaults_to_none():
    assert ModelPrice.model_validate({"in": 4.0, "cached_in": 0.2, "out": 20.0}).cached_in == 0.2
    assert ModelPrice.model_validate({"in": 4.0, "out": 20.0}).cached_in is None
    with pytest.raises(ValueError):
        ModelPrice.model_validate({"in": 4.0, "cached_in": -1, "out": 20.0})


# --- thư mục config chỉ chứa phần khác: gộp từng khoá ------------------------------------------------


def test_a_config_dir_with_only_models_takes_every_other_file_from_the_repo_config(tmp_path):
    shutil.copy(REPO_CONFIG_DIR / "models.yaml", tmp_path / "models.yaml")
    overlay, base = load_config(tmp_path), load_config()
    assert overlay.limits == base.limits and overlay.quality == base.quality and overlay.models == base.models
    assert config_sources(tmp_path, "limits.yaml") == (REPO_CONFIG_DIR / "limits.yaml",)
    assert config_sources(tmp_path, "models.yaml") == (REPO_CONFIG_DIR / "models.yaml", tmp_path / "models.yaml")
    assert config_sources(REPO_CONFIG_DIR, "limits.yaml") == (REPO_CONFIG_DIR / "limits.yaml",)


def test_a_dir_with_every_config_file_stands_alone_and_a_missing_key_is_an_error_as_before(tmp_path):
    for path in REPO_CONFIG_DIR.glob("*.yaml"):
        shutil.copy(path, tmp_path / path.name)
    assert config_sources(tmp_path, "limits.yaml") == (tmp_path / "limits.yaml",)
    assert config_bytes(tmp_path, "limits.yaml") == (REPO_CONFIG_DIR / "limits.yaml").read_bytes()
    limits = yaml.safe_load((tmp_path / "limits.yaml").read_text(encoding="utf-8"))
    del limits["cost_usd"]["per_story"]
    (tmp_path / "limits.yaml").write_text(yaml.safe_dump(limits), encoding="utf-8")
    with pytest.raises(ConfigError, match="per_story"):     # khoá thiếu: không lấy từ config/
        load_config(tmp_path)
    assert config_sources(tmp_path, "limits.yaml") == (tmp_path / "limits.yaml",)


def test_a_key_present_in_the_dir_overrides_it_and_every_other_key_comes_from_the_repo_file(tmp_path):
    (tmp_path / "limits.yaml").write_text("cost_usd:\n  per_story: 0.123\n", encoding="utf-8")
    merged, base = load_config(tmp_path).limits, load_config().limits
    assert merged.cost_usd.per_story == 0.123
    assert merged.cost_usd.per_scene == base.cost_usd.per_scene and merged.cost_usd.per_chapter == base.cost_usd.per_chapter
    assert merged.context == base.context and merged.retries == base.retries


def test_a_list_in_the_dir_replaces_the_repo_list_and_a_null_overrides_a_value(tmp_path):
    (tmp_path / "models.yaml").write_text(
        "writer_tiers:\n  - {id: x, label: X, model: openai/gpt-6-luna, eval_result: e}\n"
        "roles:\n  summary: null\n", encoding="utf-8")
    models = load_config(tmp_path).models
    assert [t.id for t in models.writer_tiers] == ["x"] and models.roles.summary is None
    assert models.roles.setup == load_config().models.roles.setup


def test_the_hash_covers_the_merged_config_so_a_change_in_either_source_changes_it(tmp_path):
    (tmp_path / "limits.yaml").write_bytes(b"cost_usd:\n  per_story: 0.5\n")  # bytes: không bị đổi sang CRLF
    both = config_bytes(tmp_path, "limits.yaml")
    base = (REPO_CONFIG_DIR / "limits.yaml").read_bytes()
    assert both.startswith(base) and both.endswith(b"per_story: 0.5\n") and both != base
    assert config_bytes(REPO_CONFIG_DIR, "limits.yaml") == base


def test_a_missing_or_empty_config_dir_is_an_error_not_a_silent_fallback_to_the_repo_config(tmp_path):
    with pytest.raises(ConfigError, match="không có file config nào"):
        load_config(tmp_path / "khong-co")
    (tmp_path / "rong").mkdir()
    with pytest.raises(ConfigError, match="không có file config nào"):
        load_config(tmp_path / "rong")


def test_a_broken_file_in_the_dir_is_still_reported_by_name(tmp_path):
    (tmp_path / "models.yaml").write_text("roles: [", encoding="utf-8")
    with pytest.raises(ConfigError, match="models.yaml"):
        load_config(tmp_path)


def test_a_merged_config_that_breaks_the_schema_names_the_file(tmp_path):
    (tmp_path / "limits.yaml").write_text("cost_usd:\n  per_story: -1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="limits.yaml"):
        load_config(tmp_path)


# --- config bộ đo Meta trong repo ---------------------------------------------------------------


def test_the_repo_meta_bench_config_uses_meta_for_every_role_and_tier_and_prices_it():
    config = load_config(META_CONFIG_DIR)
    roles = config.models.roles.model_dump()
    assert roles and all(v is None or v == MODEL for v in roles.values()) and roles["setup"] == MODEL
    assert {t.model for t in config.models.writer_tiers} == {MODEL}
    price = config.models.prices[MODEL]
    assert price.input > 0 and price.output > 0 and price.cached_in is not None
    assert config.models.provider_ignore == []     # `provider` là của OpenRouter


def test_the_meta_bench_config_dir_holds_only_what_differs_from_the_repo_config():
    assert sorted(p.name for p in META_CONFIG_DIR.glob("*.yaml")) == ["limits.yaml", "models.yaml"]
    assert set(yaml.safe_load((META_CONFIG_DIR / "limits.yaml").read_text(encoding="utf-8"))) == {"cost_usd"}
    assert set(yaml.safe_load((META_CONFIG_DIR / "models.yaml").read_text(encoding="utf-8"))) == {
        "roles", "writer_tiers", "prices"}   # writer_tiers là danh sách: đổi model thì phải chép cả danh sách


def test_the_meta_cost_caps_scale_the_luna_caps_by_the_price_ratio_and_nothing_else_changes():
    meta, base = load_config(META_CONFIG_DIR), load_config()
    luna = base.models.prices["openai/gpt-6-luna"]
    ratio = meta.models.prices[MODEL].input / luna.input
    assert ratio == meta.models.prices[MODEL].output / luna.output == 40
    for name in ("per_scene", "per_chapter", "per_story"):
        assert getattr(meta.limits.cost_usd, name) == pytest.approx(getattr(base.limits.cost_usd, name) * ratio)
    assert meta.limits.model_copy(update={"cost_usd": base.limits.cost_usd}) == base.limits


def test_the_meta_models_file_keeps_the_roles_and_tiers_of_the_repo_one_apart_from_the_model_names():
    """`writer_tiers` là danh sách nên bị thay cả (D-140): sửa `config/models.yaml` thì file của bộ đo phải sửa theo.
    Lệch thì bài đo Meta chạy với vai hay mức suy luận khác sản phẩm."""
    meta, base = load_config(META_CONFIG_DIR).models, load_config().models
    assert {r: m is None for r, m in meta.roles.model_dump().items()} == {
        r: m is None for r, m in base.roles.model_dump().items()}
    assert meta.role_reasoning == base.role_reasoning   # không chép: lấy từ config/models.yaml
    assert [t.model_copy(update={"model": ""}) for t in meta.writer_tiers] == [
        t.model_copy(update={"model": ""}) for t in base.writer_tiers]


# --- sản phẩm cho người chơi ---------------------------------------------------------------------


def test_the_product_config_has_no_meta_model_and_the_check_names_each_place(tmp_path):
    assert product_model_problems(load_config()) == []
    problems = product_model_problems(load_config(META_CONFIG_DIR))
    assert any("roles.setup" in p for p in problems) and any("writer_tiers" in p for p in problems)
    assert all(MODEL in p for p in problems)


def test_the_app_refuses_to_start_with_a_meta_model_in_its_config(tmp_path):
    config = load_config(META_CONFIG_DIR)
    with pytest.raises(ConfigError, match="meta/"):
        create_app(config=config, settings=_settings(), health_checks={}, storage_setup=lambda s: None)
    create_app(config=make_config(tmp_path), settings=_settings(), health_checks={}, storage_setup=lambda s: None)


def _settings():
    from writory.config import Settings

    return Settings(_env_file=None, neo4j_uri="bolt://x", neo4j_user="u", neo4j_password=SecretStr("p"),  # type: ignore[call-arg]
                    postgres_dsn=SecretStr("postgresql://u:p@h/d"), player_key_encryption_key=SecretStr("k"))


async def test_the_openrouter_client_the_players_use_refuses_a_meta_model_before_sending():
    seen: list[httpx.Request] = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={})

    client = OpenRouterClient(SecretStr("k"), http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    with pytest.raises(WritoryError) as caught:
        await client.chat(MODEL, [Message(role="user", content="x")])
    assert caught.value.code is ErrorCode.CONFIG_MODEL_NOT_SET and seen == []
    with pytest.raises(WritoryError):
        [e async for e in client.stream(MODEL, [Message(role="user", content="x")])]
    assert seen == [] and Path(META_CONFIG_DIR).is_dir()
