# Fact mới do bộ trích tạo (D-93): phát lại trên 10 chương của run-ky-ao-vua-1

Người đọc: Claude, 22/10/2026. Cách làm y hệt D-92 (`../2026-10-22-extract-recall-v6-1/notes.md`): `StoryRun` thật trên kho trong bộ nhớ, `--setup-from` thư mục `2026-10-21-run-ky-ao-vua-1`, văn và dàn ý gốc, chỉ vai trích gọi model thật (`openai/gpt-6-luna`, suy luận low). Khác ở đề `extract-6` (có `new_facts`) và mã của D-93 ở commit `87f8498` (trước luật bỏ Fact mồ côi). Một lần phát lại.

Chi phí: lần chạy này 0,0287 USD (vai trích). Một lần phát lại trước đó bị ngắt ở chương 9 (không có `truth_dump.json`, thư mục đã xoá) tốn khoảng 0,0247 USD. Bài A: 0,0420 USD (`../2026-10-22-memory-ky-ao-vua-facts-1/`). Tổng lượt này 0,0954 USD (trần giao 0,12).

## Số đo
| | không Fact mới (D-92, 2 lần) | có Fact mới |
|---|---|---|
| `graph_agrees` bằng `derive` | 17/39, 17/39 | 17/39 (13 câu cũ vẫn đúng) |
| Fact mới | 0 | 26 (mỗi chương 2–3; trần 3) |
| Cạnh bộ trích bỏ | — | 2 (G3: 1 câu trích sai, 1 `KNOWS` nhân vật chính không câu trích) |
| Vai trích: chi phí / token vào / token ra | 0,0173–0,0183 / 154 nghìn / 13 nghìn | 0,0287 / 225 nghìn / 21 nghìn (+55–65% chi phí) |
| Viết lại / `teller_does_not_know` | 3 / 0 (luật rộng), 2–3 / 1–2 (luật hẹp, chưa đủ 10 chương) | 4 / 5 |
- `derive` chỉ phủ 17 trong 39 câu nên `graph_agrees` không thấy lợi ích của Fact mới; phần dưới đọc tay.

## 13 câu "không có nút trong danh mục" (D-92), đọc tay trên đồ thị mới
Có đáp án = một Fact mới (hay Fact kèm ABOUT/KNOWS) có chữ trả lời được câu hỏi đúng đáp án gốc.
| Câu | Có đáp án? | Fact |
|---|---|---|
| item-07 Trần Mặc đòi gì | có | `fact_c4s1_2` "Trần Mặc xin mượn Thẻ Định Phong đến hết chuyến qua đá trôi." |
| item-08 thẻ trở lại khi nào | có | cùng Fact ("đến hết chuyến qua đá trôi") |
| alive-01 ai cứu đứa trẻ | có | `fact_c1s1_1` "Người kể đã kéo một đứa trẻ khỏi mép đá." |
| alive-04 Trần Mặc nói gì về người dự đấu giá | có | `fact_c4s1_3` "...chưa chắc đã chết." |
| knows-12 Huyền Kính hứa không làm gì | có | `fact_c6s2_1` "...không bị lục xét hay bắt khai." |
| knows-13 tìm thấy dấu ở đâu | có | `fact_c2s1_1` "Trong lều cuối chợ có một vết in nhòe..." |
| item-11 đèn lưu quang ở phe nào | không | |
| alive-02 ai đỡ ông lão | không | |
| alive-03 có ai bị cuốn không | không | |
| knows-10 dấu hộ tống của ai | không | `fact_c9s1_1` chỉ nói "đoàn người đã qua lối này sống sót", không nói của ai |
| knows-11 cảnh báo "mồi nhử" | không | |
| knows-14 dấu có thể bị làm giả | không | |
| knows-16 vì sao Vân Chi giấu | không | `fact_c5s2_2` "Tào Vân Chi đã giấu... chuyện có người sống sót" không nêu lý do |
Cộng với nhóm 8: item-03, item-04 (cho ai mượn): `fact_c4s1_2` nói Trần Mặc xin mượn, không nói đã cho mượn: trả lời được "Trần Mặc" nhưng chỉ gián tiếp.
**Kết quả: 6/13 có đáp án (cộng 2 câu nhóm 8 gián tiếp).**

## Đọc 26 Fact
- **17 cụ thể, trung tính, bám trang:** `c1s1_1`, `c2s1_1`, `c3s2_1`, `c4s1_1`, `c4s1_2`, `c4s1_3`, `c5s1_1`, `c6s1_1`, `c6s2_1`, `c7s1_1`, `c7s2_1`, `c8s1_1`, `c8s2_1`, `c9s1_1`, `c9s1_2`, `c10s2_1`, `c5s2_2`.
- **9 là quyết định, lời hứa hay nhận xét của nhân vật chính** (9 trong 26 mang `user_authored` vì chép tên người chơi, đúng quy tắc): `c5s2_1` hứa không chỉ lối, `c6s2_2` không giao thẻ, `c9s1_3` cho Trần Mặc đi cùng, `c10s2_2` từ chối giao đồ có giá trị; `c1s2_1` "nhớ nét cong...", `c2s2_1`, `c3s1_1` "có căn cứ đầu tiên cho rằng...", `c7s1_2` "quyết định chưa quay lại đối chất" ít giá trị (nhận xét, ý định); `c10s2_3` đúng nhưng mất hết `KNOWS` (xem dưới).
- **Gần trùng:** `c8s2_1` "Huyền Kính đã lần tới vùng đá trôi" với `c6s1_1`; `c7s2_1` "Những người dự đấu giá được đưa khỏi khu chợ theo một lối kín trước khi các môn phái tới" gần với `fact_luu_tu_nguyet_cuu_dan` (bí mật đã lộ ở ch5); ngưỡng `duplicate_overlap` 0,7 không bắt.
- **Một Fact mồ côi:** `c10s2_3` có `ABOUT` và `REVEALED_TO_PLAYER` nhưng không còn `KNOWS` (người canh cắt cạnh "được kể"). Đã thêm luật bỏ Fact mồ côi sau lần phát lại này; **chưa đo lại**.
- **Đề `extract-6` cho lọt "quyết định/ý định của nhân vật chính".** Có thể siết đề, chưa làm (sẽ phải phát lại).
- Không thấy Fact nào tả bí mật chưa lộ hay tên giấu (G2 không bỏ Fact nào ở lần chạy này).
