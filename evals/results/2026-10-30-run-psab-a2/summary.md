# Chạy cả truyện: psab-a2

- Commit `d9a196a63bcde0a3381da2873ac70272b2b559fd`; đề v1 (`58fecaaeebc4`); config `e2c8343b233c`; seed 20261031; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 16/16 (kế hoạch 24).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.1680 USD (trần --budget: 0.25); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0075, lượt chương đắt nhất 0.0136.
- Viết lại: 5; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 16, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:at_most_one ×2, guard:teller_does_not_know ×5. Còn lại khi hiện: guard:teller_does_not_know ×2.
- Cạnh bộ trích bỏ: 25 (Fact mới ×6, câu trích không có nguyên văn trong chương (G3) ×2, lộ bí mật hay tên đang giấu (G2) ×2, sai schema cạnh ×9, thiếu KNOWS ×2, trùng Fact ×4).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 17 | 0.01228 | 65489 | 9265 |
| extract | 37 | 0.05532 | 404605 | 34964 |
| moderate | 53 | 0.00801 | 110307 | 4984 |
| outline | 32 | 0.03955 | 200743 | 29820 |
| summary | 16 | 0.00673 | 37528 | 4088 |
| writer | 37 | 0.04606 | 299484 | 35442 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00158 | 0.00211 | 0.00239 | 0.00037 | 0.00062 | 0.00048 | 0.00756 |
| 2 | 0.00000 | 0.00250 | 0.00242 | 0.00239 | 0.00050 | 0.00073 | 0.00053 | 0.00907 |
| 3 | 0.00000 | 0.00237 | 0.00224 | 0.00251 | 0.00038 | 0.00065 | 0.00043 | 0.00858 |
| 4 | 0.00000 | 0.00252 | 0.00246 | 0.00250 | 0.00040 | 0.00065 | 0.00040 | 0.00894 |
| 5 | 0.00000 | 0.00267 | 0.00259 | 0.00250 | 0.00044 | 0.00076 | 0.00045 | 0.00941 |
| 6 | 0.00000 | 0.00240 | 0.00405 | 0.00405 | 0.00047 | 0.00067 | 0.00065 | 0.01229 |
| 7 | 0.00000 | 0.00242 | 0.00433 | 0.00405 | 0.00042 | 0.00073 | 0.00064 | 0.01259 |
| 8 | 0.00000 | 0.00269 | 0.00380 | 0.00451 | 0.00051 | 0.00086 | 0.00059 | 0.01296 |
| 9 | 0.00000 | 0.00250 | 0.00249 | 0.00270 | 0.00041 | 0.00075 | 0.00041 | 0.00927 |
| 10 | 0.00000 | 0.00262 | 0.00256 | 0.00318 | 0.00043 | 0.00080 | 0.00048 | 0.01007 |
| 11 | 0.00000 | 0.00241 | 0.00355 | 0.00478 | 0.00038 | 0.00084 | 0.00062 | 0.01258 |
| 12 | 0.00000 | 0.00264 | 0.00250 | 0.00348 | 0.00040 | 0.00084 | 0.00041 | 0.01028 |
| 13 | 0.00000 | 0.00267 | 0.00254 | 0.00347 | 0.00042 | 0.00079 | 0.00041 | 0.01030 |
| 14 | 0.00000 | 0.00256 | 0.00246 | 0.00342 | 0.00042 | 0.00074 | 0.00039 | 0.00998 |
| 15 | 0.00000 | 0.00249 | 0.00248 | 0.00367 | 0.00041 | 0.00088 | 0.00052 | 0.01046 |
| 16 | 0.00000 | 0.00251 | 0.00348 | 0.00571 | 0.00036 | 0.00097 | 0.00060 | 0.01363 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 1 | — |
| 3 | 1 | có | 2 | 0 | — | 2 | — |
| 4 | 1 | có | 2 | 0 | — | 3 | — |
| 5 | 1 | có | 2 | 0 | — | 6 | — |
| 6 | 1 | có | 2 | 1 | guard:at_most_one ×1 | 2 | — |
| 7 | 1 | có | 2 | 1 | guard:at_most_one ×1 | 0 | — |
| 8 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 1 | — |
| 9 | 1 | có | 2 | 0 | — | 0 | — |
| 10 | 1 | có | 2 | 0 | — | 1 | — |
| 11 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 5 | — |
| 12 | 1 | có | 2 | 0 | — | 0 | — |
| 13 | 1 | có | 2 | 0 | — | 0 | — |
| 14 | 1 | có | 2 | 0 | — | 1 | — |
| 15 | 1 | có | 2 | 0 | — | 2 | — |
| 16 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 1 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 16/24.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 5–8 | 5 | đúng khoảng |
| 2 | 11–15 | 13 | đúng khoảng |
| 3 | 16–20 | 16 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 4–8 | 6 | đúng khoảng |
| 2 | 1–5 | 2 | đúng khoảng |
| 3 | 7–11 | 7 | đúng khoảng |
| 4 | 12–16 | 12 | đúng khoảng |
| 5 | 13–17 | 13 | đúng khoảng |
| 6 | 18–22 | — | chưa tới hạn |
| 7 | 19–24 | — | chưa tới hạn |

| Mốc | Khoảng | Xảy ra ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–2 | 1 | đúng khoảng |
| 2 | 4–6 | 3 | sớm |
| 3 | 7–9 | 3 | sớm |
| 4 | 10–12 | 7 | sớm |
| 5 | 13–15 | 10 | sớm |
| 6 | 16–18 | 16 | đúng khoảng |
| 7 | 20–23 | — | chưa tới hạn |
| 8 | 24–24 | — | chưa tới hạn |
