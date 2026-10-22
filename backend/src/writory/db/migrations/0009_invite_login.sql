-- Đăng nhập bằng mã mời (D-89). Cách chạy: writory.db.migrate (D-20).
--
-- Mã mời: chủ dự án tạo bằng `python -m writory.db.invites create --name ...`; mã chỉ in ra một
-- lần. Mã = phần tra (`selector`, không bí mật) + phần bí mật (`verifier`). Bảng chỉ giữ selector
-- và SHA-256 của verifier; so bằng hmac.compare_digest (`db/auth.py`). Mỗi mã một `owner_id`
-- riêng, cùng cột owner_id của stories, player_keys, setup_sessions, llm_costs (0003).
-- Chưa có khoá ngoại từ các bảng đó tới đây: dữ liệu cũ của người chơi dev `dev` không có mã mời.
CREATE TABLE invites (
    id            text PRIMARY KEY,                       -- inv-<hex>: để liệt kê, thu hồi
    owner_id      text NOT NULL UNIQUE,                   -- u-<hex>
    name          text NOT NULL CHECK (length(btrim(name)) > 0),  -- chủ dự án gõ, hiện cho bạn
    selector      text NOT NULL UNIQUE,
    verifier_hash bytea NOT NULL CHECK (length(verifier_hash) = 32),
    created_at    timestamptz NOT NULL,
    revoked_at    timestamptz,
    last_login_at timestamptz
);

-- Phiên đăng nhập: token ngẫu nhiên chỉ nằm trong cookie HttpOnly; ở đây là SHA-256 của nó.
-- Hết hạn theo `expires_at` (config/limits.yaml `auth.session_ttl_hours`); thu hồi mã thì xoá phiên.
CREATE TABLE auth_sessions (
    token_hash bytea PRIMARY KEY CHECK (length(token_hash) = 32),
    invite_id  text NOT NULL REFERENCES invites (id) ON DELETE CASCADE,
    owner_id   text NOT NULL,
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at > created_at)
);
CREATE INDEX auth_sessions_invite ON auth_sessions (invite_id);

-- Số lần nhập mã của mỗi máy trong từng cửa sổ cố định (như llm_call_windows, D-56). `client` là
-- SHA-256 (hex) của địa chỉ máy để không lưu thẳng địa chỉ (với IPv4 vẫn dò ngược được); cửa sổ
-- cũ bị xoá khi đếm.
CREATE TABLE login_attempt_windows (
    client       text NOT NULL,
    window_start bigint NOT NULL CHECK (window_start >= 0),
    attempts     integer NOT NULL CHECK (attempts > 0),
    PRIMARY KEY (client, window_start)
);
