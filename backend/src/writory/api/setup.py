"""Router `setup`: khởi tạo truyện (design §4.1; D-38, D-39, D-45).

Máy chủ giữ 3 lựa chọn của mỗi bước (`setup_sessions`); trình duyệt chỉ gửi số thứ tự 0–2, cộng phần
sửa tên, tính cách, quá khứ của nhân vật chính. Thứ tự: tạo phiên → bối cảnh → hướng → nhân vật →
chốt. POST một bước = lấy lựa chọn đã có, hoặc tạo nếu chưa có (chỉ khi đó mới gọi model); PUT một
bước = chọn theo số thứ tự (đổi lựa chọn thì các bước sau bị xoá).

- G1: phản hồi là `SetupOut` (danh sách trắng): không bản kế hoạch, bí mật hay id lớp truth.
- G4: tag và phần sửa nhân vật là chữ người chơi; pipeline bọc chúng như dữ liệu.
- G11: phiên chỉ đổi sau khi thao tác thành công. Chốt truyện tất cả hoặc không gì (`start_story`).
- G9, D-57: tag tự gõ được kiểm duyệt ngay trước lần tạo bối cảnh đầu (lời gọi model đầu tiên của
  phiên), và phần người chơi sửa của nhân vật chính được kiểm duyệt trước khi lưu. Bị chặn thì
  không lưu và không gọi model nào khác.
- Gọi model bằng key người chơi (`deps.PlayerLLM`), ghi nhật ký theo phiên rồi gắn vào truyện (G8).
Chỉ mount khi bật cờ dev (D-41).
"""

import uuid
from collections.abc import Iterator

from fastapi import APIRouter, Depends

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
from writory.llm.retry import RETRY_TRANSIENT, with_retries
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
from writory.safety.moderate import ensure_input_allowed

router = APIRouter(prefix="/setup", dependencies=[Depends(deps.dev_routes_only)])

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
    tags = StoryTags(**body.tags.model_dump())
    naming = (Naming(**body.naming.model_dump()) if body.naming is not None
              else default_naming(tags.genre))
    choices = StoryChoices(tags=tags, length_level=body.length_level, naming=naming)
    rec = create_setup(conn, _new_id("setup"), owner_id=owner,
                       choices=choices.model_dump(mode="json"))
    return SetupOut.from_record(rec)


@router.get("/{session_id}", response_model=SetupOut)
def get_session(session_id: str, conn: deps.PgConn, owner: deps.Owner) -> SetupOut:
    return SetupOut.from_record(get_setup(conn, session_id, owner_id=owner))


# --- tạo lựa chọn (gọi model) --------------------------------------------------------------------


def lock_setup(session_id: str, conn: deps.PgConn) -> Iterator[None]:
    """Một phiên chỉ một lần gọi model cùng lúc, cho tạo lựa chọn từng bước lẫn chốt (G8, D-46,
    D-56): lần thứ hai báo STORY_BUSY, không gọi model. Khoá nhả khi yêu cầu kết thúc, kể cả khi
    lỗi."""
    with job_lock(conn, "setup", session_id):
        yield


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

    async def call():
        if step == "settings":
            return await propose_settings(choices, llm=client, config=config)
        setting = SettingOption.model_validate(rec.chosen("settings"))
        if step == "plots":
            return await propose_plots(choices, setting, llm=client, config=config)
        plot = PlotOption.model_validate(rec.chosen("plots"))
        return await propose_characters(choices, setting, plot, llm=client, config=config)

    options = await with_retries(call, max_retries=config.limits.retries.llm_transient,
                                 retry_on=RETRY_TRANSIENT)
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


@router.put("/{session_id}/characters", response_model=SetupOut)
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
    built = await with_retries(
        lambda: build_story(choices, setting, plot, pc, llm=client, config=config,
                            commit_id=f"{story_id}-ch0"),
        max_retries=config.limits.retries.llm_transient, retry_on=RETRY_TRANSIENT,
    )
    start_story(conn, driver, story_id, owner_id=owner, length_level=choices.length_level,
                brief=story_brief(choices, setting, plot, pc),
                plan=built.plan, initial=built.package)
    try:
        rec = finish_setup(conn, rec.id, story_id)
    except BaseException:
        # Hai yêu cầu chốt cùng lúc: yêu cầu sau không gắn được, gỡ truyện của nó.
        discard_story(conn, driver, story_id)
        raise
    return SetupOut.from_record(rec)
