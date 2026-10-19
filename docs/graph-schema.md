# Schema đồ thị

> **Trạng thái:** bản khung. Chốt ở tuần 1 sau khi dựng tay truyện mẫu 5 chương (`data/sample-story/`). Mô hình đề xuất ban đầu: design §7.2.

## Quy tắc đã chốt
- **Mọi nút và cạnh** mang `story_id` và `commit_id` (G10, D-6).
- **Thời gian:** mọi cạnh trạng thái mang `valid_from_chapter` và `valid_to_chapter` (rỗng = còn hiệu lực). Không xoá sự thật cũ; đóng nó lại. Thứ tự là số chương, không dùng giờ máy.
- **Hai lớp** trên cùng một đồ thị: lớp `truth` là toàn bộ đồ thị. Lớp `player_view` là phần nhân vật chính `KNOWS` cộng phần có `REVEALED_TO_PLAYER`. Định nghĩa chính xác của `player_view` nằm trong **một hàm/truy vấn duy nhất**, và mọi đường ra cho người chơi gọi qua nó (G1).
- **Nguồn gốc:** trường do người chơi viết mang `user_authored: true` (G4).
- **Định danh:** mỗi thực thể có `id` ổn định, `name`, `aliases[]`. Trích thay đổi chỉ được tham chiếu `id` đã có (G11).
- **Nhánh:** sao chép đồ thị khi rẽ (D-5). Schema không có `branch_id`.

## Nút
*(điền ở tuần 1: nhãn, thuộc tính bắt buộc, ràng buộc unique)*

## Cạnh
*(điền ở tuần 1)*

## Ràng buộc và index
*(điền ở tuần 1: `CREATE CONSTRAINT ...`)*

## Truy vấn mẫu phải trả lời được
Danh sách câu hỏi: design §7.3. Mỗi câu một truy vấn Cypher, có test chạy trên truyện mẫu.
