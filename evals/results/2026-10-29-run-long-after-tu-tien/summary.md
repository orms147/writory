# Chạy cả truyện: long-after-tu-tien

- Commit `905069683ef090b39d245ae6b6f279f5018dbb6e`; đề v1 (`ed0e1a5be3d9`); config `7ae6b42b412d`; seed 20261022; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 21/24 (kế hoạch 24).
- Dừng: budget ở chapter 22 (COST_LIMIT_STORY).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.2969 USD (trần --budget: 0.35); ước tính cho lời gọi không rõ chi phí: 0.0432 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0085, lượt chương đắt nhất 0.0186.
- Viết lại: 11; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 2; tự bấm thử lại: setup ×0, chapter ×3, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 21, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:early_reveal ×9, guard:teller_does_not_know ×15, leak:name ×1, quality:repetition ×1. Còn lại khi hiện: guard:teller_does_not_know ×5.
- Cạnh bộ trích bỏ: 39 (Fact mới ×9, câu trích không có nguyên văn trong chương (G3) ×3, gỡ mạch mà không có câu trích (D-82) ×1, sai schema cạnh ×10, thiếu KNOWS ×4, trùng Fact ×12).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 21 | 0.02038 | 110208 | 13203 |
| extract | 58 | 0.11135 | 830548 | 54301 |
| moderate | 79 | 0.01347 | 169213 | 8450 |
| outline | 53 | 0.06175 | 332230 | 44420 |
| summary | 21 | 0.00966 | 51521 | 6438 |
| writer | 59 | 0.08024 | 522202 | 59239 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00169 | 0.00266 | 0.00330 | 0.00050 | 0.00063 | 0.00077 | 0.00955 |
| 2 | 0.00000 | 0.00237 | 0.00243 | 0.00249 | 0.00041 | 0.00066 | 0.00042 | 0.00879 |
| 3 | 0.00000 | 0.00257 | 0.00422 | 0.00441 | 0.00047 | 0.00073 | 0.00081 | 0.01322 |
| 4 | 0.00000 | 0.00264 | 0.00260 | 0.00271 | 0.00043 | 0.00079 | 0.00047 | 0.00964 |
| 5 | 0.00000 | 0.00284 | 0.00270 | 0.00315 | 0.00044 | 0.00083 | 0.00061 | 0.01059 |
| 6 | 0.00000 | 0.00288 | 0.00287 | 0.00296 | 0.00054 | 0.00081 | 0.00046 | 0.01052 |
| 7 | 0.00000 | 0.00289 | 0.00439 | 0.00439 | 0.00045 | 0.00099 | 0.00067 | 0.01378 |
| 8 | 0.00000 | 0.00503 | 0.00733 | 0.00890 | 0.00050 | 0.00103 | 0.00132 | 0.02411 |
| 9 | 0.00000 | 0.00493 | 0.01022 | 0.01321 | 0.00044 | 0.00103 | 0.00161 | 0.03144 |
| 10 | 0.00000 | 0.00290 | 0.00394 | 0.00551 | 0.00055 | 0.00070 | 0.00063 | 0.01423 |
| 11 | 0.00000 | 0.00268 | 0.00569 | 0.00779 | 0.00045 | 0.00097 | 0.00072 | 0.01831 |
| 12 | 0.00000 | 0.00280 | 0.00272 | 0.00408 | 0.00051 | 0.00104 | 0.00042 | 0.01158 |
| 13 | 0.00000 | 0.00270 | 0.00271 | 0.00388 | 0.00047 | 0.00107 | 0.00047 | 0.01129 |
| 14 | 0.00000 | 0.00274 | 0.00279 | 0.00445 | 0.00045 | 0.00106 | 0.00049 | 0.01198 |
| 15 | 0.00000 | 0.00253 | 0.00284 | 0.00424 | 0.00049 | 0.00116 | 0.00049 | 0.01175 |
| 16 | 0.00000 | 0.00271 | 0.00272 | 0.00450 | 0.00044 | 0.00110 | 0.00046 | 0.01194 |
| 17 | 0.00000 | 0.00256 | 0.00487 | 0.00906 | 0.00036 | 0.00111 | 0.00066 | 0.01862 |
| 18 | 0.00000 | 0.00241 | 0.00242 | 0.00461 | 0.00039 | 0.00109 | 0.00040 | 0.01133 |
| 19 | 0.00000 | 0.00238 | 0.00257 | 0.00500 | 0.00045 | 0.00131 | 0.00045 | 0.01217 |
| 20 | 0.00000 | 0.00250 | 0.00251 | 0.00490 | 0.00046 | 0.00121 | 0.00047 | 0.01206 |
| 21 | 0.00000 | 0.00250 | 0.00258 | 0.00518 | 0.00046 | 0.00103 | 0.00047 | 0.01222 |
| 22 | 0.00000 | 0.00248 | 0.00245 | 0.00261 | 0.00000 | 0.00000 | 0.00018 | 0.00772 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | không | 0 | 0 | — | 0 | RETRY_LIMIT_REACHED |
| 1 | 2 | có | 2 | 0 | — | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 1 | guard:early_reveal ×1 | 1 | — |
| 4 | 1 | có | 2 | 0 | — | 4 | — |
| 5 | 1 | có | 2 | 0 | — | 2 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 8 | 1 | không | 1 | 1 | guard:early_reveal ×4, leak:name ×1 | 10 | — |
| 8 | 2 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | không | 1 | 2 | guard:teller_does_not_know ×4, guard:early_reveal ×4 | 1 | — |
| 9 | 2 | có | 2 | 1 | guard:teller_does_not_know ×2 | 0 | — |
| 10 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 0 | — |
| 11 | 1 | có | 2 | 2 | guard:teller_does_not_know ×3 | 4 | — |
| 12 | 1 | có | 2 | 0 | — | 0 | — |
| 13 | 1 | có | 2 | 0 | — | 0 | — |
| 14 | 1 | có | 2 | 0 | — | 4 | — |
| 15 | 1 | có | 2 | 0 | — | 0 | — |
| 16 | 1 | có | 2 | 0 | — | 0 | — |
| 17 | 1 | có | 2 | 2 | guard:teller_does_not_know ×5 | 5 | — |
| 18 | 1 | có | 2 | 0 | — | 0 | — |
| 19 | 1 | có | 2 | 0 | — | 2 | — |
| 20 | 1 | có | 2 | 0 | — | 0 | — |
| 21 | 1 | có | 2 | 0 | — | 1 | — |
| 22 | 1 | không | 1 | 0 | — | 4 | COST_LIMIT_STORY |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 21/24.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–8 | 6 | đúng khoảng |
| 2 | 11–13 | 11 | đúng khoảng |
| 3 | 9–11 | 11 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–24 | 3 | đúng khoảng |
| 2 | 3–8 | 3 | đúng khoảng |
| 3 | 5–11 | 5 | đúng khoảng |
| 4 | 7–13 | 11 | đúng khoảng |
| 5 | 8–12 | 8 | đúng khoảng |
| 6 | 14–19 | 14 | đúng khoảng |
| 7 | 16–22 | 16 | đúng khoảng |

| Mốc | Khoảng | Xảy ra ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–2 | 1 | đúng khoảng |
| 2 | 4–6 | 3 | sớm |
| 3 | 9–11 | 5 | sớm |
| 4 | 12–13 | 11 | sớm |
| 5 | 16–17 | 15 | sớm |
| 6 | 20–22 | 19 | sớm |
| 7 | 24–24 | — | chưa tới hạn |
