# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 22/10/2026; truyện `evals/results/2026-10-22-new-facts-replay-1`; questions v1, run v2.
- Commit `4380650258d9` (có sửa chưa commit); model trả lời `openai/gpt-6-luna` (suy luận low); tóm tắt `openai/gpt-6-luna`.
- Chạy khô (model giả): False. Nền đồ thị: neo4j.
- Lượt khai mỗi hệ: 117 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.0136 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 71% (83/117) [62–78] | 25 | 11281 | 0.0066 | 0.0000 | 0.0001 |
| Đồ thị + câu trích trên trang (BM25) | 84% (98/117) [76–89] | 11 | 12455 | 0.0070 | 0.0000 | 0.0001 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 88% (29/33) | 73% (11/15) | 62% (30/48) | 62% (13/21) | — |
| Đồ thị + câu trích trên trang (BM25) | 76% (25/33) | 100% (15/15) | 83% (40/48) | 86% (18/21) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 72% (80/111) | 50% (3/6) |
| Đồ thị + câu trích trên trang (BM25) | 85% (94/111) | 67% (4/6) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Đồ thị WriTory | 91% (68/75) | 36% (15/42) |
| Đồ thị + câu trích trên trang (BM25) | 89% (67/75) | 74% (31/42) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 100% (36/36) | 40% (6/15) | 62% (41/66) |
| Đồ thị + câu trích trên trang (BM25) | 100% (36/36) | 87% (13/15) | 74% (49/66) |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
