"""Biến thể đề cho bộ đo (pipeline/prompt_variants.py, D-109): đổi đề dàn ý, đề lựa chọn và chữ mục
tiêu chương mà KHÔNG đổi mã. Chỉ bộ đo đọc; sản phẩm (api/) không biết biến thể là gì."""

import hashlib
import re
from pathlib import Path

import pytest

from writory.config import REPO_ROOT, ConfigError
from writory.pipeline.prompt_variants import (
    GOAL_KEYS,
    PROMPTS_DIR,
    PromptVariant,
    load_prompt_variant,
)

OUTLINE = "Bạn lập dàn ý BIẾN THỂ cho một cảnh.\n"
CHOICES = "Bạn tạo lựa chọn BIẾN THỂ.\n"
GOALS = (
    "push_forward: Chương này phải làm người đọc muốn lật trang.\n"
    "standstill: Nhân vật chính đã ở {place} suốt {chapters} chương; đổi tình thế ngay.\n"
)


def make_variant(root: Path, name: str = "moi", **files: str) -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    for fname, text in files.items():
        (folder / fname.replace("__", ".")).write_bytes(text.encode("utf-8"))  # không đổi \n
    return folder


def full(root: Path, name: str = "moi") -> Path:
    return make_variant(root, name, outline_system__md=OUTLINE, choices_system__md=CHOICES,
                        goals__yaml=GOALS)


def test_a_full_variant_loads_every_file_and_hashes_each_one(tmp_path):
    full(tmp_path)
    v = load_prompt_variant("moi", root=tmp_path)
    assert v.name == "moi" and v.outline_system == OUTLINE.strip()
    assert v.choices_system == CHOICES.strip()
    assert set(v.goal_texts) == {"push_forward", "standstill"}
    assert v.goal_texts["push_forward"] == "Chương này phải làm người đọc muốn lật trang."
    assert set(v.files) == {"outline_system.md", "choices_system.md", "goals.yaml"}
    assert v.files["goals.yaml"] == hashlib.sha256(GOALS.encode("utf-8")).hexdigest()
    assert v.overrides() == ["outline_system", "choices_system", "goals:push_forward",
                             "goals:standstill"]


def test_a_file_that_is_missing_means_the_default(tmp_path):
    make_variant(tmp_path, outline_system__md=OUTLINE)
    v = load_prompt_variant("moi", root=tmp_path)
    assert v.outline_system and v.choices_system is None and dict(v.goal_texts) == {}
    assert v.overrides() == ["outline_system"]
    assert set(v.as_meta()["files"]) == {"outline_system.md"}


def test_meta_names_the_variant_its_files_and_what_it_overrides(tmp_path):
    full(tmp_path)
    meta = load_prompt_variant("moi", root=tmp_path).as_meta()
    assert meta["name"] == "moi" and meta["overrides"][0] == "outline_system"
    assert all(len(h) == 64 for h in meta["files"].values())


@pytest.mark.parametrize("name", ["", "../moi", "a/b", "A", "moi nay", ".", "moi\\x", "-moi"])
def test_unsafe_or_odd_names_are_refused_before_touching_the_disk(tmp_path, name):
    with pytest.raises(ConfigError, match="tên biến thể"):
        load_prompt_variant(name, root=tmp_path)


def test_unknown_variant_lists_what_exists(tmp_path):
    full(tmp_path, "co")
    with pytest.raises(ConfigError, match="không có biến thể") as exc:
        load_prompt_variant("khong", root=tmp_path)
    assert "co" in str(exc.value)


def test_an_empty_variant_is_refused_because_it_would_change_nothing(tmp_path):
    (tmp_path / "rong").mkdir()
    with pytest.raises(ConfigError, match="không đổi gì"):
        load_prompt_variant("rong", root=tmp_path)


def test_a_misspelled_file_name_is_refused_instead_of_silently_ignored(tmp_path):
    make_variant(tmp_path, outline__md=OUTLINE)
    with pytest.raises(ConfigError, match="outline.md"):
        load_prompt_variant("moi", root=tmp_path)


def test_a_readme_in_the_folder_is_allowed(tmp_path):
    make_variant(tmp_path, outline_system__md=OUTLINE, README__md="Ghi chú cho người đọc.")
    assert load_prompt_variant("moi", root=tmp_path).outline_system


@pytest.mark.parametrize(("file", "text", "match"), [
    ("outline_system__md", "  \n", "rỗng"),
    ("goals__yaml", "khong_co_khoa: x\n", "khong_co_khoa"),
    ("goals__yaml", "push_forward: ''\n", "rỗng"),
    ("goals__yaml", "- a\n- b\n", "ánh xạ"),
    ("goals__yaml", "standstill: Đã ở lâu rồi.\n", "{place}"),
    ("goals__yaml", "standstill: Đã ở {place} lâu.\n", "{chapters}"),
    ("goals__yaml", "push_forward: Gõ {place} vào đây.\n", "{place}"),
    ("choices_system__md", "ok <player_data source=\"x\">chữ</player_data>", "player_data"),
])
def test_bad_content_is_refused_with_the_file_named(tmp_path, file, text, match):
    make_variant(tmp_path, **{file: text})
    with pytest.raises(ConfigError, match=match):
        load_prompt_variant("moi", root=tmp_path)


def test_goal_keys_are_the_sentences_pacing_can_replace():
    from writory.pipeline import pacing

    assert GOAL_KEYS == frozenset(pacing.GOAL_DEFAULTS)


def test_the_variants_folder_is_inside_the_scenarios_tree():
    assert PROMPTS_DIR == REPO_ROOT / "evals" / "scenarios" / "prompts"


def test_the_product_never_reads_prompt_variants():
    """Chỉ bộ đo dùng biến thể: không có chữ nào về nó trong api/, và các nơi sản phẩm gọi model
    (`chapter.py`, `choices.py`) không import module này."""
    src = REPO_ROOT / "backend" / "src" / "writory"
    for path in (src / "api").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"prompt_variant|PromptVariant", text), path
    for name in ("pipeline/chapter.py", "pipeline/choices.py", "pipeline/scene.py",
                 "pipeline/pacing.py"):
        text = (src / name).read_text(encoding="utf-8")
        assert "import prompt_variants" not in text and "from writory.pipeline.prompt_variants" \
            not in text.replace("TYPE_CHECKING", ""), name


def test_variant_is_a_frozen_value():
    v = PromptVariant(name="x", outline_system="a", choices_system=None, goal_texts={}, files={})
    with pytest.raises(AttributeError):
        v.name = "y"  # type: ignore[misc]


def test_texts_hand_the_product_plain_strings_only(tmp_path):
    """Sản phẩm nhận `PromptTexts` (chuỗi thuần), không biết thư mục hay tên biến thể."""
    full(tmp_path)
    t = load_prompt_variant("moi", root=tmp_path).texts()
    assert (t.outline_system, t.choices_system) == (OUTLINE.strip(), CHOICES.strip())
    assert dict(t.goal_texts)["push_forward"].startswith("Chương này phải làm")
    assert load_prompt_variant("moi", root=tmp_path).texts() == t
