"""Router `setup`: khởi tạo truyện (design §4.1; D-38, D-39, D-45).

Máy chủ giữ các lựa chọn của mỗi bước (`setup_sessions`; 3, hoặc ít hơn khi kiểm duyệt bỏ bớt,
D-137); trình duyệt chỉ gửi số thứ tự 0–2, cộng phần sửa tên, tính cách, quá khứ của nhân vật
chính. Thứ tự: tạo phiên → bối cảnh → hướng → nhân vật → chốt. POST một bước = lấy lựa chọn đã có,
hoặc tạo nếu chưa có (chỉ khi đó mới gọi model); PUT một bước = chọn theo số thứ tự (đổi lựa chọn
thì các bước sau bị xoá).

- G1: phản hồi là `SetupOut` (danh sách trắng): không bản kế hoạch, bí mật hay id lớp truth.
- G4: tag và phần sửa nhân vật là chữ người chơi; pipeline bọc chúng như dữ liệu.
- G11: phiên chỉ đổi sau khi thao tác thành công. Chốt truyện tất cả hoặc không gì (`start_story`).
- G9, D-57: tag tự gõ được kiểm duyệt ngay trước lần tạo bối cảnh đầu (lời gọi model đầu tiên của
  phiên), và phần người chơi sửa của nhân vật chính được kiểm duyệt trước khi lưu. Bị chặn thì
  không lưu và không gọi model nào khác.
- G9, D-137: bộ lựa chọn model vừa tạo ở mỗi bước qua kiểm duyệt đầu ra trước khi lưu hay trả về
  (`moderated_options`): một lời gọi chấm từng lựa chọn, ở mức u tối của phiên. Lựa chọn bị chặn
  (chặn cứng, chặn, vượt trần) bị bỏ; còn dưới `MIN_SETUP_OPTIONS` thì tạo lại bước đó, tối đa
  `SETUP_REGENERATIONS` lần, rồi SETUP_OPTIONS_BLOCKED. Kiểm duyệt lỗi thì ném lỗi, không lưu gì.
  Chốt (`finalize`) không trả chữ model nào mới: thiết lập truyện dựng từ lựa chọn đã kiểm và chữ
  người chơi đã kiểm.
- Gọi model bằng key người chơi (`deps.PlayerLLM`), ghi nhật ký theo phiên rồi gắn vào truyện (G8).
  Thử lại lỗi mạng theo từng lời gọi model, trong pipeline (D-14, D-105), không bọc cả bước.
- Mức u tối (D-67): một khoá của `moderation.darkness_levels`, chọn lúc tạo phiên (bỏ trống thì mức
  mặc định, ghi hẳn khoá vào phiên); lưu theo truyện lúc chốt, làm trần kiểm duyệt mỗi chương.
Mount theo chế độ đăng nhập (`deps.api_guard`, D-41, D-89).
"""

import logging
import uuid
from collections.abc import Awaitable, Callable, Iterator
from functools import partial

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from writory.api import deps
from writory.api.schemas import CharacterChoiceIn, OptionChoiceIn, SetupOut, SetupStartIn
from writory.config import AppConfig, InputLimits, LimitNotSetError
from writory.db import (
    SetupRecord,
    SetupStep,
    SetupStepError,
    choose_setup_option,
    create_setup,
    discard_story,
    finish_setup,
    get_setup,
    job_lock,
    save_setup_options,
    start_story,
)
from writory.errors import ErrorCode, WritoryError
from writory.llm.base import LLMClient
from writory.pipeline.setup import (
    CharacterOption,
    Naming,
    PlotOption,
    SettingOption,
    StoryChoices,
    StoryTags,
    build_story,
    default_naming,
    propose_characters,
    propose_plots,
    propose_settings,
    story_brief,
)
from writory.safety.moderate import Source, Verdict, ensure_input_allowed, moderate

log = logging.getLogger(__name__)

router = APIRouter(prefix="/setup", dependencies=[Depends(deps.api_guard)])

# Kiểm duyệt lựa chọn khởi tạo (G9, D-137). Còn ít nhất ngần ấy lựa chọn sau khi bỏ lựa chọn bị chặn
# thì hiện số còn lại (như `pipeline.choices.MIN_CHOICES`, D-114); không thì tạo lại cả bước, tối
# đa `SETUP_REGENERATIONS` lần (giới hạn cứng, G8), mỗi lần một lời gọi tạo và một lời gọi kiểm.
MIN_SETUP_OPTIONS = 2
SETUP_REGENERATIONS = 1

_PREVIOUS: dict[SetupStep, SetupStep | None] = {
    "settings": None, "plots": "settings", "characters": "plots"}
# Trường sửa được của nhân vật chính → giới hạn trong config/limits.yaml `input`.
_EDIT_LIMITS = {"name": "character_name_max_chars", "personality": "personality_max_chars",
                "backstory": "backstory_max_chars"}


def _tags_text(tags: StoryTags) -> str:
    """Các tag người chơi đã chọn hoặc tự gõ, để kiểm duyệt."""
    return "\n".join(t for t in (tags.genre, tags.era, tags.voice, tags.darkness) if t)


def _edited_text(body: CharacterChoiceIn) -> str:
    """Chỉ phần người chơi sửa (chữ gốc của lựa chọn do model tạo, không phải chữ người chơi)."""
    return "\n".join(v for v in (body.name, body.personality, body.backstory) if v is not None)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def _limit(limits: InputLimits, name: str) -> int:
    try:
        return limits.require(name)
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None


@router.post("", response_model=SetupOut)
def start_setup(body: SetupStartIn, conn: deps.PgConn, owner: deps.Owner,
                config: deps.Config) -> SetupOut:
    """Tạo phiên từ tag, độ dài, quy ước tên (design §4.1 bước 1–3). Chưa gọi model."""
    if body.length_level not in config.story_lengths.levels:
        raise WritoryError(ErrorCode.REQUEST_INVALID, fields=["length_level"],
                           detail=f"mức độ dài {body.length_level!r} không có trong config")
    if body.length_level not in config.story_lengths.player_levels():
        raise WritoryError(ErrorCode.STORY_LENGTH_NOT_OPEN, fields=["length_level"],
                           detail=f"mức độ dài {body.length_level!r} chưa mở cho người chơi")
    if config.story_lengths.levels[body.length_level].style != body.style:
        raise WritoryError(ErrorCode.REQUEST_INVALID, fields=["length_level"],
                           detail=f"mức độ dài {body.length_level!r} không dành cho kiểu truyện {body.style!r} (D-155)")
    darkness = body.darkness_level or config.moderation.default_darkness_level
    if darkness not in config.moderation.darkness_levels:
        raise WritoryError(ErrorCode.REQUEST_INVALID, fields=["darkness_level"],
                           detail=f"mức u tối {darkness!r} không có trong config")
    tags = StoryTags(**body.tags.model_dump())
    naming = (Naming(**body.naming.model_dump()) if body.naming is not None
              else default_naming(tags.genre))
    choices = StoryChoices(tags=tags, length_level=body.length_level, naming=naming,
                           darkness_level=darkness, style=body.style)
    rec = create_setup(conn, _new_id("setup"), owner_id=owner,
                       choices=choices.model_dump(mode="json"))
    return SetupOut.from_record(rec)


@router.get("/{session_id}", response_model=SetupOut)
def get_session(session_id: str, conn: deps.PgConn, owner: deps.Owner) -> SetupOut:
    return SetupOut.from_record(get_setup(conn, session_id, owner_id=owner))


# --- tạo lựa chọn (gọi model) --------------------------------------------------------------------


def lock_setup(session_id: str, conn: deps.PgConn, owner: deps.Owner) -> Iterator[None]:
    """Một phiên chỉ một lần gọi model cùng lúc, cho tạo lựa chọn từng bước, chọn nhân vật (kiểm
    duyệt phần sửa) lẫn chốt (G8, D-46, D-56): lần thứ hai báo STORY_BUSY, không gọi model. Khoá
    nhả khi yêu cầu kết thúc (với `scope="function"`: khi hàm của route xong), kể cả khi lỗi.
    Kiểm chủ phiên trước khi giữ khoá (D-105), như `deps.lock_story`: phiên của người khác
    là 404 dù phiên đang bận, và người khác không giữ được khoá của phiên này."""
    get_setup(conn, session_id, owner_id=owner)
    with job_lock(conn, "setup", session_id):
        yield


def option_line(option: BaseModel) -> str:
    """Mọi chữ người chơi đọc của một lựa chọn khởi tạo, trên đúng một dòng (xuống dòng bên trong
    gộp thành khoảng trắng): kiểm duyệt chấm mỗi dòng là một lựa chọn (D-79, D-137)."""
    return " · ".join(" ".join(str(value).split()) for value in option.model_dump().values())


async def moderated_options[O: BaseModel](
    propose: Callable[[], Awaitable[list[O]]], *, llm: LLMClient, config: AppConfig,
    darkness_level: str | None, step: str,
) -> list[O]:
    """Tạo bộ lựa chọn của một bước (`propose`) rồi kiểm duyệt nó (G9, D-137): một lời gọi
    `moderate` nguồn `setup` cho cả bộ, mỗi lựa chọn một dòng, ở mức u tối của phiên (None = mức
    mặc định). Lựa chọn nào không được cho qua (chặn cứng, chặn, vượt trần) bị bỏ, không bao giờ
    trả về. Còn ít nhất `MIN_SETUP_OPTIONS` thì trả các lựa chọn còn lại, theo thứ tự cũ. Không thì
    tạo lại cả bước (bộ mới thay hẳn bộ cũ), tối đa `SETUP_REGENERATIONS` lần, rồi
    SETUP_OPTIONS_BLOCKED. `llm` là MeteredClient của bước (G8): lời gọi kiểm duyệt tính vào trần và
    bộ đếm lời gọi. Lỗi của lời gọi kiểm duyệt ném ra nguyên (fail closed). Log chỉ có bước, số
    lựa chọn và số lượt; loại và số dòng do `moderate` ghi, không ghi chữ."""
    tries = 1 + SETUP_REGENERATIONS
    for attempt in range(1, tries + 1):
        options = await propose()
        result = await moderate("\n".join(option_line(o) for o in options), source=Source.SETUP,
                                llm=llm, config=config, darkness_level=darkness_level)
        kept = [o for o, verdict in zip(options, result.line_verdicts, strict=True)
                if verdict is Verdict.ALLOW]
        if len(kept) >= MIN_SETUP_OPTIONS:
            if len(kept) < len(options):
                log.info("khởi tạo %s: bỏ %d/%d lựa chọn bị kiểm duyệt chặn", step,
                         len(options) - len(kept), len(options))
            return kept
        log.warning("khởi tạo %s: còn %d/%d lựa chọn sau kiểm duyệt (lượt %d/%d)", step,
                    len(kept), len(options), attempt, tries)
    raise WritoryError(
        ErrorCode.SETUP_OPTIONS_BLOCKED,
        detail=f"bước {step}: dưới {MIN_SETUP_OPTIONS} lựa chọn sau {tries} lượt tạo",
    )


async def _propose(step: SetupStep, session_id: str, conn, owner: str, config: AppConfig,
                   llm: deps.PlayerLLM) -> SetupOut:
    rec = get_setup(conn, session_id, owner_id=owner)
    if rec.options(step) is not None and rec.story_id is None:
        return SetupOut.from_record(rec)  # đã có: trả lại đúng bộ người chơi đã thấy
    prev = _PREVIOUS[step]
    if rec.story_id is not None or (prev is not None and rec.index(prev) is None):
        raise SetupStepError(f"phiên {rec.id}: chưa tạo được lựa chọn bước {step}")
    choices = StoryChoices.model_validate(rec.choices)
    client = llm.metered(setup_id=rec.id)
    if step == "settings":
        # Lời gọi model đầu tiên của phiên: tag tự gõ qua kiểm duyệt trước (G9, D-57).
        await ensure_input_allowed(_tags_text(choices.tags), llm=client, config=config)

    # Thử lại mạng nằm ở từng lời gọi model trong pipeline (`pipeline.setup._ask`, D-14, D-105).
    propose: Callable[[], Awaitable[list]]
    if step == "settings":
        propose = partial(propose_settings, choices, llm=client, config=config)
    else:
        setting = SettingOption.model_validate(rec.chosen("settings"))
        if step == "plots":
            propose = partial(propose_plots, choices, setting, llm=client, config=config)
        else:
            plot = PlotOption.model_validate(rec.chosen("plots"))
            propose = partial(propose_characters, choices, setting, plot, llm=client,
                              config=config)
    # Chỉ lựa chọn đã qua kiểm duyệt đầu ra được lưu và trả về (G9, D-137); lỗi thì không lưu gì.
    options = await moderated_options(propose, llm=client, config=config,
                                      darkness_level=choices.darkness_level, step=step)
    rec = save_setup_options(conn, rec.id, step, [o.model_dump() for o in options])
    return SetupOut.from_record(rec)


@router.post("/{session_id}/settings", response_model=SetupOut,
             dependencies=[Depends(lock_setup)])
async def propose_setting_options(session_id: str, conn: deps.PgConn, owner: deps.Owner,
                                  config: deps.Config, llm: deps.PlayerLLMs) -> SetupOut:
    """3 bối cảnh mở (design §4.1 bước 4)."""
    return await _propose("settings", session_id, conn, owner, config, llm)


@router.post("/{session_id}/plots", response_model=SetupOut,
             dependencies=[Depends(lock_setup)])
async def propose_plot_options(session_id: str, conn: deps.PgConn, owner: deps.Owner,
                               config: deps.Config, llm: deps.PlayerLLMs) -> SetupOut:
    """3 hướng cốt truyện cho bối cảnh đã chọn (bước 5)."""
    return await _propose("plots", session_id, conn, owner, config, llm)


@router.post("/{session_id}/characters", response_model=SetupOut,
             dependencies=[Depends(lock_setup)])
async def propose_character_options(session_id: str, conn: deps.PgConn, owner: deps.Owner,
                                    config: deps.Config, llm: deps.PlayerLLMs) -> SetupOut:
    """3 nhân vật chính cho bối cảnh và hướng đã chọn (bước 6)."""
    return await _propose("characters", session_id, conn, owner, config, llm)


# --- chọn theo số thứ tự ------------------------------------------------------------------------


def _choose(step: SetupStep, session_id: str, index: int, conn, owner: str,
            protagonist: dict | None = None) -> SetupOut:
    get_setup(conn, session_id, owner_id=owner)  # phiên của người khác: 404
    return SetupOut.from_record(
        choose_setup_option(conn, session_id, step, index, protagonist=protagonist))


@router.put("/{session_id}/settings", response_model=SetupOut)
def choose_setting(session_id: str, body: OptionChoiceIn, conn: deps.PgConn,
                   owner: deps.Owner) -> SetupOut:
    return _choose("settings", session_id, body.index, conn, owner)


@router.put("/{session_id}/plots", response_model=SetupOut)
def choose_plot(session_id: str, body: OptionChoiceIn, conn: deps.PgConn,
                owner: deps.Owner) -> SetupOut:
    return _choose("plots", session_id, body.index, conn, owner)


def _protagonist(option: dict, body: CharacterChoiceIn, limits: InputLimits) -> dict[str, str]:
    """Nhân vật chính = lựa chọn đã lưu, thay bằng phần người chơi sửa. Trường người chơi gửi lên
    bị kiểm độ dài theo config; trường nào rỗng sau khi bỏ khoảng trắng là lỗi."""
    pc: dict[str, str] = {}
    bad: list[str] = []
    for field, limit_name in _EDIT_LIMITS.items():
        edited = getattr(body, field)
        value = (edited if edited is not None else option[field]).strip()
        if not value or (edited is not None and len(value) > _limit(limits, limit_name)):
            bad.append(field)
        pc[field] = value
    if bad:
        raise WritoryError(ErrorCode.CHARACTER_EDIT_INVALID, detail=f"trường {bad}", fields=bad)
    return pc


# Gọi model kiểm duyệt nên giữ khoá của phiên (G8, G11). Phạm vi `function`: khoá nhả trước khi
# phản hồi đi, vì giao diện gửi lệnh chốt ngay sau phản hồi này.
@router.put("/{session_id}/characters", response_model=SetupOut,
            dependencies=[Depends(lock_setup, scope="function")])
async def choose_character(session_id: str, body: CharacterChoiceIn, conn: deps.PgConn,
                           owner: deps.Owner, config: deps.Config,
                           llm: deps.PlayerLLMs) -> SetupOut:
    rec = get_setup(conn, session_id, owner_id=owner)
    if rec.characters is None or rec.story_id is not None or body.index >= len(rec.characters):
        raise SetupStepError(f"phiên {rec.id}: chưa chọn được nhân vật")
    pc = _protagonist(rec.characters[body.index], body, config.limits.input)
    edited = _edited_text(body)
    if edited.strip():  # không sửa gì thì không có chữ người chơi để kiểm, cũng không cần key
        await ensure_input_allowed(edited, llm=llm.metered(setup_id=rec.id), config=config)
    return _choose("characters", session_id, body.index, conn, owner, protagonist=pc)


# --- chốt ---------------------------------------------------------------------------------------


def _parts(rec: SetupRecord) -> tuple[StoryChoices, SettingOption, PlotOption, CharacterOption]:
    return (StoryChoices.model_validate(rec.choices),
            SettingOption.model_validate(rec.chosen("settings")),
            PlotOption.model_validate(rec.chosen("plots")),
            CharacterOption.model_validate(rec.protagonist))


@router.post("/{session_id}/finalize", response_model=SetupOut,
             dependencies=[Depends(lock_setup)])
async def finalize(session_id: str, conn: deps.PgConn, driver: deps.Neo4jDriver,
                   owner: deps.Owner, config: deps.Config, llm: deps.PlayerLLMs) -> SetupOut:
    """Bản kế hoạch ẩn + chương 0 (`build_story`), rồi tạo truyện, tất cả hoặc không gì. Đã chốt
    rồi thì trả lại truyện cũ, không gọi model."""
    rec = get_setup(conn, session_id, owner_id=owner)
    if rec.story_id is not None:
        return SetupOut.from_record(rec)
    if rec.protagonist is None:
        raise SetupStepError(f"phiên {rec.id}: chưa chọn nhân vật")
    choices, setting, plot, pc = _parts(rec)
    story_id = _new_id("story")
    client = llm.metered(setup_id=rec.id)
    # Mỗi lời gọi model bên trong (lời gọi dựng, từng lượt sửa D-54) tự thử lại lỗi mạng
    # (`pipeline.setup._ask`, D-14). Không bọc cả `build_story` (D-105): lớp ngoài chỉ chạy lại
    # được từ đầu, tức gọi lại cả các lời gọi đã xong.
    built = await build_story(choices, setting, plot, pc, llm=client, config=config,
                              commit_id=f"{story_id}-ch0")
    darkness = choices.darkness_level or config.moderation.default_darkness_level
    start_story(conn, driver, story_id, owner_id=owner, length_level=choices.length_level,
                brief=story_brief(choices, setting, plot, pc, moderation=config.moderation),
                plan=built.plan, initial=built.package, darkness_level=darkness, style=choices.style)
    try:
        rec = finish_setup(conn, rec.id, story_id)
    except BaseException:
        # Hai yêu cầu chốt cùng lúc: yêu cầu sau không gắn được, gỡ truyện của nó.
        discard_story(conn, driver, story_id)
        raise
    return SetupOut.from_record(rec)
