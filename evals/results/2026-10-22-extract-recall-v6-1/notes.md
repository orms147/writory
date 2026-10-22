# Độ phủ của bộ trích (D-92): phát lại trên 10 chương của run-ky-ao-vua-1

Người đọc: Claude, 22/10/2026. Thư mục: `2026-10-22-extract-recall-{base-1,base-2,v5-1,v5-2,v6-1,v6-2,v7-1,v7-2}`; ghi chú này chung cho cả tám.

## Cách làm (dựng lại được)
- Văn và dàn ý lấy đúng từ `evals/results/2026-10-21-run-ky-ao-vua-1/` (`events.jsonl` `scene_ready`, `truth_dump.json` `outlines`). Lần chạy gốc có trước D-82 nên dàn ý không có `resolves` (để rỗng).
- Chạy `bench_run.StoryRun` thật, kho trong bộ nhớ (`tests/pipeline_fixtures.OverlayStore`), `--setup-from` thư mục trên (cùng kế hoạch, chương 0, lựa chọn khởi tạo), `ChapterRun` thật từng chương, từng cảnh: kiểm văn, trích, tự hé lộ, người canh, dò lộ, viết lại tối đa một lần, ghi gói. Model giả (`DryRunLLM`, chi phí 0) trả: văn cảnh và dàn ý gốc, tóm tắt, kiểm duyệt, lựa chọn. **Chỉ vai trích gọi model thật** (`openai/gpt-6-luna`, suy luận low, `max_tokens` 16000, như sản phẩm), qua `BudgetedClient`. Không áp lựa chọn của chương trước (không có `FEELS`/lời nói dối), nên khác sản phẩm ở đó.
- Văn là văn viết ra từ đồ thị của bộ trích cũ; lần phát lại giữ nguyên văn đó. Người canh dùng đồ thị mới nên có thể báo khác; văn không đổi theo.
- Script (ngoài repo): `replay_extract.py` (dựng như trên), `recall.py` (tính lại `graph_agrees`: với mọi câu có `derive` trong `questions-ky-ao-vua-1.yaml`, tính `derive` trên đồ thị chương `state_chapter` dựng từ các gói của lần phát lại rồi so với `answer.gold` bằng `bench_a_data._graph_problems`). Cho lần chạy gốc, `recall.py` ra đúng 13/39.
- Bốn cấu hình, mỗi cấu hình 2 lần: `base` = main (`extract-4`, `_prune` cũ, commit `7f69430`); `v5` = `extract-5` + `_prune` kéo theo `close`; `v6` = `v5` + `KNOWS` cho **mọi** người kể "được kể" (bản rộng, đã bỏ vì làm mất phép kiểm `teller_does_not_know`); `v7` = `v5` + `KNOWS` người kể **chỉ khi điều kể nói về chính họ** (bản giữ lại).

## Chẩn đoán 26 câu `graph_agrees: false` (không gọi model)
| Nhóm | Số | Câu |
|---|---|---|
| Nội dung không có nút trong danh mục (chi tiết sự kiện hay lời nói; bộ trích chỉ tham chiếu id có sẵn, chương 0 chỉ có 9 `Fact` bí mật) | 13 | item-07, item-08, item-11, alive-01, alive-02, alive-03, alive-04, knows-10, knows-11, knows-12, knows-13, knows-14, knows-16 |
| Kiểu cạnh hay độ mịn không biểu diễn được | 8 | item-03, item-04 (cho mượn rồi trả cùng chương: gộp theo trạng thái cuối chương xoá trung gian), rel-01 (nhận lời giữ kín), rel-02, rel-03, rel-06, rel-07 ("đi cùng ai": chỉ có `LOCATED_AT` tới 4 nơi lớn), knows-15 (`RELATES_TO` không nối nhân vật với phe) |
| `KNOWS` của nhân vật chính ghi trễ (có `derive`) | 4 | knows-02, knows-03 (trang lộ ch6, ghi ch9), knows-05, knows-06 (trang lộ ch8, ghi ch10) |
| Cạnh mới bị người canh cắt, `close` cạnh cũ vẫn vào gói | 1 | rel-04 (ch9, `sudden_relationship` 25 → −20) |
| Bộ trích không ghi dù biểu diễn được / `to_package` bỏ | 0 | cả lần chạy chỉ bỏ 2 cạnh (`REVEALED_TO_PLAYER` sai `known_as`), cả hai đã được tự hé lộ bù |
- Phân nhóm là phán đoán đọc tay (câu hỏi, evidence, `packages`, `reviews.rejected`); ranh giới giữa nhóm 1 và 2 không sắc.
- Gói chương 2, 3 rỗng vì cảnh chỉ có đối thoại, khám xét; không có thay đổi nào biểu diễn được.
- Nguyên nhân 4 câu trễ (đo lại bằng gọi thẳng bộ trích `extract-5` trên ch6 cảnh 1, 2 và ch8 cảnh 1, 2, 0,0039 USD): bộ trích **đã ghi** `KNOWS protagonist ← tran_mac` "được kể" ở cả hai cảnh ch6, nhưng chương 0 chỉ cho Bạch Thiên Sách biết `fact_tran_mac_ban_tin`, nên người canh báo `teller_does_not_know` và cạnh bị cắt. Ở ch8 bộ trích ghi `KNOWS` "suy ra" (không người kể) nên sống sót.

## Kết quả
| Cấu hình | `graph_agrees` (derive) | 13 câu đã đúng | câu false nay đúng | viết lại | `teller_does_not_know` | cạnh ch1–10 | chi phí |
|---|---|---|---|---|---|---|---|
| lần chạy gốc (`extract-2`/`3`) | 13/39 | 13 | — | 8 | 9 | 42 | 0,0972 (cả truyện) |
| base-1 | 15/39 | 13 | knows-05, 06 | 7 | 11 | 37 | 0,0219 |
| base-2 | 15/39 | 13 | knows-05, 06 | 7 | 10 | 32 | 0,0220 |
| v5-1 | 15/39 | 13 | knows-05, 06 | 8 | 17 | 35 | 0,0230 |
| v5-2 | 15/39 | 13 | knows-05, 06 | 8 | 11 | 34 | 0,0198 |
| v6-1 (người kể bất kỳ) | 17/39 | 13 | knows-02, 03, 05, 06 | 3 | 0 | 41 | 0,0173 |
| v6-2 (người kể bất kỳ) | 17/39 | 13 | knows-02, 03, 05, 06 | 3 | 0 | 38 | 0,0183 |
| **v7-1** (tự thú) | **17/39** | 13 | knows-02, 03, 05, 06 | **2** | **2** | 30* | 0,0165 |
| **v7-2** (tự thú) | **17/39** | 13 | knows-02, 03, 05, 06 | **3** | **1** | 30* | 0,0162 |
- \* `v7-1` dừng sau chương 9 và `v7-2` sau chương 8 vì chạm trần chi phí (`--budget` 0,025 mỗi lần; giữ chỗ chặn lời gọi kế tiếp), nên số cạnh, số viết lại và `teller_does_not_know` của hai lần này chỉ tính tới đó; so với các lần 10 chương thì thấp hơn một chút. `graph_agrees` không đổi vì mọi câu cần đều nằm trong chương 1–9 (đã kiểm: 17/39 tính trên các gói có).
- Chi phí các lần phát lại chỉ tính vai trích (model giả 0 USD); lần chạy gốc tính cả truyện. Tổng đã tiêu: 0,1262 USD cho sáu lần đầu (trần giao 0,15), gồm 0,0039 cho lần gọi thẳng bộ trích; thêm 0,0327 USD cho hai lần `v7` (trần giao riêng 0,05).
- `knows-05/06` đúng ở **mọi** lần phát lại kể cả `base`: nó đúng nhờ thay đổi khác giữa lần chạy gốc và main (trích ở ch8 thay vì ch10), không do D-92. Phần do D-92 là `knows-02/03`: **+2 câu**, ổn định qua hai lần.
- `extract-5` + `_prune` (v5) không đổi số này và số viết lại không giảm: đề `extract-5` không sửa được nguyên nhân thật. `rel-04` không kiểm được bằng lần phát lại (cả 6 lần giữ cạnh `RELATES_TO protagonist→tran_mac` ở ch9, không tái hiện cú nhảy điểm). Sửa `_prune` có test hồi quy riêng.
- Đọc cạnh thừa: chưa. Cạnh thêm cho người kể là `KNOWS` `how` "tự biết"; chưa đọc từng cạnh xem có sai nghĩa.

## Giới hạn và chưa kiểm
- Hai lần mỗi cấu hình, một truyện, một đề; con số 15 và 17 trùng nhau giữa hai lần nhưng không phải khoảng tin cậy.
- Trần trong schema hiện tại là 18/39; 21/26 câu còn lại cần đổi schema (nút `Fact` mới sau chương 0, kiểu cạnh đồng hành), chờ chủ dự án (D-92).
- **Chưa chạy lại bài A** trên đồ thị mới (hết trần chi phí của lượt này) nên chưa biết 17/39 đổi điểm các hệ ra sao. **Chưa chạy lại bài C** (`to_package` thêm cạnh có thể làm tăng cạnh thừa). `tests/graph` chạy trên Docker, không đụng lượt đo.

## Ca `teller_does_not_know` còn lại ở v7 (đọc tay)
- `v7-1` ch8 cảnh 1: protagonist ← Trần Mặc về `fact_luu_tu_nguyet_cuu_dan`. Trên trang, Trần Mặc nhắc việc Nguyệt đưa người đi (`ch08.md:109`: "Những người Nguyệt cô đưa đi không nằm trong lời bảo đảm"). Chương 0 chỉ cho Vân Chi và Nguyệt biết, dù Trần Mặc cùng Hội Lưu Dân. Hợp lý trên trang; điều kể không nói về Trần Mặc nên không được thêm `KNOWS`.
- `v7-1` và `v7-2` ch9 cảnh 2: protagonist ← Vân Chi về `fact_dien_co_mat`. Trên trang Vân Chi lần theo dấu khắc rồi kết luận "Đường này dẫn tới Mảnh Khiếp Tàn Thiên, và Điện Tàn Tinh ở phía dưới" (`ch09.md:129`): suy ra trong cảnh, mà bộ trích không ghi `KNOWS` "suy ra" cho nàng. Có thể là bắt oan, nhưng điều kể cũng không nói về Vân Chi.
- Kết luận đọc tay: cả hai đều đáng ngờ là bắt oan (không thấy lỗ hổng cốt truyện), và giữ luật cũ là cái giá của việc không mất phép kiểm. Chưa đọc các lượt khác của phép kiểm trên các truyện khác nên chưa biết phép kiểm bắt đúng bao nhiêu.
