"""Key OpenRouter của người chơi trong Postgres (G7, D-11, D-44): chỉ lưu và trả bản mã hoá.

Mã hoá và giải mã nằm ở `safety.crypto.KeyCipher`; module này không bao giờ thấy key gốc.
"""

import psycopg


def save_player_key(conn: psycopg.Connection, owner_id: str, ciphertext: bytes) -> None:
    """Thêm hoặc thay key của người chơi."""
    conn.execute(
        "INSERT INTO player_keys (owner_id, ciphertext) VALUES (%s, %s) "
        "ON CONFLICT (owner_id) DO UPDATE SET ciphertext = EXCLUDED.ciphertext, updated_at = now()",
        (owner_id, ciphertext),
    )


def load_player_key(conn: psycopg.Connection, owner_id: str) -> bytes | None:
    row = conn.execute(
        "SELECT ciphertext FROM player_keys WHERE owner_id = %s", (owner_id,)
    ).fetchone()
    return None if row is None else bytes(row[0])


def delete_player_key(conn: psycopg.Connection, owner_id: str) -> bool:
    """True nếu có key để xoá."""
    return conn.execute(
        "DELETE FROM player_keys WHERE owner_id = %s", (owner_id,)
    ).rowcount == 1
