# Chạy cả truyện: ab-ky-ao-v3-1

- Commit `7d2d8d2980d314fe1321458320468463576ff3d2`; đề v1 (`7b1d86e0688f`); config `ae4829a623f7`; seed 20261029; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 7).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0544 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0058, lượt chương đắt nhất 0.0129.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 6, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×8. Còn lại khi hiện: guard:teller_does_not_know ×3.
- Cạnh bộ trích bỏ: 13 (Fact mới ×6, câu trích không có nguyên văn trong chương (G3) ×5, sai schema cạnh ×1, thiếu KNOWS ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 6 | 0.00418 | 17651 | 3942 |
| extract | 15 | 0.01706 | 111352 | 14989 |
| moderate | 21 | 0.00283 | 40988 | 1940 |
| outline | 12 | 0.01324 | 61231 | 11179 |
| summary | 6 | 0.00204 | 11184 | 1277 |
| writer | 15 | 0.01509 | 111030 | 11484 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00193 | 0.00186 | 0.00229 | 0.00036 | 0.00059 | 0.00042 | 0.00744 |
| 2 | 0.00000 | 0.00213 | 0.00173 | 0.00172 | 0.00032 | 0.00067 | 0.00042 | 0.00698 |
| 3 | 0.00000 | 0.00224 | 0.00417 | 0.00480 | 0.00034 | 0.00065 | 0.00068 | 0.01289 |
| 4 | 0.00000 | 0.00226 | 0.00313 | 0.00337 | 0.00033 | 0.00065 | 0.00052 | 0.01026 |
| 5 | 0.00000 | 0.00243 | 0.00211 | 0.00252 | 0.00035 | 0.00073 | 0.00040 | 0.00854 |
| 6 | 0.00000 | 0.00226 | 0.00210 | 0.00236 | 0.00033 | 0.00088 | 0.00038 | 0.00832 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 3 | — |
| 2 | 1 | có | 2 | 0 | — | 1 | — |
| 3 | 1 | có | 2 | 2 | guard:teller_does_not_know ×5 | 8 | — |
| 4 | 1 | có | 2 | 1 | guard:teller_does_not_know ×3 | 1 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/7.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 4 | đúng khoảng |
| 2 | 4–5 | 4 | đúng khoảng |
| 3 | 5–6 | 5 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–2 | 1 | đúng khoảng |
| 2 | 3–4 | 3 | đúng khoảng |
| 3 | 3–5 | 4 | đúng khoảng |
| 4 | 5–6 | 5 | đúng khoảng |
| 5 | 6–7 | 6 | đúng khoảng |
