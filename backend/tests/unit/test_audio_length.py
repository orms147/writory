"""Truyện kiểu audio: độ dài theo phút nghe và chỉ dẫn riêng cho khởi tạo, dàn ý (D-155). Truyện chữ giữ nguyên."""

import pytest
from pydantic import ValidationError

from writory.api.schemas import PublicConfigOut
from writory.config import LengthLevel, load_config
from writory.pipeline.scene import AUDIO_OUTLINE_NOTE, outline_note_for
from writory.pipeline.setup import AUDIO_SETUP_NOTE, Naming, StoryChoices, StoryTags, _messages

CONFIG = load_config()
LEVELS = CONFIG.story_lengths.levels


def test_audio_levels_are_measured_in_minutes_and_open_to_players():
    audio = {k: v for k, v in LEVELS.items() if v.style == "audio"}
    # Nhãn và phút theo số đo của chủ dự án (D-159): audio_60 (6–7 chương) ra khoảng 30 phút với TTS thật.
    assert [(k, v.label, v.minutes) for k, v in audio.items()] == [
        ("audio_30", "Audio ~15 phút", 15), ("audio_45", "Audio ~23 phút", 23), ("audio_60", "Audio ~30 phút", 30),
        ("audio_xl", "Audio siêu dài", 45)]
    assert all(v.player_selectable for v in audio.values())
    ranges = [(v.chapters.min, v.chapters.max) for v in audio.values()]
    assert ranges == sorted(ranges) and ranges[0][0] >= 3  # dài hơn thì nhiều chương hơn
    assert all(v.style == "prose" and v.minutes is None for k, v in LEVELS.items() if k not in audio)


def test_an_audio_level_must_say_how_many_minutes_it_is():
    base = {"label": "x", "target_chars": 1000, "chapters": {"min": 3, "max": 4},
            "milestones": {"min": 2, "max": 3}, "max_due_per_chapter": 2, "player_selectable": True}
    with pytest.raises(ValidationError, match="minutes"):
        LengthLevel.model_validate(base | {"style": "audio"})
    assert LengthLevel.model_validate(base | {"style": "audio", "minutes": 30}).minutes == 30


def test_public_config_tells_the_ui_the_style_and_minutes_of_each_level():
    out = {lv.key: lv for lv in PublicConfigOut.from_config(CONFIG, writer_label="x").story_lengths}
    assert (out["audio_60"].style, out["audio_60"].minutes) == ("audio", 30)
    assert (out["short"].style, out["short"].minutes) == ("prose", None)


def test_only_audio_stories_get_the_outline_note():
    assert outline_note_for("prose") is None
    note = outline_note_for("audio")
    assert note == AUDIO_OUTLINE_NOTE
    for must in ("Chương cuối", "sáng mai", "xác nhận lại", "mất"):
        assert must in note, must
    with pytest.raises(ValueError):
        outline_note_for("thơ")


def _choices(style: str, level: str) -> StoryChoices:
    return StoryChoices(tags=StoryTags(genre="đô thị hào môn", era="hiện đại", voice="sảng văn"),
                        length_level=level, naming=Naming(names="viet", places="hu_cau"), style=style)


def test_only_audio_stories_get_the_setup_note_and_prose_prompts_are_unchanged():
    audio = _messages("Việc: thử.", _choices("audio", "audio_30"), CONFIG)
    prose = _messages("Việc: thử.", _choices("prose", "short"), CONFIG)
    assert AUDIO_SETUP_NOTE in audio[0].content and AUDIO_SETUP_NOTE not in prose[0].content
    assert prose[0].content == audio[0].content.replace("\n\n" + AUDIO_SETUP_NOTE, "")
    for must in ("tên", "một lần", "gỡ hết"):
        assert must in AUDIO_SETUP_NOTE, must


def test_every_open_level_allows_one_milestone_per_act_of_a_four_act_story():
    """Hồi quy 1/11/2026: đề khởi tạo đòi mỗi hồi một mốc và đúng một mốc kết; mức audio_30 cho tối đa 3 mốc nên kế
    hoạch 4 hồi (mở đầu, phát triển, cao trào, kết) luôn sai quy tắc sau lượt sửa (STORY_SETUP_INVALID, D-157)."""
    for key, level in CONFIG.story_lengths.player_levels().items():
        assert level.milestones.max >= min(level.chapters.max, 4), key


def test_super_long_audio_level_has_nine_to_ten_chapters():
    """Chủ dự án (3/11/2026): thêm mức dài hơn mức audio dài nhất khoảng 1/3, "tầm 10 chương là đủ" (D-159)."""
    level = LEVELS["audio_xl"]
    assert (level.chapters.min, level.chapters.max) == (9, 10)
    assert (level.style, level.player_selectable) == ("audio", True)
    assert level.milestones.max >= 4
