# Cao trào bằng code (D-142): kỳ vọng khai TRƯỚC khi tính lại

Người đọc: Claude điều phối và chủ dự án, 30/10/2026. Khai trước khi chạy `replay.py` (chưa viết) trên các truyện đã lưu; không gọi model, chỉ dựng lại mục tiêu chương bằng `chapter_goals` / `render_chapter_goals` của main (`3ec3b85`) và của nhánh `feature/climax-code`, từ `truth_dump.json` (kế hoạch, gói từng chương, dấu `milestones` trên nút `Chapter`).

## Hai thay đổi được đo
1. **Ứng viên:** dấu mốc `climax` ghi ở chương nhỏ hơn `from_chapter` của mốc chỉ là ứng viên, chưa tính xong; bộ trích vẫn được đánh dấu lại (mốc còn "chưa xảy ra" trong đề bộ trích); dấu từ `from_chapter` trở đi mới là xong. Mốc `turning_point` giữ luật cũ (dấu đầu thắng, dù trước khoảng).
2. **Hậu quả:** cao trào đã xong thì mục tiêu của `limits.context.climax_aftermath_chapters` chương kế tiếp (mặc định 2, kể cả ngoài khoảng của mốc) thay câu "đã xảy ra, không diễn lại, đi bước kế" bằng câu đòi viết hậu quả.

## Dữ liệu (đã khảo sát số dấu, chưa tính tác động)
Bảy thư mục có dấu mốc: `long-after-ky-ao-2` (24 chương), `long-after-ky-ao` (11), `long-after-tu-tien` (21), `psab-a1` (16), `psab-a2` (16), `psab-b1` (11, dừng), `psab-b1-r3` (16). Có dấu cao trào ở 5 lượt: ky-ao-2, psab-a1, psab-a2 và psab-b1-r3 ghi m6 ở ch16 (khoảng 16–18, đúng ngày đầu khoảng); long-after-tu-tien ghi m6 ở ch19 (khoảng 20–22, trước khoảng một chương). Không lượt nào có dấu m7 cao trào.

## Kỳ vọng
- **K1.** Trong 5 dấu cao trào, đúng **1** đổi kết quả (xong → ứng viên): tu-tien m6 ở ch19. Bốn dấu ở ch16 vẫn là xong.
- **K2.** Số chương có mục "Mốc cốt truyện" khác giữa main và nhánh: tu-tien đúng **hai** chương (ch20, ch21: m6 từ "ĐÃ xảy ra rồi" thành câu ứng viên; ch22 không có trong dữ liệu); ky-ao-2 đúng **hai** (ch17, ch18: câu "đã xảy ra" thành câu hậu quả); psab-a1, psab-a2, psab-b1-r3 (16 chương, cao trào xong ở ch16, chương 17 chưa viết): **không** chương nào; long-after-ky-ao và psab-b1 (dừng trước cao trào): không chương nào.
- **K3.** Mọi dòng mốc `turning_point` giống hệt giữa main và nhánh ở mọi chương của mọi lượt (0 chương khác).
- **K4.** Ngoài mục "Mốc cốt truyện" không có phần nào của mục tiêu chương khác (bí mật, mạch, nhịp, `gap`, `standstill`, `idle`): 0 chương khác. Riêng cờ `gap` (chương không mốc nào đang diễn ra) không đổi ở chương nào.
- **K5.** Ở tu-tien ch20 và ch21 mốc m6 vẫn nằm trong danh sách "chưa xảy ra" của đề bộ trích (`pending_milestones`) trên nhánh, và không nằm ở main.
- **Kỳ vọng sai nếu:** có dấu cao trào nào khác đổi, có chương `turning_point` đổi, hoặc có phần ngoài mục mốc đổi. Khi đó ghi lại là bug hay hiểu sai dữ liệu, không sửa kỳ vọng.

## Không đo được ở đây (ghi để khỏi hiểu nhầm)
Không biết model viết có viết hậu quả tốt hơn không, và bộ trích có đánh dấu lại ứng viên trong khoảng không: cả hai cần lượt chạy có gọi model, ngoài phạm vi và ngoài ngân sách của PR này. Replay giữ nguyên dấu gốc, nên ở tu-tien ứng viên không bao giờ được xác nhận trong dữ liệu.
