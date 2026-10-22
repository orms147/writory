# Chạy cả truyện: ky-ao-vua-quotes-1

- Commit `37906b490dee145ba7bcfe98921b653968c58540`; đề v1 (`6aeab8e2624b`); config `0b0a042cef24`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 1 (edges ×1); tự bấm thử lại 0.
- Chi phí: 0.0844 USD (trần --budget: 0.25); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0055, lượt chương đắt nhất 0.0118.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: leak:name ×1, quality:repetition ×4. Còn lại khi hiện: quality:repetition ×1.
- Cạnh bộ trích bỏ: 1 (sai schema cạnh ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 10 | 0.00507 | 26909 | 3407 |
| extract | 23 | 0.02058 | 145793 | 12520 |
| moderate | 33 | 0.00461 | 67128 | 2730 |
| outline | 20 | 0.02046 | 102350 | 15334 |
| setup | 5 | 0.00515 | 14064 | 8093 |
| summary | 10 | 0.00382 | 20866 | 2422 |
| writer | 23 | 0.02474 | 143612 | 20491 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00515 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00515 |
| 1 | 0.00000 | 0.00175 | 0.00301 | 0.00365 | 0.00040 | 0.00052 | 0.00056 | 0.00988 |
| 2 | 0.00000 | 0.00212 | 0.00210 | 0.00174 | 0.00036 | 0.00056 | 0.00039 | 0.00728 |
| 3 | 0.00000 | 0.00213 | 0.00212 | 0.00166 | 0.00038 | 0.00052 | 0.00042 | 0.00724 |
| 4 | 0.00000 | 0.00212 | 0.00217 | 0.00161 | 0.00040 | 0.00054 | 0.00043 | 0.00727 |
| 5 | 0.00000 | 0.00215 | 0.00463 | 0.00331 | 0.00036 | 0.00054 | 0.00076 | 0.01176 |
| 6 | 0.00000 | 0.00209 | 0.00216 | 0.00170 | 0.00037 | 0.00052 | 0.00041 | 0.00725 |
| 7 | 0.00000 | 0.00201 | 0.00215 | 0.00177 | 0.00038 | 0.00045 | 0.00046 | 0.00722 |
| 8 | 0.00000 | 0.00204 | 0.00221 | 0.00155 | 0.00040 | 0.00052 | 0.00041 | 0.00714 |
| 9 | 0.00000 | 0.00196 | 0.00212 | 0.00185 | 0.00038 | 0.00045 | 0.00040 | 0.00715 |
| 10 | 0.00000 | 0.00209 | 0.00207 | 0.00172 | 0.00038 | 0.00045 | 0.00037 | 0.00708 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 1 | leak:name ×1 | 1 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 2 | quality:repetition ×4 | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | có | 2 | 0 | — | 0 | — |
| 10 | 1 | có | 2 | 0 | — | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 5–6 | 5 | đúng khoảng |
| 2 | 7–8 | 7 | đúng khoảng |
| 3 | 9–10 | 9 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–8 | 2 | đúng khoảng |
| 2 | 3–9 | 6 | đúng khoảng |
| 3 | 4–11 | 4 | đúng khoảng |
| 4 | 6–12 | 6 | đúng khoảng |
