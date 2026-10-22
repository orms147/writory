# Chạy cả truyện: 2026-10-22-extract-recall-v5-1

- Commit `7f69430622b727d6b6fc63445388d3ab39e407fa` (có sửa chưa commit); đề v1 (`6aeab8e2624b`); config `ebc550d1c367`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0230 USD (trần --budget: 0.04); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0021, lượt chương đắt nhất 0.0033.
- Viết lại: 8; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 5 mạch.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_thread ×5, guard:teller_does_not_know ×17, quality:repetition ×4. Còn lại khi hiện: guard:overdue_thread ×3, guard:teller_does_not_know ×8, quality:repetition ×2.
- Cạnh bộ trích bỏ: 1 (câu trích không có nguyên văn trong chương (G3) ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 10 | 0.00000 | 35635 | 2520 |
| extract | 28 | 0.02299 | 187144 | 19822 |
| moderate | 38 | 0.00000 | 108297 | 1282 |
| outline | 24 | 0.00000 | 125035 | 18525 |
| summary | 10 | 0.00000 | 39430 | 720 |
| writer | 28 | 0.00000 | 212086 | 48886 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00000 | 0.00000 | 0.00224 | 0.00000 | 0.00000 | 0.00000 | 0.00224 |
| 2 | 0.00000 | 0.00000 | 0.00000 | 0.00141 | 0.00000 | 0.00000 | 0.00000 | 0.00141 |
| 3 | 0.00000 | 0.00000 | 0.00000 | 0.00141 | 0.00000 | 0.00000 | 0.00000 | 0.00141 |
| 4 | 0.00000 | 0.00000 | 0.00000 | 0.00180 | 0.00000 | 0.00000 | 0.00000 | 0.00180 |
| 5 | 0.00000 | 0.00000 | 0.00000 | 0.00160 | 0.00000 | 0.00000 | 0.00000 | 0.00160 |
| 6 | 0.00000 | 0.00000 | 0.00000 | 0.00304 | 0.00000 | 0.00000 | 0.00000 | 0.00304 |
| 7 | 0.00000 | 0.00000 | 0.00000 | 0.00265 | 0.00000 | 0.00000 | 0.00000 | 0.00265 |
| 8 | 0.00000 | 0.00000 | 0.00000 | 0.00298 | 0.00000 | 0.00000 | 0.00000 | 0.00298 |
| 9 | 0.00000 | 0.00000 | 0.00000 | 0.00326 | 0.00000 | 0.00000 | 0.00000 | 0.00326 |
| 10 | 0.00000 | 0.00000 | 0.00000 | 0.00259 | 0.00000 | 0.00000 | 0.00000 | 0.00259 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 2 | guard:teller_does_not_know ×4, guard:overdue_thread ×1 | 0 | — |
| 7 | 1 | có | 2 | 2 | guard:teller_does_not_know ×4, guard:overdue_thread ×1 | 0 | — |
| 8 | 1 | có | 2 | 1 | guard:teller_does_not_know ×3, guard:overdue_thread ×3 | 1 | — |
| 9 | 1 | có | 2 | 2 | guard:teller_does_not_know ×5, quality:repetition ×2 | 0 | — |
| 10 | 1 | có | 2 | 1 | quality:repetition ×2, guard:teller_does_not_know ×1 | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–7 | 6 | đúng khoảng |
| 2 | 8–9 | 8 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 8 | trễ |
| 2 | 1–5 | 1 | đúng khoảng |
| 3 | 4–8 | 9 | trễ |
| 4 | 6–10 | 10 | đúng khoảng |
| 5 | 7–12 | — | chưa tới hạn |
