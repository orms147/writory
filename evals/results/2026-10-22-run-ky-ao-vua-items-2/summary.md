# Chạy cả truyện: ky-ao-vua-items-2

- Commit `236705fa32084fa281edb28819a4df6161a2cbfc` (có sửa chưa commit); đề v1 (`6aeab8e2624b`); config `67e9b1cac572`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 1.
- Chi phí: 0.0790 USD (trần --budget: 0.13); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0050, lượt chương đắt nhất 0.0093.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×1, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: quality:repetition ×3. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 2 (known_as là tên của nút khác ×1, sai schema cạnh ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 12 | 0.00530 | 31730 | 3936 |
| extract | 23 | 0.01945 | 145479 | 10805 |
| moderate | 33 | 0.00449 | 67358 | 2450 |
| outline | 20 | 0.01913 | 87856 | 16307 |
| setup | 5 | 0.00381 | 8841 | 6450 |
| summary | 10 | 0.00380 | 21123 | 2313 |
| writer | 23 | 0.02297 | 128385 | 20756 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00381 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00381 |
| 1 | 0.00000 | 0.00154 | 0.00178 | 0.00186 | 0.00039 | 0.00046 | 0.00039 | 0.00642 |
| 2 | 0.00000 | 0.00180 | 0.00203 | 0.00204 | 0.00040 | 0.00068 | 0.00045 | 0.00740 |
| 3 | 0.00000 | 0.00192 | 0.00313 | 0.00229 | 0.00038 | 0.00049 | 0.00057 | 0.00878 |
| 4 | 0.00000 | 0.00192 | 0.00193 | 0.00150 | 0.00037 | 0.00047 | 0.00039 | 0.00658 |
| 5 | 0.00000 | 0.00211 | 0.00212 | 0.00176 | 0.00040 | 0.00049 | 0.00044 | 0.00732 |
| 6 | 0.00000 | 0.00214 | 0.00310 | 0.00234 | 0.00038 | 0.00053 | 0.00052 | 0.00900 |
| 7 | 0.00000 | 0.00200 | 0.00316 | 0.00264 | 0.00037 | 0.00060 | 0.00057 | 0.00934 |
| 8 | 0.00000 | 0.00203 | 0.00213 | 0.00201 | 0.00041 | 0.00058 | 0.00044 | 0.00761 |
| 9 | 0.00000 | 0.00174 | 0.00171 | 0.00143 | 0.00033 | 0.00050 | 0.00034 | 0.00605 |
| 10 | 0.00000 | 0.00194 | 0.00188 | 0.00158 | 0.00038 | 0.00050 | 0.00038 | 0.00665 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 2 | — |
| 2 | 1 | có | 2 | 0 | — | 0 | — |
| 3 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | — |
| 6 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 7 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |
| 8 | 1 | có | 2 | 0 | — | 0 | — |
| 9 | 1 | có | 2 | 0 | — | 0 | — |
| 10 | 1 | có | 2 | 0 | — | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 5–8 | 5 | đúng khoảng |
| 2 | 2–5 | 3 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 2–4 | 2 | đúng khoảng |
| 2 | 3–5 | 3 | đúng khoảng |
| 3 | 5–8 | 5 | đúng khoảng |
| 4 | 8–12 | 8 | đúng khoảng |
