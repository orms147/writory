# Chạy cả truyện: ab-trinh-tham-v3-2

- Commit `7d2d8d2980d314fe1321458320468463576ff3d2`; đề v1 (`a0997a5fc137`); config `ae4829a623f7`; seed 20261030; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0492 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0092 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0055, lượt chương đắt nhất 0.0100.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_secret ×1, quality:repetition ×1. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 5 (Fact mới ×3, câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00350 | 14894 | 3288 |
| extract | 15 | 0.01539 | 107631 | 13371 |
| moderate | 19 | 0.00258 | 37755 | 1591 |
| outline | 12 | 0.01199 | 59311 | 9924 |
| summary | 5 | 0.00178 | 9732 | 1126 |
| writer | 14 | 0.01399 | 101012 | 11191 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00149 | 0.00185 | 0.00213 | 0.00036 | 0.00072 | 0.00040 | 0.00695 |
| 2 | 0.00000 | 0.00198 | 0.00177 | 0.00199 | 0.00033 | 0.00065 | 0.00034 | 0.00706 |
| 3 | 0.00000 | 0.00209 | 0.00195 | 0.00216 | 0.00037 | 0.00065 | 0.00042 | 0.00764 |
| 4 | 0.00000 | 0.00218 | 0.00211 | 0.00221 | 0.00037 | 0.00084 | 0.00043 | 0.00814 |
| 5 | 0.00000 | 0.00220 | 0.00324 | 0.00299 | 0.00035 | 0.00065 | 0.00052 | 0.00995 |
| 6 | 0.00000 | 0.00204 | 0.00308 | 0.00390 | 0.00000 | 0.00000 | 0.00047 | 0.00949 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 1 | guard:overdue_secret ×1 | 4 | — |
| 6 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 5–5 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–6 | 5 | đúng khoảng |
| 2 | 2–4 | 3 | đúng khoảng |
| 3 | 2–5 | 4 | đúng khoảng |
| 4 | 3–6 | 3 | đúng khoảng |
