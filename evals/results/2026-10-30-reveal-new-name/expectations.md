# Khai trước: hé lộ lần hai dưới tên chính (D-136)

Khai TRƯỚC khi gọi model thật (commit này đi trước mọi lời gọi). Đo hai phần của D-136: (A) tự hé lộ tên chính mới bằng code, tính lại trên lượt đã lưu, không gọi model; (B) đề bộ trích `extract-10` so với `extract-8`, phát lại trên chương đã lưu, có gọi model, chờ duyệt.

## A. Tính lại bằng code (không gọi model)
- Lệnh: `cd backend && uv run python ../evals/results/2026-10-30-reveal-new-name/recompute.py`. Kết quả: `recompute.jsonl`, số liệu ở `notes.md`.
- Mọi chương đã ghi của mọi thư mục `evals/results/*/` có `truth_dump.json` và `chapters/`: chạy `auto_reveals` của nhánh trên toàn chữ chương (sản phẩm chạy từng cảnh) với player_view cuối chương của lượt gốc, `no_new_name` như sản phẩm (nút được bảo vệ ở đường người chơi so với đầu chương, nút đã hé lộ trong chương). Tính dồn: tên mới của chương trước vào trạng thái chương sau.
- Đã chạy một lần quét thăm dò trước khi viết file này (chương nào có tên lớp truth người chơi chưa biết trên trang), nên phần A không phải đo mù; nó tất định.
- **KA1:** mọi cạnh thêm là tên chính (`name`) của nút, câu trích chứa tên nguyên văn (G3). Code bảo đảm; kiểm lại bằng đọc.
- **KA2:** đọc tay MỌI cạnh thêm (hay 40 cạnh đầu nếu nhiều hơn): câu trích nói về đúng nút đó. Kỳ vọng 0 cạnh sai nút.
- **Luật quyết A:** có cạnh sai nút thì siết luật trước khi gộp; không thì giữ.

## B. Phát lại bộ trích `extract-8` và `extract-10` (gọi model, chờ duyệt)
- Lệnh (một mình, không song song với lượt khác dùng cùng key): `cd backend && uv run python ../evals/results/2026-10-30-reveal-new-name/replay.py --budget 0.08`. Chạy thử không tốn tiền: thêm `--dry-run`.
- Mỗi ca = một chương đã ghi, một lời gọi cho cả chương (sản phẩm: mỗi cảnh một lời gọi). Đề dựng lại từ `truth_dump.json` (danh mục, cạnh đang hiệu lực đến hết chương trước kèm `known_as`, mạch phải gỡ, mốc, luật Fact mới của config); truyện mẫu dựng từ `data/sample-story/` (như bài C, không kế hoạch). Hai bản đề cùng model, cùng mức suy luận: `extract-8` (đề ở main, lưu ở `extract8_system_prompt.txt`, dòng cạnh không có tên người chơi biết) và `extract-10` (nhánh này). Đầu ra của cả hai qua cùng `to_package` của nhánh (luật D-136, `locked` theo kế hoạch).
- Chấm: cạnh `REVEALED_TO_PLAYER` từ nút có tên ĐÃ có trong player_view đầu chương ("hé lộ lần hai"), nhận hay bị bỏ (lý do); hé lộ lần đầu của nút chưa biết và `known_as` của nó; số cạnh bị bỏ theo nhóm lý do. Ngoài các mục đó không chấm.
- "Tên mới đúng" của mỗi ca = tên chính mà `auto_reveals` của nhánh tìm thấy trên trang cho nút đã biết (tính trước, in ở `--dry-run`).

### Các ca (thứ tự ưu tiên; hết ngân sách thì ca sau không chạy, ghi là không chạy)
| Ca | Nguồn | Chương | Tên mới đúng |
|---|---|---|---|
| P0 | truyện mẫu | 5 | `ly_that` "Lý Thất" (biệt danh "gã lái đò mặt sẹo" từ ch4; tên thật bị giấu, luật a của D-61: chỉ bộ trích mở được) |
| C4 | truyện mẫu | 4 | không (ly_that ra mắt lần đầu bằng biệt danh) |
| P1 | `2026-10-29-run-long-after-tu-tien` | 2 | `co_hanh_chau` "Cố Hành Chu" (biết là "Lão Cố") |
| C2 | `2026-10-29-run-long-tu-tien-3` | 12 | không (đã biết "Cố Hành Chu", trang gọi "Lão Cố") |
| P2 | `2026-10-28-run-ab-trinh-tham-cu-2` | 6 | `tran_tan` "Trần Tấn" (biết là "ông Tấn"), `cong_an_khu_vuc` "công an khu vực" (biết là "công an") |
| C1 | `2026-10-21-run-ky-ao-vua-2` | 2 | không (trang dùng chức danh "Trưởng môn Bạch", "Nguyên lão") |
| P3 | `2026-10-22-run-long-tu-tien-2` | 5 | `han_tu_nguyet` "Hàn Tố Nguyệt" (biết là "Tố Nguyệt") |
| C3 | `2026-10-29-run-long-after-ky-ao-2` | 10 | không |
| P4 | `2026-10-29-run-long-ky-ao-hanh-trinh-1` | 2 | `ban_do_nep_gap` "Bản đồ Nếp Gấp" (biết là "tấm bản đồ") |
| P5 | `2026-10-22-run-ky-ao-vua-3` | 6 | `lenh_goi_thu_nhat` "Lệnh Gọi Thứ Nhất", `lenh_goi_thu_hai` "Lệnh Gọi Thứ Hai" (biết là "hai tờ lệnh") |

Ước tính: 10 ca × 2 bản đề = 20 lời gọi. Lời gọi bộ trích cả chương ở lần đo D-129 tốn 0,0025–0,0035 USD (`../2026-10-30-extract-milestone-kind/calls.jsonl`); truyện mẫu ngắn hơn. Ước tính tổng 0,05–0,07 USD; trần cứng `--budget 0.08`.

### Kỳ vọng
- **K1 (P0):** `extract-10` ghi `ly_that` `known_as` "Lý Thất", được nhận. `extract-8` không ghi.
- **K2 (P1–P5, 7 tên mới đúng):** `extract-10` ghi và được nhận ít nhất 4/7; `extract-8` ghi được nhận nhiều nhất 1/7.
- **K3 (C1–C3):** `extract-10` không có hé lộ lần hai nào được nhận; hé lộ lần hai bị bỏ (đã biết, biệt danh) tổng cộng nhiều nhất 2.
- **K4 (C4):** `extract-10` hé lộ lần đầu `ly_that` bằng tên trên trang ("gã lái đò mặt sẹo" hay tương đương), không bằng "Lý Thất".
- **K5:** trên mọi ca, số cạnh `extract-10` bị bỏ vì lý do KHÔNG phải của D-136 không quá số của `extract-8` cộng 3.

### Luật quyết (khai trước)
- Một lời gọi mỗi bản đề mỗi ca là NHIỄU: đọc kết quả là "tín hiệu", không phải "đã đo".
- **Tín hiệu tốt** (gộp `extract-10`): K1, K3, K4 cùng đúng và K2 đạt.
- **Tín hiệu xấu** (không gộp đề, giữ `extract-8`; phần code của D-136 vẫn gộp): K1 sai, hoặc K3 có một hé lộ lần hai được nhận, hoặc K4 sai.
- **Lẫn lộn** (K1 đúng nhưng K2 hay K5 không đạt, hay K3 bị bỏ quá 2): ghi lại, chủ dự án quyết.
- Mọi hé lộ lần hai (nhận hay bỏ) được đọc tay: câu trích có thật nói về nút đó bằng tên đó không; ghi vào `notes.md`. Không chỉnh đề lần hai trong nhánh này.
