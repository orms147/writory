# Chạy cả truyện: long-tu-tien-1

- Commit `c63765942d36ccb58a8d7f812102ecc20d6142cb`; đề v1 (`b066910518b8`); config `c77187d5ae07`; seed 20261022; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 15/24 (kế hoạch 24).
- Dừng: error ở chapter 16 (INTERNAL_ERROR).
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.1565 USD (trần --budget: 0.4); ước tính cho lời gọi không rõ chi phí: 0.0100 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0072, lượt chương đắt nhất 0.0129.
- Viết lại: 6; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 15, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×7, quality:repetition ×3. Còn lại khi hiện: guard:teller_does_not_know ×2.
- Cạnh bộ trích bỏ: 13 (Fact mới ×5, sai schema cạnh ×1, thiếu KNOWS ×7).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 17 | 0.00960 | 64304 | 5162 |
| extract | 38 | 0.05300 | 389865 | 30171 |
| moderate | 51 | 0.00782 | 107931 | 3894 |
| outline | 32 | 0.03273 | 177477 | 22666 |
| setup | 4 | 0.00357 | 7292 | 5356 |
| summary | 15 | 0.00598 | 34385 | 3376 |
| writer | 37 | 0.04384 | 246202 | 36955 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00357 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00357 |
| 1 | 0.00000 | 0.00177 | 0.00221 | 0.00256 | 0.00042 | 0.00049 | 0.00078 | 0.00823 |
| 2 | 0.00000 | 0.00187 | 0.00370 | 0.00346 | 0.00046 | 0.00057 | 0.00065 | 0.01071 |
| 3 | 0.00000 | 0.00201 | 0.00368 | 0.00346 | 0.00042 | 0.00043 | 0.00065 | 0.01066 |
| 4 | 0.00000 | 0.00214 | 0.00242 | 0.00277 | 0.00042 | 0.00058 | 0.00044 | 0.00877 |
| 5 | 0.00000 | 0.00209 | 0.00366 | 0.00418 | 0.00043 | 0.00065 | 0.00063 | 0.01164 |
| 6 | 0.00000 | 0.00219 | 0.00392 | 0.00435 | 0.00040 | 0.00061 | 0.00062 | 0.01208 |
| 7 | 0.00000 | 0.00206 | 0.00220 | 0.00272 | 0.00037 | 0.00069 | 0.00038 | 0.00842 |
| 8 | 0.00000 | 0.00236 | 0.00236 | 0.00284 | 0.00038 | 0.00068 | 0.00041 | 0.00905 |
| 9 | 0.00000 | 0.00216 | 0.00198 | 0.00318 | 0.00032 | 0.00060 | 0.00038 | 0.00863 |
| 10 | 0.00000 | 0.00219 | 0.00389 | 0.00492 | 0.00042 | 0.00078 | 0.00065 | 0.01285 |
| 11 | 0.00000 | 0.00208 | 0.00221 | 0.00332 | 0.00038 | 0.00077 | 0.00039 | 0.00914 |
| 12 | 0.00000 | 0.00260 | 0.00250 | 0.00383 | 0.00041 | 0.00072 | 0.00042 | 0.01048 |
| 13 | 0.00000 | 0.00208 | 0.00227 | 0.00221 | 0.00039 | 0.00089 | 0.00041 | 0.00823 |
| 14 | 0.00000 | 0.00200 | 0.00353 | 0.00545 | 0.00041 | 0.00086 | 0.00062 | 0.01288 |
| 15 | 0.00000 | 0.00217 | 0.00222 | 0.00374 | 0.00036 | 0.00026 | 0.00040 | 0.00916 |
| 16 | 0.00000 | 0.00096 | 0.00109 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00204 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 0 | — |
| 2 | 1 | có | 2 | 1 | guard:teller_does_not_know ×1 | 1 | — |
| 3 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 2 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 4 | — |
| 6 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | có | 2 | 0 | — | 1 | — |
| 10 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 11 | 1 | có | 2 | 0 | — | 0 | — |
| 12 | 1 | có | 2 | 0 | — | 3 | — |
| 13 | 1 | có | 2 | 0 | — | 0 | — |
| 14 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 2 | — |
| 15 | 1 | có | 2 | 0 | — | 0 | — |
| 16 | 1 | không | 0 | 0 | — | 0 | INTERNAL_ERROR |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 15/24.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 8–10 | 9 | đúng khoảng |
| 2 | 15–17 | — | chưa tới hạn |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–22 | 4 | đúng khoảng |
| 2 | 7–10 | 9 | đúng khoảng |
| 3 | 11–18 | 14 | đúng khoảng |
| 4 | 19–24 | — | chưa tới hạn |
