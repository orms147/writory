-- Lưu trữ cho API truyện (D-44): bản kế hoạch ẩn, key người chơi, phiên khởi tạo, nhật ký chi phí,
-- lựa chọn cuối chương và hành động dẫn tới chương sau. Cách chạy: writory.db.migrate (D-20).
--
-- owner_id: chưa có tài khoản (tuần 5), mọi dòng mang người chơi dev `dev` (api/deps.py,
-- DEV_OWNER_ID). Tuần 5: tạo bảng tài khoản, đổi owner_id `dev` sang id tài khoản thật (hoặc xoá
-- dữ liệu dev), rồi thêm FOREIGN KEY từ owner_id của stories, player_keys, setup_sessions,
-- llm_costs tới bảng đó. Không cột nào ở đây phải đổi kiểu.

-- Thiết lập truyện người chơi đã chọn (tag, bối cảnh, hướng, nhân vật chính), làm đề cho mọi chương.
-- Có chữ người chơi: pipeline luôn bọc như dữ liệu (G4).
ALTER TABLE stories ADD COLUMN brief text;

-- Bản kế hoạch truyện (story_plan, design §6.1): hồi, bí mật, khoảng lộ. Ẩn: không ra API (G1).
CREATE TABLE story_plans (
    story_id   text PRIMARY KEY REFERENCES stories (id) ON DELETE CASCADE,
    plan       jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Key OpenRouter của người chơi, chỉ lưu bản mã hoá Fernet (G7, D-11). Không cột nào chứa key
-- hay một phần của key; 4 ký tự cuối tính lúc đọc, sau khi giải mã.
CREATE TABLE player_keys (
    owner_id   text PRIMARY KEY,
    ciphertext bytea NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Phiên khởi tạo (design §4.1). Máy chủ giữ 3 lựa chọn của mỗi bước; trình duyệt chỉ gửi số thứ
-- tự, cộng phần sửa tên, tính cách, quá khứ của nhân vật chính (`protagonist`, chữ người chơi).
-- Số lựa chọn mỗi bước nằm trong code (pipeline/setup.py OPTION_COUNT).
CREATE TABLE setup_sessions (
    id              text PRIMARY KEY,
    owner_id        text NOT NULL,
    choices         jsonb NOT NULL,             -- StoryChoices: tag, độ dài, góc nhìn, quy ước tên
    settings        jsonb,
    setting_index   integer CHECK (setting_index >= 0),
    plots           jsonb,
    plot_index      integer CHECK (plot_index >= 0),
    characters      jsonb,
    character_index integer CHECK (character_index >= 0),
    protagonist     jsonb,
    story_id        text UNIQUE REFERENCES stories (id) ON DELETE SET NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    CHECK (setting_index IS NULL OR settings IS NOT NULL),
    CHECK (plots IS NULL OR setting_index IS NOT NULL),
    CHECK (plot_index IS NULL OR plots IS NOT NULL),
    CHECK (characters IS NULL OR plot_index IS NOT NULL),
    CHECK (character_index IS NULL OR characters IS NOT NULL),
    CHECK ((character_index IS NULL) = (protagonist IS NULL)),
    CHECK (story_id IS NULL OR protagonist IS NOT NULL)
);

-- Nhật ký chi phí: một dòng mỗi lời gọi model (G8, D-10). Trần mỗi truyện cộng từ đây. Lời gọi lúc
-- khởi tạo mang setup_session_id; khi truyện được tạo thì gắn thêm story_id.
CREATE TABLE llm_costs (
    id                bigserial PRIMARY KEY,
    owner_id          text NOT NULL,
    story_id          text REFERENCES stories (id) ON DELETE CASCADE,
    setup_session_id  text REFERENCES setup_sessions (id) ON DELETE CASCADE,
    chapter           integer CHECK (chapter >= 0),  -- chương đang viết hoặc đang đọc
    role              text NOT NULL,                 -- vai: writer, outline, extract, choices, …
    model             text NOT NULL,
    prompt_tokens     integer NOT NULL CHECK (prompt_tokens >= 0),
    completion_tokens integer NOT NULL CHECK (completion_tokens >= 0),
    cost_usd          numeric(14, 8),                -- NULL: phản hồi không có usage.cost (D-10)
    created_at        timestamptz NOT NULL DEFAULT now(),
    CHECK (story_id IS NOT NULL OR setup_session_id IS NOT NULL)
);
CREATE INDEX llm_costs_story ON llm_costs (story_id) WHERE story_id IS NOT NULL;
CREATE INDEX llm_costs_setup ON llm_costs (setup_session_id) WHERE setup_session_id IS NOT NULL;

-- Lựa chọn cuối chương phía máy chủ (D-37): dữ liệu có cấu trúc kèm id nút thật. Không ra API;
-- người chơi chỉ nhận PlayerChoice (id mờ, loại, sắc thái, chữ). Mỗi chương một bộ.
CREATE TABLE chapter_choices (
    story_id   text NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    chapter    integer NOT NULL CHECK (chapter >= 1),
    position   integer NOT NULL CHECK (position >= 0),
    choice_id  text NOT NULL,
    choice     jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, choice_id),
    UNIQUE (story_id, chapter, position)
);

-- Hành động dẫn tới chương `for_chapter`: lựa chọn đã chọn, hoặc chữ tự viết đã qua phân loại (G5).
CREATE TABLE player_actions (
    story_id    text NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    for_chapter integer NOT NULL CHECK (for_chapter >= 1),
    source      text NOT NULL CHECK (source IN ('choice', 'custom')),
    choice_id   text,
    text        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, for_chapter),
    CHECK ((source = 'choice') = (choice_id IS NOT NULL)),
    FOREIGN KEY (story_id, choice_id) REFERENCES chapter_choices (story_id, choice_id)
);
