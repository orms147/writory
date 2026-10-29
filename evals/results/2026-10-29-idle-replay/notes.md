# Phát lại tín hiệu "chương liền không đổi trạng thái" (D-112)

Người đọc: Claude, 29/10/2026. Không gọi model: chạy lại `pacing.idle_chapters` và `pacing.standstill` trên `truth_dump.json` của bốn lượt đã có (commit, hash config và model của từng lượt: `meta.json` trong thư mục đó; tất cả GPT-6 Luna). Lệnh: xem đầu `replay.py`.

## Số đo
Mỗi mục `w:A/B[S]` là chương đang viết w. **A** = số chương rỗng liền ngay trước w nếu mạch gỡ và bí mật lộ cũng tính là đổi (dạng đã bỏ). **B** = số chương rỗng theo `idle_chapters` (chỉ đổi nơi ở, đổi chủ hay chỗ đồ vật, có người chết). **S** = cờ `standstill` (D-98, ngưỡng 4) bật.

| Lượt | Chương bật cờ theo B ≥ 4 (ngưỡng `idle_chapters`) | Chương bật `standstill` (S) |
|---|---|---|
| `long-tu-tien-2` (24 chương) | 7–18 | 6, 7, 23, 24 |
| `long-tu-tien-1` (24 chương, dừng ở 17) | 11–16 | 4, 10–16 |
| `ky-ao-vua-3` (12 chương, ghi 10) | 9–11 | 8–11 |
| `tu-tien-4` (6 chương) | không | 7 |

## Đọc được
- `long-tu-tien-2`: cờ `standstill` chỉ bật ở 4 chương vì bộ trích đóng cạnh nơi ở ở ch7 và chỉ mở lại ở ch18 (`../2026-10-22-run-long-tu-tien-2/notes.md`). Tín hiệu mới bật ở 12 chương liền (7–18), đúng đoạn lặp thủ tục ch8–17.
- **Tính mạch gỡ và bí mật lộ làm tín hiệu mất tác dụng:** cột A của `long-tu-tien-2` có dãy rỗng dài nhất 2 trong ch8–17, vì ch9, 11, 14, 17 gỡ mạch đúng lịch (cả 8 mục của kế hoạch được xử lý ở chương đầu khoảng cho phép, ghi chú của lượt đó). Vì vậy `idle_chapters` KHÔNG tính chúng, lệch với đề giao việc ban đầu (liệt kê mạch/mốc/bí mật là tiến triển).
- `long-tu-tien-1`: hai tín hiệu trùng nhau (cạnh nơi ở có, hai cạnh cùng mở); tín hiệu mới không thêm chương nào.
- `ky-ao-vua-3` (chạy trước D-98): hai tín hiệu bật cùng đoạn 8–11, đoạn nhân vật chính đứng ở cửa đại điện.

## Chưa kiểm
- Không biết tín hiệu có bật oan ở truyện nhiều chương nói chuyện nhưng có tiến triển thật (hội nghị dài): cả bốn lượt đều có đoạn lặp, nên chưa có truyện đối chứng "tốt mà chậm".
- Số liệu lấy từ các lượt trước D-112: cạnh nơi ở lúc đó chưa được code giữ nguyên, nên cột B của chúng gồm cả những lần "đổi nơi" chỉ là bộ trích ghi cạnh mới.
- Chưa đo ảnh hưởng lên văn: tín hiệu chỉ thêm một dòng vào mục tiêu chương và một ghi chú vào đề tạo lựa chọn (như D-98).
