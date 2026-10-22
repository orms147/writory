# Chạy cả truyện: bakeoff-luna

- Commit `cbb9f077ac282736f79badd40bf660f45825573f` (có sửa chưa commit); đề v1 (`127d59f2867a`); config `6ad8ba9dcef3`; seed 20261022; dry-run: không.
- Model: setup `deepseek/deepseek-v4-flash`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `deepseek/deepseek-v4-flash`, suy luận low; summary `deepseek/deepseek-v4-flash`, suy luận low; choices `deepseek/deepseek-v4-flash`, suy luận low; moderate `deepseek/deepseek-v4-flash`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0672 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0069, lượt chương đắt nhất 0.0142.
- Viết lại: 4; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×1.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:sudden_relationship ×3, guard:teller_does_not_know ×1, quality:repetition ×2. Còn lại khi hiện: quality:repetition ×1.
- Cạnh bộ trích bỏ: 41 (Fact mới ×13, câu trích không có nguyên văn trong chương (G3) ×8, id không có trong danh mục ×1, ref phải dạng ×1, sai schema cạnh ×1, thiếu ABOUT ×13, thiếu KNOWS ×2, trùng Fact ×1, trùng cạnh trong cùng gói ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 6 | 0.00372 | 20454 | 10838 |
| extract | 16 | 0.02567 | 123899 | 82959 |
| moderate | 21 | 0.00757 | 48003 | 9439 |
| outline | 12 | 0.01144 | 54638 | 9217 |
| summary | 6 | 0.00239 | 17580 | 5157 |
| writer | 16 | 0.01638 | 95611 | 13364 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00171 | 0.00299 | 0.00542 | 0.00029 | 0.00076 | 0.00098 | 0.01215 |
| 2 | 0.00000 | 0.00169 | 0.00190 | 0.00178 | 0.00041 | 0.00053 | 0.00079 | 0.00710 |
| 3 | 0.00000 | 0.00200 | 0.00327 | 0.00487 | 0.00097 | 0.00042 | 0.00113 | 0.01266 |
| 4 | 0.00000 | 0.00203 | 0.00311 | 0.00654 | 0.00043 | 0.00084 | 0.00127 | 0.01421 |
| 5 | 0.00000 | 0.00201 | 0.00202 | 0.00271 | 0.00029 | 0.00117 | 0.00265 | 0.01085 |
| 6 | 0.00000 | 0.00200 | 0.00309 | 0.00435 | 0.00000 | 0.00000 | 0.00075 | 0.01019 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | guard:sudden_relationship ×1 | 13 | — |
| 2 | 1 | có | 2 | 0 | — | 1 | — |
| 3 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 4 | 1 | có | 2 | 1 | guard:sudden_relationship ×1 | 9 | — |
| 5 | 1 | có | 2 | 0 | — | 1 | CHOICES_LEAK_BLOCKED |
| 6 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1, guard:sudden_relationship ×1 | 17 | — |

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
| 2 | 2–5 | 4 | đúng khoảng |
