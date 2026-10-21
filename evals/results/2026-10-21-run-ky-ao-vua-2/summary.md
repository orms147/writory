# Chạy cả truyện: ky-ao-vua-2

- Commit `0dd03d300b70c38c02c335b20ee44aecdbbc621b`; đề v1 (`6aeab8e2624b`); config `190f06005a6c`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0916 USD (trần --budget: 0.2); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0058, lượt chương đắt nhất 0.0110.
- Viết lại: 4; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:teller_does_not_know ×2, quality:repetition ×8. Còn lại khi hiện: guard:teller_does_not_know ×1, quality:repetition ×2.
- Cạnh bộ trích bỏ: 0 (—).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 10 | 0.00526 | 29010 | 3264 |
| extract | 24 | 0.02509 | 172765 | 15141 |
| moderate | 34 | 0.00551 | 72172 | 2911 |
| outline | 20 | 0.02010 | 100674 | 15033 |
| setup | 4 | 0.00430 | 7194 | 6848 |
| summary | 10 | 0.00419 | 23282 | 2556 |
| writer | 24 | 0.02719 | 148354 | 24198 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00430 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00430 |
| 1 | 0.00000 | 0.00176 | 0.00322 | 0.00354 | 0.00038 | 0.00045 | 0.00091 | 0.01027 |
| 2 | 0.00000 | 0.00199 | 0.00334 | 0.00287 | 0.00037 | 0.00051 | 0.00056 | 0.00964 |
| 3 | 0.00000 | 0.00215 | 0.00227 | 0.00191 | 0.00047 | 0.00051 | 0.00041 | 0.00771 |
| 4 | 0.00000 | 0.00215 | 0.00251 | 0.00243 | 0.00047 | 0.00059 | 0.00047 | 0.00862 |
| 5 | 0.00000 | 0.00208 | 0.00385 | 0.00352 | 0.00043 | 0.00048 | 0.00066 | 0.01102 |
| 6 | 0.00000 | 0.00196 | 0.00233 | 0.00192 | 0.00045 | 0.00055 | 0.00053 | 0.00774 |
| 7 | 0.00000 | 0.00220 | 0.00227 | 0.00241 | 0.00042 | 0.00044 | 0.00042 | 0.00817 |
| 8 | 0.00000 | 0.00194 | 0.00212 | 0.00187 | 0.00041 | 0.00064 | 0.00047 | 0.00745 |
| 9 | 0.00000 | 0.00197 | 0.00315 | 0.00272 | 0.00038 | 0.00059 | 0.00064 | 0.00945 |
| 10 | 0.00000 | 0.00189 | 0.00214 | 0.00190 | 0.00040 | 0.00050 | 0.00044 | 0.00726 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | quality:repetition ×3 | 0 | — |
| 2 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 1 | quality:repetition ×1, guard:teller_does_not_know ×2 | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 10 | 1 | có | 2 | 0 | — | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 7–9 | 7 | đúng khoảng |
| 2 | 4–6 | 4 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–6 | 4 | đúng khoảng |
| 2 | 3–10 | 5 | đúng khoảng |
| 3 | 4–12 | 5 | đúng khoảng |
| 4 | 5–12 | 1 | sớm |
