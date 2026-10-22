# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 22/10/2026; truyện `evals/results/2026-10-22-new-facts-replay-1`; questions v1, run v2.
- Commit `73f523d40cea` (có sửa chưa commit); model trả lời `deepseek/deepseek-v4-flash` (suy luận low); tóm tắt `deepseek/deepseek-v4-flash`.
- Chạy khô (model giả): False. Nền đồ thị: neo4j.
- Lượt khai mỗi hệ: 39 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.0381 USD. Dừng sớm: budget: trần openrouter 0.04 USD: đã tiêu 0.0351, đang giữ chỗ 0.0039, lời gọi tiếp ước tối đa 0.0012.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 54% (21/39) [39–68] | 5 | 11104 | 0.0143 | 0.0000 | 0.0006 |
| Đồ thị + câu trích trên trang (BM25) | 59% (23/39) [43–73] | 0 | 13433 | 0.0215 | 0.0000 | 0.0009 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 82% (9/11) | 60% (3/5) | 56% (9/16) | 0% (0/7) | — |
| Đồ thị + câu trích trên trang (BM25) | 82% (9/11) | 100% (5/5) | 56% (9/16) | 0% (0/7) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 54% (20/37) | 50% (1/2) |
| Đồ thị + câu trích trên trang (BM25) | 59% (22/37) | 50% (1/2) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Đồ thị WriTory | 80% (20/25) | 7% (1/14) |
| Đồ thị + câu trích trên trang (BM25) | 80% (20/25) | 21% (3/14) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 83% (10/12) | 40% (2/5) | 41% (9/22) |
| Đồ thị + câu trích trên trang (BM25) | 75% (9/12) | 40% (2/5) | 55% (12/22) |

## Cache prompt (D-96)

Lượt lạnh: nhà cung cấp báo 0 token đọc từ cache; lượt có cache: báo > 0. Prompt lặp (lần hỏi thứ 2, 3 hoặc chạy lại trong vài chục phút) được cache nên rẻ hơn nhiều: so USD mỗi lời gọi giữa hai lần chạy chỉ có nghĩa khi tỉ lệ cache giống nhau. Giữ chỗ ngân sách và trần G8 vẫn tính theo giá lạnh.

| Hệ | Lời gọi lạnh | USD / lời gọi lạnh | Lời gọi có cache | USD / lời gọi có cache | Không rõ | Token vào được cache |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 23 | 0.000548 | 4 | 0.000424 | 0 | 9% |
| Đồ thị + câu trích trên trang (BM25) | 22 | 0.000904 | 3 | 0.000539 | 0 | 1% |

## Lỗi

- Đồ thị + câu trích trên trang (BM25): RETRY_LIMIT_REACHED ×2

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
