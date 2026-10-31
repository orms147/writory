# Kết quả: bài A trên truyện dài 24 chương, sáu hệ, Meta Muse

Người đọc: Claude (điều phối), 31/10/2026. Khai trước: `expectations.md` cùng thư mục (commit `7fca714`, trước
mọi lời gọi). Kết quả: `../2026-10-31-memory-long-ky-ao-2-muse/` (`summary.md`, `results.jsonl`, `meta.json`).
Model trả lời và tóm tắt `meta/muse-wonder-1.0` (suy luận low). 300/300 lượt, không lượt lỗi, không dừng vì trần.
Chi 9,04 USD Meta, trần 30 (ước thô 20,89 theo giá không cache; nhét cả truyện có 49% token vào được cache).

## Số chính (đúng / 50, khoảng tin cậy 95%)
| Hệ | Đúng | Kiêng | USD / câu |
|---|---|---|---|
| Nhét cả truyện (`full`) | 100% [93–100] | 0 | 0,0811 |
| Đồ thị + câu trích (`graph_quotes`) | 86% [74–93] | 3 | 0,0207 |
| Tóm tắt cuộn (`rolling`) | 84% [71–92] | 7 | 0,0359 (gồm dựng tóm tắt) |
| RAG BM25 (`rag`) | 70% [56–81] | 12 | 0,0149 |
| Đồ thị (`graph`) | 66% [52–78] | 12 | 0,0184 |
| Không bộ nhớ (`none`) | 8% [3–19] | 46 | 0,0098 |

## Theo luật khai trước
- **(a) `graph_quotes` so với `rag`: hơn** (86% so với 70%, chênh 16 điểm; khoảng tin cậy chồng nhau ở 74–81
  nên không phải "hơn rõ").
- **(b) `graph` so với `rag`: chưa phân biệt được** (66% so với 70%).
- **(c) `graph_quotes` so với `full`: `full` hơn** (100% so với 86%, chênh 14 điểm; hai khoảng tin cậy chạm
  nhau ở 93, không tách hẳn). `full` tốn 3,9 lần mỗi câu (0,0811 so với 0,0207 USD).
- **(d) 33 câu cách từ 10 chương trở lên:** `graph_quotes` 27/33 (82%) so với `rag` 21/33 (64%): **hơn**;
  `full` 33/33 so với `graph_quotes`: **`full` hơn**. (`graph` 19/33, `rolling` 26/33.)
- **Chẩn đoán phần đọc đồ thị: đạt.** `graph` đúng 31/34 câu đồ thị bộ trích có đáp án (91%, ngưỡng 60%;
  oracle chỉ thấy đủ câu trích ở 26/34, model suy ra được thêm). Ở 16 câu đồ thị thiếu hoặc sai, `graph` chỉ
  đúng 2. Nút thắt của đồ thị vẫn là độ phủ của bộ trích, như truyện vừa.
- Dự đoán khai trước: `full` cao nhất và đắt nhất (đúng); (a) chưa phân biệt được (**sai**: `graph_quotes`
  hơn); (b) `graph` thấp hơn `rag` (đúng chiều, dưới ngưỡng); chẩn đoán đạt (đúng).

## Đọc tay (luật 5, không sửa điểm)
Lượt sai không kiêng: `graph_quotes` 4, `rag` 3.
- **Đồ thị nói sai thắng câu trích đúng** (`graph_quotes`, cả ba câu đều có `graph_agrees: false` và `derive`,
  tức code kiểm đồ thị nói khác trang):
  - lie-03 trả "Không": đồ thị không có `KNOWS` nào của Tạ Vân về lời nói dối ch2, model đọc chỗ trống thành
    "chưa biết".
  - rel-08 trả "Có": `LOCATED_AT` của nhân vật chính trễ một chương (còn ở Rừng Rủ Sương tới ch9).
  - knows-14 trả "Không": câu chứng cứ chỉ có bốn chữ ("Tạ Vân cũng nhìn thấy."), BM25 không kéo được; `rag`
    cũng sai câu này.
- **Đáp án đúng nhưng khác cấp nơi chốn:** rel-11 (`graph_quotes` "Trụ gỗ", `rag` "phần sàn phía bên kia, sát
  trụ gỗ đóng xiên", `graph` "trụ gỗ"; đáp án "Bến Cầu Gãy"). Chữ "ở nơi nào" của câu hỏi cho phép trả lời ở
  cấp nhỏ hơn: lỗi soạn đề của Claude, giữ điểm.
- `rag` item-04 trả "Tạ Vân" (đáp án: Mai Thảo nhận lại bản đồ cuối ch22): đoạn kéo về là đoạn trước ch22 hay
  vụ ném bản đồ ở ch24 (suy luận, chưa kiểm đoạn đã gửi).
- Câu Claude ghi "chưa chắc": knows-07 mọi hệ có bộ nhớ trả Tạ Vân (`rolling` kiêng); rel-06 `graph` kiêng như
  đã ngại, các hệ có bộ nhớ khác đúng; knows-17 các hệ có bộ nhớ trả đủ "Đinh Lộc", không chỉ nhắc biệt danh; alive-04 `rolling` sai;
  alive-03, rel-02, lie-04 mọi hệ có bộ nhớ đúng.
- `graph` kiêng ở rel-03 và rel-10 dù đồ thị có đáp án, và sai rel-11: cả ba ở nhóm quan hệ và nơi chốn (nhóm
  thấp nhất của `graph`, 4/11). Vì sao chưa kiểm (ngữ cảnh gửi model không lưu trong `results.jsonl`).

## Không khai trước, chỉ mô tả
- `rolling` (84%) sát `graph_quotes` (86%), đắt hơn 1,7 lần mỗi câu khi tính cả dựng tóm tắt. Ở truyện vừa
  (Luna) hai hệ bằng nhau ở 79%.
- So với truyện vừa (`evals/results/2026-10-22-memory-ky-ao-vua-1/notes.md`) thứ hạng đổi: ở đó `rag` (84%) trên
  `graph_quotes` (79%). Khác model (Luna, 3 lần hỏi), khác đề và trước D-93, D-144, nên không so thẳng được.

## Hệ quả (suy luận, chưa đo)
- Ở truyện dài, lai đồ thị với câu trích trên trang là đường rẻ tốt nhất trong các hệ đo (`full` đúng hết nhưng
  ngữ cảnh 123 nghìn ký tự ở ch24 và tăng theo độ dài).
- Lỗi đáng ngại nhất của hệ lai là đồ thị nói sai hay thiếu mà model tin hơn trang (lie-03, rel-08). Hai hướng có
  thể đo sau, chưa làm: báo cho model biết khối đồ thị có thể thiếu (chỗ trống không phải "không"), và nâng độ
  phủ `KNOWS` của người khác ngoài nhân vật chính.

## Chưa kiểm
- Một lần hỏi, một truyện, một model: khoảng tin cậy rộng (khoảng ±10–14 điểm).
- Kết quả là của Muse; Luna (model của sản phẩm) chưa chạy đề này.
- `graph_agrees` của 10 câu không có `derive` do người soạn khai tay.
