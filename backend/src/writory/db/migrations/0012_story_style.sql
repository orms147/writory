-- Kiểu truyện người chơi chọn lúc khởi tạo (D-153): 'prose' (truyện chữ, như trước) hay 'audio' (kịch bản audio:
-- cùng đường viết, đồ thị và người canh, chỉ đổi văn phong của model viết). Truyện có trước migration này là 'prose'.
-- Danh sách nằm trong code (`pipeline.scene.STORY_STYLES`), nên có CHECK.
-- Cách chạy: writory.db.migrate (D-20).

ALTER TABLE stories ADD COLUMN style text NOT NULL DEFAULT 'prose' CHECK (style IN ('prose', 'audio'));
