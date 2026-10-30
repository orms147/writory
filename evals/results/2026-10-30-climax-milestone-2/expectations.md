# Khai trước: phát lại bộ trích `extract-8` và `extract-11` trên chương đã lưu (D-139)

Khai TRƯỚC khi gọi model thật (commit chứa file này đi trước mọi lời gọi; không sửa file này sau khi chạy). Mục đích: đo thay đổi D-139 mà không viết lại cả truyện:
- dòng mốc của bộ trích có loại (bước ngoặt / cao trào);
- mốc cao trào chỉ ghi khi trang cho thấy cả cao trào lẫn hậu quả của nó (điều đã đổi hẳn vì cao trào); mối nguy có từ trước chỉ tiếp diễn không phải hậu quả, quyết định tạm có điều kiện chưa phải cao trào;
- câu trích mốc là `quotes`: 1 đến `MILESTONE_QUOTE_MAX_PARTS` đoạn, mỗi đoạn nguyên văn, đúng thứ tự trong chương (code kiểm từng đoạn, G3), thay cho một đoạn liền.

Lần thử trước (`extract-9`, D-129, `../2026-10-30-extract-milestone-kind/`) ra tín hiệu xấu: luật đòi hai điều mà câu trích phải liền một đoạn, model ghép hai chỗ bằng "[...]" hay sửa chữ, G3 từ chối; ky-ao ch16 (cao trào đúng hạn) mất dấu. Phép đo này giữ nguyên các ca và ý của K1–K4 của D-129, thêm lặp n=2 mỗi bản đề mỗi ca.

## Cách phát lại
- Nguồn chương và đồ thị: `../2026-10-29-run-long-after-tu-tien/` và `../2026-10-29-run-long-after-ky-ao-2/` (lượt chạy sau D-116, bộ trích `extract-8`). Mỗi ca = một chương đã ghi. Đề dựng lại từ `truth_dump.json` như D-129: danh mục thực thể và cạnh đang hiệu lực đến hết chương trước, mạch phải gỡ, mốc chưa xảy ra và mốc đã xong tính bằng `chapter_goals` với cờ của `config/limits.yaml`, luật Fact mới của config. Chữ chương là toàn bộ chương (`chapters/chNN.md`, bỏ tiêu đề, dòng lựa chọn dẫn tới và phần lựa chọn cuối chương), **một lời gọi cho cả chương**, khác sản phẩm (mỗi cảnh một lời gọi). Không có nút `Lie` của lựa chọn dẫn tới chương trong danh mục.
- Hai bản đề, cùng model, cùng mức suy luận của vai `extract`, cùng mọi thứ khác:
  - `extract-8`: đề của main `6698094` (`extract8_system_prompt.txt`, trùng chữ với file cùng tên của D-129), dòng mốc không có cột loại, schema JSON của main (`extract8_schema.json`: mốc có `quote` một chuỗi). Script dựng lại đúng schema đó và kiểm bằng `assert` trước khi gọi.
  - `extract-11`: code của nhánh này (`extract11_system_prompt.txt` là bản chép để đọc; script `assert` nó trùng `SYSTEM_PROMPT` của code).
- Cả hai bản qua cùng `accept_milestones` của nhánh. Với câu trích một đoạn luật nhận y như main (`test_pipeline_extract.py::test_old_replies_with_a_single_quote_field_parse_as_one_part`, `::test_a_single_short_quote_is_still_accepted_as_before`). Chỉ chấm mục `milestones` của đầu ra (id + câu trích, mốc model trả và mốc code nhận); các phần khác không chấm.
- **Lặp n=2:** mỗi ca 4 lời gọi theo thứ tự `extract-8`, `extract-11`, `extract-8`, `extract-11`. "Gốc" = dấu đã có trong lượt chạy gốc (thuộc tính `milestones` của nút Chapter trong gói chương).
- Trần chi phí cứng `--budget 0.10` (script dừng trước lời gọi tiếp theo khi chi thật cộng giữ chỗ vượt trần, như D-129). Ước tính: 40 lời gọi; D-129 tốn 0,0017–0,0033 USD mỗi lời gọi đầu và 0,0005–0,0009 mỗi lời gọi lặp có cache, nên khoảng 0,06–0,07 USD; không có cache thì tới khoảng 0,13 và trần cắt các lời gọi cuối (tầng 3).
- Chạy một mình, không song song với lượt khác dùng cùng key.

## Các ca (thứ tự ưu tiên; hết ngân sách thì các lời gọi sau không chạy và ghi là không chạy)
1. **Mục tiêu:** tu-tien ch19 (m6 cao trào, khoảng 20–22; gốc nhận m6 ở đây); ky-ao ch24 (m7 cao trào, khoảng 20–23; gốc không nhận).
2. **Đối chứng có dấu đúng:** ky-ao ch16 (m6 cao trào, đúng hạn); tu-tien ch11 (m4 bước ngoặt); ky-ao ch10 (m5 bước ngoặt); tu-tien ch5 (m3 bước ngoặt).
3. **Chương ngữ cảnh** (mốc đang chờ chưa xảy ra): tu-tien ch18, ch17 (m6); ky-ao ch22, ch23 (m7).

## Đọc tay trước khi chạy (căn cứ của K1, K2)
- tu-tien ch19 (`chapters/ch19.md`): "Nàng được dùng hộp để dò mạch." (dòng 135) là cho phép tạm, có điều kiện ("Không ép nó đáp lại. Chỉ dò theo ánh sáng.", dòng 141). Vết nứt mở rộng (dòng 151) là mối nguy có suốt chương (dòng 51, 73, 79, 99). Đường lui bị lấp (dòng 121) xảy ra trước quyết định, không do nó. Câu hỏi ai được dùng hộp còn mở ở ch21 (dòng 103–105; lựa chọn 2 hỏi vì sao Ninh muốn giao hộp cho Huyền Tiêu Tông). Theo luật mới: chưa phải cao trào kèm hậu quả.
- ky-ao ch24: quyết định "Tôi sẽ dùng nó để mở đường…" (dòng 87, trước đó dòng 75) và hậu quả không đảo được: xé dải đường về (dòng 91), "Phần bản đồ còn lại không thể chỉ đường quay về nữa." (dòng 97). Vế "tới Bến Cầu Gãy" chưa trọn (dòng 113: lối tới bến mở ra, họ đi vào), như D-129 ghi; kỳ vọng giữ như D-129 (vế chính là quyết định).
- ky-ao ch16: sự thật được nói ra "Đoàn Khương thúc đẩy vụ bắt Đinh Lộc để thu hồi Bản đồ Nếp Gấp." (dòng 31) và hậu quả: Mai Thảo bỏ đi (dòng 41), thôi chờ Tạ Vân giúp (dòng 49), tự xoá dấu, "Đường quay lại cũng đi luôn." (dòng 61).

## Kỳ vọng (mỗi "lần" là một lời gọi)
- **K1:** tu-tien ch19: `extract-11` **không trả** m6 (trong đầu ra của model, không chỉ là code không nhận) ở cả 2 lần. `extract-8` nhận m6 như lượt gốc: chỉ để đối chiếu, không dùng để quyết.
- **K2:** ky-ao ch24: `extract-11` nhận m7 ở cả 2 lần, câu trích (một hay nhiều đoạn) chỉ vào quyết định dùng bản đồ (dòng 75 hay 87) và/hoặc việc xé dải đường về (dòng 91–97). `extract-8` có thể không nhận.
- **K3:** mỗi ca đối chứng: số lần `extract-11` nhận đúng mốc gốc ≥ số lần `extract-8` nhận mốc đó; riêng ky-ao ch16 (cao trào đúng hạn) `extract-11` nhận m6 ít nhất 1/2 lần; `extract-11` không nhận mốc nào khác ở các chương đối chứng.
- **K4:** chương ngữ cảnh: ở mỗi chương, số lần `extract-11` nhận một mốc ≤ số lần `extract-8` nhận.
- **K5 (G3):** trên mọi lời gọi đã chạy, số câu trích mốc của `extract-11` bị code từ chối vì lý do G3 (mọi lý do có "(G3)" của mốc) ≤ của `extract-8`.

## Luật quyết (khai trước)
- **Tín hiệu tốt** nếu K1 đúng 2/2, K2 đúng 2/2, K3, K4 và K5 đều đúng.
- **Tín hiệu xấu** nếu một trong các điều sau xảy ra: `extract-11` trả m6 ở tu-tien ch19 ở cả 2 lần (không sửa được dấu sớm); `extract-11` không nhận m6 ở ky-ao ch16 lần nào (lặp lại lỗi của `extract-9`); `extract-11` nhận một dấu mới ở ca đối chứng hay chương ngữ cảnh mà đọc tay thấy câu trích không cho thấy điều mốc mô tả; K5 sai.
- **Không xác định** trong mọi trường hợp còn lại (ví dụ K1 hay K2 đúng 1/2).
- Dấu mới hay dấu mất đều được đọc tay (câu trích, hay từng đoạn, có thật nói điều mốc mô tả không; với cao trào: có hậu quả không) và ghi vào `notes.md`; không dựa vào đếm.
- n=2 vẫn là nhiễu: kết quả đọc là "tín hiệu", không phải "đã đo".
- Theo kết luận:
  - tốt: đề nghị gộp `extract-11` cùng code câu trích nhiều đoạn (D-139 ghi kết quả);
  - xấu: không gộp `extract-11`; code câu trích nhiều đoạn cũng không gộp (schema gửi model là một phần của đề: không có đề xin nhiều đoạn thì code đó không có đường vào); PR chỉ còn kết quả đo, như D-129;
  - không xác định: không gộp mặc định, ghi lại và hỏi chủ dự án.
- Không sửa đề lần hai trong PR này để cho khớp.

## Bổ sung 30/10/2026: đo thêm ca đối chứng (bổ sung sau kết quả "không xác định", chủ dự án chọn đo thêm)
Khai TRƯỚC mọi lời gọi của lần đo thêm (commit chứa phần này đi trước lời gọi đầu). Phần trên giữ nguyên. Kết quả lần chạy đầu (`notes.md`) giữ nguyên: K1, K2, K4, K5 đúng; K3 sai (đối chứng 5/8 so với 6/8). Lần đo thêm chỉ để quyết K3.

**Cách chạy.** Chỉ 4 ca đối chứng, theo thứ tự ưu tiên ky-ao ch16, tu-tien ch11, ky-ao ch10, tu-tien ch5. Mỗi ca thêm lần 3 đến 6 cho mỗi bản đề, xen kẽ 8, 11 như trước: 32 lời gọi. Cùng code đề, schema, cách dựng đề và cách chấm của lần chạy đầu (`replay.py`, thêm `--first-rep`/`--repeats`, mặc định như cũ). Ghi vào `control-n6/`. Lệnh (từ `backend/`): `uv run python ../evals/results/2026-10-30-climax-milestone-2/replay.py --only 2- --first-rep 3 --repeats 4 --budget 0.08 --out ../evals/results/2026-10-30-climax-milestone-2/control-n6`. Trần cứng 0,08 USD; ước tính 0,04–0,05 USD (lần chạy đầu: trung bình 0,00239 USD cho lời gọi chưa có cache, 0,00075 cho lời gọi có cache).

**Gộp.** Mỗi bản đề, mỗi ca: lần 1–2 (lần chạy đầu) cộng lần 3–6, tức 6 lần mỗi ca, 24 lần gộp mỗi bản đề. Chỉ tính cặp (ca, lần) mà cả hai bản đề đều chạy; trần cắt thì bỏ cả cặp. Tính bằng `pool.py`.
- **Nhận đúng** (R) = số lần code nhận đúng mốc gốc của chương đó. R8, R11 là tổng gộp; R8(16), R11(16) là riêng ky-ao ch16 (cao trào đúng hạn, rủi ro chính của luật "đòi hậu quả").
- **Dấu sai** của `extract-11`: dấu được nhận của một mốc không phải mốc gốc của chương, hoặc dấu của mốc gốc mà đọc tay thấy câu trích (hay một đoạn) không cho thấy điều mốc mô tả. Mọi dấu được nhận của `extract-11` ở lần 3–6 đều được đọc tay và ghi vào `notes.md`.

**Luật quyết của phần đo thêm.**
- **Tốt** nếu cả bốn điều đều đúng: R11 ≥ R8 − 1; R11(16) ≥ R8(16) − 1; `extract-11` không có dấu sai; số câu trích mốc bị G3 từ chối của `extract-11` trên 24 lần gộp ≤ của `extract-8`.
- **Xấu** nếu có một trong các điều: R11 ≤ R8 − 4; R11(16) ≤ R8(16) − 3; `extract-11` có ít nhất một dấu sai.
- **Không xác định** trong mọi trường hợp còn lại, và khi còn ít hơn 20 cặp gộp mỗi bản đề (trần cắt).
- Lý do chọn ngưỡng (suy luận, không phải kiểm định): với 24 lần và tỉ lệ nhận khoảng 0,7, độ lệch chuẩn của hiệu R11 − R8 vào khoảng 3 dấu, nên chênh 1 là trong nhiễu (biên chấp nhận nhỏ), chênh 4 trở lên khó do nhiễu riêng. Ở một ca 6 lần, chênh 3 là một nửa số lần.

**Kết luận chung.** K1, K2, K4, K5 đã đúng ở lần chạy đầu, nên phần đo thêm quyết cả phép đo:
- tốt: đề nghị gộp `extract-11` cùng code câu trích nhiều đoạn (D-139 ghi kết quả);
- xấu: không gộp; gỡ code và đề khỏi PR, giữ kết quả đo; D-139 ghi "đã thử, không dùng", như D-129;
- không xác định: không gộp, xử lý như xấu (gỡ code, giữ kết quả đo), D-139 ghi "đã thử, chưa phân biệt được, không dùng"; chủ dự án có thể quyết khác.
- Không sửa đề trong PR này để cho khớp, và không đo thêm lần nữa trong PR này.
