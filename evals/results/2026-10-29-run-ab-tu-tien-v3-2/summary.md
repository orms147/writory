# Chạy cả truyện: ab-tu-tien-v3-2

- Commit `7d2d8d2980d314fe1321458320468463576ff3d2`; đề v1 (`42aeb39100b7`); config `ae4829a623f7`; seed 20261028; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0635 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0067, lượt chương đắt nhất 0.0148.
- Viết lại: 5; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×6, quality:repetition ×1. Còn lại khi hiện: guard:teller_does_not_know ×2.
- Cạnh bộ trích bỏ: 12 (Fact mới ×2, câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×4, thiếu KNOWS ×4, trùng Fact ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00360 | 15143 | 3424 |
| extract | 17 | 0.02097 | 138594 | 17170 |
| moderate | 22 | 0.00363 | 46772 | 2324 |
| outline | 13 | 0.01357 | 68278 | 11667 |
| summary | 5 | 0.00199 | 11459 | 1120 |
| writer | 17 | 0.01970 | 133383 | 16325 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00195 | 0.00206 | 0.00177 | 0.00038 | 0.00057 | 0.00042 | 0.00716 |
| 2 | 0.00000 | 0.00231 | 0.00227 | 0.00227 | 0.00044 | 0.00068 | 0.00050 | 0.00847 |
| 3 | 0.00000 | 0.00231 | 0.00362 | 0.00382 | 0.00043 | 0.00084 | 0.00076 | 0.01178 |
| 4 | 0.00000 | 0.00252 | 0.00504 | 0.00533 | 0.00037 | 0.00074 | 0.00077 | 0.01477 |
| 5 | 0.00000 | 0.00232 | 0.00349 | 0.00381 | 0.00038 | 0.00077 | 0.00065 | 0.01142 |
| 6 | 0.00000 | 0.00215 | 0.00323 | 0.00396 | 0.00000 | 0.00000 | 0.00052 | 0.00986 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 3 | — |
| 4 | 1 | có | 2 | 2 | guard:teller_does_not_know ×3 | 4 | — |
| 5 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 2 | — |
| 6 | 1 | có | 2 | 1 | quality:repetition ×1 | 3 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 4–5 | 4 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 4–6 | 4 | đúng khoảng |
| 3 | 5–6 | 6 | đúng khoảng |
| 4 | 3–5 | 4 | đúng khoảng |
