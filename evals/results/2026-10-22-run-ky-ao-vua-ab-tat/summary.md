# Chạy cả truyện: ky-ao-vua-ab-tat

- Commit `c6db5cc7759d75e43f638d38d16180fbcd7f6894`; đề v1 (`6aeab8e2624b`); config `19b2a28450bf`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 7/10 (kế hoạch 12).
- Dừng: error ở chapter 8 (LLM_REQUEST_INVALID).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0595 USD (trần --budget: 0.12); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0049, lượt chương đắt nhất 0.0112.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 7, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: quality:repetition ×9. Còn lại khi hiện: quality:repetition ×3.
- Cạnh bộ trích bỏ: 0 (—).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 7 | 0.00385 | 21149 | 2408 |
| extract | 16 | 0.01611 | 110734 | 9978 |
| moderate | 23 | 0.00360 | 49987 | 1886 |
| outline | 16 | 0.01411 | 75865 | 11085 |
| summary | 7 | 0.00307 | 17719 | 1720 |
| writer | 16 | 0.01880 | 99761 | 17465 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00148 | 0.00247 | 0.00237 | 0.00050 | 0.00060 | 0.00058 | 0.00799 |
| 2 | 0.00000 | 0.00179 | 0.00451 | 0.00315 | 0.00038 | 0.00047 | 0.00086 | 0.01117 |
| 3 | 0.00000 | 0.00198 | 0.00214 | 0.00177 | 0.00037 | 0.00050 | 0.00037 | 0.00714 |
| 4 | 0.00000 | 0.00257 | 0.00256 | 0.00237 | 0.00048 | 0.00057 | 0.00047 | 0.00901 |
| 5 | 0.00000 | 0.00214 | 0.00251 | 0.00223 | 0.00047 | 0.00059 | 0.00045 | 0.00839 |
| 6 | 0.00000 | 0.00213 | 0.00230 | 0.00232 | 0.00044 | 0.00058 | 0.00046 | 0.00823 |
| 7 | 0.00000 | 0.00202 | 0.00230 | 0.00191 | 0.00044 | 0.00053 | 0.00042 | 0.00762 |
| 8 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 2 | quality:repetition ×9 | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | không | 0 | 0 | — | 0 | LLM_REQUEST_INVALID |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 7/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 7–9 | 7 | đúng khoảng |
| 2 | 4–6 | 4 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 4 | đúng khoảng |
| 2 | 3–10 | 5 | đúng khoảng |
| 3 | 4–12 | 4 | đúng khoảng |
| 4 | 5–12 | 5 | đúng khoảng |
