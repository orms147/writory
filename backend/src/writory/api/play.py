"""Router chơi: viết chương qua SSE, lựa chọn, hành động tự viết, đọc lại truyện (design §4.2,
§6.2–6.4; D-36, D-37, D-46).

- `POST /stories/{id}/chapters/next` (SSE, `text/event-stream`): chạy `ChapterRun` và phát
  `pipeline.events` (sự kiện `stage`, `scene_ready`, `scene_blocked`, `chapter_committed`,
  `choices_ready`, `story_finished`, `error`). Mọi điều kiện kiểm được trước khi viết (truyện,
  chương dở, hành động dẫn tới chương, key, trần) nằm trong dependency, nên lỗi đó là JSON thường
  có status (G12).
- Chương cuối của bản kế hoạch (D-50): pipeline phát `story_finished` thay cho `choices_ready`.
  Truyện đã kết thì `POST .../choices` trả bộ rỗng, không gọi model; chọn lựa chọn hay gửi hành động
  tự viết báo STORY_COMPLETE.
- G1: sự kiện là schema người chơi của `pipeline.events`; lựa chọn có cấu trúc (id nút, lời nói
  dối) chỉ lưu ở `chapter_choices`. `choices_ready` chỉ phát sau khi bộ lựa chọn đã lưu, để id mờ
  người chơi bấm luôn có ở máy chủ.
- G11, D-6: pipeline không ghi gì trước bước ghi chương. Người chơi ngắt kết nối thì FastAPI huỷ
  task đang chạy chương: trước bước ghi thì không có gì được ghi; bước ghi (`commit_chapter`)
  chạy đồng bộ nên không bị cắt giữa chừng. Chương đã ghi mà chưa kịp có lựa chọn: tạo lại bằng
  `POST /stories/{id}/choices`.
- G8: một truyện chỉ một lần viết chương cùng lúc (`db.job_lock` trong `get_chapter_job`); lần
  thứ hai báo STORY_BUSY, không gọi model.
- G5: chữ tự viết qua `classify_action` + `ensure_in_story` trước khi lưu làm hành động.
- Chọn lựa chọn lưu hành động cho chương sau; khi viết chương đó, lời nói dối (`Lie`, `TOLD`, `TOLD_TO`,
  `ABOUT`) và nội tâm (`FEELS`) của lựa chọn được ghi vào gói của chính chương đó (D-55).
Chỉ mount khi bật cờ dev (D-41).
"""

import logging
import traceback
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from writory.api import deps
from writory.api.schemas import (
    ActionOut,
    ChapterOut,
    ChoiceIn,
    ChoicesOut,
    CustomActionIn,
    StoryOut,
)
from writory.db import (
    ActionRecord,
    chapter_records,
    chapter_scenes,
    job_lock,
    load_action,
    load_choice,
    load_choices,
    load_story_brief,
    save_action,
    save_choices,
)
from writory.errors import ErrorCode, WritoryError
from writory.graph import player_view, protagonist_id
from writory.guard.state import Neo4jState
from writory.llm.base import require_model, role_extra
from writory.llm.retry import RETRY_TRANSIENT, with_retries
from writory.pipeline.chapter import ChapterRequest, ChapterRun
from writory.pipeline.choices import Choice, LieEffect, make_choices
from writory.pipeline.events import (
    KIND_LABELS,
    TONE_LABELS,
    ChapterEvent,
    ChoicesReady,
    PlayerChoice,
    error_event,
)
from writory.pipeline.store import GraphStore
from writory.pipeline.story_plan import StoryPlan
from writory.safety.classify import classify_action, ensure_in_story
from writory.safety.leak import leak_names
from writory.safety.redact import redact

log = logging.getLogger(__name__)

router = APIRouter(prefix="/stories", dependencies=[Depends(deps.dev_routes_only)])
Plan = Annotated[StoryPlan, Depends(deps.get_story_plan)]


# --- lựa chọn phía máy chủ --------------------------------------------------------------------


def choice_record(c: Choice) -> dict[str, Any]:
    """`Choice` → dict lưu được thành jsonb (`chapter_choices.choice`). Chỉ phía máy chủ."""
    return {
        "id": c.id, "kind": c.kind, "tone": c.tone, "text": c.text,
        "listeners": list(c.listeners), "about": list(c.about),
        "lie": None if c.lie is None else {"content": c.lie.content,
                                            "told_to": list(c.lie.told_to)},
        "feeling": c.feeling,
    }


def choice_from_record(d: dict[str, Any]) -> Choice:
    lie = d["lie"]
    return Choice(
        id=d["id"], kind=d["kind"], tone=d["tone"], text=d["text"],
        listeners=tuple(d["listeners"]), about=tuple(d["about"]),
        lie=None if lie is None else LieEffect(lie["content"], tuple(lie["told_to"])),
        feeling=d["feeling"],
    )


def _for_player(records: list[dict[str, Any]]) -> list[PlayerChoice]:
    return [choice_from_record(r).for_player() for r in records]


def action_text(c: Choice) -> str:
    """Chữ hành động đưa vào đề chương sau (`ChapterRequest.player_action`, luôn bọc như dữ liệu).
    Mang kèm dữ liệu có cấu trúc dạng chữ (lời nói dối, cảm xúc thầm), không có id nút."""
    label = KIND_LABELS[c.kind] + (f", {TONE_LABELS[c.tone]}" if c.tone else "")
    parts = [f"[{label}] {c.text}"]
    if c.lie is not None:
        parts.append(f"Lời nói dối: {c.lie.content}")
    if c.feeling:
        parts.append(f"Cảm xúc thầm: {c.feeling}")
    return "\n".join(parts)


def _action_out(conn, story_id: str, rec: ActionRecord | None) -> ActionOut | None:
    if rec is None:
        return None
    text = rec.text
    if rec.source == "choice":
        choice = load_choice(conn, story_id, rec.for_chapter - 1, rec.choice_id)
        text = choice["text"] if choice is not None else ""
    return ActionOut(for_chapter=rec.for_chapter, source=rec.source, text=text)


def _picked_choice(conn, story_id: str, chapter: int, action: ActionRecord | None) -> Choice | None:
    """Lựa chọn người chơi đã chọn ở cuối `chapter`, để tác động của nó vào gói chương sau (D-55).
    Ô tự viết không có dữ liệu có cấu trúc. Khoá ngoại bảo đảm lựa chọn còn đó; không còn là dữ
    liệu hỏng, nên dừng (fail closed) thay vì viết chương mà bỏ qua lựa chọn."""
    if action is None or action.source != "choice":
        return None
    record = load_choice(conn, story_id, chapter, action.choice_id)
    if record is None:
        raise RuntimeError(f"truyện {story_id}: hành động trỏ tới lựa chọn {action.choice_id} "
                           f"không có ở chương {chapter}")
    return choice_from_record(record)


def _has_pending(conn, story_id: str) -> bool:
    return any(r.status == "pending" for r in chapter_records(conn, story_id))


def _committed(story) -> int:
    if story.committed_chapter is None:  # truyện tạo qua /setup luôn có chương 0
        raise RuntimeError(f"truyện {story.id} chưa có chương 0")
    return story.committed_chapter


# --- viết chương (SSE) --------------------------------------------------------------------------


def sse_event(event: ChapterEvent) -> ServerSentEvent:
    """Một sự kiện SSE: `event:` là loại sự kiện, `data:` là JSON của schema người chơi."""
    return ServerSentEvent(data=event, event=event.type)


@dataclass
class ChapterJob:
    story_id: str
    chapter: int
    run: ChapterRun


def get_chapter_job(story: deps.OwnedStory, conn: deps.PgConn, driver: deps.Neo4jDriver,
                    config: deps.Config, plan: Plan, llm: deps.PlayerLLMs) -> Iterator[ChapterJob]:
    """Mọi điều kiện kiểm được trước khi viết, để lỗi là JSON có status thay vì sự kiện SSE.

    Giữ khoá của truyện (`db.job_lock`) từ trước các phép kiểm tới khi yêu cầu kết thúc: stream
    xong, lỗi, hay người chơi ngắt kết nối (FastAPI thoát dependency có `yield` sau khi stream
    dừng). Lần viết thứ hai cùng lúc báo STORY_BUSY, không gọi model (G8, D-46)."""
    committed = _committed(story)
    with job_lock(conn, "story", story.id):
        if _has_pending(conn, story.id):
            raise WritoryError(ErrorCode.CHAPTER_PENDING, detail=f"truyện {story.id}")
        chapter = committed + 1
        if chapter > plan.total_chapters:
            raise WritoryError(ErrorCode.STORY_COMPLETE, detail=f"truyện {story.id}: {committed}")
        action = load_action(conn, story.id, chapter)
        if action is None and committed >= 1:
            raise WritoryError(ErrorCode.CHOICE_REQUIRED, detail=f"truyện {story.id}, ch{chapter}")
        brief = load_story_brief(conn, story.id)
        if brief is None:
            raise RuntimeError(f"truyện {story.id} không có thiết lập truyện")  # fail closed
        client, tracker = llm.open(story_id=story.id, chapter=chapter)
        tracker.ensure_budget()  # trần chưa đặt hoặc đã chạm: báo trước khi mở stream
        request = ChapterRequest(
            present_ids=(), scene_count=config.story_lengths.scenes_per_chapter.min,
            story_brief=brief, player_action=None if action is None else action.text,
            choice=_picked_choice(conn, story.id, committed, action),
        )
        run = ChapterRun(request, llm=client, store=GraphStore(conn, driver, story.id),
                         config=config, plan=plan, tracker=tracker)
        yield ChapterJob(story.id, chapter, run)


@router.post("/{story_id}/chapters/next", response_class=EventSourceResponse)
async def write_next_chapter(
    job: Annotated[ChapterJob, Depends(get_chapter_job)], conn: deps.PgConn,
) -> AsyncIterator[ServerSentEvent]:
    held: ChoicesReady | None = None
    async for event in job.run.events():
        if isinstance(event, ChoicesReady):
            held = event  # chỉ phát sau khi đã lưu phía máy chủ
            continue
        yield sse_event(event)
    if held is None:
        return
    try:
        saved = save_choices(conn, job.story_id, job.chapter,
                             [choice_record(c) for c in job.run.outcome.choices])
    except Exception:  # noqa: BLE001 — chương đã ghi; lựa chọn tạo lại được
        log.error("lưu lựa chọn chương %s của %s lỗi:\n%s", job.chapter, job.story_id,
                  redact(traceback.format_exc()))
        yield sse_event(error_event(WritoryError(ErrorCode.INTERNAL_ERROR)))
        return
    yield sse_event(ChoicesReady(chapter=job.chapter, choices=_for_player(saved)))


# --- đọc lại truyện -----------------------------------------------------------------------------


@router.get("/{story_id}", response_model=StoryOut)
def story_state(story: deps.OwnedStory, conn: deps.PgConn, plan: Plan) -> StoryOut:
    """Trạng thái để mở lại truyện: chương đã ghi, lựa chọn đang chờ, hành động đã chọn."""
    chapter = _committed(story)
    pending = _has_pending(conn, story.id)
    choices = _for_player(load_choices(conn, story.id, chapter)) if chapter >= 1 else []
    action = _action_out(conn, story.id, load_action(conn, story.id, chapter + 1))
    finished = chapter >= plan.total_chapters
    return StoryOut(
        story_id=story.id, length_level=story.length_level, chapter=chapter, pending=pending,
        choices=choices, action=action, finished=finished,
        next_ready=not finished and not pending and (chapter == 0 or action is not None),
    )


@router.get("/{story_id}/chapters/{number}", response_model=ChapterOut)
def chapter_text(number: int, story: deps.OwnedStory, conn: deps.PgConn) -> ChapterOut:
    """Văn một chương đã ghi (chương 0 không có trang)."""
    scenes = chapter_scenes(conn, story.id, number) if number >= 1 else None
    if not scenes:
        raise WritoryError(ErrorCode.CHAPTER_NOT_FOUND, detail=f"{story.id} ch{number}")
    return ChapterOut(number=number, scenes=scenes)


# --- lựa chọn và hành động ----------------------------------------------------------------------


@router.post("/{story_id}/choices", response_model=ChoicesOut,
             dependencies=[Depends(deps.lock_story)])
async def chapter_choices(story: deps.OwnedStory, conn: deps.PgConn, driver: deps.Neo4jDriver,
                          config: deps.Config, plan: Plan, llm: deps.PlayerLLMs,
                          brief: deps.StoryBrief) -> ChoicesOut:
    """Bộ lựa chọn của chương hiện tại; chưa có (bị chặn vì lộ, hoặc mất kết nối sau khi chương
    đã ghi) thì tạo lại từ player_view (G1, D-37). Đã có thì trả lại, không gọi model."""
    chapter = _committed(story)
    if chapter == 0 or chapter >= plan.total_chapters:  # chương cuối không có lựa chọn (D-50)
        return ChoicesOut(chapter=chapter, choices=[])
    existing = load_choices(conn, story.id, chapter)
    if existing:
        return ChoicesOut(chapter=chapter, choices=_for_player(existing))
    scenes = chapter_scenes(conn, story.id, chapter)
    if not scenes:
        raise RuntimeError(f"truyện {story.id}: chương {chapter} không có văn")
    choices = await make_choices(
        llm.metered(story_id=story.id, chapter=chapter),
        require_model(config.models.roles, "choices"),
        view=player_view(driver, story.id, chapter), protagonist_id=protagonist_id(driver, story.id),
        last_scene_text=scenes[-1],
        truth_names=leak_names(Neo4jState(driver, story.id)),  # D-48: một quy tắc cho mọi nơi
        plan=plan, story_brief=brief,  # D-52: chữ khởi tạo người chơi đã đọc
        retries=config.limits.retries, extra=role_extra(config.models, "choices"),
    )
    saved = save_choices(conn, story.id, chapter, [choice_record(c) for c in choices])
    return ChoicesOut(chapter=chapter, choices=_for_player(saved))


def _not_finished(story, plan: StoryPlan) -> int:
    """Chương đã ghi cuối; truyện đã tới chương cuối của kế hoạch thì báo STORY_COMPLETE (D-50)."""
    chapter = _committed(story)
    if chapter >= plan.total_chapters:
        raise WritoryError(ErrorCode.STORY_COMPLETE, detail=f"truyện {story.id}: {chapter}")
    return chapter


@router.post("/{story_id}/choice", response_model=ActionOut)
def pick_choice(body: ChoiceIn, story: deps.OwnedStory, conn: deps.PgConn,
                plan: Plan) -> ActionOut:
    """Chọn một lựa chọn của chương hiện tại bằng id mờ. Chọn lại được tới khi viết chương sau."""
    chapter = _not_finished(story, plan)
    record = load_choice(conn, story.id, chapter, body.choice_id) if chapter >= 1 else None
    if record is None:
        raise WritoryError(ErrorCode.CHOICE_NOT_FOUND, detail=f"{story.id} ch{chapter}")
    choice = choice_from_record(record)
    save_action(conn, story.id, chapter + 1, source="choice", text=action_text(choice),
                choice_id=choice.id)
    return ActionOut(for_chapter=chapter + 1, source="choice", text=choice.text)


@router.post("/{story_id}/action", response_model=ActionOut,
             dependencies=[Depends(deps.lock_story)])
async def custom_action(body: CustomActionIn, story: deps.OwnedStory, conn: deps.PgConn,
                        config: deps.Config, plan: Plan, llm: deps.PlayerLLMs) -> ActionOut:
    """Ô tự viết: phân loại bằng model có đầu ra enum (G5) trước khi lưu. Bị chặn thì không lưu.
    Truyện đã kết thì báo trước khi gọi model (G8)."""
    chapter = _not_finished(story, plan) + 1
    client = llm.metered(story_id=story.id, chapter=chapter)
    result = await with_retries(lambda: classify_action(body.text, llm=client, config=config),
                                max_retries=config.limits.retries.llm_transient,
                                retry_on=RETRY_TRANSIENT)
    ensure_in_story(result)
    text = body.text.strip()
    save_action(conn, story.id, chapter, source="custom", text=text)
    return ActionOut(for_chapter=chapter, source="custom", text=text)
