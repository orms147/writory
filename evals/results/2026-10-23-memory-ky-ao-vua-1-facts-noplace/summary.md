# Bài A: bộ nhớ, kết quả

- Đề: CHỦ DỰ ÁN DUYỆT 22/10/2026; truyện `evals/results/2026-10-22-new-facts-replay-1`; questions v1, run v2.
- Commit `3754252549df`; model trả lời `openai/gpt-6-luna` (suy luận low); tóm tắt `openai/gpt-6-luna`.
- Chạy khô (model giả): False. Nền đồ thị: neo4j.
- Lượt khai mỗi hệ: 117 (câu × lần hỏi). Đúng = đúng đáp án gốc; kiêng = trả "Không biết" (không tính đúng); lượt lỗi hay chưa chạy tính chưa đúng.
- Đã tiêu: 0.0244 USD. Dừng sớm: không.

## Độ chính xác chung

| Hệ | Đúng [CI 95%] | Kiêng | Ngữ cảnh TB (ký tự) | Chi phí trả lời | Chi phí dựng | USD / câu |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 74% (86/117) [65–81] | 30 | 11265 | 0.0244 | 0.0000 | 0.0002 |

## Theo nhóm câu hỏi

| Hệ | đồ vật | sống / chết | ai biết gì | quan hệ hiện tại | lời nói dối |
|---|---|---|---|---|---|
| Đồ thị WriTory | 85% (28/33) | 73% (11/15) | 69% (33/48) | 67% (14/21) | — |

## Câu nhớ và câu suy luận (`inference`, tách riêng)

| Hệ | Câu nhớ | Câu suy luận |
|---|---|---|
| Đồ thị WriTory | 75% (83/111) | 50% (3/6) |

## Đồ thị bộ trích có đáp án hay không (`graph_agrees`, D-83)

Đáp án gốc lấy từ trang. "Có đáp án": đồ thị bộ trích đã dựng cho đúng đáp án ở chương được hỏi (code kiểm). "Thiếu hoặc sai": đồ thị không có hoặc nói khác.

| Hệ | Đồ thị có đáp án | Đồ thị thiếu hoặc sai |
|---|---|---|
| Đồ thị WriTory | 92% (69/75) | 40% (17/42) |

## Theo khoảng cách (chương hỏi trừ chương của sự thật)

| Hệ | cách 0 chương | cách 1-2 chương | cách 3+ chương |
|---|---|---|---|
| Đồ thị WriTory | 100% (36/36) | 60% (9/15) | 62% (41/66) |

## Cache prompt (D-96)

Lượt lạnh: nhà cung cấp báo 0 token đọc từ cache; lượt có cache: báo > 0. Prompt lặp (lần hỏi thứ 2, 3 hoặc chạy lại trong vài chục phút) được cache nên rẻ hơn nhiều: so USD mỗi lời gọi giữa hai lần chạy chỉ có nghĩa khi tỉ lệ cache giống nhau. Giữ chỗ ngân sách và trần G8 vẫn tính theo giá lạnh.

| Hệ | Lời gọi lạnh | USD / lời gọi lạnh | Lời gọi có cache | USD / lời gọi có cache | Không rõ | Token vào được cache |
|---|---|---|---|---|---|---|
| Đồ thị WriTory | 37 | 0.000530 | 80 | 0.000061 | 0 | 68% |

Chi tiết từng lượt: `results.jsonl` (câu trả lời thô, điểm, chi phí từng lời gọi); lỗi: `errors.jsonl`; tóm tắt của hệ "tóm tắt": `summaries.jsonl`.
