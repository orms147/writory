# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 22/10/2026; truyện `evals/results/2026-10-21-run-ky-ao-vua-1`; questions v1, run v2.
- Commit `100fd492afc9`; model trả lời `openai/gpt-6-luna` (suy luận low); tóm tắt `openai/gpt-6-luna`.
- Chạy khô (model giả): False. Nền đồ thị: neo4j.
- Lượt khai mỗi hệ: 117 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.2299 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 49% (57/117) [40–58] | 47 | 10015 | 0.0230 | 0.0000 | 0.0002 |
| Đồ thị + câu trích trên trang (BM25) | 79% (92/117) [70–85] | 7 | 11189 | 0.0245 | 0.0000 | 0.0002 |
| Không bộ nhớ (chỉ chương N) | 31% (36/117) [23–40] | 72 | 7466 | 0.0178 | 0.0000 | 0.0002 |
| Tóm tắt cuộn + chương N | 79% (92/117) [70–85] | 17 | 12724 | 0.0260 | 0.0039 | 0.0003 |
| RAG BM25 + chương N | 84% (98/117) [76–89] | 10 | 9775 | 0.0215 | 0.0000 | 0.0002 |
| Nhét cả truyện (chương 1..N) | 91% (107/117) [85–95] | 1 | 59388 | 0.1133 | 0.0000 | 0.0010 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 70% (23/33) | 40% (6/15) | 38% (18/48) | 48% (10/21) | — |
| Đồ thị + câu trích trên trang (BM25) | 79% (26/33) | 93% (14/15) | 79% (38/48) | 67% (14/21) | — |
| Không bộ nhớ (chỉ chương N) | 39% (13/33) | 20% (3/15) | 25% (12/48) | 38% (8/21) | — |
| Tóm tắt cuộn + chương N | 97% (32/33) | 47% (7/15) | 67% (32/48) | 100% (21/21) | — |
| RAG BM25 + chương N | 79% (26/33) | 100% (15/15) | 88% (42/48) | 71% (15/21) | — |
| Nhét cả truyện (chương 1..N) | 88% (29/33) | 87% (13/15) | 92% (44/48) | 100% (21/21) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 49% (54/111) | 50% (3/6) |
| Đồ thị + câu trích trên trang (BM25) | 80% (89/111) | 50% (3/6) |
| Không bộ nhớ (chỉ chương N) | 30% (33/111) | 50% (3/6) |
| Tóm tắt cuộn + chương N | 79% (88/111) | 67% (4/6) |
| RAG BM25 + chương N | 83% (92/111) | 100% (6/6) |
| Nhét cả truyện (chương 1..N) | 91% (101/111) | 100% (6/6) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Đồ thị WriTory | 97% (38/39) | 24% (19/78) |
| Đồ thị + câu trích trên trang (BM25) | 97% (38/39) | 69% (54/78) |
| Không bộ nhớ (chỉ chương N) | 56% (22/39) | 18% (14/78) |
| Tóm tắt cuộn + chương N | 90% (35/39) | 73% (57/78) |
| RAG BM25 + chương N | 74% (29/39) | 88% (69/78) |
| Nhét cả truyện (chương 1..N) | 82% (32/39) | 96% (75/78) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 97% (35/36) | 20% (3/15) | 29% (19/66) |
| Đồ thị + câu trích trên trang (BM25) | 100% (36/36) | 80% (12/15) | 67% (44/66) |
| Không bộ nhớ (chỉ chương N) | 94% (34/36) | 13% (2/15) | 0% (0/66) |
| Tóm tắt cuộn + chương N | 100% (36/36) | 67% (10/15) | 70% (46/66) |
| RAG BM25 + chương N | 97% (35/36) | 100% (15/15) | 73% (48/66) |
| Nhét cả truyện (chương 1..N) | 97% (35/36) | 93% (14/15) | 88% (58/66) |

## Lỗi

- Đồ thị WriTory: HARNESS_ERROR ×54
- Đồ thị + câu trích trên trang (BM25): HARNESS_ERROR ×54

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
