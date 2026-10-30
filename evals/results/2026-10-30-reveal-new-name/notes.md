# Hé lộ lần hai dưới tên chính (D-136): kết quả

Khai trước: `expectations.md` (commit 4febfc4, trước mọi lời gọi). Phần A không gọi model. Phần B: code ở commit `79a343f82f5feaee9a86ab5b6d7b17e0589029e7` (`meta.json`, cây sạch), config `combined` sha256 `194e9aa655c67f9d1041f05b3735c87aa7051436e9217a9b5905778067497518` (`bench_run.config_sha256`), model `openai/gpt-6-luna`, suy luận `low`, vai `extract`.

**Kết luận: tín hiệu xấu theo luật khai trước (K1 sai). Không gộp `extract-10`; đề bộ trích giữ `extract-8`; phần code của D-136 giữ.**

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

## B. Phát lại bộ trích `extract-8` và `extract-10`
Lệnh (chủ dự án duyệt chi tiêu, chạy một mình): `cd backend && PYTHONIOENCODING=utf-8 uv run python ../evals/results/2026-10-30-reveal-new-name/replay.py --budget 0.08`. Dữ liệu: `results.jsonl`, `calls.jsonl`, `meta.json`; chữ đề `extract8_system_prompt.txt`, `extract10_system_prompt.txt`. Chạy lại đúng như lần đo cần checkout commit trên (đề `extract-10` không còn trong code).

- 20/20 lời gọi xong, không dừng vì trần, không ca nào bỏ. Chi thật **0,0301 USD** (`extract-8` 0,0147; `extract-10` 0,0154), lời gọi đắt nhất 0,0024 USD, 5 506–16 845 token đề, mọi lời gọi `finish_reason: stop`. Ước tính trước 0,05–0,07 USD: thấp hơn ước tính.

| Kỳ vọng | Kết quả | |
|---|---|---|
| K1 (P0, truyện mẫu ch5: ghi `ly_that` "Lý Thất") | `extract-10` không ghi cạnh hé lộ lần hai nào; `extract-8` cũng không | **sai** |
| K2 (P1–P5, ít nhất 4/7 tên mới được nhận) | `extract-10` 0/7; `extract-8` 0/7 | **sai** |
| K3 (C1–C3, không hé lộ lần hai được nhận; bị bỏ nhiều nhất 2) | cả hai bản: 0 hé lộ lần hai, không cạnh nào bị bỏ | đúng |
| K4 (C4: hé lộ đầu `ly_that` bằng tên trên trang) | cả hai bản: `known_as` "gã lái đò mặt sẹo" | đúng |
| K5 (cạnh `extract-10` bị bỏ vì lý do khác D-136 ≤ `extract-8` + 3) | `extract-10` 6, `extract-8` 1 | **sai** |

- Hé lộ lần hai duy nhất model ghi (đọc tay): `extract-10`, P1, `co_hanh_chau` `known_as` "Cố Hành Chu", câu trích "Cố Hành Chu đã ghìm bánh lái." Trang có "Cố Hành Chu ghìm bánh lái." (không có "đã"), nên `to_package` bỏ vì câu trích không nguyên văn (G3), đúng luật. Tên và nút đúng; chỉ câu trích sai.
- 6 cạnh `extract-10` bị bỏ vì lý do khác: P0 1 (nhóm "sai schema cạnh", bản `extract-8` cũng có đúng một), P1 1 (câu trích ở trên), P2 4 (2 "sai schema cạnh", 2 Fact mới thiếu `KNOWS`). Nhóm "sai schema cạnh" là lý do ngoài danh sách của bộ đo; chữ gốc không lưu, nên không biết cụ thể.
- Một lời gọi mỗi bản đề mỗi ca là nhiễu (khai trước): đọc là tín hiệu, không phải đã đo. Không sửa đề lần hai trong nhánh này.
- Theo luật quyết khai trước: K1 sai nên là **tín hiệu xấu**. Bỏ phần đề (chữ đề và dòng cạnh "người chơi biết là"), giữ `extract-8`; giữ luật code `new_name_problem`, tự hé lộ tên chính, `to_package` áp luật cho cạnh bộ trích ghi.
- Suy luận, chưa kiểm: model ở mức suy luận `low` theo đề cũ ở hầu hết chương (không ghi lại nút đã hé lộ), có thể vì luật mới là ngoại lệ trong một đoạn dài. Lần thử sau cần phép đo khai trước mới.
