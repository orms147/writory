# Chạy cả truyện: ky-ao-vua-1

- Commit `123873e69c15b055d6b4d24171ad77f2864e08b8`; đề v1 (`6aeab8e2624b`); config `190f06005a6c`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0972 USD (trần --budget: 0.6); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0059, lượt chương đắt nhất 0.0130.
- Viết lại: 8; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:overdue_thread ×17, guard:sudden_relationship ×1, guard:teller_does_not_know ×9, quality:repetition ×3. Còn lại khi hiện: guard:overdue_thread ×8, guard:sudden_relationship ×1, guard:teller_does_not_know ×5, quality:repetition ×2.
- Cạnh bộ trích bỏ: 2 (sai schema cạnh ×2).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 10 | 0.00481 | 25136 | 3335 |
| extract | 28 | 0.02638 | 168318 | 18513 |
| moderate | 38 | 0.00648 | 84097 | 3045 |
| outline | 20 | 0.01895 | 89604 | 15507 |
| setup | 4 | 0.00340 | 7205 | 5047 |
| summary | 10 | 0.00433 | 25371 | 2325 |
| writer | 28 | 0.03288 | 171494 | 31003 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00340 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00340 |
| 1 | 0.00000 | 0.00165 | 0.00222 | 0.00224 | 0.00041 | 0.00045 | 0.00074 | 0.00771 |
| 2 | 0.00000 | 0.00178 | 0.00207 | 0.00146 | 0.00041 | 0.00051 | 0.00046 | 0.00670 |
| 3 | 0.00000 | 0.00193 | 0.00204 | 0.00150 | 0.00038 | 0.00042 | 0.00040 | 0.00667 |
| 4 | 0.00000 | 0.00193 | 0.00379 | 0.00270 | 0.00047 | 0.00038 | 0.00070 | 0.00997 |
| 5 | 0.00000 | 0.00199 | 0.00215 | 0.00159 | 0.00041 | 0.00046 | 0.00042 | 0.00702 |
| 6 | 0.00000 | 0.00194 | 0.00466 | 0.00352 | 0.00041 | 0.00054 | 0.00078 | 0.01184 |
| 7 | 0.00000 | 0.00191 | 0.00372 | 0.00293 | 0.00047 | 0.00046 | 0.00076 | 0.01025 |
| 8 | 0.00000 | 0.00196 | 0.00344 | 0.00310 | 0.00043 | 0.00054 | 0.00059 | 0.01005 |
| 9 | 0.00000 | 0.00190 | 0.00507 | 0.00408 | 0.00047 | 0.00057 | 0.00093 | 0.01302 |
| 10 | 0.00000 | 0.00197 | 0.00372 | 0.00328 | 0.00046 | 0.00047 | 0.00069 | 0.01059 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 2 | guard:teller_does_not_know ×4, guard:overdue_thread ×2 | 1 | — |
| 7 | 1 | có | 2 | 1 | guard:overdue_thread ×2, guard:teller_does_not_know ×1 | 0 | — |
| 8 | 1 | có | 2 | 1 | guard:overdue_thread ×4, guard:teller_does_not_know ×2 | 0 | — |
| 9 | 1 | có | 2 | 2 | guard:teller_does_not_know ×2, guard:overdue_thread ×4, quality:repetition ×1, guard:sudden_relationship ×1 | 0 | — |
| 10 | 1 | có | 2 | 1 | guard:overdue_thread ×5, quality:repetition ×1 | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 6–7 | 6 | đúng khoảng |
| 2 | 8–9 | 8 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | — | chưa có, đã quá hạn |
| 2 | 1–5 | 1 | đúng khoảng |
| 3 | 4–8 | 10 | trễ |
| 4 | 6–10 | — | chưa có, đã quá hạn |
| 5 | 7–12 | — | chưa tới hạn |
