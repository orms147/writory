"""Router `config`: các con số giao diện cần, lấy từ config/ để giao diện không tự đặt số (D-66).

Chỉ có giới hạn người chơi thấy được (ký tự, số câu hỏi, trần chi phí, độ dài, nhãn mức viết, các mức
u tối). Không model id, giá, trần nội bộ của mức u tối hay ngưỡng nội bộ (`PublicConfigOut`, G1).
Mount theo chế độ đăng nhập (`deps.api_guard`, D-41, D-89). Không cần đăng nhập:
màn đăng nhập cũng cần các số này.
"""

from fastapi import APIRouter, Depends

from writory.api import deps
from writory.api.schemas import PublicConfigOut
from writory.pipeline.chapter import writer_tier

router = APIRouter(prefix="/config", dependencies=[Depends(deps.api_guard)])


@router.get("/public", response_model=PublicConfigOut)
def public_config(config: deps.Config) -> PublicConfigOut:
    # Mức viết của đường chơi là mức đầu (ChapterRequest.writer_tier = None; D-33).
    return PublicConfigOut.from_config(config, writer_label=writer_tier(config, None).label)
