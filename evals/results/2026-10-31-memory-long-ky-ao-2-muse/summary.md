# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 31/10/2026; truyện `evals/results/2026-10-29-run-long-after-ky-ao-2`; questions v1, run v2.
- Commit `7fca71449215`; model trả lời `meta/muse-wonder-1.0` (suy luận low); tóm tắt `meta/muse-wonder-1.0`.
- Chạy khô (model giả): False. Nền đồ thị: memory.
- Lượt khai mỗi hệ: 50 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 9.0376 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 66% (33/50) [52–78] | 12 | 10048 | 0.9213 | 0.0000 | 0.0184 |
| Đồ thị + câu trích trên trang (BM25) | 86% (43/50) [74–93] | 3 | 12176 | 1.0360 | 0.0000 | 0.0207 |
| Không bộ nhớ (chỉ chương N) | 8% (4/50) [3–19] | 46 | 5506 | 0.4902 | 0.0000 | 0.0098 |
| Tóm tắt cuộn + chương N | 84% (42/50) [71–92] | 7 | 20957 | 1.1774 | 0.6156 | 0.0359 |
| RAG BM25 + chương N | 70% (35/50) [56–81] | 12 | 7846 | 0.7430 | 0.0000 | 0.0149 |
| Nhét cả truyện (chương 1..N) | 100% (50/50) [93–100] | 0 | 123167 | 4.0541 | 0.0000 | 0.0811 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 100% (10/10) | 71% (5/7) | 65% (11/17) | 36% (4/11) | 60% (3/5) |
| Đồ thị + câu trích trên trang (BM25) | 100% (10/10) | 100% (7/7) | 94% (16/17) | 55% (6/11) | 80% (4/5) |
| Không bộ nhớ (chỉ chương N) | 30% (3/10) | 14% (1/7) | 0% (0/17) | 0% (0/11) | 0% (0/5) |
| Tóm tắt cuộn + chương N | 80% (8/10) | 57% (4/7) | 94% (16/17) | 91% (10/11) | 80% (4/5) |
| RAG BM25 + chương N | 70% (7/10) | 86% (6/7) | 88% (15/17) | 45% (5/11) | 40% (2/5) |
| Nhét cả truyện (chương 1..N) | 100% (10/10) | 100% (7/7) | 100% (17/17) | 100% (11/11) | 100% (5/5) |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 67% (32/48) | 50% (1/2) |
| Đồ thị + câu trích trên trang (BM25) | 85% (41/48) | 100% (2/2) |
| Không bộ nhớ (chỉ chương N) | 8% (4/48) | 0% (0/2) |
| Tóm tắt cuộn + chương N | 83% (40/48) | 100% (2/2) |
| RAG BM25 + chương N | 69% (33/48) | 100% (2/2) |
| Nhét cả truyện (chương 1..N) | 100% (48/48) | 100% (2/2) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Đồ thị WriTory | 91% (31/34) | 12% (2/16) |
| Đồ thị + câu trích trên trang (BM25) | 91% (31/34) | 75% (12/16) |
| Không bộ nhớ (chỉ chương N) | 9% (3/34) | 6% (1/16) |
| Tóm tắt cuộn + chương N | 79% (27/34) | 94% (15/16) |
| RAG BM25 + chương N | 65% (22/34) | 81% (13/16) |
| Nhét cả truyện (chương 1..N) | 100% (34/34) | 100% (16/16) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 100% (4/4) | 67% (2/3) | 63% (27/43) |
| Đồ thị + câu trích trên trang (BM25) | 100% (4/4) | 100% (3/3) | 84% (36/43) |
| Không bộ nhớ (chỉ chương N) | 100% (4/4) | 0% (0/3) | 0% (0/43) |
| Tóm tắt cuộn + chương N | 100% (4/4) | 100% (3/3) | 81% (35/43) |
| RAG BM25 + chương N | 100% (4/4) | 67% (2/3) | 67% (29/43) |
| Nhét cả truyện (chương 1..N) | 100% (4/4) | 100% (3/3) | 100% (43/43) |

## Cache prompt (D-96)

Lượt lạnh: nhà cung cấp báo 0 token đọc từ cache; lượt có cache: báo > 0. Prompt lặp (lần hỏi thứ 2, 3 hoặc chạy lại trong vài chục phút) được cache nên rẻ hơn nhiều: so USD mỗi lời gọi giữa hai lần chạy chỉ có nghĩa khi tỉ lệ cache giống nhau. Giữ chỗ ngân sách và trần G8 vẫn tính theo giá lạnh.

| Hệ | Lời gọi lạnh | USD / lời gọi lạnh | Lời gọi có cache | USD / lời gọi có cache | Không rõ | Token vào được cache |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 8 | 0.018086 | 42 | 0.018490 | 0 | 4% |
| Đồ thị + câu trích trên trang (BM25) | 7 | 0.021560 | 43 | 0.020582 | 0 | 4% |
| Không bộ nhớ (chỉ chương N) | 8 | 0.013074 | 42 | 0.009181 | 0 | 43% |
| Tóm tắt cuộn + chương N | 7 | 0.029759 | 43 | 0.022536 | 0 | 28% |
| RAG BM25 + chương N | 6 | 0.016618 | 44 | 0.014621 | 0 | 7% |
| Nhét cả truyện (chương 1..N) | 10 | 0.156453 | 40 | 0.062240 | 0 | 49% |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
