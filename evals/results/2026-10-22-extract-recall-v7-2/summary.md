# Chạy cả truyện: 2026-10-22-extract-recall-v7-2

- Commit `1cdf43f720522c8a280b04c3ed6cfc21e56b8024` (có sửa chưa commit); đề v1 (`6aeab8e2624b`); config `ebc550d1c367`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 8/10 (kế hoạch 12).
- Dừng: budget ở chapter 9 (COST_LIMIT_STORY).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0162 USD (trần --budget: 0.025); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0012, lượt chương đắt nhất 0.0022.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 2 mạch.
- Tóm tắt chương: tạo 8, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_thread ×3, guard:teller_does_not_know ×1, quality:repetition ×1. Còn lại khi hiện: guard:overdue_thread ×1.
- Cạnh bộ trích bỏ: 0 (—).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 8 | 0.00000 | 26404 | 2016 |
| extract | 20 | 0.01619 | 131281 | 11124 |
| moderate | 28 | 0.00000 | 77614 | 980 |
| outline | 20 | 0.00000 | 103410 | 15066 |
| summary | 8 | 0.00000 | 30729 | 576 |
| writer | 20 | 0.00000 | 143925 | 33610 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00000 | 0.00000 | 0.00155 | 0.00000 | 0.00000 | 0.00000 | 0.00155 |
| 2 | 0.00000 | 0.00000 | 0.00000 | 0.00149 | 0.00000 | 0.00000 | 0.00000 | 0.00149 |
| 3 | 0.00000 | 0.00000 | 0.00000 | 0.00149 | 0.00000 | 0.00000 | 0.00000 | 0.00149 |
| 4 | 0.00000 | 0.00000 | 0.00000 | 0.00180 | 0.00000 | 0.00000 | 0.00000 | 0.00180 |
| 5 | 0.00000 | 0.00000 | 0.00000 | 0.00167 | 0.00000 | 0.00000 | 0.00000 | 0.00167 |
| 6 | 0.00000 | 0.00000 | 0.00000 | 0.00211 | 0.00000 | 0.00000 | 0.00000 | 0.00211 |
| 7 | 0.00000 | 0.00000 | 0.00000 | 0.00205 | 0.00000 | 0.00000 | 0.00000 | 0.00205 |
| 8 | 0.00000 | 0.00000 | 0.00000 | 0.00178 | 0.00000 | 0.00000 | 0.00000 | 0.00178 |
| 9 | 0.00000 | 0.00000 | 0.00000 | 0.00224 | 0.00000 | 0.00000 | 0.00000 | 0.00224 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 1 | guard:overdue_thread ×2 | 0 | — |
| 7 | 1 | có | 2 | 1 | guard:overdue_thread ×1 | 0 | — |
| 8 | 1 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | không | 1 | 1 | quality:repetition ×1, guard:teller_does_not_know ×1 | 0 | COST_LIMIT_STORY |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 8/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–7 | 6 | đúng khoảng |
| 2 | 8–9 | 8 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 7 | trễ |
| 2 | 1–5 | 4 | đúng khoảng |
| 3 | 4–8 | 8 | đúng khoảng |
| 4 | 6–10 | — | chưa tới hạn |
| 5 | 7–12 | — | chưa tới hạn |
