# Chạy cả truyện: ab-tu-tien-cu-2

- Commit `51a13a8328827f66c018e6e9e9eead9ac902885d` (có sửa chưa commit); đề v1 (`42aeb39100b7`); config `1b9db7f9197d`; seed 20261028; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0627 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0062, lượt chương đắt nhất 0.0128.
- Viết lại: 5; hiện bản trước vì bản viết lại có lỗi chặn: 1; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_secret ×2, guard:teller_does_not_know ×8, leak:name ×1, quality:repetition ×2. Còn lại khi hiện: guard:overdue_secret ×1, guard:teller_does_not_know ×3, quality:repetition ×2.
- Cạnh bộ trích bỏ: 13 (câu trích không có nguyên văn trong chương (G3) ×2, sai schema cạnh ×2, thiếu KNOWS ×6, trùng Fact ×2, trùng cạnh trong cùng gói ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 7 | 0.00339 | 23225 | 2446 |
| extract | 17 | 0.02226 | 143872 | 17839 |
| moderate | 22 | 0.00347 | 47389 | 1858 |
| outline | 12 | 0.01173 | 62439 | 8522 |
| summary | 5 | 0.00203 | 11900 | 1088 |
| writer | 17 | 0.01985 | 111423 | 16952 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00125 | 0.00196 | 0.00297 | 0.00040 | 0.00085 | 0.00045 | 0.00789 |
| 2 | 0.00000 | 0.00179 | 0.00439 | 0.00492 | 0.00038 | 0.00059 | 0.00075 | 0.01283 |
| 3 | 0.00000 | 0.00212 | 0.00243 | 0.00281 | 0.00042 | 0.00065 | 0.00046 | 0.00890 |
| 4 | 0.00000 | 0.00223 | 0.00382 | 0.00357 | 0.00042 | 0.00062 | 0.00060 | 0.01125 |
| 5 | 0.00000 | 0.00217 | 0.00363 | 0.00396 | 0.00042 | 0.00067 | 0.00068 | 0.01153 |
| 6 | 0.00000 | 0.00216 | 0.00362 | 0.00403 | 0.00000 | 0.00000 | 0.00053 | 0.01034 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 2 | guard:teller_does_not_know ×2, leak:name ×1, quality:repetition ×1 | 3 | — |
| 3 | 1 | có | 2 | 0 | — | 2 | — |
| 4 | 1 | có | 2 | 1 | guard:overdue_secret ×2, quality:repetition ×1 | 0 | — |
| 5 | 1 | có | 2 | 1 | guard:teller_does_not_know ×5 | 5 | — |
| 6 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 3 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 5 | trễ |
| 2 | 4–5 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 4–6 | 4 | đúng khoảng |
| 3 | 5–6 | 6 | đúng khoảng |
| 4 | 3–5 | 4 | đúng khoảng |
