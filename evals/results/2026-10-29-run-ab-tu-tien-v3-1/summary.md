# Chạy cả truyện: ab-tu-tien-v3-1

- Commit `7d2d8d2980d314fe1321458320468463576ff3d2`; đề v1 (`42aeb39100b7`); config `ae4829a623f7`; seed 20261028; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0627 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0062, lượt chương đắt nhất 0.0128.
- Viết lại: 5; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×4, leak:name ×1, quality:repetition ×2. Còn lại khi hiện: guard:teller_does_not_know ×1.
- Cạnh bộ trích bỏ: 12 (Fact mới ×4, câu trích không có nguyên văn trong chương (G3) ×2, known_as là tên của nút khác ×1, sai schema cạnh ×1, thiếu KNOWS ×4).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00344 | 15332 | 3056 |
| extract | 17 | 0.02168 | 140664 | 18074 |
| moderate | 22 | 0.00321 | 44063 | 2155 |
| outline | 12 | 0.01355 | 67128 | 10330 |
| summary | 5 | 0.00187 | 10222 | 1178 |
| writer | 17 | 0.01894 | 135985 | 13566 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00200 | 0.00340 | 0.00342 | 0.00036 | 0.00058 | 0.00054 | 0.01029 |
| 2 | 0.00000 | 0.00217 | 0.00308 | 0.00312 | 0.00036 | 0.00062 | 0.00053 | 0.00988 |
| 3 | 0.00000 | 0.00247 | 0.00243 | 0.00304 | 0.00042 | 0.00076 | 0.00044 | 0.00955 |
| 4 | 0.00000 | 0.00231 | 0.00356 | 0.00385 | 0.00038 | 0.00070 | 0.00063 | 0.01142 |
| 5 | 0.00000 | 0.00232 | 0.00222 | 0.00258 | 0.00035 | 0.00078 | 0.00050 | 0.00876 |
| 6 | 0.00000 | 0.00228 | 0.00427 | 0.00568 | 0.00000 | 0.00000 | 0.00057 | 0.01279 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | leak:name ×1 | 1 | — |
| 2 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 2 | — |
| 3 | 1 | có | 2 | 0 | — | 1 | — |
| 4 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 2 | guard:teller_does_not_know ×3 | 8 | — |

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
| 4 | 3–5 | 3 | đúng khoảng |
