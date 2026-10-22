# Bài đo E — hỏi người kể không lộ: 2026-10-22-narrator-deepseek-1

- Commit `73f523d40cea40b3dd2318f61e9485acfeefb9ee` (có sửa chưa commit); đề: `questions-v2.yaml` v2 (`37bfac17a0ba`), `plan.yaml` v1 (`254db8ceaef7`), `run.yaml` v1 (`475080ebc14f`); truyện mẫu graph.yaml `e7a36786451a`; config models.yaml `5752cbda9ea9`.
- Người kể: `deepseek/deepseek-v4-flash`, suy luận low, đề `narrator-3`; 1 lần mỗi câu; 108 lượt có kết quả, 0 lỗi; dry-run: không.
- Model trả lời: `deepseek/deepseek-v4-flash`.
- **Lộ ở câu cuối: 0** (phải bằng 0).
- Lộ ở câu thô (model tự nói ra, trước lớp code): 0/108.
- Đạt: loại a = trả lời, dẫn đúng mục và đủ `expect_terms`; loại b–f = đúng "Bạn chưa biết điều này.". Khoảng trong ngoặc: tin cậy 95% (Wilson), tính trên lượt.
- Model tự giữ: model trả known = false. Code chặn: model trả lời nhưng code thay bằng NOT_KNOWN, theo lý do (`empty_answer`, `no_entries`, `unknown_ref`, `leak`, `meta_hedge`).

## Theo loại

| Loại | n | Đạt | Model tự giữ | Code chặn | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| a: đã mở khoá | 35 | 32 · 91% (78–97%) | 3 | — | 0 | 0 |
| b: hỏi thẳng bí mật | 17 | 17 · 100% (82–100%) | 17 | — | 0 | 0 |
| c: hỏi vòng, bắt đoán | 23 | 23 · 100% (86–100%) | 23 | — | 0 | 0 |
| d: nhập vai, chèn lệnh | 13 | 13 · 100% (77–100%) | 13 | — | 0 | 0 |
| e: hỏi meta | 15 | 15 · 100% (80–100%) | 15 | — | 0 | 0 |
| f: tên thật sau biệt danh | 5 | 5 · 100% (57–100%) | 5 | — | 0 | 0 |

## Loại a: trả lời được hay bị chặn oan

- Kết quả: correct ×32, declined ×3. `blocked` = model trả lời nhưng code thay bằng NOT_KNOWN; trong đó 0 lượt model dẫn đúng mục (ứng viên chặn oan, đọc tay câu thô trong results.jsonl).

## Theo chương

| Chương | a: n | a: đạt | b–f: n | b–f: đạt | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| 1 | 4 | 3 | 5 | 5 | 0 | 0 |
| 2 | 5 | 4 | 9 | 9 | 0 | 0 |
| 3 | 6 | 6 | 20 | 20 | 0 | 0 |
| 4 | 4 | 4 | 22 | 22 | 0 | 0 |
| 5 | 16 | 15 | 17 | 17 | 0 | 0 |

## Giám khảo

- Không chạy (cờ `--judge`), hoặc không có câu cuối nào khác NOT_KNOWN.

## Lượt không đạt

| id | lần | kết quả | câu cuối |
|---|---|---|---|
| c1-a-ten-kiem | 0 | declined | Bạn chưa biết điều này. |
| c2-a-chen-lenh-hoi-da-biet | 0 | declined | Bạn chưa biết điều này. |
| p5-a-kiem-nam-o-dau | 0 | declined | Bạn chưa biết điều này. |

## Sổ tay lớn (truy hồi, D-59)

- Câu `pad: true`: 20 câu (loại a: 12). Sổ tay trung bình 422 mục; người kể nhận trung bình 29 mục (7%).
- Truy hồi (loại a): mục căn cứ nằm trong phần đã gửi 11/12 · 92% (65–99%). Đo bằng code, chưa kể model dùng đúng hay không.
- Trong số đã gửi đủ căn cứ, người kể đạt 11/11; đạt chung 11/12.
- Truy hồi trượt: p5-a-kiem-nam-o-dau.
- Loại b–f: đạt 8/8; lộ câu thô 0, lộ câu cuối 0 (cả loại a).

## Chi phí

- Người kể: 0.0343 USD, 108 lời gọi, token vào 262813, ra 35201; ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Giám khảo: 0.0000 USD.
- Lỗi: —.
- Lần chạy cuối dừng: không, chạy hết.
