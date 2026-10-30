# Cao trào bằng code (D-142): tính lại trên truyện đã lưu

Người đọc: Claude điều phối và chủ dự án, 30/10/2026. Kỳ vọng khai trước ở `expectations.md` (commit `b7bbd19`, trước khi viết `replay.py` và trước mọi phép tính; không sửa sau đó). **Không gọi model**, không Neo4j, chi 0 USD.

- **Cách đo:** `replay.py` dựng lại mục tiêu chương (`chapter_goals` + `render_chapter_goals`) của mọi chương đã ghi, từ `truth_dump.json` (kế hoạch, gói từng chương, dấu `milestones` trên nút `Chapter`), với `limits.context` của config hiện hành; chạy hai lần: checkout `main` `3ec3b85` ("cũ", đầu ra `replay_old.json`) và nhánh `feature/climax-code` commit `10af1f5f6346cd968422c7fc9562e82f1a0a1067` ("mới", `replay_new.json`, tree sạch). `compare.py` so và ghi `compare.json`. Lệnh: `cd backend && uv run python ../evals/results/2026-10-30-climax-code/replay.py <out.json>`, rồi `python compare.py old.json new.json`.
- **Config:** sha256 gộp `6304a5ab89aa4d935e8285c31772ef2a084406f1a8be0d069b866a17c06dbdf8` (`bench_run.config_sha256` trên `config/` của nhánh; có `climax_aftermath_chapters: 2`). Model: không có (không gọi model).
- **Dữ liệu:** bảy lượt có dấu mốc (`long-after-ky-ao-2` 24 chương, `long-after-ky-ao` 11, `long-after-tu-tien` 21, `psab-a1` 16, `psab-a2` 16, `psab-b1` 11, `psab-b1-r3` 16).

## Kỳ vọng và kết quả
| | khai trước | kết quả | |
|---|---|---|---|
| K1 | đúng 1 dấu cao trào đổi (tu-tiên m6, xong → ứng viên) | đúng 1: `long-after-tu-tien` m6 | **đúng** |
| K2 | mục "Mốc cốt truyện" khác ở tu-tiên ch20, ch21; ky-ao-2 ch17, ch18; các lượt khác không chương nào | đúng như vậy | **đúng** |
| K3 | dòng bước ngoặt giống hệt ở mọi chương | 0 chương khác | **đúng** |
| K4 | ngoài mục mốc không phần nào đổi (kể cả cờ `gap`) | **2 chương khác** (tu-tiên ch20, ch21), cả hai là cờ `gap` True → False | **sai** |
| K5 | tu-tiên ch20, ch21: m6 còn trong danh sách bộ trích được đánh dấu ở mới, không ở cũ | đúng hai chương đó | **đúng** |

## K4 sai: đọc được
Ở tu-tiên ch20 và ch21 bản cũ coi m6 là xong, nên chương chỉ còn mốc "đã xảy ra" và mốc kết ở xa: `gap` bật và đề thêm câu "Chương này không có mốc cốt truyện riêng, nên tự nó phải đổi tình thế…" (`milestone_gap`), vừa nói đã có mốc cao trào xong vừa nói không có mốc. Bản mới tính ứng viên là mốc đang diễn ra, nên `gap` tắt và câu đó biến mất. Đây là hệ quả của quyết định 1 chứ không phải lỗi, và là chỗ tôi dự đoán sai (`gap` suy ra từ trạng thái mốc, đáng lẽ phải thấy). Ghi lại, không sửa kỳ vọng (đúng điều đã khai).

## Chữ thay đổi (đọc `replay_old.json` / `replay_new.json`)
- ky-ao-2 ch17, ch18: câu "Mốc ĐÃ xảy ra rồi: không diễn lại, đi bước kế (xảy ra ở chương 16; cao trào, chương 16–18)" thành "Cao trào ĐÃ xảy ra rồi: không diễn lại mà viết HẬU QUẢ của nó (ai phải trả giá, điều gì đổi vĩnh viễn, ai phản ứng ra sao) (xảy ra ở chương 16; cao trào, chương 16–18)". Mốc kế tiếp (cao trào 20–23) giữ nguyên.
- tu-tiên ch20, ch21: câu "đã xảy ra rồi" thành "Mốc cao trào có dấu sớm nhưng CHƯA tính là đã xảy ra: nếu cao trào chưa thật sự diễn ra thì chương này đưa nó vào; nếu nó đã diễn ra rồi thì viết hậu quả của nó, không diễn lại (dấu sớm ở chương 19; cao trào, chương 20–22)".
- Bốn lượt 16 chương (`psab-*`, ky-ao): cao trào xong ở ch16, chương 17 chưa viết: không chương nào đổi.

## Chưa kiểm
- Replay giữ nguyên dấu của lượt gốc, nên không biết bộ trích (`extract-8`) có đánh dấu lại ứng viên trong khoảng không, không biết model viết có viết hậu quả tốt hơn không, và không biết ứng viên sai (tu-tiên m6) có kéo cao trào thật vào ch20–22 không. Cần lượt chạy có gọi model và đo khai trước riêng.
- Chỉ năm dấu cao trào (bốn cùng một dạng ở ch16), nên "1/5 đổi" không nói được tỉ lệ.
- Ứng viên không được xác nhận thì mốc cao trào được giục (câu `milestone_candidate`) trong cả khoảng; đây là cái giá đã nhận ở D-142, chưa đo tác hại.
