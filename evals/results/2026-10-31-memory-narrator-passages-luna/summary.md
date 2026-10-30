# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 22/10/2026; truyện `evals/results/2026-10-22-new-facts-replay-1`; questions v1, run v2.
- Commit `f431a6f46520`; model trả lời `openai/gpt-6-luna` (suy luận low); tóm tắt `openai/gpt-6-luna`.
- Chạy khô (model giả): False. Nền đồ thị: memory.
- Lượt khai mỗi hệ: 39 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.0330 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 33% (13/39) [21–49] | 26 | 10661 | 0.0135 | 0.0000 | 0.0003 |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 69% (27/39) [54–81] | 12 | 15028 | 0.0194 | 0.0000 | 0.0005 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 18% (2/11) | 40% (2/5) | 44% (7/16) | 29% (2/7) | — |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 55% (6/11) | 80% (4/5) | 75% (12/16) | 71% (5/7) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 35% (13/37) | 0% (0/2) |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 70% (26/37) | 50% (1/2) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 40% (10/25) | 21% (3/14) |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 60% (15/25) | 86% (12/14) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 17% (2/12) | 60% (3/5) | 36% (8/22) |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 33% (4/12) | 80% (4/5) | 86% (19/22) |

## Cache prompt (D-96)

Lượt lạnh: nhà cung cấp báo 0 token đọc từ cache; lượt có cache: báo > 0. Prompt lặp (lần hỏi thứ 2, 3 hoặc chạy lại trong vài chục phút) được cache nên rẻ hơn nhiều: so USD mỗi lời gọi giữa hai lần chạy chỉ có nghĩa khi tỉ lệ cache giống nhau. Giữ chỗ ngân sách và trần G8 vẫn tính theo giá lạnh.

| Hệ | Lời gọi lạnh | USD / lời gọi lạnh | Lời gọi có cache | USD / lời gọi có cache | Không rõ | Token vào được cache |
|---|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | 1 | 0.000508 | 38 | 0.000343 | 0 | 29% |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | 0 | — | 39 | 0.000498 | 0 | 26% |

## Người kể: lý do chặn và lộ

Câu "Bạn chưa biết điều này." tính là kiêng. Lý do: `empty_notebook`, `model_not_known`, `empty_answer`, `no_entries`, `unknown_ref`, `leak`, `meta_hedge`. Lộ: bộ chấm chặt của bài E trên câu cuối; "ngoài trang" = chuỗi trúng không có trong văn chương 1..N người chơi đã đọc.

| Hệ | Lý do chặn | Lộ ở câu cuối | Lộ ngoài trang | Sai (không kiêng) | Đoạn TB mỗi lời gọi |
|---|---|---|---|---|---|
| Người kể, chỉ sổ tay (narrator-3) | model_not_known ×26 | 0 | 0 | 0 | 0.0 |
| Người kể, sổ tay + đoạn trên trang (narrator-4) | model_not_known ×12 | 1 | 0 | 0 | 5.9 |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
