# Bài A: bộ nhớ, kết quả

- Đề: CHỜ DUYỆT. Dẫn xuất từ questions-ky-ao-vua-1.yaml (đã duyệt 22/10/2026): cùng câu hỏi, đáp án và câu trích; chỉ đổi nguồn đồ thị sang lần phát lại có Fact mới (D-93) và cờ graph_agrees/derive của 12 câu theo đồ thị đó, soạn SAU khi thấy đồ thị.; truyện `evals/results/2026-10-22-new-facts-replay-1`; questions v1, run v2.
- Commit `87f84987bdff` (có sửa chưa commit); model trả lời `openai/gpt-6-luna` (suy luận low); tóm tắt `openai/gpt-6-luna`.
- Chạy khô (model giả): False. Nền đồ thị: neo4j.
- Lượt khai mỗi hệ: 39 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.0420 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 74% (29/39) [59–85] | 8 | 11281 | 0.0203 | 0.0000 | 0.0005 |
| Đồ thị + câu trích trên trang (BM25) | 82% (32/39) [67–91] | 3 | 12455 | 0.0217 | 0.0000 | 0.0006 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 100% (11/11) | 80% (4/5) | 62% (10/16) | 57% (4/7) | — |
| Đồ thị + câu trích trên trang (BM25) | 73% (8/11) | 100% (5/5) | 81% (13/16) | 86% (6/7) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 76% (28/37) | 50% (1/2) |
| Đồ thị + câu trích trên trang (BM25) | 84% (31/37) | 50% (1/2) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Đồ thị WriTory | 96% (24/25) | 36% (5/14) |
| Đồ thị + câu trích trên trang (BM25) | 88% (22/25) | 71% (10/14) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 100% (12/12) | 40% (2/5) | 68% (15/22) |
| Đồ thị + câu trích trên trang (BM25) | 100% (12/12) | 80% (4/5) | 73% (16/22) |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
