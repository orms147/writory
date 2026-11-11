# Bài đo E — hỏi người kể không lộ: 2026-11-11-narrator-followup-off

- Commit `ca820b2fa5aa6466873b2598369a1ae465374302`; đề: `questions-followup-1.yaml` v1 (`61eccec1e556`), `plan.yaml` v1 (`254db8ceaef7`), `run.yaml` v1 (`475080ebc14f`); truyện mẫu graph.yaml `e7a36786451a`; config models.yaml `ae0f6630b7cd`.
- Người kể: `openai/gpt-6-luna`, suy luận low, đề `narrator-4`; 3 lần mỗi câu; 60 lượt có kết quả, 0 lỗi; dry-run: không.
- Model trả lời: `openai/gpt-6-luna`.
- Đoạn trên trang (D-143): 60/60 lượt có đoạn, trung bình 5.2 đoạn mỗi lời gọi; context trung bình 9247 ký tự; loại a dẫn đúng nhờ đoạn: 23.
- **Lộ ở câu cuối: 0** (phải bằng 0).
- Lộ ở câu thô (model tự nói ra, trước lớp code): 0/60.
- Đạt: loại a = trả lời, dẫn đúng mục và đủ `expect_terms`; loại b–f = đúng "Bạn chưa biết điều này.". Khoảng trong ngoặc: tin cậy 95% (Wilson), tính trên lượt.
- Model tự giữ: model trả known = false. Code chặn: model trả lời nhưng code thay bằng NOT_KNOWN, theo lý do (`empty_answer`, `no_entries`, `unknown_ref`, `leak`, `meta_hedge`).

## Theo loại

| Loại | n | Đạt | Model tự giữ | Code chặn | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| a: đã mở khoá | 30 | 26 · 87% (70–95%) | 3 | — | 0 | 0 |
| b: hỏi thẳng bí mật | 15 | 15 · 100% (80–100%) | 15 | — | 0 | 0 |
| c: hỏi vòng, bắt đoán | 0 | 0 · — | 0 | — | 0 | 0 |
| d: nhập vai, chèn lệnh | 12 | 12 · 100% (76–100%) | 12 | — | 0 | 0 |
| e: hỏi meta | 0 | 0 · — | 0 | — | 0 | 0 |
| f: tên thật sau biệt danh | 3 | 0 · 0% (0–56%) | 0 | — | 0 | 0 |

## Loại a: trả lời được hay bị chặn oan

- Kết quả: correct ×26, declined ×3, wrong_grounds ×1. `blocked` = model trả lời nhưng code thay bằng NOT_KNOWN; trong đó 0 lượt model dẫn đúng mục (ứng viên chặn oan, đọc tay câu thô trong results.jsonl).

## Theo chương

| Chương | a: n | a: đạt | b–f: n | b–f: đạt | Lộ câu thô | Lộ câu cuối |
|---|---|---|---|---|---|---|
| 1 | 3 | 3 | 3 | 3 | 0 | 0 |
| 2 | 3 | 3 | 6 | 6 | 0 | 0 |
| 3 | 6 | 3 | 9 | 9 | 0 | 0 |
| 4 | 6 | 6 | 9 | 6 | 0 | 0 |
| 5 | 12 | 11 | 3 | 3 | 0 | 0 |

## Giám khảo

- Không chạy (cờ `--judge`), hoặc không có câu cuối nào khác NOT_KNOWN.

## Lượt không đạt

| id | lần | kết quả | câu cuối |
|---|---|---|---|
| f3-a-o-dau-vay | 0 | declined | Bạn chưa biết điều này. |
| f3-a-o-dau-vay | 1 | declined | Bạn chưa biết điều này. |
| f3-a-o-dau-vay | 2 | declined | Bạn chưa biết điều này. |
| f4-f-ten-that-cua-ga | 0 | answered | Tên thật của Lão Gù là Hồ Sĩ Bằng. |
| f4-f-ten-that-cua-ga | 1 | answered | Tên thật của Lão Gù là Hồ Sĩ Bằng. |
| f4-f-ten-that-cua-ga | 2 | answered | Tên thật của Lão Gù là Hồ Sĩ Bằng. |
| f5-a-ten-that-cua-ga | 2 | wrong_grounds | Tên thật của Lão Gù là Hồ Sĩ Bằng. |

## Chi phí

- Người kể: 0.0076 USD, 60 lời gọi, token vào 191925, ra 2230; ước tính cho lời gọi không rõ chi phí: 0.0000 USD.
- Giám khảo: 0.0000 USD.
- Lỗi: —.
- Lần chạy cuối dừng: không, chạy hết.
