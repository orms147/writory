-- Truyện, chương, gói thay đổi đồ thị (D-6). Cách chạy: writory.db.migrate (D-20).

CREATE TABLE stories (
    id                text PRIMARY KEY,
    owner_id          text,                    -- tài khoản: tuần 5
    length_level      text NOT NULL,           -- khoá trong config/story_lengths.yaml
    committed_chapter integer CHECK (committed_chapter >= 0),  -- NULL = chưa commit chương nào
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chapters (
    story_id   text NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    commit_id  text NOT NULL,
    number     integer NOT NULL CHECK (number >= 0),
    status     text NOT NULL CHECK (status IN ('pending', 'committed', 'failed')),
    scenes     jsonb NOT NULL,                 -- danh sách văn bản các cảnh
    error      text,                           -- lý do failed, chỉ để log
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, commit_id)
);

-- Mỗi số chương có tối đa một bản chưa hỏng; bản failed được giữ lại để đo và gỡ lỗi.
CREATE UNIQUE INDEX chapters_one_live_per_number
    ON chapters (story_id, number) WHERE status <> 'failed';
-- Mỗi truyện có tối đa một chương pending.
CREATE UNIQUE INDEX chapters_one_pending_per_story
    ON chapters (story_id) WHERE status = 'pending';

-- Outbox: gói thay đổi đồ thị của một chương, để áp lại khi reconcile.
CREATE TABLE change_packages (
    story_id   text NOT NULL,
    commit_id  text NOT NULL,
    package    jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, commit_id),
    FOREIGN KEY (story_id, commit_id) REFERENCES chapters (story_id, commit_id) ON DELETE CASCADE
);
