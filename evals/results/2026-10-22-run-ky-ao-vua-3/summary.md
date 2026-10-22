# Chạy cả truyện: ky-ao-vua-3

- Commit `041846516ea3788fcb3a37845a9e989f232c92c1`; đề v1 (`6aeab8e2624b`); config `190f06005a6c`; seed 20261021; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 10/10 (kế hoạch 12).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0778 USD (trần --budget: 0.2); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0049, lượt chương đắt nhất 0.0089.
- Viết lại: 3; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×2.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 10, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: leak:name ×2, quality:repetition ×3. Còn lại khi hiện: —.
- Cạnh bộ trích bỏ: 5 (hé lộ nút có tên mà thiếu known_as (D-17) ×3, sai schema cạnh ×2).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 18 | 0.00700 | 43428 | 7414 |
| extract | 23 | 0.02068 | 152317 | 11548 |
| moderate | 31 | 0.00407 | 61938 | 2229 |
| outline | 20 | 0.01745 | 86780 | 13206 |
| setup | 4 | 0.00365 | 7339 | 6154 |
| summary | 10 | 0.00349 | 19319 | 2150 |
| writer | 23 | 0.02142 | 124499 | 18634 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 0 | 0.00365 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00000 | 0.00365 |
| 1 | 0.00000 | 0.00166 | 0.00198 | 0.00233 | 0.00039 | 0.00128 | 0.00033 | 0.00798 |
| 2 | 0.00000 | 0.00171 | 0.00284 | 0.00286 | 0.00037 | 0.00048 | 0.00056 | 0.00882 |
| 3 | 0.00000 | 0.00173 | 0.00184 | 0.00157 | 0.00034 | 0.00044 | 0.00037 | 0.00629 |
| 4 | 0.00000 | 0.00176 | 0.00183 | 0.00187 | 0.00034 | 0.00076 | 0.00035 | 0.00691 |
| 5 | 0.00000 | 0.00169 | 0.00172 | 0.00154 | 0.00034 | 0.00119 | 0.00029 | 0.00677 |
| 6 | 0.00000 | 0.00183 | 0.00185 | 0.00211 | 0.00034 | 0.00063 | 0.00037 | 0.00712 |
| 7 | 0.00000 | 0.00178 | 0.00177 | 0.00174 | 0.00033 | 0.00052 | 0.00037 | 0.00651 |
| 8 | 0.00000 | 0.00170 | 0.00274 | 0.00253 | 0.00034 | 0.00049 | 0.00046 | 0.00826 |
| 9 | 0.00000 | 0.00178 | 0.00184 | 0.00161 | 0.00035 | 0.00062 | 0.00036 | 0.00655 |
| 10 | 0.00000 | 0.00180 | 0.00303 | 0.00253 | 0.00035 | 0.00058 | 0.00060 | 0.00890 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 3 | RETRY_LIMIT_REACHED |
| 2 | 1 | có | 2 | 1 | leak:name ×2 | 2 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 0 | — | 0 | — |
| 5 | 1 | có | 2 | 0 | — | 0 | RETRY_LIMIT_REACHED |
| 6 | 1 | có | 2 | 0 | — | 0 | — |
| 7 | 1 | có | 2 | 0 | — | 0 | — |
| 8 | 1 | có | 2 | 1 | quality:repetition ×2 | 0 | — |
| 9 | 1 | có | 2 | 0 | — | 0 | — |
| 10 | 1 | có | 2 | 1 | quality:repetition ×1 | 0 | — |

## Kế hoạch so với kết quả

- Kết truyện: không (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 10/12.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 7–8 | 7 | đúng khoảng |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 1–3 | 1 | đúng khoảng |
| 2 | 4–6 | 4 | đúng khoảng |
| 3 | 6–8 | 6 | đúng khoảng |
| 4 | 8–10 | 8 | đúng khoảng |
| 5 | 10–12 | — | chưa tới hạn |
