# Khai trước: đề dàn ý ch8 tu-tiên có/không dòng mốc "kế tiếp" m4

Khai TRƯỚC khi gọi model thật. Câu hỏi (giả thuyết 3 của `evals/results/2026-10-29-milestone-diagnosis/notes.md`): dòng mốc "kế tiếp" m4 ("Danh nghĩa của Ninh Tuyết Anh bị vạch rõ trước những người trên thuyền", khoảng 12–13), hiện từ ch6 vì m3 đã xong ở ch5, có đẩy dàn ý ch8 tới chỗ nhắc điều của bí mật `fact_su_gia_that` (khoảng lộ 11–13) hay không?

## Cách đo
- Ca: `evals/results/2026-10-29-run-long-after-tu-tien`, chương 8, **cảnh 2** (cảnh người canh báo `early_reveal` ở lượt gốc). Dựng lại đề dàn ý bằng chính `outline_messages` trên đồ thị đến hết ch7 (nạp gói chương từ `truth_dump.json` vào một truyện Neo4j tạm, xoá sau khi chạy), tóm tắt ch6–7, câu mở hai chương trước, tên cấm, mục tiêu chương dựng bằng `chapter_goals`; cảnh 1 là chữ chương đã ghi (cảnh trước), **không kèm gói thay đổi của cảnh 1** (không lưu riêng) và không có đoạn trích từ trang (`page_quotes_top_k` = 0 ở lượt gốc).
- Hai bên, **10 lời gọi mỗi bên**, cùng model, cùng mức suy luận, cùng đề trừ mục "### Mốc cốt truyện":
  - **A (có m4):** mục tiêu chương như lượt gốc, có dòng "Mốc kế tiếp … Danh nghĩa của Ninh Tuyết Anh bị vạch rõ…".
  - **B (không m4):** cùng mục tiêu chương nhưng bỏ hẳn mục "Mốc cốt truyện" (cờ `gap` giữ nguyên như A).
- Chấm: một dàn ý "trúng" nếu bất kỳ nhóm `leak_terms` nào của `fact_su_gia_that` có mọi cụm cùng nằm trong một nhịp/câu của dàn ý (đúng luật của bộ dò lộ `safety/leak.py`, so bỏ dấu, trọn từ). Chỉ chấm chữ của dàn ý (`goal`, `beats`, `ends_at`). Số liệu phụ (không dùng để quyết): dàn ý nhắc "Minh Ước" ở bất kỳ đâu.
- **Arm thăm dò C (khai thêm TRƯỚC khi gọi model, sau khi dựng đề thấy điều dưới đây):** cùng B nhưng bỏ thêm mạch `thread_lap_truong_su_gia` ("Ninh Tuyết Anh thật sự đại diện cho phe nào?", hạn gỡ ch7–13). Lý do: đề dàn ý ch8 dựng lại có mục "Mạch phải gỡ" ghi mạch này "Có thể gỡ ở chương này (hạn gỡ chương 7–13)", trong khi bí mật `fact_su_gia_that`, cùng nội dung, chỉ mở từ ch11. Mạch đó có trong cả A và B (và trong baseline), nên là yếu tố gây nhiễu độc lập với dòng mốc. C không dùng để quyết luật A/B dưới đây; chỉ để biết mạch có là nguồn đẩy chính hay không.
- 10 lời gọi mỗi bên, ba bên, 30 lời gọi dàn ý. Trần chi phí cứng `--budget 0.10`.

## Kỳ vọng và luật quyết (khai trước)
- Nếu giả thuyết đúng: A trúng nhiều hơn B.
- **Có tín hiệu** nếu `trúng(A) − trúng(B) ≥ 3` trên 10 lời gọi mỗi bên. Dưới 3 (kể cả A < B): **không phân biệt được**; không kết luận B tốt hơn. 10 lời gọi chỉ đủ phát hiện chênh lệch lớn: không có tín hiệu không nghĩa là không có tác động.
- Dừng ở đây dù kết quả thế nào: không chạy lượt 24 chương (hỏi lại writory-28).
- Đọc tay các dàn ý trúng của cả hai bên và ghi vào notes (nhắc đúng điều của bí mật hay chỉ trùng từ).
