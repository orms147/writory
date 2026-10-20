"""Router `stories`: sổ tay và hỏi người kể (design §4.2, §6.6; D-40, D-41).

CHƯA kiểm truyện thuộc ai (G10): chưa có đăng nhập (tuần 5). Vì vậy `create_app` chỉ mount
router này khi `Settings.enable_dev_routes` bật (mặc định tắt), và mọi route ở đây còn kiểm lại
cờ đó lúc chạy, để gắn router vào app khác cũng không mở được.
TODO(G10, tuần 5): dependency kiểm quyền sở hữu truyện; truyện của người khác → STORY_NOT_FOUND.
"""

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from writory.api import deps
from writory.api.schemas import NarratorAnswerOut, NarratorQuestionIn, NotebookOut
from writory.config import AppConfig
from writory.graph import PlayerView
from writory.llm.cost import MeteredClient
from writory.pipeline.narrator import NarratorQuota, ask_narrator
from writory.pipeline.story_plan import StoryPlan


def _dev_routes_only(request: Request) -> None:
    """Fail closed: chỉ chạy khi create_app đã bật cờ dev cho chính app này."""
    if getattr(request.app.state, "dev_routes_enabled", False) is not True:
        raise HTTPException(status_code=404)


router = APIRouter(prefix="/stories", dependencies=[Depends(_dev_routes_only)])


@router.get("/{story_id}/notebook", response_model=NotebookOut)
def notebook(view: Annotated[PlayerView, Depends(deps.get_player_view)]) -> NotebookOut:
    """Sổ tay: chỉ lớp người chơi biết ở chương đã commit (G1, D-16)."""
    return NotebookOut.from_view(view)


@router.post("/{story_id}/narrator", response_model=NarratorAnswerOut)
async def narrator(
    body: NarratorQuestionIn,
    view: Annotated[PlayerView, Depends(deps.get_player_view)],
    config: Annotated[AppConfig, Depends(deps.get_app_config)],
    llm: Annotated[MeteredClient, Depends(deps.get_narrator_llm)],
    plan: Annotated[StoryPlan, Depends(deps.get_story_plan)],
    truth_names: Annotated[Mapping[str, tuple[str, ...]], Depends(deps.get_truth_names)],
    quota: Annotated[NarratorQuota, Depends(deps.get_narrator_quota)],
) -> NarratorAnswerOut:
    """Hỏi người kể: không mất lượt truyện; số câu mỗi chương có trần (G8)."""
    answer = await ask_narrator(
        body.question, view, llm=llm, config=config, truth_names=truth_names, plan=plan,
        quota=quota,
    )
    return NarratorAnswerOut(answer=answer)
