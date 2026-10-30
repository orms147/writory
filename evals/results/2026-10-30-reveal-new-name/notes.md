# Hé lộ lần hai dưới tên chính (D-136): kết quả

Khai trước: `expectations.md`. Code đo: nhánh `feature/reveal-new-name` (commit có file này). Config: `config/` của cùng commit. Phần A không gọi model.

## A. Tính lại bằng code, không gọi model
Lệnh: `cd backend && uv run python ../evals/results/2026-10-30-reveal-new-name/recompute.py`. Dữ liệu: `recompute.jsonl`.

- 503 chương đã ghi của 51 thư mục có `truth_dump.json` và chữ chương (`2026-10-20-run-tu-tien-2` không đọc được gói cũ, cũng không có chương). Tính dồn qua các chương.
- **37 cạnh tên mới trên 22 lượt**, mỗi cặp (lượt, nút) đúng một cạnh: 16 đồ vật, 9 nơi chốn, 6 phe, 6 nhân vật. Ở cả 37 cặp, lượt gốc không lần nào ghi tên mới đó (đếm trên mọi cạnh hé lộ của `truth_dump.json`), ví dụ trang gọi `co_hanh_chau` là "Cố Hành Chu" ở 15 chương liền (2–16) mà sổ tay vẫn hiện "Lão Cố" (`2026-10-29-run-long-after-tu-tien`), `ban_do_nep_gap` hiện "tấm giấy gấp" trong khi trang gọi "Bản đồ Nếp Gấp" (`2026-10-29-run-psab-a1`).
- 5 cạnh hé lộ lần đầu ra khác lượt gốc: do chạy trên cả chương thay vì từng cảnh, không phải luật mới; không tính.
- **KA1 đạt:** mọi `known_as` là tên chính của nút (khoá `name_key`), câu trích chứa nguyên văn (code; đọc lại 37 dòng).
- **KA2 đạt:** đọc tay cả 37 câu trích, câu nào cũng nói về đúng nút đó. Ca cần nhìn kỹ: "Dân Lạc Tinh Thôn được ở lại đảo" cho `lac_tinh_thon` (đúng làng; "Dân Lạc Tinh" của nút `dan_lac_tinh` lấy từ câu khác); "chính điện Thanh Vi", "khu luyện đan Thanh Vi" là tên chính của hai nơi chốn đã biết dưới tên ngắn.
- Điều thấy thêm, không phải kỳ vọng khai trước: chữ hiện lấy đúng chuỗi trang ("đội Tuần Muối" viết thường chữ đầu, D-17), và vài tên chính chỉ khác tên cũ một từ ("Chiếc Cọc Thề" thành "Cọc Thề", "lò cũ" thành "gian lò cũ").
- **Luật quyết A:** không có cạnh sai nút, giữ luật.

Quét thăm dò trước khi viết `expectations.md` (cùng dữ liệu, chưa chỉ tên chính) cho thấy lý do chỉ nhận tên chính: phần lớn cách gọi khác trên trang là biệt danh hay chức danh của nút đã biết tên thật ("Thuyền trưởng" của `tham_mac_ngon`, "Bạch trưởng lão", "Lục sư tỷ", "Trưởng môn Bạch"), nhận cả chúng thì tên hiện trong sổ tay đổi theo từng cách gọi.

## B. Phát lại bộ trích (chờ duyệt)
Chưa chạy: cần duyệt chi tiêu. Lệnh và trần: `expectations.md`, phần B.
