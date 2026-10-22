# Chạy cả truyện: 2026-10-22-extract-recall-base-2

- Commit `7f69430622b727d6b6fc63445388d3ab39e407fa`; đề v1 (`6aeab8e2624b`); config `ebc550d1c367`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0220 USD (trần --budget: 0.04); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0021, lượt chương đắt nhất 0.0031.
- Viết lại: 7; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 5 mạch.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:at_most_one ×2, guard:overdue_thread ×5, guard:teller_does_not_know ×10, quality:repetition ×4. Còn lại khi hiện: guard:at_most_one ×1, guard:overdue_thread ×3, guard:teller_does_not_know ×5, quality:repetition ×2.
- Cạnh bộ trích bỏ: 1 (câu trích không có nguyên văn trong chương (G3) ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 10 | 0.00000 | 35506 | 2520 |
| extract | 27 | 0.02201 | 173051 | 19490 |
| moderate | 37 | 0.00000 | 104591 | 1263 |
| outline | 25 | 0.00000 | 130575 | 19303 |
| summary | 10 | 0.00000 | 39430 | 720 |
| writer | 27 | 0.00000 | 202959 | 46649 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00000 | 0.00000 | 0.00156 | 0.00000 | 0.00000 | 0.00000 | 0.00156 |
| 2 | 0.00000 | 0.00000 | 0.00000 | 0.00136 | 0.00000 | 0.00000 | 0.00000 | 0.00136 |
| 3 | 0.00000 | 0.00000 | 0.00000 | 0.00142 | 0.00000 | 0.00000 | 0.00000 | 0.00142 |
| 4 | 0.00000 | 0.00000 | 0.00000 | 0.00232 | 0.00000 | 0.00000 | 0.00000 | 0.00232 |
| 5 | 0.00000 | 0.00000 | 0.00000 | 0.00190 | 0.00000 | 0.00000 | 0.00000 | 0.00190 |
| 6 | 0.00000 | 0.00000 | 0.00000 | 0.00307 | 0.00000 | 0.00000 | 0.00000 | 0.00307 |
| 7 | 0.00000 | 0.00000 | 0.00000 | 0.00221 | 0.00000 | 0.00000 | 0.00000 | 0.00221 |
| 8 | 0.00000 | 0.00000 | 0.00000 | 0.00293 | 0.00000 | 0.00000 | 0.00000 | 0.00293 |
| 9 | 0.00000 | 0.00000 | 0.00000 | 0.00261 | 0.00000 | 0.00000 | 0.00000 | 0.00261 |
| 10 | 0.00000 | 0.00000 | 0.00000 | 0.00263 | 0.00000 | 0.00000 | 0.00000 | 0.00263 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 1 | guard:at_most_one ×2 | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 2 | guard:teller_does_not_know ×5, guard:overdue_thread ×2 | 0 | — |
| 7 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2, guard:overdue_thread ×1 | 0 | — |
| 8 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2, guard:overdue_thread ×2 | 1 | — |
| 9 | 1 | có | 2 | 1 | quality:repetition ×2, guard:teller_does_not_know ×1 | 0 | — |
| 10 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–7 | 6 | đúng khoảng |
| 2 | 8–9 | 8 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 9 | trễ |
| 2 | 1–5 | 1 | đúng khoảng |
| 3 | 4–8 | 6 | đúng khoảng |
| 4 | 6–10 | 10 | đúng khoảng |
| 5 | 7–12 | — | chưa tới hạn |
