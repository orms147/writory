# Chạy cả truyện: long-tu-tien-3

- Commit `7592dfca698f93ed3a8de283019f0949a350b3fd`; đề v1 (`ed0e1a5be3d9`); config `fa18bc12ad63`; seed 20261022; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 17/24 (kế hoạch 24).
- Dừng: error ở chapter 18 (RETRY_LIMIT_REACHED).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.2152 USD (trần --budget: 0.35); ước tính cho lời gọi không rõ chi phí: 0.0545 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0123, lượt chương đắt nhất 0.0185.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 1; tự bấm thử lại: setup ×0, chapter ×2, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 17, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:early_reveal ×3, guard:teller_does_not_know ×4. Còn lại khi hiện: guard:teller_does_not_know ×1.
- Cạnh bộ trích bỏ: 9 (Fact mới ×3, câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×2, trùng Fact ×3).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 18 | 0.01572 | 86008 | 11395 |
| extract | 40 | 0.06962 | 506845 | 35186 |
| moderate | 57 | 0.00909 | 119422 | 5438 |
| outline | 44 | 0.05670 | 264934 | 50083 |
| setup | 4 | 0.00371 | 7368 | 5622 |
| summary | 17 | 0.00689 | 38168 | 4240 |
| writer | 40 | 0.05350 | 351966 | 38702 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00371 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00371 |
| 1 | 0.00000 | 0.00224 | 0.00264 | 0.00292 | 0.00042 | 0.00060 | 0.00076 | 0.00958 |
| 2 | 0.00000 | 0.00248 | 0.00248 | 0.00235 | 0.00043 | 0.00066 | 0.00041 | 0.00881 |
| 3 | 0.00000 | 0.00436 | 0.00681 | 0.00641 | 0.00038 | 0.00080 | 0.00098 | 0.01975 |
| 4 | 0.00000 | 0.00264 | 0.00282 | 0.00262 | 0.00046 | 0.00083 | 0.00054 | 0.00991 |
| 5 | 0.00000 | 0.00287 | 0.00422 | 0.00452 | 0.00043 | 0.00084 | 0.00064 | 0.01353 |
| 6 | 0.00000 | 0.01104 | 0.00275 | 0.00300 | 0.00042 | 0.00079 | 0.00051 | 0.01851 |
| 7 | 0.00000 | 0.00276 | 0.00264 | 0.00320 | 0.00039 | 0.00083 | 0.00044 | 0.01027 |
| 8 | 0.00000 | 0.00273 | 0.00268 | 0.00345 | 0.00040 | 0.00083 | 0.00041 | 0.01050 |
| 9 | 0.00000 | 0.00264 | 0.00385 | 0.00539 | 0.00037 | 0.00085 | 0.00056 | 0.01367 |
| 10 | 0.00000 | 0.00277 | 0.00275 | 0.00379 | 0.00041 | 0.00072 | 0.00046 | 0.01090 |
| 11 | 0.00000 | 0.00272 | 0.00269 | 0.00406 | 0.00039 | 0.00098 | 0.00040 | 0.01125 |
| 12 | 0.00000 | 0.00272 | 0.00283 | 0.00386 | 0.00043 | 0.00101 | 0.00049 | 0.01134 |
| 13 | 0.00000 | 0.00273 | 0.00263 | 0.00397 | 0.00037 | 0.00106 | 0.00041 | 0.01117 |
| 14 | 0.00000 | 0.00305 | 0.00277 | 0.00441 | 0.00040 | 0.00112 | 0.00042 | 0.01218 |
| 15 | 0.00000 | 0.00257 | 0.00246 | 0.00439 | 0.00039 | 0.00106 | 0.00048 | 0.01133 |
| 16 | 0.00000 | 0.00260 | 0.00255 | 0.00434 | 0.00041 | 0.00154 | 0.00049 | 0.01193 |
| 17 | 0.00000 | 0.00252 | 0.00264 | 0.00451 | 0.00040 | 0.00120 | 0.00047 | 0.01174 |
| 18 | 0.00000 | 0.00125 | 0.00128 | 0.00242 | 0.00000 | 0.00000 | 0.00020 | 0.00515 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | không | 1 | 1 | guard:early_reveal ×3 | 0 | — |
| 3 | 2 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 1 | — |
| 8 | 1 | có | 2 | 0 | — | 2 | — |
| 9 | 1 | có | 2 | 1 | guard:teller_does_not_know ×3 | 1 | — |
| 10 | 1 | có | 2 | 0 | — | 0 | — |
| 11 | 1 | có | 2 | 0 | — | 4 | — |
| 12 | 1 | có | 2 | 0 | — | 0 | — |
| 13 | 1 | có | 2 | 0 | — | 0 | — |
| 14 | 1 | có | 2 | 0 | — | 0 | — |
| 15 | 1 | có | 2 | 0 | — | 0 | — |
| 16 | 1 | có | 2 | 0 | — | 1 | — |
| 17 | 1 | có | 2 | 0 | — | 0 | — |
| 18 | 1 | không | 1 | 0 | — | 0 | RETRY_LIMIT_REACHED |
| 18 | 2 | không | 0 | 0 | — | 0 | RETRY_LIMIT_REACHED |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 17/24.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–8 | 6 | đúng khoảng |
| 2 | 11–13 | 11 | đúng khoảng |
| 3 | 9–11 | 9 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–24 | 4 | đúng khoảng |
| 2 | 3–8 | 6 | đúng khoảng |
| 3 | 5–11 | 5 | đúng khoảng |
| 4 | 7–13 | 11 | đúng khoảng |
| 5 | 8–12 | 8 | đúng khoảng |
| 6 | 14–19 | 14 | đúng khoảng |
| 7 | 16–22 | 16 | đúng khoảng |
