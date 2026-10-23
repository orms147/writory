"""Router `auth`: đăng nhập bằng mã mời (D-89).

- `POST /auth/login` `{code}`: đếm lần nhập mã của máy (`config/limits.yaml` `auth`; sau proxy là
  địa chỉ proxy tin cậy báo, `deps.client_address`, D-103), rồi kiểm mã;
  đúng thì đặt cookie phiên `HttpOnly`, `SameSite=Lax`, `Secure` khi không phải localhost.
- `POST /auth/logout`: xoá phiên phía máy chủ và cookie.
- `GET /auth/session`: chế độ, đã đăng nhập chưa, tên người được mời. Không cần đăng nhập.
Chế độ `dev` không có đăng nhập: cả ba trả `mode: "dev"`, không đặt cookie.
Mã và token không vào log, lỗi hay phản hồi; thân phản hồi không có token (chỉ cookie).
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from writory.api import deps
from writory.config import AuthLimits, LimitNotSetError
from writory.db.auth import (
    SESSION_COOKIE,
    SessionInfo,
    end_session,
    login_with_code,
    take_login_attempt,
)
from writory.errors import ErrorCode, WritoryError

router = APIRouter(prefix="/auth", dependencies=[Depends(deps.api_guard)])

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(max_length=200)


class AuthSessionOut(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: Literal["dev", "invite"]
    logged_in: bool
    name: str | None  # tên chủ dự án đặt cho mã mời; chế độ dev thì None


def _out(request: Request, info: SessionInfo | None) -> AuthSessionOut:
    if request.app.state.settings.auth_mode != "invite":
        return AuthSessionOut(mode="dev", logged_in=True, name=None)
    return AuthSessionOut(mode="invite", logged_in=info is not None,
                          name=None if info is None else info.name)


def _limit(limits: AuthLimits, name: str) -> int:
    try:
        return limits.require(name)
    except LimitNotSetError as e:
        raise WritoryError(ErrorCode.CONFIG_LIMIT_NOT_SET, detail=str(e)) from None


def _secure(request: Request) -> bool:
    """`Secure` trừ khi trình duyệt mở bằng http trên localhost (máy dev, thử chồng prod). Theo
    `Host` mà proxy giữ nguyên, nên sau proxy https trên tên miền thật luôn `Secure`, kể cả khi
    header scheme bị giả; trên localhost thì theo scheme tin được (D-103)."""
    return (request.url.hostname or "") not in _LOCAL_HOSTS or deps.forwarded_https(request)


Session = Annotated[SessionInfo | None, Depends(deps.current_session)]
Clock = Annotated[deps.Clock, Depends(deps.get_clock)]


@router.post("/login", response_model=AuthSessionOut)
def login(body: LoginIn, request: Request, response: Response, conn: deps.PgConn,
          config: deps.Config, clock: Clock) -> AuthSessionOut:
    if request.app.state.settings.auth_mode != "invite":
        return _out(request, None)
    limits = config.limits.auth
    ttl_hours = _limit(limits, "session_ttl_hours")
    per_window = _limit(limits, "login_attempts_per_window")
    window = _limit(limits, "login_window_seconds")
    now = clock()
    # Sau proxy: chỉ tin header từ proxy tin cậy; IPv6 đếm theo /64 (D-103).
    client = deps.rate_limit_key(deps.client_address(request))
    if not take_login_attempt(conn, client, per_window, window_seconds=window, now=now):
        raise WritoryError(ErrorCode.LOGIN_RATE_LIMITED, detail="hết lượt nhập mã của máy này")
    result = login_with_code(conn, body.code, ttl=timedelta(hours=ttl_hours),
                             now=datetime.fromtimestamp(now, UTC))
    if result is None:
        raise WritoryError(ErrorCode.INVITE_CODE_INVALID, detail="mã sai, sai dạng hoặc đã thu hồi")
    response.set_cookie(SESSION_COOKIE, result.token, max_age=ttl_hours * 3600, path="/",
                        httponly=True, samesite="lax", secure=_secure(request))
    return _out(request, result.session)


@router.post("/logout", response_model=AuthSessionOut)
def logout(request: Request, response: Response, conn: deps.PgConn) -> AuthSessionOut:
    if request.app.state.settings.auth_mode != "invite":
        return _out(request, None)
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        end_session(conn, token)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax",
                           secure=_secure(request))
    return _out(request, None)


@router.get("/session", response_model=AuthSessionOut)
def session(request: Request, info: Session) -> AuthSessionOut:
    return _out(request, info)
