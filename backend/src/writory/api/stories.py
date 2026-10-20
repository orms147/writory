"""Router `stories`: sổ tay và hỏi người kể (design §4.2, §6.6; D-40, D-41).

Truyện được kiểm theo chủ (`deps.get_owned_story`: truyện của người khác → STORY_NOT_FOUND), nhưng
CHƯA có đăng nhập (tuần 5): mọi người là người chơi dev, nên G10 chưa thật sự được thi hành. Vì vậy
`create_app` chỉ mount router này khi `Settings.enable_dev_routes` bật (mặc định tắt), và mọi route
ở đây còn kiểm lại cờ đó lúc chạy, để gắn router vào app khác cũng không mở được.
TODO(G10, tuần 5): `deps.get_owner_id` lấy người đang đăng nhập.
"""

from collections.abc import Mapping
from typing import Annotated

from fastapi import APIRouter, Depends

from writory.api import deps
from writory.api.schemas import NarratorAnswerOut, NarratorQuestionIn, NotebookOut
from writory.config import AppConfig
from writory.graph import PlayerView
from writory.llm.cost import MeteredClient
from writory.pipeline.narrator import NarratorQuota, ask_narrator
from writory.pipeline.story_plan import StoryPlan

router = APIRouter(prefix="/stories", dependencies=[Depends(deps.dev_routes_only)])


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
    brief: deps.StoryBrief,
    quota: Annotated[NarratorQuota, Depends(deps.get_narrator_quota)],
) -> NarratorAnswerOut:
    """Hỏi người kể: không mất lượt truyện; số câu mỗi chương có trần (G8)."""
    answer = await ask_narrator(
        body.question, view, llm=llm, config=config, truth_names=truth_names, plan=plan,
        story_brief=brief, quota=quota,
    )
    return NarratorAnswerOut(answer=answer)
