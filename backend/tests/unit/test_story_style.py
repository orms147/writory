"""Kiểu truyện: truyện chữ hay kịch bản audio (D-153). Chỉ đổi văn phong của model viết; đồ thị, dàn ý, trích,
người canh, sổ tay giữ nguyên."""

import pytest
from pydantic import ValidationError

from writory.api.play import script_text
from writory.api.schemas import SetupStartIn
from writory.config import REPO_ROOT
from writory.pipeline.scene import (
    AUDIO_STYLE_GUIDE_PATH,
    STORY_STYLES,
    load_style_guide,
    style_guide_for,
)

START = {"tags": {"genre": "đô thị", "era": "hiện đại", "voice": "lạnh"}, "length_level": "short"}


def test_prose_keeps_the_default_guide_and_audio_gets_its_own():
    assert STORY_STYLES == ("prose", "audio")
    assert style_guide_for("prose") is None  # ChapterRun dùng bản mặc định như trước
    audio = style_guide_for("audio")
    assert audio == load_style_guide(AUDIO_STYLE_GUIDE_PATH) and "TTS" in audio
    assert audio != load_style_guide()
    with pytest.raises(ValueError, match="kiểu truyện"):
        style_guide_for("thơ")


def test_the_audio_guide_keeps_every_rule_the_code_checks():
    """Kiểm văn bằng code chấm cùng các luật cho mọi kiểu truyện: bản audio không được bỏ luật nào."""
    audio = load_style_guide(AUDIO_STYLE_GUIDE_PATH)
    for rule in ('mở đầu bằng "- "', "không dùng ngoặc kép cho lời thoại", 'xưng "tôi"',
                 "không viết chữ Hán", "Không được nói ra bí mật", "Xưng hô theo đúng bảng",
                 "Chỉ viết văn bản của cảnh"):
        assert rule in audio, rule
    assert "<!--" not in audio  # khối chú thích bị bỏ


def test_the_prod_image_carries_the_audio_guide():
    dockerfile = (REPO_ROOT / "deploy" / "backend.Dockerfile").read_text(encoding="utf-8")
    assert "evals/scenarios/quality/style_guide_audio_vi.md" in dockerfile


def test_the_story_style_column_has_a_migration():
    files = sorted((REPO_ROOT / "backend" / "src" / "writory" / "db" / "migrations").glob("*_story_style.sql"))
    assert files and "style" in files[0].read_text(encoding="utf-8")


def test_setup_takes_a_known_style_and_defaults_to_prose():
    assert SetupStartIn.model_validate(START).style == "prose"
    assert SetupStartIn.model_validate(START | {"style": "audio"}).style == "audio"
    with pytest.raises(ValidationError):
        SetupStartIn.model_validate(START | {"style": "radio"})


def test_the_script_joins_shown_chapters_in_order_and_quotes_dialogue_for_tts():
    texts = {2: "Tôi quay lại.\n- Anh là ai?\n\nCô ta tái mặt.", 1: "Ngày đầu về nhà.\n- Cút ra ngoài!"}
    assert script_text(texts) == ("Ngày đầu về nhà.\n“Cút ra ngoài!”\n\n"
                                  "Tôi quay lại.\n“Anh là ai?”\n\nCô ta tái mặt.\n")
    assert script_text({}) == ""
