-- Số câu hỏi người kể đã dùng, theo truyện và chương (G8, D-40). Cách chạy: writory.db.migrate (D-20).
-- Giới hạn nằm ở config/limits.yaml (rate_limit.narrator_questions_per_chapter), không nằm ở đây.

CREATE TABLE narrator_questions (
    story_id   text NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    chapter    integer NOT NULL CHECK (chapter >= 0),   -- chương đã commit lúc hỏi
    asked      integer NOT NULL CHECK (asked >= 0),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, chapter)
);
