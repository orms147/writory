# Chạy cả truyện: 2026-10-22-new-facts-replay-3

- Commit `2c1310ad5ce5a1e0ec7d13a277ff64f857b443a5`; đề v1 (`6aeab8e2624b`); config `3852aa7fdd9d`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 9/10 (kế hoạch 12).
- Dừng: budget ở chapter 10 (COST_LIMIT_STORY).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0286 USD (trần --budget: 0.038); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0023, lượt chương đắt nhất 0.0043.
- Viết lại: 6; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 2 mạch.
- Tóm tắt chương: tạo 9, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_thread ×2, guard:teller_does_not_know ×3, quality:repetition ×3. Còn lại khi hiện: guard:overdue_thread ×1, quality:repetition ×1.
- Cạnh bộ trích bỏ: 18 (Fact mới ×4, câu trích không có nguyên văn trong chương (G3) ×2, sai schema cạnh ×4, thiếu KNOWS ×4, trùng Fact ×4).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 9 | 0.00000 | 43253 | 2268 |
| extract | 25 | 0.02860 | 234512 | 22869 |
| moderate | 34 | 0.00000 | 96491 | 1150 |
| outline | 23 | 0.00000 | 125498 | 17674 |
| summary | 9 | 0.00000 | 35193 | 648 |
| writer | 26 | 0.00000 | 200739 | 45223 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00000 | 0.00000 | 0.00177 | 0.00000 | 0.00000 | 0.00000 | 0.00177 |
| 2 | 0.00000 | 0.00000 | 0.00000 | 0.00177 | 0.00000 | 0.00000 | 0.00000 | 0.00177 |
| 3 | 0.00000 | 0.00000 | 0.00000 | 0.00214 | 0.00000 | 0.00000 | 0.00000 | 0.00214 |
| 4 | 0.00000 | 0.00000 | 0.00000 | 0.00248 | 0.00000 | 0.00000 | 0.00000 | 0.00248 |
| 5 | 0.00000 | 0.00000 | 0.00000 | 0.00306 | 0.00000 | 0.00000 | 0.00000 | 0.00306 |
| 6 | 0.00000 | 0.00000 | 0.00000 | 0.00341 | 0.00000 | 0.00000 | 0.00000 | 0.00341 |
| 7 | 0.00000 | 0.00000 | 0.00000 | 0.00287 | 0.00000 | 0.00000 | 0.00000 | 0.00287 |
| 8 | 0.00000 | 0.00000 | 0.00000 | 0.00362 | 0.00000 | 0.00000 | 0.00000 | 0.00362 |
| 9 | 0.00000 | 0.00000 | 0.00000 | 0.00429 | 0.00000 | 0.00000 | 0.00000 | 0.00429 |
| 10 | 0.00000 | 0.00000 | 0.00000 | 0.00319 | 0.00000 | 0.00000 | 0.00000 | 0.00319 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 3 | — |
| 5 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 1 | — |
| 6 | 1 | có | 2 | 1 | guard:overdue_thread ×2 | 2 | — |
| 7 | 1 | có | 2 | 0 | — | 2 | — |
| 8 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 3 | — |
| 9 | 1 | có | 2 | 2 | guard:teller_does_not_know ×1, quality:repetition ×2 | 7 | — |
| 10 | 1 | không | 1 | 1 | quality:repetition ×1 | 0 | COST_LIMIT_STORY |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 9/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–7 | 6 | đúng khoảng |
| 2 | 8–9 | 8 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 7 | trễ |
| 2 | 1–5 | 1 | đúng khoảng |
| 3 | 4–8 | 6 | đúng khoảng |
| 4 | 6–10 | — | chưa tới hạn |
| 5 | 7–12 | — | chưa tới hạn |
