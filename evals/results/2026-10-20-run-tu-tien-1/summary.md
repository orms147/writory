# Chạy cả truyện: tu-tien-1

- Commit `9d7b4c6c4a50f4eed14fc3d680fdafc16f6528d5`; đề v1 (`478816434f86`); config `bd738ab0169f`; seed 20261020; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Chi phí: 0.0512 USD (trần --budget: 0.3); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0055, lượt chương đắt nhất 0.0099.
- Viết lại: 5; cảnh bị chặn: 0; tự bấm thử lại: setup ×1, chapter ×0, choices ×0.
- Lỗi tìm thấy: guard:at_most_one ×1, guard:teller_does_not_know ×1, leak:name ×4, quality:repetition ×2. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 2 (câu trích không có nguyên văn trong chương (G3) ×1, sai schema cạnh ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 6 | 0.00249 | 14884 | 1258 |
| extract | 17 | 0.01763 | 114219 | 11345 |
| outline | 12 | 0.00861 | 40674 | 7061 |
| setup | 5 | 0.00629 | 7837 | 11294 |
| writer | 17 | 0.01614 | 81778 | 16368 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | choices | Tổng |
|---|---|---|---|---|---|---|
| 0 | 0.00629 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00629 |
| 1 | 0.00000 | 0.00140 | 0.00371 | 0.00440 | 0.00034 | 0.00985 |
| 2 | 0.00000 | 0.00139 | 0.00288 | 0.00329 | 0.00036 | 0.00793 |
| 3 | 0.00000 | 0.00130 | 0.00174 | 0.00190 | 0.00047 | 0.00541 |
| 4 | 0.00000 | 0.00154 | 0.00291 | 0.00288 | 0.00042 | 0.00776 |
| 5 | 0.00000 | 0.00144 | 0.00163 | 0.00181 | 0.00043 | 0.00531 |
| 6 | 0.00000 | 0.00154 | 0.00328 | 0.00333 | 0.00046 | 0.00862 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 2 | leak:name ×4, guard:teller_does_not_know ×1 | 1 | — |
| 2 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 1 | guard:at_most_one ×1 | 1 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
