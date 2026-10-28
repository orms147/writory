# Chạy cả truyện: ab-trinh-tham-cu-2

- Commit `51a13a8328827f66c018e6e9e9eead9ac902885d` (có sửa chưa commit); đề v1 (`a0997a5fc137`); config `1b9db7f9197d`; seed 20261030; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0531 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0061, lượt chương đắt nhất 0.0136.
- Viết lại: 4; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_secret ×1, guard:overdue_thread ×1, guard:teller_does_not_know ×5, quality:repetition ×2. Còn lại khi hiện: guard:teller_does_not_know ×3, quality:repetition ×2.
- Cạnh bộ trích bỏ: 16 (câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×7, thiếu KNOWS ×7, trùng Fact ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00276 | 13827 | 2060 |
| extract | 16 | 0.01838 | 123028 | 15298 |
| moderate | 21 | 0.00288 | 42745 | 1533 |
| outline | 12 | 0.01103 | 55974 | 8709 |
| summary | 5 | 0.00175 | 9786 | 1056 |
| writer | 16 | 0.01629 | 95158 | 13597 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00130 | 0.00181 | 0.00237 | 0.00038 | 0.00040 | 0.00040 | 0.00667 |
| 2 | 0.00000 | 0.00171 | 0.00184 | 0.00196 | 0.00037 | 0.00054 | 0.00036 | 0.00678 |
| 3 | 0.00000 | 0.00202 | 0.00288 | 0.00338 | 0.00032 | 0.00064 | 0.00052 | 0.00975 |
| 4 | 0.00000 | 0.00201 | 0.00187 | 0.00209 | 0.00033 | 0.00060 | 0.00035 | 0.00725 |
| 5 | 0.00000 | 0.00220 | 0.00460 | 0.00511 | 0.00036 | 0.00057 | 0.00075 | 0.01358 |
| 6 | 0.00000 | 0.00178 | 0.00330 | 0.00347 | 0.00000 | 0.00000 | 0.00050 | 0.00905 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 1 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 2 | guard:teller_does_not_know ×4, guard:overdue_secret ×1 | 6 | — |
| 6 | 1 | có | 2 | 1 | guard:overdue_thread ×1, quality:repetition ×2 | 9 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 5–5 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–6 | 6 | đúng khoảng |
| 2 | 2–4 | 3 | đúng khoảng |
| 3 | 2–5 | 5 | đúng khoảng |
| 4 | 3–6 | 3 | đúng khoảng |
