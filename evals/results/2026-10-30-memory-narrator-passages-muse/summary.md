# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 22/10/2026; truyện `evals/results/2026-10-22-new-facts-replay-1`; questions v1, run v2.
- Commit `f431a6f46520`; model trả lời `meta/muse-wonder-1.0` (suy luận low); tóm tắt `meta/muse-wonder-1.0`.
- Chạy khô (model giả): False. Nền đồ thị: memory.
- Lượt khai mỗi hệ: 78 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 1.7419 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 38% (30/78) [28–50] | 47 | 10661 | 0.7039 | 0.0000 | 0.0090 |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 67% (52/78) [56–76] | 19 | 15028 | 1.0380 | 0.0000 | 0.0133 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 27% (6/22) | 40% (4/10) | 44% (14/32) | 43% (6/14) | — |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 50% (11/22) | 80% (8/10) | 75% (24/32) | 64% (9/14) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 41% (30/74) | 0% (0/4) |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 68% (50/74) | 50% (2/4) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 46% (23/50) | 25% (7/28) |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 58% (29/50) | 82% (23/28) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 29% (7/24) | 70% (7/10) | 36% (16/44) |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 33% (8/24) | 80% (8/10) | 82% (36/44) |

## Cache prompt (D-96)

Lượt lạnh: nhà cung cấp báo 0 token đọc từ cache; lượt có cache: báo > 0. Prompt lặp (lần hỏi thứ 2, 3 hoặc chạy lại trong vài chục phút) được cache nên rẻ hơn nhiều: so USD mỗi lời gọi giữa hai lần chạy chỉ có nghĩa khi tỉ lệ cache giống nhau. Giữ chỗ ngân sách và trần G8 vẫn tính theo giá lạnh.

| Hệ | Lời gọi lạnh | USD / lời gọi lạnh | Lời gọi có cache | USD / lời gọi có cache | Không rõ | Token vào được cache |
|---|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 8 | 0.020594 | 70 | 0.007703 | 0 | 78% |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 0 | — | 78 | 0.013307 | 0 | 60% |

## Người kể: lý do chặn và lộ

Câu "Bạn chưa biết điều này." tính là kiêng. Lý do: `empty_notebook`, `model_not_known`, `empty_answer`, `no_entries`, `unknown_ref`, `leak`, `meta_hedge`. Lộ: bộ chấm chặt của bài E trên câu cuối; "ngoài trang" = chuỗi trúng không có trong văn chương 1..N người chơi đã đọc.

| Hệ | Lý do chặn | Lộ ở câu cuối | Lộ ngoài trang | Sai (không kiêng) | Đoạn TB mỗi lời gọi |
|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | model_not_known ×47 | 1 | 0 | 1 | 0.0 |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | model_not_known ×19 | 5 | 0 | 7 | 5.9 |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
