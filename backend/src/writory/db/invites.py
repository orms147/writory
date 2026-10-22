"""Lệnh của chủ dự án để quản lý mã mời (D-89). Chạy trong `backend/`:

    uv run python -m writory.db.invites create --name "Tên bạn"   # in mã đúng một lần
    uv run python -m writory.db.invites list                       # không bao giờ in mã
    uv run python -m writory.db.invites revoke inv-...             # thu hồi, xoá các phiên

Đọc `POSTGRES_DSN` từ biến môi trường hoặc `.env` (`writory.config.Settings`). Không chạy
migration: chạy migration trước (docs/runbook.md, mục Migration Postgres).
"""

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

import psycopg

from writory.db.auth import create_invite, list_invites, revoke_invite


def _when(value: datetime | None) -> str:
    return "-" if value is None else value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _run(args: argparse.Namespace, conn: psycopg.Connection) -> int:
    now = datetime.now(UTC)
    if args.command == "create":
        record, code = create_invite(conn, args.name, now=now)
        print(f"Đã tạo mã mời {record.id} cho {record.name} (owner_id {record.owner_id}).")
        print("Mã mời (chỉ hiện lần này, gửi riêng cho người được mời):")
        print(f"  {code}")
        return 0
    if args.command == "list":
        rows = list_invites(conn)
        if not rows:
            print("Chưa có mã mời nào.")
        for r in rows:
            state = "đã thu hồi " + _when(r.revoked_at) if r.revoked_at else "còn dùng"
            print(f"{r.id}  {r.name}  owner_id={r.owner_id}  tạo {_when(r.created_at)}  "
                  f"đăng nhập gần nhất {_when(r.last_login_at)}  {state}")
        return 0
    if revoke_invite(conn, args.invite_id, now=now):
        print(f"Đã thu hồi {args.invite_id}; các phiên đăng nhập của mã này đã bị xoá.")
        return 0
    print(f"Không có mã mời {args.invite_id} còn dùng.", file=sys.stderr)
    return 1


def main(argv: Sequence[str] | None = None, *, conn: psycopg.Connection | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m writory.db.invites",
                                     description="Quản lý mã mời đăng nhập (D-89).")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create", help="tạo mã mời mới, in mã một lần")
    create.add_argument("--name", required=True, help="tên người được mời (hiện cho họ khi vào)")
    sub.add_parser("list", help="liệt kê mã mời, không in mã")
    revoke = sub.add_parser("revoke", help="thu hồi một mã mời")
    revoke.add_argument("invite_id")
    args = parser.parse_args(argv)
    if conn is not None:
        return _run(args, conn)
    from writory.config import Settings
    from writory.db.connection import connect

    with connect(Settings()) as own:
        return _run(args, own)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # chữ có dấu khi chuyển hướng ra file trên Windows
    sys.exit(main())
