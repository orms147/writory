# Chạy cả truyện: psab-b1

- Commit `d9a196a63bcde0a3381da2873ac70272b2b559fd`; đề v1 (`58fecaaeebc4`); config `e41337d6de42`; seed 20261031; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 11/16 (kế hoạch 24).
- Dừng: error ở chapter 12 (INTERNAL_ERROR).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.1127 USD (trần --budget: 0.25); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0077, lượt chương đắt nhất 0.0143.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 11, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×2, quality:repetition ×1. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 9 (sai schema cạnh ×4, thiếu KNOWS ×2, trùng Fact ×3).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 12 | 0.00911 | 45944 | 7645 |
| extract | 25 | 0.03666 | 265732 | 24101 |
| moderate | 36 | 0.00533 | 76228 | 2839 |
| outline | 22 | 0.02611 | 133810 | 19667 |
| summary | 11 | 0.00466 | 27033 | 2563 |
| writer | 25 | 0.03085 | 196185 | 25286 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00155 | 0.00234 | 0.00239 | 0.00047 | 0.00069 | 0.00045 | 0.00789 |
| 2 | 0.00000 | 0.00230 | 0.00346 | 0.00340 | 0.00038 | 0.00071 | 0.00056 | 0.01081 |
| 3 | 0.00000 | 0.00236 | 0.00228 | 0.00262 | 0.00042 | 0.00078 | 0.00042 | 0.00888 |
| 4 | 0.00000 | 0.00250 | 0.00239 | 0.00252 | 0.00039 | 0.00072 | 0.00043 | 0.00895 |
| 5 | 0.00000 | 0.00245 | 0.00257 | 0.00287 | 0.00044 | 0.00077 | 0.00043 | 0.00954 |
| 6 | 0.00000 | 0.00232 | 0.00254 | 0.00292 | 0.00045 | 0.00115 | 0.00047 | 0.00985 |
| 7 | 0.00000 | 0.00239 | 0.00239 | 0.00277 | 0.00038 | 0.00080 | 0.00040 | 0.00914 |
| 8 | 0.00000 | 0.00240 | 0.00362 | 0.00504 | 0.00039 | 0.00079 | 0.00053 | 0.01277 |
| 9 | 0.00000 | 0.00248 | 0.00264 | 0.00340 | 0.00045 | 0.00091 | 0.00052 | 0.01039 |
| 10 | 0.00000 | 0.00256 | 0.00260 | 0.00328 | 0.00046 | 0.00088 | 0.00046 | 0.01023 |
| 11 | 0.00000 | 0.00280 | 0.00403 | 0.00545 | 0.00043 | 0.00089 | 0.00066 | 0.01426 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 1 | — |
| 3 | 1 | có | 2 | 0 | — | 1 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 2 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 1 | quality:repetition ×1 | 2 | — |
| 9 | 1 | có | 2 | 0 | — | 2 | — |
| 10 | 1 | có | 2 | 0 | — | 0 | — |
| 11 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 1 | — |
| 12 | 1 | không | 0 | 0 | — | 0 | INTERNAL_ERROR |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 11/24.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 5–8 | 5 | đúng khoảng |
| 2 | 11–15 | 11 | đúng khoảng |
| 3 | 16–20 | — | chưa tới hạn |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 4–8 | 5 | đúng khoảng |
| 2 | 1–5 | 1 | đúng khoảng |
| 3 | 7–11 | 7 | đúng khoảng |
| 4 | 12–16 | — | chưa tới hạn |
| 5 | 13–17 | — | chưa tới hạn |
| 6 | 18–22 | — | chưa tới hạn |
| 7 | 19–24 | — | chưa tới hạn |

| Mốc | Khoảng | Xảy ra ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–2 | 1 | đúng khoảng |
| 2 | 4–6 | 2 | sớm |
| 3 | 7–9 | 3 | sớm |
| 4 | 10–12 | 7 | sớm |
| 5 | 13–15 | 11 | sớm |
| 6 | 16–18 | — | chưa tới hạn |
| 7 | 20–23 | — | chưa tới hạn |
| 8 | 24–24 | — | chưa tới hạn |
