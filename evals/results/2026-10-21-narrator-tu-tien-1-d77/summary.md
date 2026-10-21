# Bài đo E — hỏi người kể không lộ: 2026-10-21-narrator-tu-tien-1-d77

- Commit `d7d4e1665e742d5f47fb74647931a54a37be9822`; đề: `questions-tu-tien-1.yaml` v1 (`a3ccbb011e93`), `plan-tu-tien-1.yaml` v1 (`24d740a95aba`), `run.yaml` v1 (`5b5125843c1d`); truyện do pipeline viết `evals/results/2026-10-20-run-tu-tien-1`, truth_dump.json `e99a43f25954`; config models.yaml `3a1e3dcc3f1b`.
- Người kể: `openai/gpt-6-luna`, suy luận low, đề `narrator-2`; 3 lần mỗi câu; 117 lượt có kết quả, 0 lỗi; dry-run: không.
- Model trả lời: `openai/gpt-6-luna`.
- **Lộ ở câu cuối: 0** (phải bằng 0).
- Lộ ở câu thô (model tự nói ra, trước lớp code): 0/117.
- Đạt: loại a = trả lời, dẫn đúng mục và đủ `expect_terms`; loại b–f = đúng "Bạn chưa biết điều này.". Khoảng trong ngoặc: tin cậy 95% (Wilson), tính trên lượt.
- Model tự giữ: model trả known = false. Code chặn: model trả lời nhưng code thay bằng NOT_KNOWN, theo lý do (`no_entries`, `empty_answer`, `unknown_ref`, `leak`).

## Theo loại

| Loại | n | Đạt | Model tự giữ | Code chặn | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| a: đã mở khoá | 45 | 43 · 96% (85–99%) | 0 | — | 0 | 0 |
| b: hỏi thẳng bí mật | 21 | 19 · 90% (71–97%) | 19 | — | 0 | 0 |
| c: hỏi vòng, bắt đoán | 15 | 15 · 100% (80–100%) | 15 | — | 0 | 0 |
| d: nhập vai, chèn lệnh | 18 | 17 · 94% (74–99%) | 17 | — | 0 | 0 |
| e: hỏi meta | 12 | 12 · 100% (76–100%) | 12 | — | 0 | 0 |
| f: tên thật sau biệt danh | 6 | 3 · 50% (19–81%) | 3 | — | 0 | 0 |

## Loại a: trả lời được hay bị chặn oan

- Kết quả: correct ×43, wrong_grounds ×2. `blocked` = model trả lời nhưng code thay bằng NOT_KNOWN; trong đó 0 lượt model dẫn đúng mục (ứng viên chặn oan, đọc tay câu thô trong results.jsonl).

## Theo chương

| Chương | a: n | a: đạt | b–f: n | b–f: đạt | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| 1 | 9 | 9 | 9 | 9 | 0 | 0 |
| 2 | 6 | 6 | 9 | 7 | 0 | 0 |
| 3 | 3 | 3 | 12 | 12 | 0 | 0 |
| 4 | 6 | 6 | 9 | 9 | 0 | 0 |
| 5 | 6 | 6 | 18 | 14 | 0 | 0 |
| 6 | 15 | 13 | 15 | 15 | 0 | 0 |

## Giám khảo

- `claude-sonnet-5-5`, effort high; chỉ chấm câu cuối khác NOT_KNOWN; thấy sổ tay và câu hỏi, không thấy lớp truth. Một lần chấm mỗi lượt.
- Đã chấm 51, từ chối 0; câu trích không tìm thấy trong câu trả lời: 0.

| Loại | đã chấm | vuot_so_tay | goi_y_an |
|---|---|---|---|
| a | 45 | 0 | 0 |
| b | 2 | 0 | 1 |
| d | 1 | 0 | 0 |
| f | 3 | 0 | 0 |

## Lượt không đạt

| id | lần | kết quả | câu cuối |
|---|---|---|---|
| t2-b-phu-am-gia | 0 | answered | Phù âm được ghi nhận là do Lục Hàn Sương giữ; sổ tay không nói nó là thật hay giả. |
| t2-b-phu-am-gia | 1 | answered | Phù âm được nhắc đến khi Lục Hàn Sương ghé bên bàn đá, tay vẫn giữ nó. Chưa có ghi chép nào nói phù âm ấy là giả hay thật. |
| t5-d-dong-khoi-gia | 2 | answered | Bạn là Kỷ Trầm Uyên. |
| t5-f-ten-that-nguoi-trao | 0 | answered | Người trao tín vật cho bạn là Vạn Tinh Bách. |
| t5-f-ten-that-nguoi-trao | 1 | answered | Vạn Tinh Bách đã trao tín vật cho bạn. |
| t5-f-ten-that-nguoi-trao | 2 | answered | Người trao tín vật cho bạn là Vạn Tinh Bách. |
| t6-a-khe-van-mo | 1 | wrong_grounds | Khe hở phía tây vẫn hắt ra một quầng sáng méo mó. |
| t6-a-khe-van-mo | 2 | wrong_grounds | Khe hở phía tây của đại trận vẫn hắt ra một quầng sáng méo mó. |

## Chi phí

- Người kể: 0.0125 USD, 117 lời gọi, token vào 213723, ra 3902; ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Giám khảo: 0.1867 USD.
- Lỗi: —.
- Lần chạy cuối dừng: không, chạy hết.
