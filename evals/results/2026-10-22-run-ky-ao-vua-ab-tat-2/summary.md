# Chạy cả truyện: ky-ao-vua-ab-tat-2

- Commit `c6db5cc7759d75e43f638d38d16180fbcd7f6894`; đề v1 (`6aeab8e2624b`); config `19b2a28450bf`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 9/10 (kế hoạch 12).
- Dừng: budget ở chapter 10 (COST_LIMIT_STORY).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0912 USD (trần --budget: 0.1); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0061, lượt chương đắt nhất 0.0125.
- Viết lại: 7; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 9, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: quality:repetition ×10. Còn lại khi hiện: quality:repetition ×1.
- Cạnh bộ trích bỏ: 1 (sai schema cạnh ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 9 | 0.00479 | 27496 | 2710 |
| extract | 26 | 0.02522 | 184990 | 13024 |
| moderate | 35 | 0.00564 | 77182 | 2811 |
| outline | 21 | 0.02046 | 104350 | 16569 |
| summary | 9 | 0.00394 | 22846 | 2159 |
| writer | 26 | 0.03111 | 167074 | 28267 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00148 | 0.00385 | 0.00352 | 0.00047 | 0.00056 | 0.00071 | 0.01059 |
| 2 | 0.00000 | 0.00203 | 0.00344 | 0.00258 | 0.00042 | 0.00054 | 0.00060 | 0.00961 |
| 3 | 0.00000 | 0.00207 | 0.00224 | 0.00177 | 0.00041 | 0.00049 | 0.00045 | 0.00744 |
| 4 | 0.00000 | 0.00225 | 0.00272 | 0.00227 | 0.00053 | 0.00068 | 0.00051 | 0.00895 |
| 5 | 0.00000 | 0.00206 | 0.00409 | 0.00284 | 0.00048 | 0.00049 | 0.00073 | 0.01068 |
| 6 | 0.00000 | 0.00209 | 0.00485 | 0.00381 | 0.00043 | 0.00049 | 0.00085 | 0.01252 |
| 7 | 0.00000 | 0.00257 | 0.00211 | 0.00189 | 0.00037 | 0.00049 | 0.00042 | 0.00786 |
| 8 | 0.00000 | 0.00208 | 0.00357 | 0.00295 | 0.00040 | 0.00057 | 0.00064 | 0.01020 |
| 9 | 0.00000 | 0.00189 | 0.00223 | 0.00185 | 0.00043 | 0.00050 | 0.00043 | 0.00734 |
| 10 | 0.00000 | 0.00193 | 0.00201 | 0.00173 | 0.00000 | 0.00000 | 0.00030 | 0.00597 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 2 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 1 | — |
| 5 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 6 | 1 | có | 2 | 2 | quality:repetition ×3 | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 9 | 1 | có | 2 | 0 | — | 0 | — |
| 10 | 1 | không | 1 | 1 | quality:repetition ×1 | 0 | COST_LIMIT_STORY |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 9/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 7–9 | 7 | đúng khoảng |
| 2 | 4–6 | 4 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 4 | đúng khoảng |
| 2 | 3–10 | 3 | đúng khoảng |
| 3 | 4–12 | 5 | đúng khoảng |
| 4 | 5–12 | 1 | sớm |
