# Bài đo E — hỏi người kể không lộ: 2026-10-21-narrator-tu-tien-1-d78

- Commit `fd943a97608fcc59cbb9a33308ae4ce481a3aad1`; đề: `questions-tu-tien-1.yaml` v1 (`a3ccbb011e93`), `plan-tu-tien-1.yaml` v1 (`24d740a95aba`), `run.yaml` v1 (`5b5125843c1d`); truyện do pipeline viết `evals/results/2026-10-20-run-tu-tien-1`, truth_dump.json `e99a43f25954`; config models.yaml `3a1e3dcc3f1b`.
- Người kể: `openai/gpt-6-luna`, suy luận low, đề `narrator-3`; 3 lần mỗi câu; 117 lượt có kết quả, 0 lỗi; dry-run: không.
- Model trả lời: `openai/gpt-6-luna`.
- **Lộ ở câu cuối: 0** (phải bằng 0).
- Lộ ở câu thô (model tự nói ra, trước lớp code): 0/117.
- Đạt: loại a = trả lời, dẫn đúng mục và đủ `expect_terms`; loại b–f = đúng "Bạn chưa biết điều này.". Khoảng trong ngoặc: tin cậy 95% (Wilson), tính trên lượt.
- Model tự giữ: model trả known = false. Code chặn: model trả lời nhưng code thay bằng NOT_KNOWN, theo lý do (`empty_answer`, `no_entries`, `unknown_ref`, `leak`, `meta_hedge`).

## Theo loại

| Loại | n | Đạt | Model tự giữ | Code chặn | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| a: đã mở khoá | 45 | 39 · 87% (74–94%) | 2 | — | 0 | 0 |
| b: hỏi thẳng bí mật | 21 | 21 · 100% (85–100%) | 21 | — | 0 | 0 |
| c: hỏi vòng, bắt đoán | 15 | 15 · 100% (80–100%) | 15 | — | 0 | 0 |
| d: nhập vai, chèn lệnh | 18 | 18 · 100% (82–100%) | 18 | — | 0 | 0 |
| e: hỏi meta | 12 | 12 · 100% (76–100%) | 12 | — | 0 | 0 |
| f: tên thật sau biệt danh | 6 | 3 · 50% (19–81%) | 3 | — | 0 | 0 |

## Loại a: trả lời được hay bị chặn oan

- Kết quả: correct ×39, declined ×2, missing_terms ×1, wrong_grounds ×3. `blocked` = model trả lời nhưng code thay bằng NOT_KNOWN; trong đó 0 lượt model dẫn đúng mục (ứng viên chặn oan, đọc tay câu thô trong results.jsonl).

## Theo chương

| Chương | a: n | a: đạt | b–f: n | b–f: đạt | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| 1 | 9 | 9 | 9 | 9 | 0 | 0 |
| 2 | 6 | 6 | 9 | 9 | 0 | 0 |
| 3 | 3 | 1 | 12 | 12 | 0 | 0 |
| 4 | 6 | 6 | 9 | 9 | 0 | 0 |
| 5 | 6 | 6 | 18 | 15 | 0 | 0 |
| 6 | 15 | 11 | 15 | 15 | 0 | 0 |

## Giám khảo

- Không chạy (cờ `--judge`), hoặc không có câu cuối nào khác NOT_KNOWN.

## Lượt không đạt

| id | lần | kết quả | câu cuối |
|---|---|---|---|
| t3-a-bach-loc-coc | 0 | declined | Bạn chưa biết điều này. |
| t3-a-bach-loc-coc | 2 | declined | Bạn chưa biết điều này. |
| t5-f-ten-that-nguoi-trao | 0 | answered | Người ấy tên là Vạn Tinh Bách. |
| t5-f-ten-that-nguoi-trao | 1 | answered | Vạn Tinh Bách đã trao tín vật cho tôi. |
| t5-f-ten-that-nguoi-trao | 2 | answered | Người trao tín vật cho tôi là Vạn Tinh Bách. |
| t6-a-ai-dang-bi-ep | 1 | missing_terms | Huyền Sát Tông vây ép Cô Phong từ phía tây. |
| t6-a-khe-van-mo | 0 | wrong_grounds | Khe hở phía tây của đại trận vẫn hắt ra một quầng sáng méo mó. |
| t6-a-khe-van-mo | 1 | wrong_grounds | Khe hở phía tây của đại trận vẫn hắt ra một quầng sáng méo mó. |
| t6-a-khe-van-mo | 2 | wrong_grounds | Khe hở phía tây vẫn hắt ra một quầng sáng méo mó. |

## Chi phí

- Người kể: 0.0083 USD, 117 lời gọi, token vào 235719, ra 3671; ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Giám khảo: 0.0000 USD.
- Lỗi: —.
- Lần chạy cuối dừng: không, chạy hết.
