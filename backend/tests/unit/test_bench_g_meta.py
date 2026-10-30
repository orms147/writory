"""Bộ đo guardrail G5, G6, G9 chọn nhà cung cấp theo `--config-dir` (D-140), không còn OpenRouter cứng."""

import pytest

from writory.config import REPO_ROOT, load_config
from writory.safety import bench_g5, bench_g6, bench_g9

META_DIR = REPO_ROOT / "evals" / "config" / "meta"


class Stop(Exception):
    pass


CASES = [
    (bench_g5, "classify"),
    (bench_g6, "overreach"),
    (bench_g9, "moderate"),
]


@pytest.mark.parametrize(("module", "role"), CASES)
def test_the_parser_takes_a_config_dir_and_an_env_file(module, role):
    args = module.build_parser().parse_args([])
    assert args.config_dir.name == "config" and args.env_file.name == ".env"
    args = module.build_parser().parse_args(["--config-dir", str(META_DIR), "--env-file", "x.env"])
    assert args.config_dir == META_DIR and args.env_file.name == "x.env"


@pytest.mark.parametrize(("module", "role"), CASES)
async def test_the_real_run_asks_the_shared_factory_for_the_model_of_its_role(monkeypatch, tmp_path, module, role):
    seen = {}

    def factory(config, env_file, **kw):
        seen.update(config=config, env_file=env_file, models=kw["models"])
        raise Stop

    monkeypatch.setattr("writory.llm.provider.bench_llm", factory)
    args = module.build_parser().parse_args(["--config-dir", str(META_DIR), "--env-file", str(tmp_path / "e"),
                                             "--budget", "0.5"])
    with pytest.raises(Stop):
        await module._main(args)
    assert seen["models"] == ["meta/muse-wonder-1.0"] and seen["env_file"] == tmp_path / "e"
    assert getattr(seen["config"].models.roles, role) == "meta/muse-wonder-1.0"


def test_the_shared_meta_block_names_the_provider_only_when_it_knows_the_config():
    config = load_config(META_DIR)
    block = bench_g5.run_meta([], bench_g5.CASES_PATH, config=config, models=[config.models.roles.classify])
    assert block["provider"] == "meta"
    assert "provider" not in bench_g5.run_meta([], bench_g5.CASES_PATH)
