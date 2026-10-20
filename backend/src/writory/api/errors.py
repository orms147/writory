"""Lỗi trả người chơi qua API (G12, D-29).

- `WritoryError` → `player_payload()` với HTTP status lấy từ bảng duy nhất `HTTP_STATUS`.
- Exception khác → `INTERNAL_ERROR`, câu tiếng Việt cố định. Không traceback, không `str(e)` trong
  phản hồi; chi tiết chỉ vào log, đã qua redact (G7).
"""

import logging
import traceback

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from writory.errors import ErrorCode, WritoryError
from writory.safety.redact import redact

log = logging.getLogger(__name__)

# Mỗi mã lỗi đúng một status. Test bắt buộc đủ mọi mã: thêm mã mới thì thêm vào đây.
HTTP_STATUS: dict[ErrorCode, int] = {
    ErrorCode.CONFIG_LIMIT_NOT_SET: 503,
    ErrorCode.CONFIG_MODEL_NOT_SET: 503,
    ErrorCode.COST_LIMIT_SCENE: 402,
    ErrorCode.COST_LIMIT_CHAPTER: 402,
    ErrorCode.COST_LIMIT_STORY: 402,
    ErrorCode.LLM_COST_UNKNOWN: 502,
    ErrorCode.RETRY_LIMIT_REACHED: 503,
    ErrorCode.LLM_AUTH_FAILED: 400,  # key của người chơi bị OpenRouter từ chối: người chơi sửa được
    ErrorCode.LLM_INSUFFICIENT_CREDITS: 402,
    ErrorCode.LLM_RATE_LIMITED: 429,
    ErrorCode.LLM_CONTENT_BLOCKED: 422,
    ErrorCode.LLM_REQUEST_INVALID: 502,
    ErrorCode.LLM_UNAVAILABLE: 503,
    ErrorCode.LLM_BAD_RESPONSE: 502,
    ErrorCode.PLAYER_KEY_MISSING: 400,
    ErrorCode.PLAYER_KEY_UNREADABLE: 400,
    # Ghi chương (D-6, db/chapters.py)
    ErrorCode.STORY_NOT_FOUND: 404,  # G10: truyện không có hoặc không thuộc người này
    ErrorCode.CHAPTER_SAVE_FAILED: 409,  # Neo4j từ chối gói; đã gỡ, truyện giữ nguyên
    ErrorCode.CHAPTER_PENDING: 409,
    ErrorCode.CHAPTER_OUT_OF_ORDER: 409,
    ErrorCode.CHAPTER_PACKAGE_INVALID: 500,  # gói do hệ thống tạo sai, không do người chơi
    # Ô tự viết hành động (G5, D-27): chữ người chơi không xử lý được
    ErrorCode.ACTION_EMPTY: 422,
    ErrorCode.ACTION_TOO_LONG: 422,
    ErrorCode.ACTION_OUT_OF_STORY: 422,
    ErrorCode.ACTION_FORBIDDEN: 422,
    ErrorCode.ACTION_UNCLEAR: 422,
    ErrorCode.INTERNAL_ERROR: 500,
    # Dò lộ bí mật (G2, D-26): bản viết của model không dùng được, giống LLM_BAD_RESPONSE.
    # Status chung, không gợi rằng có bí mật.
    ErrorCode.SCENE_LEAK_BLOCKED: 502,
    # Hỏi người kể (D-40)
    ErrorCode.NARRATOR_QUESTION_EMPTY: 422,
    ErrorCode.NARRATOR_QUESTION_TOO_LONG: 422,
    ErrorCode.NARRATOR_LIMIT_REACHED: 429,
    ErrorCode.WRITORY_RATE_LIMITED: 429,  # G8: giới hạn mỗi phút của WriTory, chưa có bộ đếm
    # Khởi tạo truyện (D-39): kết quả của model không dùng được, giống LLM_BAD_RESPONSE.
    ErrorCode.STORY_SETUP_INVALID: 502,
    ErrorCode.CHOICES_LEAK_BLOCKED: 502,  # D-37: như SCENE_LEAK_BLOCKED
    # Phiên khởi tạo (D-44)
    ErrorCode.SETUP_NOT_FOUND: 404,
    ErrorCode.SETUP_STEP_NOT_READY: 409,
    ErrorCode.PLAYER_KEY_INVALID: 422,
    ErrorCode.REQUEST_INVALID: 422,  # D-45: lỗi kiểm thân yêu cầu, không chép lại đầu vào
}


async def _writory_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, WritoryError)
    log.warning("%s %s -> %s", request.method, request.url.path, exc)  # str() đã redact detail
    return JSONResponse(exc.player_payload(), status_code=HTTP_STATUS[exc.code])


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    details = redact("".join(traceback.format_exception(exc)))
    log.error("%s %s -> lỗi không lường trước:\n%s", request.method, request.url.path, details)
    err = WritoryError(ErrorCode.INTERNAL_ERROR)
    return JSONResponse(err.player_payload(), status_code=HTTP_STATUS[err.code])


async def _request_invalid(request: Request, exc: Exception) -> JSONResponse:
    """Lỗi kiểm thân yêu cầu (422). Bản mặc định của FastAPI trả `input` của từng lỗi, tức chép lại
    chữ người chơi gửi lên, kể cả key (G7). Ở đây log và phản hồi chỉ có vị trí và loại lỗi."""
    assert isinstance(exc, RequestValidationError)
    where = "; ".join(f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('type')}"
                      for e in exc.errors())
    log.warning("%s %s -> %s (%s)", request.method, request.url.path,
                ErrorCode.REQUEST_INVALID.value, where)
    err = WritoryError(ErrorCode.REQUEST_INVALID)
    return JSONResponse(err.player_payload(), status_code=HTTP_STATUS[err.code])


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(WritoryError, _writory_error)
    app.add_exception_handler(RequestValidationError, _request_invalid)
    app.add_exception_handler(Exception, _unexpected_error)
