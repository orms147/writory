# Chạy cả truyện: long-after-ky-ao

- Commit `905069683ef090b39d245ae6b6f279f5018dbb6e`; đề v1 (`58fecaaeebc4`); config `7ae6b42b412d`; seed 20261031; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 11/24 (kế hoạch 24).
- Dừng: error ở chapter 12 (RETRY_LIMIT_REACHED).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.1078 USD (trần --budget: 0.35); ước tính cho lời gọi không rõ chi phí: 0.0545 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0067, lượt chương đắt nhất 0.0126.
- Viết lại: 2; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×1, choices ×1.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 11, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×1, quality:repetition ×1. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 4 (câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×3).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 13 | 0.00919 | 46692 | 8777 |
| extract | 25 | 0.03397 | 253994 | 21657 |
| moderate | 35 | 0.00488 | 70614 | 2999 |
| outline | 27 | 0.02766 | 139254 | 20519 |
| summary | 11 | 0.00422 | 23756 | 2511 |
| writer | 28 | 0.02786 | 187856 | 21388 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00192 | 0.00194 | 0.00190 | 0.00035 | 0.00053 | 0.00040 | 0.00705 |
| 2 | 0.00000 | 0.00215 | 0.00202 | 0.00235 | 0.00040 | 0.00064 | 0.00042 | 0.00800 |
| 3 | 0.00000 | 0.00228 | 0.00218 | 0.00228 | 0.00041 | 0.00062 | 0.00040 | 0.00816 |
| 4 | 0.00000 | 0.00264 | 0.00233 | 0.00248 | 0.00039 | 0.00073 | 0.00045 | 0.00903 |
| 5 | 0.00000 | 0.00226 | 0.00354 | 0.00377 | 0.00039 | 0.00067 | 0.00056 | 0.01119 |
| 6 | 0.00000 | 0.00226 | 0.00219 | 0.00235 | 0.00034 | 0.00072 | 0.00034 | 0.00820 |
| 7 | 0.00000 | 0.00231 | 0.00227 | 0.00284 | 0.00038 | 0.00089 | 0.00040 | 0.00909 |
| 8 | 0.00000 | 0.00240 | 0.00222 | 0.00298 | 0.00036 | 0.00088 | 0.00042 | 0.00927 |
| 9 | 0.00000 | 0.00246 | 0.00236 | 0.00315 | 0.00040 | 0.00081 | 0.00041 | 0.00959 |
| 10 | 0.00000 | 0.00233 | 0.00237 | 0.00315 | 0.00047 | 0.00172 | 0.00037 | 0.01041 |
| 11 | 0.00000 | 0.00235 | 0.00344 | 0.00501 | 0.00034 | 0.00098 | 0.00052 | 0.01264 |
| 12 | 0.00000 | 0.00230 | 0.00099 | 0.00170 | 0.00000 | 0.00000 | 0.00018 | 0.00517 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 1 | — |
| 5 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | có | 2 | 0 | — | 0 | — |
| 10 | 1 | có | 2 | 0 | — | 1 | RETRY_LIMIT_REACHED |
| 11 | 1 | có | 2 | 1 | quality:repetition ×1 | 2 | — |
| 12 | 1 | không | 1 | 0 | — | 0 | RETRY_LIMIT_REACHED |
| 12 | 2 | không | 0 | 0 | — | 0 | RETRY_LIMIT_REACHED |

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
| 1 | 4–8 | 4 | đúng khoảng |
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
| 5 | 13–15 | 9 | sớm |
| 6 | 16–18 | — | chưa tới hạn |
| 7 | 20–23 | — | chưa tới hạn |
| 8 | 24–24 | — | chưa tới hạn |
