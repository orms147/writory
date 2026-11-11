-- Lượt hỏi đáp người kể đã xong, theo truyện và chương (D-162). Cách chạy: writory.db.migrate (D-20).
-- `question`: chữ người chơi gõ (đã qua kiểm duyệt đầu vào). `answer`: đúng chữ đã hiện cho người chơi, đã qua
-- mọi phép kiểm của người kể (kể cả câu "Bạn chưa biết điều này."); câu thô của model không bao giờ được lưu.
-- `source_chapters`: chương nguồn đã hiện kèm câu trả lời. Giao diện đọc lại để hiện; người kể chỉ nhận các lượt
-- của chương đang đọc khi `limits.narrator_history.turns` > 0. Xoá truyện thì xoá theo.

CREATE TABLE narrator_turns (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    story_id        text NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    chapter         integer NOT NULL CHECK (chapter >= 0),   -- chương đã commit lúc hỏi
    question        text NOT NULL,
    answer          text NOT NULL,
    source_chapters integer[] NOT NULL DEFAULT '{}',
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX narrator_turns_story_chapter ON narrator_turns (story_id, chapter, id);
