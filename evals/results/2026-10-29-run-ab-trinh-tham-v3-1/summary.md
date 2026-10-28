# Chạy cả truyện: ab-trinh-tham-v3-1

- Commit `7d2d8d2980d314fe1321458320468463576ff3d2`; đề v1 (`a0997a5fc137`); config `ae4829a623f7`; seed 20261030; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0493 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0062, lượt chương đắt nhất 0.0110.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_secret ×1, guard:teller_does_not_know ×1. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 4 (câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×1, trùng Fact ×1, trùng cạnh trong cùng gói ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00309 | 14188 | 2626 |
| extract | 14 | 0.01602 | 103192 | 14383 |
| moderate | 19 | 0.00247 | 36739 | 1642 |
| outline | 12 | 0.01256 | 59429 | 10261 |
| summary | 5 | 0.00164 | 9055 | 1017 |
| writer | 14 | 0.01349 | 100869 | 10219 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00174 | 0.00176 | 0.00198 | 0.00035 | 0.00054 | 0.00041 | 0.00677 |
| 2 | 0.00000 | 0.00211 | 0.00184 | 0.00191 | 0.00032 | 0.00057 | 0.00036 | 0.00712 |
| 3 | 0.00000 | 0.00212 | 0.00186 | 0.00215 | 0.00034 | 0.00069 | 0.00042 | 0.00757 |
| 4 | 0.00000 | 0.00223 | 0.00187 | 0.00222 | 0.00029 | 0.00060 | 0.00036 | 0.00757 |
| 5 | 0.00000 | 0.00227 | 0.00324 | 0.00389 | 0.00034 | 0.00069 | 0.00053 | 0.01096 |
| 6 | 0.00000 | 0.00209 | 0.00291 | 0.00387 | 0.00000 | 0.00000 | 0.00041 | 0.00928 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 1 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 1 | guard:overdue_secret ×1 | 0 | — |
| 6 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 2 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 4 | đúng khoảng |
| 2 | 5–5 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–6 | 4 | đúng khoảng |
| 2 | 2–4 | 3 | đúng khoảng |
| 3 | 2–5 | 4 | đúng khoảng |
| 4 | 3–6 | 3 | đúng khoảng |
