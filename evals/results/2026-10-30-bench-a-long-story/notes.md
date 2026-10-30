# Bài đo A, hệ đồ thị trên truyện dài: so ngữ cảnh trước và sau sửa D-144 (30/10/2026)

Không gọi model. `support_dump.py` dựng ngữ cảnh của hệ `graph` và `graph_quotes` cho mọi câu của ba đề cũ (truyện mẫu `questions.yaml`, `questions-ky-ao-vua-1.yaml`, `questions-ky-ao-vua-1-facts.yaml`) rồi ghi `context_supports` (oracle) và độ dài chữ. Chạy từ `backend/`: `uv run python <đường dẫn>/support_dump.py <ra.json>` (`PYTHONIOENCODING=utf-8`).

- `before.json`: main `3ec3b85` (trước sửa). `after.json`: main `d1464e3` (có D-144, commit sửa `c855251`). Chạy lại `after.json` ở `d1464e3` ra đúng bản đã đo trên nhánh sửa.
- Mỗi khoá là `<đề>:<id câu>:<hệ>`, giá trị `[context_supports, độ dài chữ]`; 244 ngữ cảnh.

## Kết quả
- Truyện mẫu (88 ngữ cảnh) và `questions-ky-ao-vua-1.yaml` (78): **chữ và `context_supports` không đổi** ở mọi ngữ cảnh.
- `questions-ky-ao-vua-1-facts.yaml` (78): **30 ngữ cảnh đổi chữ** (khối vượt trần dòng giữ dòng khác), **7 oracle đổi từ sai sang đúng**, không cái nào đổi ngược lại: `alive-04` (`graph`), `item-07` (`graph`, `graph_quotes`), `item-08` (`graph`), `knows-12` (`graph`), `knows-13` (`graph`, `graph_quotes`). Gần khớp danh sách câu mà Fact mới phủ ở D-93 (thiếu `alive-01`, chỉ đúng ở `graph_quotes`).
- Hệ quả đã ghi ở D-144: số hệ đồ thị đo trước D-144 trên đề có Fact (D-93, D-95, D-96) không so thẳng được với số sau; model thật thấy ngữ cảnh khác ở 30 chỗ đó nên phải đo lại trước khi so. Số cũ của bài A trên đề truyện mẫu và đề 10 chương không có Fact vẫn so được.

## Giới hạn
Oracle (`context_supports`) chỉ nói ngữ cảnh có đủ chứng cứ để trả lời, không nói model trả lời đúng. Không có lượt model thật ở đây.
