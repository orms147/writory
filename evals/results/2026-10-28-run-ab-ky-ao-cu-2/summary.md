# Chạy cả truyện: ab-ky-ao-cu-2

- Commit `51a13a8328827f66c018e6e9e9eead9ac902885d` (có sửa chưa commit); đề v1 (`7b1d86e0688f`); config `1b9db7f9197d`; seed 20261029; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 7).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0474 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0051, lượt chương đắt nhất 0.0092.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 6, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×4, quality:repetition ×1. Còn lại khi hiện: guard:teller_does_not_know ×2.
- Cạnh bộ trích bỏ: 8 (Fact mới ×3, câu trích không có nguyên văn trong chương (G3) ×1, thiếu KNOWS ×4).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 7 | 0.00360 | 19181 | 2916 |
| extract | 14 | 0.01568 | 103003 | 13731 |
| moderate | 20 | 0.00241 | 38560 | 1422 |
| outline | 12 | 0.01082 | 55390 | 8483 |
| summary | 6 | 0.00195 | 10791 | 1200 |
| writer | 14 | 0.01290 | 78607 | 10362 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00132 | 0.00259 | 0.00370 | 0.00033 | 0.00071 | 0.00055 | 0.00919 |
| 2 | 0.00000 | 0.00171 | 0.00160 | 0.00171 | 0.00029 | 0.00040 | 0.00030 | 0.00601 |
| 3 | 0.00000 | 0.00187 | 0.00283 | 0.00304 | 0.00034 | 0.00055 | 0.00048 | 0.00911 |
| 4 | 0.00000 | 0.00204 | 0.00201 | 0.00248 | 0.00034 | 0.00056 | 0.00036 | 0.00780 |
| 5 | 0.00000 | 0.00196 | 0.00188 | 0.00231 | 0.00032 | 0.00067 | 0.00034 | 0.00748 |
| 6 | 0.00000 | 0.00192 | 0.00200 | 0.00243 | 0.00033 | 0.00070 | 0.00039 | 0.00776 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | quality:repetition ×1, guard:teller_does_not_know ×1 | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 1 | guard:teller_does_not_know ×3 | 3 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 4 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/7.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 4–5 | 4 | đúng khoảng |
| 3 | 5–6 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–2 | 1 | đúng khoảng |
| 2 | 3–4 | 3 | đúng khoảng |
| 3 | 3–5 | 4 | đúng khoảng |
| 4 | 5–6 | 5 | đúng khoảng |
| 5 | 6–7 | 6 | đúng khoảng |
