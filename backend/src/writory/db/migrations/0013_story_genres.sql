-- Khoá thể loại người chơi chọn lúc khởi tạo, theo thứ tự chọn (D-160): khoá trong config/genres.yaml. Đề của thể loại
-- vào dàn ý và model viết mỗi chương. Truyện có trước migration này là mảng rỗng (truyện audio rỗng được coi là sảng
-- văn, `pipeline.genres.story_genre_keys`). Danh mục nằm trong config nên không có CHECK.
-- Cách chạy: writory.db.migrate (D-20).

ALTER TABLE stories ADD COLUMN genres text[] NOT NULL DEFAULT '{}';
