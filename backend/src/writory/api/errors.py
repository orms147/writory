"""Lỗi trả người chơi qua API (G12, D-29).

- `WritoryError` → `player_payload()` với HTTP status lấy từ bảng duy nhất `HTTP_STATUS`.
- Exception khác → `INTERNAL_ERROR`, câu tiếng Việt cố định. Không traceback, không `str(e)` trong
  phản hồi; chi tiết chỉ vào log, đã qua redact (G7).
- Lỗi kiểm thân yêu cầu → `REQUEST_INVALID` kèm `fields` (đường dẫn trường sai), không bao giờ kèm
  giá trị đầu vào (D-45).
- `HTTPException` của Starlette/FastAPI (route không có, router người chơi chưa bật qua
  `deps.api_guard`, sai phương thức, thân không đọc được) → mã theo status (`_HTTP_CODES`), không
  chép `detail`. Bản mặc định trả `{"detail": ...}`: không mã, không câu tiếng Việt, và chép lại
  `detail` (G12).
"""

import logging
import re
import traceback
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.LLM_BAD_RESPONSE: 502,
    ErrorCode.PLAYER_KEY_MISSING: 400,
    ErrorCode.PLAYER_KEY_UNREADABLE: 400,
    # Ghi chương (D-6, db/chapters.py)
    ErrorCode.STORY_NOT_FOUND: 404,  # G10: truyện không có hoặc không thuộc người này
    ErrorCode.CHAPTER_SAVE_FAILED: 409,  # Neo4j từ chối gói; đã gỡ, truyện giữ nguyên
    ErrorCode.CHAPTER_PENDING: 409,
    ErrorCode.CHAPTER_OUT_OF_ORDER: 409,
    ErrorCode.CHAPTER_PACKAGE_INVALID: 500,  # gói do hệ thống tạo sai, không do người chơi
    ErrorCode.CHAPTER_QUOTE_NOT_IN_TEXT: 500,  # G3, D-106: câu trích của gói không có trong văn
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
    ErrorCode.STORY_LENGTH_NOT_OPEN: 422,  # D-88: mức độ dài chưa mở cho người chơi
    ErrorCode.CHOICES_LEAK_BLOCKED: 502,  # D-37: như SCENE_LEAK_BLOCKED
    ErrorCode.INPUT_BLOCKED: 422,  # G9, D-57: chữ người chơi bị kiểm duyệt chặn
    # Phiên khởi tạo (D-44)
    ErrorCode.SETUP_NOT_FOUND: 404,
    ErrorCode.SETUP_STEP_NOT_READY: 409,
    ErrorCode.PLAYER_KEY_INVALID: 422,
    ErrorCode.REQUEST_INVALID: 422,  # D-45: lỗi kiểm thân yêu cầu, không chép lại đầu vào
    ErrorCode.CHARACTER_EDIT_INVALID: 422,
    # Chơi (D-46)
    ErrorCode.CHOICE_NOT_FOUND: 404,
    ErrorCode.CHOICE_REQUIRED: 409,
    ErrorCode.CHAPTER_NOT_FOUND: 404,
    ErrorCode.STORY_COMPLETE: 409,
    # Đăng nhập bằng mã mời (D-89)
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.INVITE_CODE_INVALID: 401,
    ErrorCode.LOGIN_RATE_LIMITED: 429,
    ErrorCode.REQUEST_ORIGIN_INVALID: 403,  # CSRF: route ghi không phải JSON cùng origin
    ErrorCode.STORY_BUSY: 409,  # D-46: đang có một lần viết/chốt khác của cùng truyện, phiên
    # Lỗi của bộ định tuyến (`_http_error`)
    ErrorCode.ROUTE_NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
}

# Status của HTTPException → mã. Status khác: từ 500 là INTERNAL_ERROR, dưới 500 là REQUEST_INVALID.
_HTTP_CODES: dict[int, ErrorCode] = {404: ErrorCode.ROUTE_NOT_FOUND,
                                     405: ErrorCode.METHOD_NOT_ALLOWED}


async def _writory_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, WritoryError)
    log.warning("%s %s -> %s", request.method, request.url.path, exc)  # str() đã redact detail
    return JSONResponse(exc.player_payload(), status_code=HTTP_STATUS[exc.code])


async def _unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    details = redact("".join(traceback.format_exception(exc)))
    log.error("%s %s -> lỗi không lường trước:\n%s", request.method, request.url.path, details)
    err = WritoryError(ErrorCode.INTERNAL_ERROR)
    return JSONResponse(err.player_payload(), status_code=HTTP_STATUS[err.code])


# Một đoạn của đường dẫn trường được trả về nguyên văn chỉ khi có dạng định danh (tên trường của
# schema). Đoạn khác (tên trường lạ do người gửi đặt, có thể chính là key) thành "?". Regex ở đây
# chỉ kiểm định dạng.
_FIELD_PART = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,63}")
_LOC_SOURCES = frozenset({"body", "query", "path", "header", "cookie"})


def field_path(loc: Sequence[Any], error_type: str | None = None) -> str:
    """`("body", "tags", "genre")` → `"tags.genre"`. Không bao giờ chứa giá trị đầu vào (G7)."""
    if error_type == "json_invalid":  # loc là vị trí ký tự trong thân, không phải trường
        return "body"
    parts = list(loc[1:]) if len(loc) > 1 and loc[0] in _LOC_SOURCES else list(loc)
    out = []
    for part in parts:
        if isinstance(part, int) and not isinstance(part, bool):
            out.append(str(part))  # chỉ số trong danh sách
        elif isinstance(part, str) and _FIELD_PART.fullmatch(part):
            out.append(part)
        else:
            out.append("?")
    return ".".join(out) or (str(loc[0]) if loc and loc[0] in _LOC_SOURCES else "?")


async def _request_invalid(request: Request, exc: Exception) -> JSONResponse:
    """Lỗi kiểm thân yêu cầu (422). Bản mặc định của FastAPI trả `input` của từng lỗi, tức chép lại
    chữ người chơi gửi lên, kể cả key (G7). Ở đây log và phản hồi chỉ có đường dẫn trường (đã lọc
    như `field_path`) và loại lỗi; không `input`, không `ctx`."""
    assert isinstance(exc, RequestValidationError)
    errors = [(field_path(e.get("loc", ()), e.get("type")), e.get("type")) for e in exc.errors()]
    log.warning("%s %s -> %s (%s)", request.method, request.url.path,
                ErrorCode.REQUEST_INVALID.value, "; ".join(f"{f}: {t}" for f, t in errors))
    fields = list(dict.fromkeys(f for f, _ in errors))
    err = WritoryError(ErrorCode.REQUEST_INVALID, fields=fields)
    return JSONResponse(err.player_payload(), status_code=HTTP_STATUS[err.code])


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    """HTTPException của bộ định tuyến hay của FastAPI: mã theo status, câu tiếng Việt cố định.
    Giữ header (405 có `Allow`); `detail` không vào phản hồi hay log."""
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_CODES.get(exc.status_code) or (
        ErrorCode.INTERNAL_ERROR if exc.status_code >= 500 else ErrorCode.REQUEST_INVALID)
    log.info("%s %s -> %s (HTTP %d)", request.method, request.url.path, code.value,
             exc.status_code)
    err = WritoryError(code)
    return JSONResponse(err.player_payload(), status_code=HTTP_STATUS[code], headers=exc.headers)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(WritoryError, _writory_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _request_invalid)
    app.add_exception_handler(Exception, _unexpected_error)
