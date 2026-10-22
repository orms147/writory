# Fact mới với đề extract-7 (D-95): phát lại trên 10 chương của run-ky-ao-vua-1

Người đọc: Claude, 22/10/2026. Cách làm như D-92 và D-93 (`../2026-10-22-extract-recall-v6-1/notes.md`, `../2026-10-22-new-facts-replay-1/notes.md`): `StoryRun` thật trên kho trong bộ nhớ, văn và dàn ý gốc, chỉ vai trích gọi model thật. Mã: đề `extract-7`, chống trùng với `related_overlap` 0,5 tính trên tập nhỏ hơn (**bản đầu**, trước hai sửa cuối); commit D-95 sau đó đổi sang 0,65 một chiều và thêm luật không ghi `KNOWS` đã mở. Một lần phát lại. Chi phí 0,0296 USD (trần giao 0,05); không còn đủ trần cho lần thứ hai nên **bản cuối chưa được đo**.

## Số đo
| | D-93 (`extract-6`) | D-95 bản đầu (`extract-7`) |
|---|---|---|
| Fact mới | 26 | 20 |
| Quyết định / ý định / nhận xét thuần | 9 (4 ít giá trị) | 0 |
| Chấp thuận, cho phép (hành vi, vẫn hợp lệ) | trong 9 | 3 (`c5s2_1`, `c8s1_1`, `c10s1_2`) |
| `derive` (`graph_agrees`) | 17/39 | 15/39, 17/39 sau khi bỏ 3 `KNOWS` trùng (offline) |
| Fact bị bỏ vì trùng (remap) | 0 | 6 (ch3 ×1, ch6 ×1, ch8 ×4 gồm lượt viết lại) |
| Fact bị luật mồ côi bỏ | — | 2 (ch5, ch7; lượt viết lại, Fact sau lượt viết lại vẫn có) |
| Vai trích: chi phí / token vào / ra | 0,0287 / 225 nghìn / 21 nghìn | 0,0296 / 240 nghìn / 24 nghìn |
| Viết lại / `teller_does_not_know` | 4 / 5 | 6 / 5 |

## Vì sao `derive` tụt 17 → 15, và cách sửa
Ba `KNOWS` bị ghi thêm lên cặp đã có `KNOWS` đang hiệu lực: ch3 `protagonist → fact_dau_gia_bien_mat`, ch6 `→ fact_luu_tu_nguyet_cuu_dan`, ch8 `→ fact_tran_mac_ban_tin`. Đường remap (Fact trùng thì dùng lại id cũ) chuyển `KNOWS` sang Fact cũ mà không kiểm cặp đã có. `derive` đòi đúng một cạnh nên knows-03 (`edge_since`) và knows-07 (`edge_prop`) lỗi. Bỏ ba cạnh này khỏi đồ thị đã chụp thì `derive` lên 17/39 (kiểm offline bằng cùng mã chấm). Đã sửa: `to_package` không ghi `KNOWS` mà cặp đã có (test `test_knows_already_open_is_not_written_again_when_a_duplicate_is_remapped`).

## 20 Fact đọc tay
- **Cụ thể, trung tính, bám trang (17):** `c1s1_1` (nhân vật chính kéo đứa trẻ), `c1s1_2` (Vân Chi nắm tay ông lão), `c1s2_1`, `c2s1_1`, `c2s1_2`, `c3s1_1`, `c3s2_1`, `c4s2_1`, `c4s2_2`, `c5s1_1`, `c6s1_1`, `c7s1_1`, `c8s2_1`, `c9s1_1`, `c9s1_2`, `c10s1_1`, `c10s2_1`.
- **Hành vi chấp thuận hay cho phép (3):** `c5s2_1` (đồng ý giữ kín lối xuống), `c8s1_1` (cho Trần Mặc đi theo với điều kiện), `c10s1_2` (Trần Mặc đồng ý nói trước quyết định). Là hành vi, không phải ý nghĩ; giữ.
- **Còn nghi trùng:** `c4s2_1` ("Vân Chi chụp cổ tay một người đang trượt khỏi mép") nói gần như cùng chuyện `c1s1_2` ở chương 1; `c3s2_1` và `c4s2_2` đều là "vệt kéo"; `c9s1_2` và `c7s1_1`. Ngưỡng cũ không bắt vì chương khác nhau, thực thể `ABOUT` khác hay hệ số thấp.
- Chỉ 1 Fact `user_authored` (`c5s2_1`), do câu "quyết định" của nhân vật chính bị đề mới loại; Fact kể nhân vật chính dùng "Nhân vật chính", trung tính.

## 13 câu "không có nút" (D-92), đọc tay
Có đáp án: alive-01 (`c1s1_1`), alive-02 (`c1s1_2`), knows-13 (`c2s1_1`) = **3/13**. D-93: 6/13 (item-07, 08, alive-01, 04, knows-12, 13).
- Mất so với D-93: item-07, item-08 (Fact Trần Mặc xin mượn thẻ bị bỏ vì **câu trích không nguyên văn**, G3, ở ch4 cảnh 1, một lần lệch của model; không do đề), alive-04 (không có Fact "chưa chắc đã chết" ở lần này), knows-12 (Fact điều khoản bị gộp vào `fact_tran_mac_ban_tin` bởi ngưỡng trùng 0,5 cũ).
- Mới có so với D-93: alive-02.
- Hai nguyên nhân: biến thiên giữa các lần chạy của model (câu trích, Fact nào được chọn) và ngưỡng trùng cũ; chỉ nguyên nhân thứ hai đã sửa trong mã. Một lần chạy mỗi bên không tách được hai thứ.

## Chưa kiểm
- Mã cuối (ngưỡng 0,65 một chiều, `KNOWS` đã mở) chưa phát lại; bài A chưa chạy lại (hết trần).
- Độ phủ nhóm 13 câu có thể giữ nguyên hay tụt thật vì đề hạn chế hơn: cần một lần phát lại nữa (~0,03 USD), tốt nhất hai lần để thấy biến thiên.
