"""Đề thể loại của truyện đi vào dàn ý và model viết mỗi chương (D-160)."""

import logging

from writory.config import load_config
from writory.pipeline.genres import chapter_notes, story_genre_keys
from writory.pipeline.scene import AUDIO_OUTLINE_NOTE, AUDIO_STYLE_GUIDE_PATH, load_style_guide

CFG = load_config()
SANG_VAN = CFG.genres.get("sang_van")


def test_story_genre_keys_legacy_audio():
    """Truyện audio tạo trước D-160 (không khoá) viết tiếp bằng giọng sảng văn như cũ; truyện chữ cũ không thể loại."""
    assert story_genre_keys((), "audio", CFG.genres) == ("sang_van",)
    assert story_genre_keys((), "prose", CFG.genres) == ()
    assert story_genre_keys(("do_thi", "sang_van"), "audio", CFG.genres) == ("do_thi", "sang_van")


def test_unknown_story_genre_skipped(caplog):
    with caplog.at_level(logging.WARNING, logger="writory.pipeline.genres"):
        keys = story_genre_keys(("da_bi_xoa", "do_thi"), "prose", CFG.genres)
    assert keys == ("do_thi",)
    assert "1 khoá" in caplog.text and "da_bi_xoa" not in caplog.text


def test_prose_story_without_genres_unchanged():
    """Không thể loại: (None, None), để `ChapterRun` dùng văn phong mặc định và đề dàn ý như trước."""
    assert chapter_notes("prose", (), CFG.genres) == (None, None)


def test_genre_briefs_reach_outline_and_writer():
    guide, outline = chapter_notes("prose", ("trinh_tham", "sang_van"), CFG.genres)
    assert guide is not None and guide.startswith(load_style_guide()) and SANG_VAN.voice_brief in guide
    assert outline is not None and SANG_VAN.outline_brief in outline and AUDIO_OUTLINE_NOTE not in outline


def test_legacy_audio_story_keeps_its_voice():
    guide, outline = chapter_notes("audio", (), CFG.genres)
    assert guide is not None and guide.startswith(load_style_guide(AUDIO_STYLE_GUIDE_PATH))
    assert SANG_VAN.voice_brief in guide
    assert outline is not None and outline.startswith(AUDIO_OUTLINE_NOTE) and SANG_VAN.outline_brief in outline


def test_genre_without_voice_keeps_default_guide():
    """Thể loại không có `voice_brief`, `outline_brief`: truyện chữ giữ văn phong mặc định của `ChapterRun`."""
    assert chapter_notes("prose", ("do_thi",), CFG.genres) == (None, None)
