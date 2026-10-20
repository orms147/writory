-- Tóm tắt chương do vai `summary` viết sau khi ghi chương (D-49). Chữ máy chủ dùng nội bộ cho đề
-- dàn ý và đề viết của các chương sau; không ra API. Chương 0 không có trang nên không có tóm tắt.
-- Mỗi chương một tóm tắt; thiếu thì chương sau vẫn chạy (D-6: chương đã ghi không phụ thuộc bảng này).
CREATE TABLE chapter_summaries (
    story_id   text NOT NULL REFERENCES stories (id) ON DELETE CASCADE,
    chapter    integer NOT NULL CHECK (chapter >= 1),
    summary    text NOT NULL CHECK (summary <> ''),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (story_id, chapter)
);
