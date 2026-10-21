"""Router `config`: các con số giao diện cần, lấy từ config/ để giao diện không tự đặt số (D-66).

Chỉ có giới hạn người chơi thấy được (ký tự, số câu hỏi, trần chi phí, độ dài, nhãn mức viết, các mức
u tối). Không model id, giá, trần nội bộ của mức u tối hay ngưỡng nội bộ (`PublicConfigOut`, G1).
Chỉ mount khi bật cờ dev (D-41), như các router khác của giao diện.
"""

from fastapi import APIRouter, Depends

from writory.api import deps
from writory.api.schemas import PublicConfigOut
from writory.pipeline.chapter import writer_tier

router = APIRouter(prefix="/config", dependencies=[Depends(deps.dev_routes_only)])


@router.get("/public", response_model=PublicConfigOut)
def public_config(config: deps.Config) -> PublicConfigOut:
    # Mức viết của đường chơi là mức đầu (ChapterRequest.writer_tier = None; D-33).
    return PublicConfigOut.from_config(config, writer_label=writer_tier(config, None).label)
