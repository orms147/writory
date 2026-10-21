# Nhận xét đọc tay: tu-tien-4

Người đọc: Claude (điều phối), 21/10/2026. Nguồn: `summary.md`, `report.json`, `truth_dump.json`, `chapters/`.

Lần chạy đầu tiên có đủ các sửa sau lần 1: nhịp theo kế hoạch và tóm tắt chương (D-49, D-50), sửa lỗi lần 1 (D-51, D-52), khởi tạo chịu lỗi (D-54), luật tên bí mật và tự hé lộ (D-61, D-62), kiểm duyệt (D-57, D-58, D-70). Cùng đề và seed với lần 1.

## So với lần 1 (`2026-10-20-run-tu-tien-1`)
| | Lần 1 | Lần 4 |
|---|---|---|
| Chương ghi được | 6/6 | 6/6 |
| Kết truyện ở chương cuối | không | **có** (`story_finished`, "Hết truyện.") |
| Bí mật lộ đúng khoảng | 0/2 (đều chưa lộ) | **1/1** |
| Mạch gỡ đúng hạn | 1/4 | **3/4** |
| Đổi ngôi kể | chương 6 | **không**: mọi chương kể "tôi" |
| Chữ Hán trong dàn ý hay văn | có (một dàn ý) | **không** |
| Cảnh viết lại vì bắt nhầm tên | có ở chương 1 | **không** |
| Lượt viết lại | 5 | 3 |
| Chi phí | 0,0512 USD | 0,0596 USD (có thêm tóm tắt và kiểm duyệt) |

## Còn lại
1. **Khởi tạo vẫn là bước dễ hỏng nhất.**
   - Lượt bấm đầu hỏng sau 1 lượt sửa: "chương 5 có 4 việc đến hạn, tối đa 3".
   - Lượt bấm thứ hai cần sửa 1 lần, gồm một lỗi hồi không có mốc và năm cạnh `KNOWS` của nhân vật chính ở chương 0.
   - Model muốn nhân vật chính biết sẵn bối cảnh ("ba tông môn tranh quyền"), là điều người chơi đã đọc lúc khởi tạo.
   - Bước này tốn 0,0093 USD, khoảng 16% tổng.
2. **Một mạch quá hạn mà không gỡ** (mạch 3, hạn 1–6). Người canh đã bắt (`overdue_thread`), nhưng bản viết lại vẫn chưa gỡ. Luật hiện tại cho cảnh vẫn hiện, không chặn người chơi (D-50).
3. **Lời thoại trong lựa chọn vẫn luôn "nói thật"**, cả 5 chương. Câu khuyến khích trong prompt (`choices-2`, D-51) không đủ.
4. Kiểm lặp từ vẫn bắt 3 lần. Đã đọc lướt: đều là cụm lặp thật, không phải tên riêng.
5. Văn đọc tốt, giữ giọng tu tiên mưu lược, kết có hậu quả rõ ràng. Truyện xoay quanh một cuộc thương nghị, nhưng có tiến triển qua các chương, không còn quanh quẩn như lần 1.
