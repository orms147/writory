"""Kiểm duyệt lựa chọn khởi tạo (G9, D-137): bộ lựa chọn model tạo ở mỗi bước (bối cảnh, hướng
truyện, nhân vật chính) qua một lời gọi kiểm duyệt chấm từng lựa chọn, ở mức u tối người chơi đã
chọn, trước khi lưu hay trả về. Model giả, không Docker.

Luồng qua API trên Postgres + Neo4j: tests/graph/test_setup_api.py.
"""

import html

import pytest

from tests.moderation_fixtures import ModeratedLLM, lines_reply
from writory.api.setup import (
    MIN_SETUP_OPTIONS,
    SETUP_REGENERATIONS,
    moderated_options,
    option_line,
)
from writory.config import CostLimits, load_config
from writory.errors import ErrorCode, WritoryError
from writory.llm.cost import CostTracker, MeteredClient
from writory.llm.fake import FakeLLM
from writory.pipeline.setup import OPTION_COUNT, CharacterOption, PlotOption, SettingOption
from writory.safety.moderate import ChoicesModerationOutput
from writory.safety.wrap import CLOSE_TAG

CFG = load_config()
HARD = ("sexual_minors", "mild")
BLOCK = ("real_world_harm", "strong")


def settings(tag: str = "") -> list[SettingOption]:
    return [SettingOption(title=f"Bối cảnh {i}{tag}", intro=f"Trấn ven sông thứ {i}{tag}.")
            for i in range(OPTION_COUNT)]


class Proposer:
    """Bước tạo lựa chọn giả: mỗi lần gọi trả bộ kế tiếp, đếm số lần gọi."""

    def __init__(self, *batches: list) -> None:
        self.batches = list(batches)
        self.calls = 0

    async def __call__(self) -> list:
        self.calls += 1
        return self.batches.pop(0)


def moderator(*replies) -> ModeratedLLM:
    """Chỉ lời gọi kiểm duyệt được trả lời; lời gọi model nào khác làm test đỏ."""
    return ModeratedLLM(FakeLLM.scripted([]), replies)


async def run(proposer: Proposer, llm, *, level: str | None = "light", step: str = "settings"):
    return await moderated_options(proposer, llm=llm, config=CFG, darkness_level=level, step=step)


def test_the_minimum_is_below_the_option_count():
    assert 1 <= MIN_SETUP_OPTIONS < OPTION_COUNT and SETUP_REGENERATIONS >= 0


def test_an_option_line_has_every_field_on_one_line():
    pc = CharacterOption(name="Lục Vân", personality="Ít nói,\n  cố chấp.",
                         backstory="Con thợ rèn.\nMồ côi từ nhỏ.")
    line = option_line(pc)
    assert "\n" not in line
    for part in ("Lục Vân", "Ít nói, cố chấp.", "Con thợ rèn. Mồ côi từ nhỏ."):
        assert part in line
    assert "Hướng 1" in option_line(PlotOption(title="Hướng 1", summary="Lần theo dấu vết."))


async def test_the_whole_set_goes_to_one_moderation_call_as_wrapped_data():
    chars = [CharacterOption(name=f"Lục Vân {i}", personality="Ít nói, cố chấp.",
                             backstory=f"Con thợ rèn thứ {i}.") for i in range(OPTION_COUNT)]
    llm = moderator()
    got = await run(Proposer(chars), llm, step="characters")
    assert got == chars
    assert llm.script.moderation_schemas == [ChoicesModerationOutput]  # một lời gọi cho cả bộ
    [messages] = llm.moderation_calls
    system = " ".join(m.content for m in messages if m.role == "system")
    [user] = [m.content for m in messages if m.role == "user"]
    # G4: chữ model viết (người chơi sẽ đọc, rồi thành thiết lập truyện) chỉ nằm trong khối dữ liệu.
    assert user.count("<player_data") == 1 and user.rstrip().endswith(CLOSE_TAG)
    data = html.unescape(user.split("<player_data", 1)[1])
    for i, c in enumerate(chars, 1):
        assert f"[{i}] {option_line(c)}" in data
        assert c.name not in system
    assert "<player_data" not in system


@pytest.mark.parametrize("finding", [HARD, BLOCK, ("gore", "strong")],
                         ids=["hard-block", "block", "over-darkness"])
async def test_a_blocked_option_is_dropped_and_the_others_are_kept(finding):
    proposer = Proposer(settings())
    llm = moderator(lines_reply(OPTION_COUNT, {2: [finding]}))
    got = await run(proposer, llm)
    assert [o.title for o in got] == ["Bối cảnh 0", "Bối cảnh 2"]
    # Còn đủ số tối thiểu: không tạo lại, không thêm lời gọi.
    assert proposer.calls == 1 and len(llm.moderation_calls) == 1


@pytest.mark.parametrize(("level", "kept"), [("light", 2), ("moderate", 3), (None, 3)])
async def test_the_darkness_ceiling_is_the_one_the_player_chose(level, kept):
    """Máu me tả lướt: vượt trần của mức "Nhẹ", trong trần của mức "Vừa" (mặc định khi phiên cũ
    không có mức, D-67)."""
    assert CFG.moderation.default_darkness_level == "moderate"
    llm = moderator(lines_reply(OPTION_COUNT, {1: [("gore", "mild")]}))
    assert len(await run(Proposer(settings()), llm, level=level)) == kept


async def test_below_the_minimum_the_step_is_generated_once_more_and_moderated_again():
    proposer = Proposer(settings(), settings(" mới"))
    llm = moderator(lines_reply(OPTION_COUNT, {1: [HARD], 3: [BLOCK]}), lines_reply(OPTION_COUNT))
    got = await run(proposer, llm)
    assert [o.title for o in got] == [f"Bối cảnh {i} mới" for i in range(OPTION_COUNT)]
    assert proposer.calls == 2 and len(llm.moderation_calls) == 2
    assert "Bối cảnh 0 mới" in llm.moderation_calls[1][-1].content
    assert all("Bối cảnh 1." not in o.intro for o in got)  # không trộn bộ cũ vào bộ mới


async def test_still_below_the_minimum_after_the_last_try_is_a_specific_error():
    tries = 1 + SETUP_REGENERATIONS  # giới hạn cứng (G8)
    proposer = Proposer(*[settings(f" lượt {k}") for k in range(tries)])
    llm = moderator(*[lines_reply(OPTION_COUNT, {1: [HARD], 2: [HARD]})] * tries)
    with pytest.raises(WritoryError) as exc:
        await run(proposer, llm)
    assert exc.value.code is ErrorCode.SETUP_OPTIONS_BLOCKED
    assert proposer.calls == tries and len(llm.moderation_calls) == tries
    # G12: câu trung tính, không loại nội dung, không chữ của lựa chọn.
    payload = exc.value.player_payload()
    assert set(payload) == {"code", "message"}
    for text in (payload["message"], str(exc.value)):
        assert "Bối cảnh" not in text and "sexual" not in text


@pytest.mark.parametrize("failure", ["transient", "bad-json"])
async def test_moderation_that_cannot_answer_fails_closed(failure):
    retries = CFG.limits.retries
    if failure == "transient":
        replies = [WritoryError(ErrorCode.LLM_UNAVAILABLE)] * (1 + retries.llm_transient)
    else:
        replies = ["không phải JSON"] * (1 + retries.extract_schema_retry)
    proposer = Proposer(settings())
    with pytest.raises(WritoryError) as exc:
        await run(proposer, moderator(*replies))
    assert exc.value.code in {ErrorCode.LLM_UNAVAILABLE, ErrorCode.RETRY_LIMIT_REACHED}
    assert proposer.calls == 1  # không tạo lại, không trả về bộ chưa kiểm


async def test_moderation_is_metered_and_stops_at_the_cost_cap():
    """G8: lời gọi kiểm duyệt qua đúng client của bước (MeteredClient của nơi gọi), nên tính vào
    trần và dừng trước lời gọi khi đã chạm trần."""
    limits = CostLimits(per_scene=1.0, per_chapter=1.0, per_story=1.0)
    tracker = CostTracker(limits)
    llm = MeteredClient(ModeratedLLM(FakeLLM.scripted([]), cost_usd=0.002), tracker)
    await run(Proposer(settings()), llm)
    assert tracker.story_usd == pytest.approx(0.002)

    inner = ModeratedLLM(FakeLLM.scripted([]))
    spent = MeteredClient(inner, CostTracker(limits, story_spent_usd=1.0))
    with pytest.raises(WritoryError) as exc:
        await run(Proposer(settings()), spent)
    assert exc.value.code is ErrorCode.COST_LIMIT_STORY
    assert inner.moderation_calls == []
