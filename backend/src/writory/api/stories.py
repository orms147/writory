"""Router `stories`: tủ truyện, sổ tay và hỏi người kể (design §4.2, §6.6; D-40, D-41, D-66).

Truyện được kiểm theo chủ ("G10 ở API", docs/security.md): `deps.get_owned_story` so với người đang
dùng (`deps.get_owner_id`: người chơi dev ở chế độ `dev`, chủ của phiên đăng nhập bằng mã mời ở chế
độ `invite`, D-89); truyện của người khác → STORY_NOT_FOUND. `create_app` mount router này theo chế
độ (D-41, D-89), và mọi route còn kiểm lại lúc chạy (`deps.api_guard`), để gắn router vào app khác
cũng không mở được.
"""

from collections.abc import Mapping
from functools import partial
from typing import Annotated

from fastapi import APIRouter, Depends

from writory.api import deps
from writory.api.schemas import (
    ChapterEstimateOut,
    NarratorAnswerOut,
    NarratorQuestionIn,
    NarratorRemainingOut,
    NotebookOut,
    StoryListOut,
    StorySummaryOut,
)
from writory.config import AppConfig
from writory.db import owned_story_summaries
from writory.graph import PlayerView
from writory.llm.cost import MeteredClient, estimate_chapter_cost
from writory.pipeline.narrator import (
    NarratorCounter,
    ask_narrator,
    remaining_questions,
    source_chapters,
)
from writory.pipeline.story_plan import StoryPlan
from writory.safety.moderate import ensure_input_allowed

router = APIRouter(prefix="/stories", dependencies=[Depends(deps.api_guard)])
Counter = Annotated[NarratorCounter, Depends(deps.get_narrator_quota)]


async def _moderate_input(text: str, *, llm: MeteredClient, config: AppConfig) -> None:
    await ensure_input_allowed(text, llm=llm, config=config)


@router.get("", response_model=StoryListOut)
def list_stories(conn: deps.PgConn, owner: deps.Owner, config: deps.Config) -> StoryListOut:
    """Tủ truyện: truyện của người đang dùng, mới nhất trước (G10). Chỉ chữ người chơi đã thấy
    (G1): tên hướng truyện đã chọn, câu cuối của cảnh cuối đã hiện."""
    return StoryListOut(stories=[StorySummaryOut.from_record(r, config.story_lengths)
                                 for r in owned_story_summaries(conn, owner)])


@router.get("/{story_id}/notebook", response_model=NotebookOut)
def notebook(view: Annotated[PlayerView, Depends(deps.get_player_view)]) -> NotebookOut:
    """Sổ tay: chỉ lớp người chơi biết ở chương đã commit (G1, D-16)."""
    return NotebookOut.from_view(view)


@router.post("/{story_id}/narrator", response_model=NarratorAnswerOut,
             dependencies=[Depends(deps.lock_narrator)])
async def narrator(
    body: NarratorQuestionIn,
    view: Annotated[PlayerView, Depends(deps.get_player_view)],
    config: Annotated[AppConfig, Depends(deps.get_app_config)],
    llm: Annotated[MeteredClient, Depends(deps.get_narrator_llm)],
    plan: Annotated[StoryPlan, Depends(deps.get_story_plan)],
    truth_names: Annotated[Mapping[str, tuple[str, ...]], Depends(deps.get_truth_names)],
    brief: deps.StoryBrief,
    quota: Counter,
) -> NarratorAnswerOut:
    """Hỏi người kể: không mất lượt truyện; số câu mỗi chương có trần (G8). Câu hỏi qua kiểm duyệt
    (G9, D-57) sau khi kiểm độ dài, trước khi giữ lượt và trước model người kể.

    Trả thêm số câu còn lại của chương (bộ đếm `narrator_questions`, sau khi giữ lượt) và chương
    của các mục câu trả lời dẫn, tính từ `player_view` (D-65). Hết lượt: NARRATOR_LIMIT_REACHED
    như cũ."""
    result = await ask_narrator(
        body.question, view, llm=llm, config=config, truth_names=truth_names, plan=plan,
        story_brief=brief, quota=quota,
        moderate=partial(_moderate_input, llm=llm, config=config),
    )
    return NarratorAnswerOut(
        answer=result.answer,
        remaining=await remaining_questions(quota, view.story_id, view.chapter, config),
        source_chapters=source_chapters(view, result.refs),
    )


@router.get("/{story_id}/narrator", response_model=NarratorRemainingOut)
async def narrator_remaining(story: deps.OwnedStory, config: deps.Config,
                             quota: Counter) -> NarratorRemainingOut:
    """Số câu hỏi người kể còn lại ở chương đã commit, để hiện trước khi hỏi (D-65). Không cần key,
    không gọi model."""
    chapter = story.committed_chapter or 0
    return NarratorRemainingOut(
        remaining=await remaining_questions(quota, story.id, chapter, config))


@router.get("/{story_id}/estimate", response_model=ChapterEstimateOut)
def chapter_estimate(story: deps.OwnedStory, config: deps.Config,
                     ledger: Annotated[deps.CostLedger, Depends(deps.get_cost_ledger)]
                     ) -> ChapterEstimateOut:
    """Chương tới tốn khoảng bao nhiêu (design §10, D-87): trung vị chi phí thật các chương đã ghi
    của chính truyện; chưa có chương nào thì số mặc định trong config. Không gọi model, không cần
    key."""
    est = estimate_chapter_cost(ledger.chapter_costs(story.id),
                                default_usd=config.limits.chapter_estimate.default_usd)
    return ChapterEstimateOut(chapter=(story.committed_chapter or 0) + 1, usd=est.usd,
                              source=est.source, chapters_used=est.chapters_used)
