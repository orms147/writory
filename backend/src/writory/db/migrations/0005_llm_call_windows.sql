-- Số lời gọi model của mỗi người chơi trong từng phút (G8, D-56). Cửa sổ cố định một phút:
-- window_start = giây kể từ epoch chia 60. Giới hạn nằm ở config/limits.yaml
-- (rate_limit.llm_calls_per_minute_per_user), không nằm ở đây. Cách chạy: writory.db.migrate (D-20).
-- owner_id: giống llm_costs, chưa có bảng tài khoản (tuần 5) nên không có khoá ngoại.

CREATE TABLE llm_call_windows (
    owner_id     text NOT NULL,
    window_start bigint NOT NULL CHECK (window_start >= 0),
    calls        integer NOT NULL CHECK (calls > 0),
    PRIMARY KEY (owner_id, window_start)
);
