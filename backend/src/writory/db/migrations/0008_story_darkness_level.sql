-- Mức u tối người chơi chọn lúc khởi tạo, lưu theo truyện (G9, D-67): khoá trong
-- config/moderation.yaml `darkness_levels`. Kiểm duyệt đầu ra mỗi chương dùng mức này (D-58).
-- NULL: truyện tạo trước migration này hoặc không qua /setup; dùng `default_darkness_level`.
-- Không có CHECK theo danh sách khoá: danh sách nằm trong config, không nằm ở đây. Code kiểm khoá
-- lúc tạo phiên và lúc dựng chương (khoá lạ thì báo lỗi, không âm thầm dùng mặc định).
-- Cách chạy: writory.db.migrate (D-20).

ALTER TABLE stories ADD COLUMN darkness_level text;
