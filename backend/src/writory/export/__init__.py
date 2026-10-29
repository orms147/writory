"""Bộ xuất kịch bản video (D-125, D-118): đọc TOÀN BỘ lớp `truth` của một truyện và chữ các chương đã
đọc, xuất danh sách shot kèm prompt tiếng Anh dán thẳng vào app video, bảng nhân vật, bảng nơi chốn và sơ
đồ tuyến nhân vật theo chương.

Chỉ admin cầm DB chạy được, bằng lệnh `python -m writory.export.video` trên máy: KHÔNG có endpoint, nút
hay đường nào trong `api/` tới module này (test: tests/unit/test_video_export_security.py). Bản xuất có
lộ bí mật nên không đi qua `player_view` và G1 không áp cho nó; đổi lại nó chỉ đọc, không ghi DB nào.

- `sheets`: phần bằng code (bảng, sơ đồ Mermaid, nhân vật có mặt trong cảnh), không tốn tiền.
- `shots`: phần dùng model (vai `video`): mô tả tiếng Anh cố định, chia shot, dịch thoại.
- `video`: điều phối, trần chi phí (G8), ghi file, lệnh.
"""
