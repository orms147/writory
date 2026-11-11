# Kết quả: người kể với câu hỏi "bẩn" (bài E, đề `questions-dirty-1.yaml`)

Người đọc: Claude (điều phối), 11/11/2026. Khai trước: `expectations.md` cùng thư mục (commit `2af5090`, trước mọi
lời gọi; chủ dự án duyệt đề và trần 0,40 USD ngày 11/11/2026). Kết quả: `../2026-11-11-narrator-dirty-1/`
(`summary.md`, `results.jsonl`, `meta.json`). Người kể `openai/gpt-6-luna`, suy luận low. 147/147 lượt, không lỗi,
không dừng vì trần. Chi 0,0175 USD OpenRouter.

## Theo luật khai trước
1. **Giữ bí mật: đạt.** Lộ ở câu cuối 0, lộ ở câu thô 0/147. Cả 6 câu bí mật viết bẩn ra đúng "Bạn chưa biết điều
   này." ở mọi lượt (18/18).
2. **Trả lời được** (số câu gốc đạt ở đa số lượt, trên 10; trong ngoặc là số lượt):
   | Kiểu | Câu đạt | Lượt đạt | So với `goc` |
   |---|---|---|---|
   | `goc` | 9 | 28/30 | |
   | `khongdau` | 10 | 30/30 | chưa phân biệt được (lệch 1 câu, chiều hơn) |
   | `saichinhta` | 10 | 30/30 | chưa phân biệt được (lệch 1 câu, chiều hơn) |
   | `trongkhong` | 9 | 28/30 | ngang |
3. **Câu hai ý:** 9/9 lượt đủ cả hai ý.
- Dự đoán khai trước: đúng cả ba mục.

## Đọc tay (luật 4, không sửa điểm)
Bốn lượt không đạt đều ở một câu, `c5-a-lai-do-ten-that` ("Gã lái đò mặt sẹo tên thật là gì?", chương 5): hai lượt
của `goc` và hai lượt của `trongkhong`, cùng lý do `model_not_known` (model tự trả `known: false` dù sổ tay chương 5
có tên Lý Thất). Bản không dấu và bản teencode của chính câu này đạt 3/3. Vậy đây là model từ chối không ổn định ở
một câu hỏi về tên thật, không phải do cách gõ. Chưa tìm nguyên nhân; số lượt quá ít để kết luận.

## Giới hạn
- Như đã khai: một truyện, sổ tay nhỏ gửi nguyên nên không ép phần truy hồi; mười câu gốc chỉ thấy được khác biệt lớn.
- Chưa đo câu không dấu ở truyện dài, nơi câu trả lời nằm trong đoạn trên trang (tìm đoạn không bỏ dấu khi so từ).
- Một lần chạy, một model.
