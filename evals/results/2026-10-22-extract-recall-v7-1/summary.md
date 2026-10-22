# Chạy cả truyện: 2026-10-22-extract-recall-v7-1

- Commit `1cdf43f720522c8a280b04c3ed6cfc21e56b8024` (có sửa chưa commit); đề v1 (`6aeab8e2624b`); config `ebc550d1c367`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 9/10 (kế hoạch 12).
- Dừng: budget ở chapter 10 (COST_LIMIT_STORY).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0165 USD (trần --budget: 0.025); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0019, lượt chương đắt nhất 0.0027.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 9, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:at_most_one ×1, guard:teller_does_not_know ×2, quality:repetition ×2. Còn lại khi hiện: guard:teller_does_not_know ×1, quality:repetition ×1.
- Cạnh bộ trích bỏ: 1 (sai schema cạnh ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 9 | 0.00000 | 30072 | 2268 |
| extract | 20 | 0.01646 | 129993 | 12036 |
| moderate | 29 | 0.00000 | 79748 | 1055 |
| outline | 19 | 0.00000 | 93436 | 14347 |
| summary | 9 | 0.00000 | 35193 | 648 |
| writer | 20 | 0.00000 | 140567 | 33911 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00000 | 0.00000 | 0.00128 | 0.00000 | 0.00000 | 0.00000 | 0.00128 |
| 2 | 0.00000 | 0.00000 | 0.00000 | 0.00147 | 0.00000 | 0.00000 | 0.00000 | 0.00147 |
| 3 | 0.00000 | 0.00000 | 0.00000 | 0.00146 | 0.00000 | 0.00000 | 0.00000 | 0.00146 |
| 4 | 0.00000 | 0.00000 | 0.00000 | 0.00194 | 0.00000 | 0.00000 | 0.00000 | 0.00194 |
| 5 | 0.00000 | 0.00000 | 0.00000 | 0.00161 | 0.00000 | 0.00000 | 0.00000 | 0.00161 |
| 6 | 0.00000 | 0.00000 | 0.00000 | 0.00195 | 0.00000 | 0.00000 | 0.00000 | 0.00195 |
| 7 | 0.00000 | 0.00000 | 0.00000 | 0.00175 | 0.00000 | 0.00000 | 0.00000 | 0.00175 |
| 8 | 0.00000 | 0.00000 | 0.00000 | 0.00231 | 0.00000 | 0.00000 | 0.00000 | 0.00231 |
| 9 | 0.00000 | 0.00000 | 0.00000 | 0.00269 | 0.00000 | 0.00000 | 0.00000 | 0.00269 |
| 10 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 1 | guard:at_most_one ×1, guard:teller_does_not_know ×1 | 0 | — |
| 9 | 1 | có | 2 | 1 | quality:repetition ×2, guard:teller_does_not_know ×1 | 0 | — |
| 10 | 1 | không | 0 | 0 | — | 0 | COST_LIMIT_STORY |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 9/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–7 | 6 | đúng khoảng |
| 2 | 8–9 | 8 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 6 | đúng khoảng |
| 2 | 1–5 | 1 | đúng khoảng |
| 3 | 4–8 | 8 | đúng khoảng |
| 4 | 6–10 | — | chưa tới hạn |
| 5 | 7–12 | — | chưa tới hạn |
