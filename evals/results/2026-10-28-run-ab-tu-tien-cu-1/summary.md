# Chạy cả truyện: ab-tu-tien-cu-1

- Commit `51a13a8328827f66c018e6e9e9eead9ac902885d` (có sửa chưa commit); đề v1 (`42aeb39100b7`); config `1b9db7f9197d`; seed 20261028; dry-run: không.
- Model: setup `openai/gpt-6-luna`, suy luận low; outline `openai/gpt-6-luna`, suy luận low; extract `openai/gpt-6-luna`, suy luận low; summary `openai/gpt-6-luna`, suy luận low; choices `openai/gpt-6-luna`, suy luận low; moderate `openai/gpt-6-luna`, suy luận low; writer `openai/gpt-6-luna`, suy luận none.
- Chương đã ghi: 6/6 (kế hoạch 6).
- Dừng: không, chạy hết.
- Khởi tạo: lượt sửa 0 (—); tự bấm thử lại 0.
- Chi phí: 0.0590 USD (trần --budget: 0.15); ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Trần config (USD): cảnh 0.02, chương 0.08, truyện 1.0. Cảnh đắt nhất 0.0064, lượt chương đắt nhất 0.0133.
- Viết lại: 4; hiện bản trước vì bản viết lại có lỗi chặn: 0; cảnh bị chặn: 0; tự bấm thử lại: setup ×0, chapter ×0, choices ×0.
- Dàn ý cảnh cuối bỏ mạch đến hạn sau mọi lượt thử (D-82): 0 mạch.
- Tóm tắt chương: tạo 5, lỗi 0; chương chạy thiếu tóm tắt chương trước: 0.
- Lỗi tìm thấy: guard:at_most_one ×1, guard:overdue_secret ×1, guard:teller_does_not_know ×6. Còn lại khi hiện: guard:at_most_one ×1, guard:overdue_secret ×1, guard:teller_does_not_know ×2.
- Cạnh bộ trích bỏ: 17 (Fact mới ×4, câu trích không có nguyên văn trong chương (G3) ×1, hé lộ nút có tên mà thiếu known_as (D-17) ×2, known_as là tên của nút khác ×1, sai schema cạnh ×5, thiếu KNOWS ×3, trùng Fact ×1).

## Chi phí theo vai

| Vai | Lời gọi | USD | Token vào | Token ra |
|---|---|---|---|---|
| choices | 5 | 0.00277 | 16118 | 1503 |
| extract | 16 | 0.02085 | 135216 | 16602 |
| moderate | 21 | 0.00338 | 43945 | 1593 |
| outline | 12 | 0.01211 | 62520 | 8598 |
| summary | 5 | 0.00196 | 10889 | 1206 |
| writer | 16 | 0.01795 | 102478 | 14791 |

## Chi phí theo chương (USD, mọi lượt)

| Chương | setup | outline | writer | extract | summary | choices | moderate | Tổng |
|---|---|---|---|---|---|---|---|---|
| 1 | 0.00000 | 0.00182 | 0.00238 | 0.00341 | 0.00045 | 0.00057 | 0.00081 | 0.00943 |
| 2 | 0.00000 | 0.00181 | 0.00278 | 0.00363 | 0.00034 | 0.00046 | 0.00047 | 0.00950 |
| 3 | 0.00000 | 0.00224 | 0.00227 | 0.00245 | 0.00038 | 0.00049 | 0.00040 | 0.00823 |
| 4 | 0.00000 | 0.00213 | 0.00353 | 0.00350 | 0.00041 | 0.00069 | 0.00065 | 0.01091 |
| 5 | 0.00000 | 0.00202 | 0.00462 | 0.00506 | 0.00038 | 0.00056 | 0.00069 | 0.01334 |
| 6 | 0.00000 | 0.00209 | 0.00236 | 0.00279 | 0.00000 | 0.00000 | 0.00037 | 0.00760 |

## Từng lượt chương

| Chương | Lượt | Đã ghi | Cảnh | Viết lại | Lỗi tìm thấy | Cạnh bị bỏ | Lỗi |
|---|---|---|---|---|---|---|---|
| 1 | 1 | có | 2 | 0 | — | 8 | — |
| 2 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2, guard:at_most_one ×1 | 2 | — |
| 3 | 1 | có | 2 | 0 | — | 0 | — |
| 4 | 1 | có | 2 | 1 | guard:teller_does_not_know ×2 | 2 | — |
| 5 | 1 | có | 2 | 2 | guard:teller_does_not_know ×2, guard:overdue_secret ×1 | 0 | — |
| 6 | 1 | có | 2 | 0 | — | 5 | — |

## Kế hoạch so với kết quả

- Kết truyện: có (chương cuối phát `story_finished`, không có lựa chọn).
- Tính tới hết chương 6/6.

| Bí mật | Khoảng lộ | Lộ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 4–5 | 6 | trễ |

| Mạch phải gỡ | Hạn gỡ | Gỡ ở chương | Đánh giá |
|---|---|---|---|
| 1 | 3–4 | 3 | đúng khoảng |
| 2 | 4–6 | 6 | đúng khoảng |
| 3 | 5–6 | 6 | đúng khoảng |
| 4 | 3–5 | 3 | đúng khoảng |
