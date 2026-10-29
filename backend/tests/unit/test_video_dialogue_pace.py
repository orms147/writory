"""Bộ xuất kịch bản video: lời thoại không được dày hơn thời lượng của shot (D-127, lỗ còn lại của D-125).
Kiểm bằng code ở `scene_problems`, model làm lại trong lượt thử lại sẵn có, và nếu vẫn dày thì code tách
shot theo câu thoại thay vì vứt cảnh. Không mạng, không model thật; số trong test là số của LIMITS dưới đây,
không phải số của config thật."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests.unit.test_video_export import (
    ALLOW,
    LIMITS,
    config,
    options,
    scene_json,
    scene_of,
    sheet_json,
    shot,
    source,
)
from writory.config import VideoExportLimits, load_config
from writory.errors import ErrorCode, WritoryError
from writory.export import shots, video
from writory.export.shots import ShotDraft
from writory.llm.fake import FakeLLM

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "video_export" / "dense_shot_demo_3_2_8.json"
RATES = {"zh": 5.0, "ja": 6.0, "vi": 4.0, "en": 3.0}
PACED = LIMITS.model_copy(update={"dialogue_max_per_second": RATES})
CAST = ["protagonist", "gu", "lan"]
PLACES = ["lo_ren"]


def line(who: str, text: str, source_text: str = "nguồn") -> dict:
    return {"speaker_id": who, "text": text, "source_text": source_text}


def talk(text: str, *, duration: int = 6, who: str = "gu") -> dict:
    """Một shot có đúng một lượt thoại của Lão Gù."""
    return shot(appears=["protagonist", "gu"], duration_s=duration, dialogue=[line(who, text)])


def real_shot() -> dict:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert data["_nguồn"] and "evals/results/2026-10-29-video-export-demo" in data["_nguồn"]
    return data["shot"]


REAL_IDS = (["bach_kinh_luan", "han_tinh_chau", "duong_anh_lac", "lao_thanh_nguyen"], ["hanh_lang_phong_luan"])


def real_problems(duration: int = 9, lang: str | None = "zh") -> list[str]:
    draft = scene_of(real_shot() | {"duration_s": duration})
    return shots.scene_problems(draft, *REAL_IDS, PACED, lang_tag=lang)


# --- đơn vị đo lời thoại ------------------------------------------------------------------------


@pytest.mark.parametrize("tag, text, expected", [
    ("zh", "你来晚了。", 4),                       # dấu câu không đọc thành tiếng
    ("zh", "不用你替大家选路。我走在前面。", 13),
    ("zh-TW", "你來晚了，老兄！", 6),
    ("ja", "遅いな、おまえ。", 6),
    ("vi", "Mày đến muộn.", 3),                     # tiếng Việt: mỗi âm tiết là một từ
    ("vi", "  Không   ai đi đầu một mình!  ", 6),
    ("en", "You are late, old man.", 5),
    ("en", "— …", 0),                               # chỉ dấu câu: không có gì để nói
    ("zh", "", 0),
])
def test_speech_units_count_letters_for_chinese_and_japanese_and_words_for_the_rest(tag, text, expected):
    assert shots.speech_units(tag, text) == expected


def test_the_limit_is_looked_up_by_the_primary_language_subtag_and_unknown_languages_are_unchecked():
    assert shots.pace_limit(PACED, "zh") == 5.0 and shots.pace_limit(PACED, "zh-TW") == 5.0
    assert shots.pace_limit(PACED, "EN") == 3.0
    assert shots.pace_limit(PACED, "fr") is None and shots.pace_limit(PACED, "th") is None
    assert shots.pace_limit(LIMITS, "zh") is None  # config không khai: không kiểm


def test_the_pace_limits_are_in_the_repo_config_and_must_be_positive():
    rates = load_config().limits.video_export.dialogue_max_per_second
    assert rates and set(rates) >= {"zh", "ja", "vi", "en"} and all(v > 0 for v in rates.values())
    with pytest.raises(ValidationError):
        VideoExportLimits(dialogue_max_per_second={"zh": 0})
    with pytest.raises(ValidationError):
        VideoExportLimits(dialogue_max_per_second={"zh": -1.5})


# --- kiểm trong scene_problems ------------------------------------------------------------------


def test_the_real_dense_shot_from_the_demo_is_caught():
    problems = real_problems(duration=9)
    assert len(problems) == 1 and "shot 1" in problems[0] and "thoại dày" in problems[0]
    assert "103" in problems[0] and "9" in problems[0], "phải nói số chữ và số giây để đọc được vì sao"


def test_a_long_enough_duration_makes_the_same_dialogue_pass():
    # 103 chữ cần 20,6 giây ở 5 chữ/giây; trần thời lượng shot là 12 giây nên shot này chỉ sửa được bằng cách tách.
    assert any("thoại dày" in p for p in real_problems(duration=12))
    roomy = PACED.model_copy(update={"shot_seconds_max": 30})
    draft = scene_of(real_shot() | {"duration_s": 21})
    assert shots.scene_problems(draft, *REAL_IDS, roomy, lang_tag="zh") == []


def test_without_a_language_the_pace_is_not_checked_so_old_callers_are_unchanged():
    assert real_problems(lang=None) == []
    assert shots.scene_problems(scene_of(talk("你好" * 40)), CAST, PLACES, PACED) == []


def test_the_pace_adds_up_the_lines_of_one_shot_and_ignores_punctuation():
    three = shot(appears=["protagonist", "gu", "lan"], duration_s=4,
                 dialogue=[line("gu", "你来晚了。"), line("lan", "对不起，我来晚了！"), line("gu", "…")])
    # 4 + 7 + 0 = 11 chữ trong 4 giây là 2,75 chữ/giây: qua.
    assert shots.scene_problems(scene_of(three), CAST, PLACES, PACED, lang_tag="zh") == []
    tight = three | {"duration_s": 3}      # 3,67 chữ/giây: vẫn qua
    assert shots.scene_problems(scene_of(tight), CAST, PLACES, PACED, lang_tag="zh") == []
    long = three | {"dialogue": three["dialogue"] + [line("lan", "你" * 10)], "duration_s": 3}
    assert any("thoại" in p for p in shots.scene_problems(scene_of(long), CAST, PLACES, PACED, lang_tag="zh"))


@pytest.mark.parametrize("lang, ok_text, dense_text", [
    ("vi", "Mày đến muộn rồi đấy", "Mày đến muộn rồi đấy lão già ạ không biết đường à sao lại thế"),
    ("en", "You are late again", "You are late again old man and you know it well"),
])
def test_vietnamese_and_english_are_counted_in_words(lang, ok_text, dense_text):
    ok = scene_of(talk(ok_text, duration=3))
    dense = scene_of(talk(dense_text, duration=3))
    assert shots.scene_problems(ok, CAST, PLACES, PACED, lang_tag=lang) == []
    assert any("thoại" in p for p in shots.scene_problems(dense, CAST, PLACES, PACED, lang_tag=lang))


def test_a_language_without_a_limit_is_never_flagged():
    assert shots.scene_problems(scene_of(talk("x " * 300, duration=3)), CAST, PLACES, PACED,
                                lang_tag="fr") == []


def test_pace_problems_are_the_only_problems_when_the_rest_of_the_scene_is_fine():
    """Phân biệt lỗi nhịp thoại (code tách được) với lỗi khác (phải làm lại hoặc bỏ cảnh)."""
    assert all("thoại dày" in p for p in real_problems())
    broken = real_shot() | {"location_id": "bay"}
    problems = shots.scene_problems(scene_of(broken), *REAL_IDS, PACED, lang_tag="zh")
    assert any("location_id" in p for p in problems) and any("thoại dày" in p for p in problems)
    assert shots.pace_only(problems) is False and shots.pace_only(real_problems()) is True
    assert shots.pace_only([]) is False


# --- tách bằng code -----------------------------------------------------------------------------


def draft_of(raw: dict) -> ShotDraft:
    return scene_of(raw).shots[0]


def test_the_real_dense_shot_is_split_by_dialogue_line_inside_the_duration_range():
    original = draft_of(real_shot())
    parts, flags = shots.split_dense_shots([original], PACED, "zh")
    assert flags == [True, True] and len(parts) == 2
    # 18 + 26 chữ vào phần một (9 giây), 19 + 40 chữ vào phần hai (12 giây): đúng độ dài thoại.
    assert [len(p.dialogue) for p in parts] == [2, 2] and [p.duration_s for p in parts] == [9, 12]
    assert [d for p in parts for d in p.dialogue] == list(original.dialogue)   # đủ, đúng thứ tự
    for p in parts:
        assert 3 <= p.duration_s <= 12
        assert shots.speech_units("zh", " ".join(d.text for d in p.dialogue)) <= 5 * p.duration_s
        for field in ("location_id", "time_of_day", "shot_size", "camera_angle", "camera_move", "appears",
                      "action_en", "covers"):
            assert getattr(p, field) == getattr(original, field)
        assert {d.speaker_id for d in p.dialogue} <= set(p.appears)


def test_shots_within_the_pace_are_left_untouched_and_unflagged():
    fine = draft_of(talk("你来晚了。", duration=6))
    silent = draft_of(shot())
    parts, flags = shots.split_dense_shots([fine, silent], PACED, "zh")
    assert parts == [fine, silent] and flags == [False, False]


def test_only_the_dense_shot_of_a_scene_is_split_and_the_order_is_kept():
    a, b, c = draft_of(talk("你好。")), draft_of(real_shot()), draft_of(talk("再见。"))
    parts, flags = shots.split_dense_shots([a, b, c], PACED, "zh")
    assert flags == [False, True, True, False] and parts[0] == a and parts[-1] == c
    assert parts[1].dialogue and parts[2].dialogue


def test_a_short_part_gets_the_minimum_duration_and_never_less():
    raw = shot(appears=["protagonist", "gu", "lan"], duration_s=12,
               dialogue=[line("gu", "你" * 58), line("lan", "好吗嗯")])    # 61 chữ, vừa quá 60 của một shot 12 giây
    parts, flags = shots.split_dense_shots([draft_of(raw)], PACED, "zh")
    assert [p.duration_s for p in parts] == [12, 3] and flags == [True, True]    # 3 chữ cần 1 giây, trần dưới là 3


def test_lines_that_exactly_fill_the_longest_shot_stay_together():
    raw = shot(appears=["protagonist", "gu", "lan"], duration_s=6,
               dialogue=[line("gu", "你" * 30), line("lan", "好" * 30)])    # 60 chữ = 5 chữ/giây x 12 giây
    parts, flags = shots.split_dense_shots([draft_of(raw)], PACED, "zh")
    assert len(parts) == 1 and parts[0].duration_s == 12 and flags == [True]


def test_dialogue_that_fits_one_longer_shot_is_not_split_only_lengthened():
    raw = shot(appears=["protagonist", "gu"], duration_s=4, dialogue=[line("gu", "你" * 30)])
    parts, flags = shots.split_dense_shots([draft_of(raw)], PACED, "zh")
    assert len(parts) == 1 and parts[0].duration_s == 6 and flags == [True]     # 30 chữ / 5 = 6 giây
    assert parts[0].dialogue == draft_of(raw).dialogue and parts[0].action_en == draft_of(raw).action_en


def test_one_line_too_long_for_any_shot_stays_whole_instead_of_losing_words():
    raw = shot(appears=["protagonist", "gu"], duration_s=12, dialogue=[line("gu", "你" * 100)])
    parts, flags = shots.split_dense_shots([draft_of(raw)], PACED, "zh")
    assert len(parts) == 1 and parts[0].dialogue[0].text == "你" * 100 and parts[0].duration_s == 12
    assert flags == [False]    # không đổi gì: vẫn quá dày, và được đánh dấu riêng ở bản xuất (pace_exceeded)
    assert shots.pace_exceeded(parts[0], PACED, "zh") is True


def test_english_dialogue_is_split_by_words_per_second():
    words = " ".join(["go"] * 14)
    lines = [line("gu", words), line("lan", words), line("gu", words)]
    raw = shot(appears=["protagonist", "gu", "lan"], duration_s=5, dialogue=lines)   # 42 từ, 3 từ/giây
    parts, flags = shots.split_dense_shots([draft_of(raw)], PACED, "en")
    assert [len(p.dialogue) for p in parts] == [2, 1] and [p.duration_s for p in parts] == [10, 5]
    assert flags == [True, True] and not any(shots.pace_exceeded(p, PACED, "en") for p in parts)
    assert [d for p in parts for d in p.dialogue] == list(draft_of(raw).dialogue)


# --- gọi model: làm lại rồi mới tách ------------------------------------------------------------


async def run_scene(llm, tmp_path, lang="zh", limits=None):
    cfg = config(tmp_path)
    limits = limits or PACED
    return await shots.make_scene_shots(
        llm, "m", [], characters=REAL_IDS[0], locations=REAL_IDS[1], limits=limits,
        retries=cfg.limits.retries, lang_tag=lang)


def real_json(duration: int = 9) -> str:
    return scene_json(real_shot() | {"duration_s": duration})


async def test_a_dense_first_answer_is_retried_and_a_good_second_answer_is_used_as_is(tmp_path):
    good = scene_json(real_shot() | {"dialogue": real_shot()["dialogue"][:1]})
    llm = FakeLLM.scripted([real_json(), good])
    result = await run_scene(llm, tmp_path)
    assert len(llm.calls) == 2 and len(result.shots) == 1 and result.split_by_code == [False]


async def test_when_every_attempt_is_too_dense_the_code_splits_instead_of_dropping_the_scene(tmp_path):
    retries = config(tmp_path).limits.retries.extract_schema_retry
    llm = FakeLLM.scripted([real_json()] * (retries + 1))
    result = await run_scene(llm, tmp_path)
    assert len(llm.calls) == retries + 1                     # đã dùng hết lượt thử lại sẵn có
    assert len(result.shots) == 2 and result.split_by_code == [True, True]
    assert [s.duration_s for s in result.shots] == [9, 12]
    assert shots.scene_problems(result, *REAL_IDS, PACED, lang_tag="zh") == []


async def test_a_hard_problem_on_the_last_attempt_still_uses_the_earlier_dense_but_valid_answer(tmp_path):
    retries = config(tmp_path).limits.retries.extract_schema_retry
    hard = scene_json(real_shot() | {"location_id": "bay"})
    llm = FakeLLM.scripted([real_json()] + [hard] * retries)
    result = await run_scene(llm, tmp_path)
    assert result.split_by_code == [True, True]


async def test_a_story_cost_cap_is_not_hidden_by_an_earlier_dense_answer(tmp_path):
    """Hết trần chi phí giữa các lượt thử là chuyện khác với hết lượt thử lại: lỗi phải lên được tới nơi gọi."""
    llm = FakeLLM.scripted([real_json(), WritoryError(ErrorCode.COST_LIMIT_STORY)])
    with pytest.raises(WritoryError) as caught:
        await run_scene(llm, tmp_path)
    assert caught.value.code is ErrorCode.COST_LIMIT_STORY


async def test_a_scene_that_never_had_a_valid_answer_still_fails_as_before(tmp_path):
    retries = config(tmp_path).limits.retries.extract_schema_retry
    hard = scene_json(real_shot() | {"location_id": "bay"})
    llm = FakeLLM.scripted([hard] * (retries + 1))
    with pytest.raises(WritoryError) as caught:
        await run_scene(llm, tmp_path)
    assert caught.value.code is ErrorCode.RETRY_LIMIT_REACHED and "location_id" in str(caught.value.__cause__)


async def test_without_a_pace_limit_for_the_language_the_dense_answer_is_accepted_as_it_is(tmp_path):
    llm = FakeLLM.scripted([real_json()])
    result = await run_scene(llm, tmp_path, lang="th")
    assert len(llm.calls) == 1 and len(result.shots) == 1 and result.split_by_code == [False]


async def test_calls_that_do_not_pass_a_language_keep_the_old_behaviour(tmp_path):
    cfg = config(tmp_path)
    llm = FakeLLM.scripted([real_json()])
    result = await shots.make_scene_shots(llm, "m", [], characters=REAL_IDS[0], locations=REAL_IDS[1],
                                          limits=PACED, retries=cfg.limits.retries)
    assert len(llm.calls) == 1 and result.split_by_code == [False]


# --- đề ----------------------------------------------------------------------------------------


def test_the_scene_prompt_tells_the_model_the_pace_from_config_and_the_version_moved():
    assert shots.PROMPT_VERSION == "video-2"
    system = shots.scene_messages(chapter=1, scene=1, scene_text="x", characters=[], locations=[],
                                  relations=[], where=None, lang_tag="zh", limits=PACED)[0].content
    assert "5 characters per second" in system
    english = shots.scene_messages(chapter=1, scene=1, scene_text="x", characters=[], locations=[],
                                   relations=[], where=None, lang_tag="en", limits=PACED)[0].content
    assert "3 words per second" in english
    french = shots.scene_messages(chapter=1, scene=1, scene_text="x", characters=[], locations=[],
                                  relations=[], where=None, lang_tag="fr", limits=PACED)[0].content
    assert "per second" not in french
    nolimit = shots.scene_messages(chapter=1, scene=1, scene_text="x", characters=[], locations=[],
                                   relations=[], where=None, lang_tag="zh", limits=LIMITS)[0].content
    assert "per second" not in nolimit


# --- cả đường xuất ------------------------------------------------------------------------------


def dense_for_the_story() -> dict:
    """Shot thật của demo nhưng nhân vật là của truyện thử (cùng độ dày thoại, cùng nhịp)."""
    lines = real_shot()["dialogue"]
    who = ["gu", "protagonist", "gu", "protagonist"]      # cảnh 1.1 của truyện thử chỉ có hai người này
    return shot(appears=["protagonist", "gu"], duration_s=9,
                dialogue=[line(w, x["text"], x["source_text"]) for w, x in zip(who, lines, strict=True)])


async def test_the_export_marks_split_shots_and_keeps_the_scene_ok(tmp_path):
    cfg = config(tmp_path)
    retries = cfg.limits.retries.extract_schema_retry
    dense = scene_json(dense_for_the_story())
    script = [sheet_json(), *[dense] * (retries + 1), ALLOW,
              scene_json(shot(appears=["protagonist", "lan"], dialogue=[], covers="Cô Lan đứng ở cửa")), ALLOW,
              scene_json(shot(location_id="cho", dialogue=[], covers="x")), ALLOW]
    llm = FakeLLM.scripted(script)
    export = await video.build_export(source(), config=cfg, llm=llm, options=options())
    first = export.scenes[0]
    assert first.status == "ok" and [s.split_by_code for s in first.shots] == [True, True]
    assert [s.n for s in first.shots] == [1, 2] and all(not s.pace_over for s in first.shots)
    assert all(not s.split_by_code for sc in export.scenes[1:] for s in sc.shots)
    # Mỗi phần có prompt riêng, chỉ chứa lời thoại của phần đó, và thời lượng của nó.
    assert first.shots[0].prompt_en.count("Spoken line in Chinese") == 2
    assert f"Duration: {first.shots[0].duration_s} seconds." in first.shots[0].prompt_en
    md = video.render_markdown(export)
    assert md.count("pace fixed by code") == 2
    data = video.export_json(export)["chapters"][0]["scenes"][0]["shots"]
    assert [s["split_by_code"] for s in data] == [True, True]


async def test_an_unsplittable_line_is_reported_as_pace_over_in_the_files(tmp_path):
    cfg = config(tmp_path)
    huge = shot(appears=["protagonist", "gu"], duration_s=12,
                dialogue=[line("gu", "你" * 100, "Một câu rất dài.")])
    retries = cfg.limits.retries.extract_schema_retry
    script = [sheet_json(), *[scene_json(huge)] * (retries + 1), ALLOW,
              scene_json(shot(dialogue=[])), ALLOW, scene_json(shot(dialogue=[])), ALLOW]
    export = await video.build_export(source(), config=cfg, llm=FakeLLM.scripted(script), options=options())
    only = export.scenes[0].shots[0]
    assert export.scenes[0].status == "ok" and len(export.scenes[0].shots) == 1
    assert only.pace_over and not only.split_by_code
    assert "denser than" in video.render_markdown(export)
