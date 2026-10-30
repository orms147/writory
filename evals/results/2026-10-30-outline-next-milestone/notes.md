# Đề dàn ý ch8 tu-tiên có/không dòng mốc "kế tiếp" m4: kết quả

Kỳ vọng và luật khai trước: `expectations.md` (cùng thư mục). Câu hỏi gốc: giả thuyết 3 của `../2026-10-29-milestone-diagnosis/notes.md`.

- **Chạy:** 30/10/2026, commit `b56524c` (main 2fb651c cộng nhánh, không đổi code sản phẩm), config gộp `acaab6e9a1f6…` (tính sau lượt chạy bằng `bench_run.config_sha256`, `meta.json` không ghi), model vai dàn ý theo `config/models.yaml` (`meta.json`: `openai/gpt-6-luna`). Không chạy song song với lượt nào khác.
- **Chi phí:** 30 lời gọi, 0,0205 USD trên trần 0,10.

## Kết quả
| Arm | Đề | Dàn ý trúng `leak_terms` của `fact_su_gia_that` | Nhắc "Minh Ước" | Dàn ý chọn gỡ mạch |
|---|---|---|---|---|
| A | có dòng m4 (như lượt gốc) | 0/10 | 0/10 | `thread_ke_pha_la_ban` 4/10 |
| B | bỏ dòng m4 | 0/10 | 0/10 | `thread_ke_pha_la_ban` 6/10 |
| C (thăm dò) | bỏ m4 và mạch `thread_lap_truong_su_gia` | 0/10 | 0/10 | `thread_ke_pha_la_ban` 10/10 |

**Theo luật khai trước: không phân biệt được** (trúng(A) − trúng(B) = 0 < 3). Không có dàn ý trúng nên không có gì để đọc tay.

**Đã kiểm:** ở A và B không dàn ý nào chọn gỡ mạch `thread_lap_truong_su_gia` (mạch có hạn gỡ rộng hơn khoảng lộ của bí mật cùng nội dung) dù đề cho phép.
**Suy luận, chưa kiểm:** ở đề dàn ý dựng lại, cả dòng mốc lẫn mạch đều không đẩy dàn ý tới bí mật; tám lỗi `early_reveal` ở ch8–9 của lượt gốc có lẽ đến từ bước viết (model viết thấy nhiều ngữ cảnh hơn dàn ý) hay từ ngẫu nhiên, không từ dòng mốc. 10 lời gọi chỉ đủ phát hiện chênh lệch lớn: không có tín hiệu không có nghĩa là không có tác động. Theo luật khai trước, dừng ở đây; không chạy lượt 24 chương.
