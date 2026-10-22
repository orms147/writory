"""Đăng nhập bằng mã mời (D-89): mã mời, phiên đăng nhập, bộ đếm lần nhập mã.

Mã mời và token phiên chỉ có dạng gốc trong bộ nhớ: lúc tạo (in ra một lần, đặt vào cookie) và
lúc người chơi gửi lên. Postgres chỉ giữ SHA-256. Không hàm nào ở đây ghi log; nơi gọi không được
đưa mã hay token vào log, lỗi hay phản hồi (bộ lọc log `safety.redact` vẫn xoá nếu lỡ có).

Mã mời: `wt-` + 32 ký tự base32 (160 bit), chia nhóm 4. 8 ký tự đầu là `selector` để tra hàng
(không bí mật), 24 ký tự sau (120 bit) là phần bí mật, so với băm đã lưu bằng `hmac.compare_digest`.
Mã có đủ entropy nên SHA-256 một lần là đủ, không cần hàm băm chậm. Token phiên: `wts_` +
`secrets.token_urlsafe(32)` (256 bit), tra thẳng theo băm của nó.
"""

import hashlib
import hmac
import secrets
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import psycopg

SESSION_COOKIE = "writory_session"
CODE_PREFIX = "wt"
TOKEN_PREFIX = "wts_"
_ALPHABET = "abcdefghijklmnopqrstuvwxyz234567"  # base32 thường, không có 0, 1, 8, 9
_SELECTOR_CHARS = 8
_SECRET_CHARS = 24
_CODE_CHARS = _SELECTOR_CHARS + _SECRET_CHARS
_MAX_TYPED_CHARS = 200
_DUMMY_HASH = hashlib.sha256(b"writory-no-such-invite").digest()


def _sha256(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()


def new_invite_code() -> str:
    raw = "".join(secrets.choice(_ALPHABET) for _ in range(_CODE_CHARS))
    return f"{CODE_PREFIX}-" + "-".join(raw[i:i + 4] for i in range(0, _CODE_CHARS, 4))


def parse_invite_code(typed: str) -> tuple[str, str] | None:
    """(selector, phần bí mật) của mã người chơi gõ hay dán; sai dạng thì None. Chấp nhận chữ hoa,
    khoảng trắng, thiếu dấu gạch hay thiếu tiền tố. Chỉ kiểm định dạng, không đọc ý định (G5)."""
    if len(typed) > _MAX_TYPED_CHARS:
        return None
    text = "".join(typed.split()).lower().replace("-", "")
    if text.startswith(CODE_PREFIX) and len(text) == _CODE_CHARS + len(CODE_PREFIX):
        text = text[len(CODE_PREFIX):]
    if len(text) != _CODE_CHARS or any(ch not in _ALPHABET for ch in text):
        return None
    return text[:_SELECTOR_CHARS], text[_SELECTOR_CHARS:]


def new_session_token() -> str:
    return TOKEN_PREFIX + secrets.token_urlsafe(32)


# --- mã mời ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class InviteRecord:
    """Một mã mời, không có mã (mã không lưu ở đâu)."""

    id: str
    owner_id: str
    name: str
    created_at: datetime
    revoked_at: datetime | None
    last_login_at: datetime | None


_INVITE_COLS = "id, owner_id, name, created_at, revoked_at, last_login_at"


def create_invite(conn: psycopg.Connection, name: str, *, now: datetime) -> tuple[InviteRecord, str]:
    """Tạo mã mời cho một người chơi mới (owner_id riêng). Trả mã gốc đúng một lần."""
    name = name.strip()
    if not name:
        raise ValueError("tên người được mời rỗng")
    code = new_invite_code()
    selector, secret = parse_invite_code(code)  # type: ignore[misc]  # mã vừa tạo luôn đúng dạng
    row = conn.execute(
        f"INSERT INTO invites (id, owner_id, name, selector, verifier_hash, created_at) "
        f"VALUES (%s, %s, %s, %s, %s, %s) RETURNING {_INVITE_COLS}",
        (f"inv-{uuid.uuid4().hex[:12]}", f"u-{uuid.uuid4().hex[:16]}", name, selector,
         _sha256(secret), now),
    ).fetchone()
    return InviteRecord(*row), code


def list_invites(conn: psycopg.Connection) -> list[InviteRecord]:
    rows = conn.execute(f"SELECT {_INVITE_COLS} FROM invites ORDER BY created_at, id").fetchall()
    return [InviteRecord(*r) for r in rows]


def revoke_invite(conn: psycopg.Connection, invite_id: str, *, now: datetime) -> bool:
    """Thu hồi mã và xoá mọi phiên của nó. False nếu không có mã đó hoặc đã thu hồi. Truyện, key,
    chi phí của người đó giữ nguyên (theo owner_id)."""
    with conn.transaction():
        done = conn.execute(
            "UPDATE invites SET revoked_at = %s WHERE id = %s AND revoked_at IS NULL",
            (now, invite_id)).rowcount == 1
        if done:
            conn.execute("DELETE FROM auth_sessions WHERE invite_id = %s", (invite_id,))
    return done


# --- phiên -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SessionInfo:
    owner_id: str
    name: str
    expires_at: datetime


@dataclass(frozen=True)
class LoginResult:
    token: str  # chỉ để đặt vào cookie
    session: SessionInfo


def login_with_code(conn: psycopg.Connection, typed: str, *, ttl: timedelta,
                    now: datetime) -> LoginResult | None:
    """Mã đúng và chưa thu hồi thì tạo phiên mới; không thì None (không nói sai ở đâu)."""
    parsed = parse_invite_code(typed)
    if parsed is None:
        return None
    selector, secret = parsed
    row = conn.execute(
        "SELECT id, owner_id, name, verifier_hash, revoked_at FROM invites WHERE selector = %s",
        (selector,)).fetchone()
    expected = bytes(row[3]) if row is not None else _DUMMY_HASH
    matches = hmac.compare_digest(_sha256(secret), expected)
    if row is None or not matches or row[4] is not None:
        return None
    invite_id, owner_id, name = row[0], row[1], row[2]
    token = new_session_token()
    expires = now + ttl
    with conn.transaction():
        conn.execute("DELETE FROM auth_sessions WHERE invite_id = %s AND expires_at <= %s",
                     (invite_id, now))
        conn.execute(
            "INSERT INTO auth_sessions (token_hash, invite_id, owner_id, created_at, expires_at) "
            "VALUES (%s, %s, %s, %s, %s)", (_sha256(token), invite_id, owner_id, now, expires))
        conn.execute("UPDATE invites SET last_login_at = %s WHERE id = %s", (now, invite_id))
    return LoginResult(token, SessionInfo(owner_id, name, expires))


def session_owner(conn: psycopg.Connection, token: str, *, now: datetime) -> SessionInfo | None:
    """Chủ của phiên còn hạn, của mã chưa thu hồi; không thì None."""
    if not token.startswith(TOKEN_PREFIX) or len(token) > _MAX_TYPED_CHARS:
        return None
    row = conn.execute(
        "SELECT s.owner_id, i.name, s.expires_at FROM auth_sessions s "
        "JOIN invites i ON i.id = s.invite_id "
        "WHERE s.token_hash = %s AND s.expires_at > %s AND i.revoked_at IS NULL",
        (_sha256(token), now)).fetchone()
    return None if row is None else SessionInfo(*row)


def end_session(conn: psycopg.Connection, token: str) -> None:
    conn.execute("DELETE FROM auth_sessions WHERE token_hash = %s", (_sha256(token),))


class PostgresSessionLookup:
    """Tra phiên cho `api.deps.get_owner_id`. Mở kết nối chỉ khi cần tra (chế độ `dev` không
    chạm Postgres); `open_conn` trả kết nối dùng chung thì không đóng (test)."""

    def __init__(self, open_conn: Callable[[], psycopg.Connection], *, close: bool = False) -> None:
        self._open = open_conn
        self._close = close

    def owner_of(self, token: str, *, now: datetime) -> SessionInfo | None:
        conn = self._open()
        try:
            return session_owner(conn, token, now=now)
        finally:
            if self._close:
                conn.close()


# --- giới hạn số lần nhập mã -------------------------------------------------------------------

_KEEP_WINDOWS = 4


def take_login_attempt(conn: psycopg.Connection, client: str, limit: int, *,
                       window_seconds: int, now: float) -> bool:
    """Giữ một lần nhập mã của máy `client` trong cửa sổ chứa `now`; False khi đã đủ `limit`. Cùng
    kiểu `db.rate_limit.take_llm_call` (D-56): một câu lệnh kiểm và tăng, yêu cầu đồng thời không
    vượt `limit`. Đếm mọi lần, đúng hay sai, nên thử mã hàng loạt không có lợi gì. Chỉ lưu băm."""
    key = hashlib.sha256(client.encode("utf-8")).hexdigest()
    window = int(now // window_seconds)
    row = conn.execute(
        "INSERT INTO login_attempt_windows (client, window_start, attempts) VALUES (%s, %s, 1) "
        "ON CONFLICT (client, window_start) DO UPDATE "
        "SET attempts = login_attempt_windows.attempts + 1 "
        "WHERE login_attempt_windows.attempts < %s RETURNING attempts",
        (key, window, limit)).fetchone()
    conn.execute("DELETE FROM login_attempt_windows WHERE window_start < %s",
                 (window - _KEEP_WINDOWS,))
    return row is not None
