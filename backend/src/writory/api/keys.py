"""Router `player`: key OpenRouter của người chơi (design §10, G7, D-45).

Thêm và thay bằng PUT, xoá bằng DELETE, xem bằng GET. Phản hồi chỉ có 4 ký tự cuối. Key gốc chỉ
sống trong yêu cầu PUT (để mã hoá) và trong client model (để gọi); không vào log, lỗi hay phản hồi.
Chỉ mount khi bật cờ dev (D-41): chưa có đăng nhập, mọi người là người chơi dev (TODO G10, tuần 5).
"""

from fastapi import APIRouter, Depends

from writory.api import deps
from writory.api.schemas import PlayerKeyIn, PlayerKeyOut
from writory.errors import WritoryError
from writory.safety.crypto import key_last4, validate_player_key

router = APIRouter(prefix="/player", dependencies=[Depends(deps.dev_routes_only)])


@router.get("/key", response_model=PlayerKeyOut)
def key_status(keys: deps.Keys, cipher: deps.Cipher) -> PlayerKeyOut:
    token = keys.load()
    if token is None:
        return PlayerKeyOut(has_key=False, last4=None)
    return PlayerKeyOut(has_key=True, last4=key_last4(cipher.decrypt(token)))


@router.put("/key", response_model=PlayerKeyOut)
def put_key(body: PlayerKeyIn, keys: deps.Keys, cipher: deps.Cipher) -> PlayerKeyOut:
    """Thêm hoặc thay key. Chưa gọi OpenRouter để thử key: key sai báo LLM_AUTH_FAILED ở lời gọi đầu."""
    try:
        api_key = validate_player_key(body.api_key)
    except WritoryError as e:  # nói trường nào sai (G12); chi tiết vẫn không có key (G7)
        raise WritoryError(e.code, e.detail, fields=["api_key"]) from None
    keys.save(cipher.encrypt(api_key))
    return PlayerKeyOut(has_key=True, last4=key_last4(api_key))


@router.delete("/key", response_model=PlayerKeyOut)
def delete_key(keys: deps.Keys) -> PlayerKeyOut:
    keys.delete()
    return PlayerKeyOut(has_key=False, last4=None)
