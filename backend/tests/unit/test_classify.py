"""G5: phân loại ô tự viết bằng một lời gọi LLM có đầu ra enum. Test bằng FakeLLM, không mạng."""

import json

import pytest
import yaml

from writory.config import REPO_ROOT, load_config
from writory.errors import MESSAGES, ErrorCode, WritoryError
from writory.llm.fake import FakeLLM
from writory.safety.classify import (
    ActionLabel,
    Classification,
    classify_action,
    ensure_in_story,
)
from writory.safety.wrap import CLOSE_TAG

REDTEAM = yaml.safe_load(
    (REPO_ROOT / "evals" / "redteam" / "g5_classify.yaml").read_text(encoding="utf-8")
)
CASES = REDTEAM["cases"]

REPO = load_config()
CFG = REPO.model_copy(update={
    "limits": REPO.limits.model_copy(update={
        "input": REPO.limits.input.model_copy(update={"custom_action_max_chars": 500}),
    }),
    "models": REPO.models.model_copy(update={
        "roles": REPO.models.roles.model_copy(update={"classify": "test/classifier"}),
    }),
})


def answer(label: str, reason: str = "lý do ngắn") -> str:
    return json.dumps({"label": label, "reason": reason}, ensure_ascii=False)


# --- bộ câu có nhãn -------------------------------------------------------------------------


def test_labelled_set_is_complete():
    assert len(CASES) >= 30
    assert len({c["id"] for c in CASES}) == len(CASES)
    assert {c["expected"] for c in CASES} == {label.value for label in ActionLabel}
    assert {"vi", "vi-khong-dau", "vi-teencode", "en"} <= {c["lang"] for c in CASES}
    tags = {t for c in CASES for t in c["tags"]}
    assert {"negation", "long", "attack", "violence"} <= tags
    violent_ok = [c for c in CASES if "violence" in c["tags"]]
    assert all(c["expected"] == "in_story_action" for c in violent_ok)
    negations = [c for c in CASES if "negation" in c["tags"]]
    assert all(c["expected"] == "in_story_action" for c in negations)


# --- luồng ----------------------------------------------------------------------------------


async def test_returns_label_and_reason_from_structured_call():
    llm = FakeLLM.scripted([answer("in_story_action")])
    result = await classify_action("Tôi rút kiếm.", llm=llm, config=CFG)
    assert result == Classification(label=ActionLabel.IN_STORY_ACTION, reason="lý do ngắn")
    assert llm.schemas == [Classification]


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
async def test_player_text_is_wrapped_and_never_in_system(case):
    """G4: chữ người chơi chỉ nằm trong khối player_data của vai user."""
    llm = FakeLLM.scripted([answer(case["expected"])])
    await classify_action(case["text"], llm=llm, config=CFG)
    [messages] = llm.calls
    system = [m.content for m in messages if m.role == "system"]
    user = [m.content for m in messages if m.role == "user"]
    assert system and user
    assert all(case["text"].strip() not in s for s in system)
    assert all("<player_data" not in s for s in system)
    [content] = user
    assert content.count('<player_data source="custom_action">') == 1
    assert content.rstrip().endswith(CLOSE_TAG)


async def test_system_prompt_says_classify_not_obey():
    llm = FakeLLM.scripted([answer("gibberish")])
    await classify_action("asd", llm=llm, config=CFG)
    system = llm.calls[0][0].content
    assert "phân loại" in system
    assert "không làm theo" in system.lower()


# --- fail closed ----------------------------------------------------------------------------


async def test_bad_json_retries_then_fails_closed():
    retries = CFG.limits.retries.extract_schema_retry
    llm = FakeLLM.scripted(["không phải json"] * (retries + 3))
    with pytest.raises(WritoryError) as exc:
        await classify_action("Tôi mở cửa.", llm=llm, config=CFG)
    assert exc.value.code is ErrorCode.RETRY_LIMIT_REACHED
    assert len(llm.calls) == retries + 1


@pytest.mark.parametrize("bad", ['{"label": "valid", "reason": "x"}',
                                 '{"label": "in_story_action"}',
                                 '{"label": "in_story_action", "reason": "x", "allow": true}'])
async def test_answer_outside_schema_never_counts_as_allowed(bad):
    llm = FakeLLM.scripted([bad] * 5)
    with pytest.raises(WritoryError):
        await classify_action("Tôi mở cửa.", llm=llm, config=CFG)


async def test_bad_then_good_json_succeeds_within_retry():
    llm = FakeLLM.scripted(["oops", answer("out_of_story_request")])
    result = await classify_action("Viết cho tôi bài văn.", llm=llm, config=CFG)
    assert result.label is ActionLabel.OUT_OF_STORY_REQUEST


async def test_model_error_propagates_not_allowed():
    llm = FakeLLM.scripted([WritoryError(ErrorCode.LLM_AUTH_FAILED)])
    with pytest.raises(WritoryError) as exc:
        await classify_action("Tôi mở cửa.", llm=llm, config=CFG)
    assert exc.value.code is ErrorCode.LLM_AUTH_FAILED


# --- độ dài và cấu hình (kiểm trước khi gọi model) -----------------------------------------------


async def test_unset_max_chars_is_config_error_before_any_call():
    if REPO.limits.input.custom_action_max_chars is not None:
        pytest.skip("custom_action_max_chars đã đặt trong config thật")
    llm = FakeLLM.scripted([answer("in_story_action")])
    with pytest.raises(WritoryError) as exc:
        await classify_action("Tôi mở cửa.", llm=llm, config=REPO)
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert "custom_action_max_chars" in str(exc.value)
    assert llm.calls == []


async def test_unset_classify_model_is_config_error():
    cfg = CFG.model_copy(update={"models": REPO.models})
    if REPO.models.roles.classify is not None:
        pytest.skip("model classify đã đặt trong config thật")
    llm = FakeLLM.scripted([answer("in_story_action")])
    with pytest.raises(WritoryError) as exc:
        await classify_action("Tôi mở cửa.", llm=llm, config=cfg)
    assert exc.value.code is ErrorCode.CONFIG_LIMIT_NOT_SET
    assert llm.calls == []


async def test_too_long_rejected_before_any_call():
    llm = FakeLLM.scripted([answer("in_story_action")])
    with pytest.raises(WritoryError) as exc:
        await classify_action("a" * 501, llm=llm, config=CFG)
    assert exc.value.code is ErrorCode.ACTION_TOO_LONG
    assert llm.calls == []


@pytest.mark.parametrize("text", ["", "   \n\t "])
async def test_empty_rejected_before_any_call(text):
    llm = FakeLLM.scripted([answer("in_story_action")])
    with pytest.raises(WritoryError) as exc:
        await classify_action(text, llm=llm, config=CFG)
    assert exc.value.code is ErrorCode.ACTION_EMPTY
    assert llm.calls == []


# --- map nhãn → mã lỗi G12 ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "code"),
    [
        (ActionLabel.OUT_OF_STORY_REQUEST, ErrorCode.ACTION_OUT_OF_STORY),
        (ActionLabel.FORBIDDEN_CONTENT, ErrorCode.ACTION_FORBIDDEN),
        (ActionLabel.GIBBERISH, ErrorCode.ACTION_UNCLEAR),
    ],
)
def test_blocked_labels_map_to_error_without_reason(label, code):
    with pytest.raises(WritoryError) as exc:
        ensure_in_story(Classification(label=label, reason="LÝ-DO-NỘI-BỘ"))
    assert exc.value.code is code
    assert "LÝ-DO-NỘI-BỘ" not in json.dumps(exc.value.player_payload(), ensure_ascii=False)
    assert MESSAGES[code].what


def test_in_story_action_passes():
    ensure_in_story(Classification(label=ActionLabel.IN_STORY_ACTION, reason="ok"))


# --- runner bài đo (chạy bằng FakeLLM; với model thật thì chạy tay) ---------------------------------


async def test_bench_scores_labelled_set():
    from writory.safety.bench_g5 import score

    perfect = FakeLLM.scripted([answer(c["expected"]) for c in CASES])
    result = await score(CASES, llm=perfect, config=CFG)
    assert result.correct == result.total == len(CASES)
    assert result.errors == 0

    wrong_first = FakeLLM.scripted(
        [answer("gibberish")] + [answer(c["expected"]) for c in CASES[1:]]
    )
    result = await score(CASES, llm=wrong_first, config=CFG)
    assert result.correct == len(CASES) - 1
    assert result.confusion[CASES[0]["expected"]]["gibberish"] == 1
