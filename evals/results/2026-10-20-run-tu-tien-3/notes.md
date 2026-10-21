# Nhận xét đọc tay: tu-tien-3

Người đọc: Claude (điều phối), 20/10/2026. Nguồn: `summary.md`, `truth_dump.json` (mục `chapters`, `errors`).

- Khởi tạo qua ngay lượt đầu, không cần lượt sửa (D-54 có tác dụng).
- Chương 1 cảnh 1 bị chặn cả 2 lần bấm thử lại (`SCENE_LEAK_BLOCKED`, chỉ `leak:name`). Chi phí 0,0126 USD.
- Tên bị cấm đều là tên giới thiệu bình thường: "Đoàn Khương", "Diệp Tĩnh Lan", "sân Vấn Kiếm", "kho kiếm cụ", "chấp sự Lương", "phòng chấp sự".
  - "kho kiếm cụ" không tránh được, vì bối cảnh người chơi chọn ghi nhân vật chính là "kẻ giữ kiếm cụ".
  - Nguyên nhân: bộ dò lộ (D-26) cấm mọi tên chưa có trong `player_view`, mà bộ trích không hé lộ thực thể ngay lần đầu cảnh nêu tên nó.
- Hướng sửa chủ dự án duyệt: chỉ cấm tên thật bị giấu sau biệt danh và tên được kế hoạch bảo vệ; tên khác xuất hiện trên trang thì code tự hé lộ, kèm câu trích (D-61, D-62).
