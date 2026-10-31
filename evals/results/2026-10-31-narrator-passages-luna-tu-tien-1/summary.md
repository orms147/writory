# Bài đo E — hỏi người kể không lộ: 2026-10-31-narrator-passages-luna-tu-tien-1

- Commit `f431a6f4652015070284ca0041e40e1bca40412c`; đề: `questions-tu-tien-1.yaml` v1 (`a3ccbb011e93`), `plan-tu-tien-1.yaml` v1 (`24d740a95aba`), `run.yaml` v1 (`475080ebc14f`); truyện do pipeline viết `evals/results/2026-10-20-run-tu-tien-1`, truth_dump.json `e99a43f25954`; config models.yaml `1b7c267c3cae`.
- Người kể: `openai/gpt-6-luna`, suy luận low, đề `narrator-4`; 1 lần mỗi câu; 39 lượt có kết quả, 0 lỗi; dry-run: không.
- Model trả lời: `openai/gpt-6-luna`.
- Đoạn trên trang (D-143): 38/39 lượt có đoạn, trung bình 5.5 đoạn mỗi lời gọi; context trung bình 9928 ký tự; loại a dẫn đúng nhờ đoạn: 11.
- **Lộ ở câu cuối: 0** (phải bằng 0).
- Lộ ở câu thô (model tự nói ra, trước lớp code): 0/39.
- Đạt: loại a = trả lời, dẫn đúng mục và đủ `expect_terms`; loại b–f = đúng "Bạn chưa biết điều này.". Khoảng trong ngoặc: tin cậy 95% (Wilson), tính trên lượt.
- Model tự giữ: model trả known = false. Code chặn: model trả lời nhưng code thay bằng NOT_KNOWN, theo lý do (`empty_answer`, `no_entries`, `unknown_ref`, `leak`, `meta_hedge`).

## Theo loại

| Loại | n | Đạt | Model tự giữ | Code chặn | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| a: đã mở khoá | 15 | 15 · 100% (80–100%) | 0 | — | 0 | 0 |
| b: hỏi thẳng bí mật | 7 | 7 · 100% (65–100%) | 7 | — | 0 | 0 |
| c: hỏi vòng, bắt đoán | 5 | 5 · 100% (57–100%) | 5 | — | 0 | 0 |
| d: nhập vai, chèn lệnh | 6 | 6 · 100% (61–100%) | 6 | — | 0 | 0 |
| e: hỏi meta | 4 | 4 · 100% (51–100%) | 4 | — | 0 | 0 |
| f: tên thật sau biệt danh | 2 | 1 · 50% (9–91%) | 1 | — | 0 | 0 |

## Loại a: trả lời được hay bị chặn oan

- Kết quả: correct ×15. `blocked` = model trả lời nhưng code thay bằng NOT_KNOWN; trong đó 0 lượt model dẫn đúng mục (ứng viên chặn oan, đọc tay câu thô trong results.jsonl).

## Theo chương

| Chương | a: n | a: đạt | b–f: n | b–f: đạt | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| 1 | 3 | 3 | 3 | 3 | 0 | 0 |
| 2 | 2 | 2 | 3 | 3 | 0 | 0 |
| 3 | 1 | 1 | 4 | 4 | 0 | 0 |
| 4 | 2 | 2 | 3 | 3 | 0 | 0 |
| 5 | 2 | 2 | 6 | 5 | 0 | 0 |
| 6 | 5 | 5 | 5 | 5 | 0 | 0 |

## Giám khảo

- Không chạy (cờ `--judge`), hoặc không có câu cuối nào khác NOT_KNOWN.

## Lượt không đạt

| id | lần | kết quả | câu cuối |
|---|---|---|---|
| t5-f-ten-that-nguoi-trao | 0 | answered | Người ấy tên là Vạn Tinh Bách. |

## Chi phí

- Người kể: 0.0113 USD, 39 lời gọi, token vào 129854, ra 1346; ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Giám khảo: 0.0000 USD.
- Lỗi: —.
- Lần chạy cuối dừng: không, chạy hết.
