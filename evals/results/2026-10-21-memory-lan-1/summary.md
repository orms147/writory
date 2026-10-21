# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 21/10/2026; questions v1, run v1.
- Commit `5b84de22dd29`; model trả lời `openai/gpt-6-luna` (suy luận low); tóm tắt `openai/gpt-6-luna`.
- Chạy khô (model giả): False. Nền đồ thị: neo4j.
- Lượt khai mỗi hệ: 132 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.0737 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 91% (120/132) [85–95] | 6 | 5121 | 0.0160 | 0.0000 | 0.0001 |
| Không bộ nhớ (chỉ chương N) | 59% (78/132) [51–67] | 47 | 1692 | 0.0135 | 0.0000 | 0.0001 |
| Tóm tắt cuộn + chương N | 86% (114/132) [79–91] | 7 | 3515 | 0.0116 | 0.0008 | 0.0001 |
| RAG BM25 + chương N | 91% (120/132) [85–95] | 4 | 3950 | 0.0122 | 0.0000 | 0.0001 |
| Nhét cả truyện (chương 1..N) | 92% (121/132) [86–95] | 5 | 7162 | 0.0195 | 0.0000 | 0.0001 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 94% (31/33) | 90% (19/21) | 100% (18/18) | 81% (22/27) | 91% (30/33) |
| Không bộ nhớ (chỉ chương N) | 82% (27/33) | 24% (5/21) | 61% (11/18) | 59% (16/27) | 58% (19/33) |
| Tóm tắt cuộn + chương N | 91% (30/33) | 100% (21/21) | 100% (18/18) | 52% (14/27) | 94% (31/33) |
| RAG BM25 + chương N | 100% (33/33) | 100% (21/21) | 100% (18/18) | 70% (19/27) | 88% (29/33) |
| Nhét cả truyện (chương 1..N) | 91% (30/33) | 100% (21/21) | 94% (17/18) | 81% (22/27) | 94% (31/33) |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 91% (117/129) | 100% (3/3) |
| Không bộ nhớ (chỉ chương N) | 58% (75/129) | 100% (3/3) |
| Tóm tắt cuộn + chương N | 86% (111/129) | 100% (3/3) |
| RAG BM25 + chương N | 91% (117/129) | 100% (3/3) |
| Nhét cả truyện (chương 1..N) | 91% (118/129) | 100% (3/3) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 95% (57/60) | 83% (35/42) | 93% (28/30) |
| Không bộ nhớ (chỉ chương N) | 97% (58/60) | 31% (13/42) | 23% (7/30) |
| Tóm tắt cuộn + chương N | 90% (54/60) | 79% (33/42) | 90% (27/30) |
| RAG BM25 + chương N | 97% (58/60) | 86% (36/42) | 87% (26/30) |
| Nhét cả truyện (chương 1..N) | 88% (53/60) | 98% (41/42) | 90% (27/30) |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
