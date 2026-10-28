# Chạy cả truyện: ab-trinh-tham-cu-1

- Commit `51a13a8328827f66c018e6e9e9eead9ac902885d` (có sửa chưa commit); đề v1 (`a0997a5fc137`); config `1b9db7f9197d`; seed 20261030; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0475 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0060, lượt chương đắt nhất 0.0107.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_secret ×1, guard:teller_does_not_know ×1. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 15 (Fact mới ×3, câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×5, thiếu KNOWS ×1, trùng Fact ×5).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00281 | 14162 | 2071 |
| extract | 14 | 0.01545 | 101238 | 13724 |
| moderate | 19 | 0.00259 | 38305 | 1484 |
| outline | 12 | 0.01086 | 54922 | 7989 |
| summary | 5 | 0.00184 | 10435 | 1062 |
| writer | 14 | 0.01397 | 81364 | 11803 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00165 | 0.00196 | 0.00228 | 0.00041 | 0.00051 | 0.00044 | 0.00725 |
| 2 | 0.00000 | 0.00170 | 0.00176 | 0.00219 | 0.00033 | 0.00054 | 0.00036 | 0.00687 |
| 3 | 0.00000 | 0.00185 | 0.00186 | 0.00201 | 0.00034 | 0.00051 | 0.00037 | 0.00693 |
| 4 | 0.00000 | 0.00185 | 0.00193 | 0.00219 | 0.00036 | 0.00058 | 0.00040 | 0.00731 |
| 5 | 0.00000 | 0.00200 | 0.00354 | 0.00345 | 0.00038 | 0.00067 | 0.00061 | 0.01065 |
| 6 | 0.00000 | 0.00182 | 0.00291 | 0.00335 | 0.00000 | 0.00000 | 0.00042 | 0.00849 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 3 | — |
| 2 | 1 | có | 2 | 0 | — | 4 | — |
| 3 | 1 | có | 2 | 0 | — | 4 | — |
| 4 | 1 | có | 2 | 0 | — | 1 | — |
| 5 | 1 | có | 2 | 1 | guard:overdue_secret ×1 | 0 | — |
| 6 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 3 | — |

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
| 4 | 3–6 | 4 | đúng khoảng |
