# Chạy cả truyện: bakeoff-deepseek

- Commit `cbb9f077ac282736f79badd40bf660f45825573f` (có sửa chưa commit); đề v1 (`127d59f2867a`); config `6ad8ba9dcef3`; seed 20261022; dry-run: không.
- Model: setup `deepseek/deepseek-v4-flash`, suy luận low; outline `deepseek/deepseek-v4-flash`, suy luận low; extract `deepseek/deepseek-v4-flash`, suy luận low; summary `deepseek/deepseek-v4-flash`, suy luận low; choices `deepseek/deepseek-v4-flash`, suy luận low; moderate `deepseek/deepseek-v4-flash`, suy luận low; writer `deepseek/deepseek-v4-flash`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0814 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0089, lượt chương đắt nhất 0.0188.
- Viết lại: 7; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:early_reveal ×1, guard:sudden_relationship ×6, leak:secret ×1, quality:dialogue_format ×24, quality:length ×2, quality:narration_person ×2. Còn lại khi hiện: quality:length ×1.
- Cạnh bộ trích bỏ: 85 (Fact mới ×47, câu trích không có nguyên văn trong chương (G3) ×19, gỡ mạch mà không có câu trích (D-82) ×1, hé lộ nút có tên mà thiếu known_as (D-17) ×1, id không có trong danh mục ×4, ref phải dạng ×1, sai schema cạnh ×6, thiếu ABOUT ×5, trùng Fact ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00298 | 19025 | 7550 |
| extract | 20 | 0.04031 | 153781 | 128855 |
| moderate | 24 | 0.00861 | 60999 | 11724 |
| outline | 12 | 0.01263 | 66853 | 43093 |
| summary | 5 | 0.00235 | 18049 | 4333 |
| writer | 19 | 0.01451 | 145861 | 28425 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00155 | 0.00233 | 0.00806 | 0.00040 | 0.00067 | 0.00130 | 0.01430 |
| 2 | 0.00000 | 0.00209 | 0.00240 | 0.00585 | 0.00068 | 0.00056 | 0.00126 | 0.01284 |
| 3 | 0.00000 | 0.00186 | 0.00234 | 0.00426 | 0.00029 | 0.00064 | 0.00105 | 0.01045 |
| 4 | 0.00000 | 0.00267 | 0.00186 | 0.01151 | 0.00038 | 0.00058 | 0.00175 | 0.01875 |
| 5 | 0.00000 | 0.00221 | 0.00260 | 0.00551 | 0.00060 | 0.00052 | 0.00195 | 0.01339 |
| 6 | 0.00000 | 0.00226 | 0.00298 | 0.00512 | 0.00000 | 0.00000 | 0.00130 | 0.01166 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | quality:narration_person ×1, guard:early_reveal ×1, guard:sudden_relationship ×3, leak:secret ×1 | 13 | — |
| 2 | 1 | có | 2 | 1 | quality:dialogue_format ×6, guard:sudden_relationship ×2 | 36 | — |
| 3 | 1 | có | 2 | 1 | quality:dialogue_format ×1 | 1 | — |
| 4 | 1 | có | 2 | 1 | quality:dialogue_format ×17 | 14 | — |
| 5 | 1 | có | 2 | 1 | quality:length ×1 | 7 | — |
| 6 | 1 | có | 2 | 2 | quality:narration_person ×1, guard:sudden_relationship ×1, quality:length ×1 | 14 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 4–4 | 4 | đúng khoảng |
| 2 | 5–5 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–6 | 5 | đúng khoảng |
| 2 | 2–5 | 2 | đúng khoảng |
