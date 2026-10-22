# Fact mới với đề extract-7, mã cuối của D-95: hai lần phát lại (replay-3 và replay-4)

Người đọc: Claude, 22/10/2026. Cách làm như `../2026-10-22-new-facts-replay-2/notes.md`: `StoryRun` thật trên kho trong bộ nhớ, văn và dàn ý gốc của `run-ky-ao-vua-1`, chỉ vai trích gọi model thật. Mã: đề `extract-7`, `related_overlap` 0,65 một chiều, không ghi `KNOWS` đã mở. Quy tắc quyết định khai trước với `writory-2a`: cả hai lần có một câu nhóm 13 ≥ 5/13, `derive` ≥ 17/39, Fact quyết định hay ý định ≤ 1 mỗi lần thì giữ `extract-7`; cả hai ≤ 4/13 thì nới đề; còn lại là **lẫn lộn**, báo lại.

**Khác biệt mã giữa hai lần:** replay-3 chạy trước sửa `_human_protagonist` (id nội bộ `protagonist` lọt vào chữ 4 Fact, ví dụ "Protagonist kéo một đứa trẻ…"); replay-4 chạy sau sửa (Fact kể "nhân vật chính"). Hai lần không cùng mã nên không phải hai mẫu thuần của cùng một cấu hình, nhưng phần sửa chỉ đổi chữ trong Fact, không đổi Fact nào được giữ.

## Số đo
| | replay-3 | replay-4 |
|---|---|---|
| Chương xong | 9/10 (dừng ở chương 10 vì trần chi phí giữ chỗ) | 10/10 |
| Chi phí vai trích | 0,0286 USD | 0,0276 USD |
| Fact mới | 21 | 21 |
| `derive` (`graph_agrees`) | 17/39 | 17/39 |
| Nhóm 13 câu có đáp án (từ khoá khai trước, đọc lại tay) | **6/13** (item-07, item-08, alive-01, alive-02, knows-12, knows-13) | **2/13** (knows-12, knows-13) |
| Quyết định / ý định thuần | 0 | 0 |
| Viết lại / `teller_does_not_know` | 6 / 3 | 3 / 2 |

Chấm bằng `facts_score.py` và `recall.py` (kịch bản ngoài repo, từ khoá khai trước khi xem kết quả; đã đọc tay các Fact khớp). Tổng hai lần: 0,0562 USD trên trần 0,07.

## Đọc tay
- **Quyết định/ý định:** ba Fact bị cờ từ khoá ("xin mượn", "đặt … vào tay", "đồng ý nói trước mặt … mọi quyết định") đều là hành vi hay lời hứa nêu trên trang, không phải ý nghĩ. `fact_c2s2_1` của replay-3 ("nhận ra nét khắc giống dấu hiệu nhà họ Phó") là điều nhân vật chính nhận thấy; chỉ ở ranh giới, không tính vào ý định thuần.
- **Vì sao 6 → 2:** replay-4 không có Fact nào ở chương 1 cảnh 1 (alive-01, alive-02: kéo đứa trẻ, nắm tay ông lão) và không có Fact "mượn thẻ" ở chương 4 (item-07, item-08). Thử riêng cảnh ch4 cảnh 1 ba lần (khoảng 0,003 USD, ngoài hai lần phát lại): hai lần model ghi Fact mượn thẻ với câu trích nguyên văn, một lần ghi nhưng câu trích đổi "Ta" thành "Tôi", G3 bỏ. Nghĩa là cùng một cảnh, cùng đề, cùng mã: Fact này có hay không là do biến thiên của model, không do đề. Với hai lần, kết luận chắc chắn duy nhất là độ phủ nhóm 13 câu dao động mạnh (2–6/13), chưa đủ mẫu để nói đề `extract-7` làm tụt độ phủ hay không.
- **Chống trùng, luật mồ côi:** replay-4 có 1 Fact remap vì trùng, 2 Fact bị luật mồ côi bỏ, 1 thiếu `KNOWS`, 1 trượt G3, 3 ref bị bỏ. Không còn `KNOWS` trùng cặp (nguyên nhân `derive` tụt xuống 15 ở replay-2).
- Chương 10 của replay-3 không có: trần giữ chỗ của `BudgetedClient` dừng chạy sớm khoảng 0,009 USD.

## Chưa kiểm
- Bài A (`bench-a-run`) chưa chạy lại trên đồ thị có Fact mới của đề này.
- Hiệu quả của chuẩn hoá `protagonist` chỉ kiểm bằng test và so chữ hai lần (replay-4 không còn "Protagonist" trong chữ Fact).
- Số lần phát lại quá ít để tách biến thiên của model khỏi tác động của đề.
