# Nhận xét đọc tay: bài F, so deepseek-v4-flash và gpt-6-luna (D-101)

Người đọc: Claude, 22/10/2026. Nguồn: `summary.md`, `key.json`, `results.jsonl`, `code_metrics.json`, `../2026-10-22-run-bakeoff-{deepseek,luna,hy3,setup}/`. Đọc tay: đoạn đầu chương 1 và đoạn cuối chương 6 của cả hai; đầu chương 3; các lựa chọn cuối chương 1; kiểm từng điều giám khảo nêu về mâu thuẫn ngọc/ấn và lựa chọn bị hỏng chữ. Chưa đọc hết 12 chương.

## Phạm vi và những lần ngắt
- **Hy3 bị loại giữa chừng theo yêu cầu chủ dự án (22/10/2026).** Lượt `tencent/hy3` (suy luận viết none, dàn ý low) dừng ở chương 1, **0 chương ghi, chi phí 0,0097 USD**; cảnh 1 chương 1 bị chặn `guard:early_reveal` sau 2 lượt trước khi dừng. `meta.json` của lượt đó còn `status: running`. Không chấm, không đưa vào bảng. Chỉ để tham khảo: trong 9 lời gọi trước khi dừng chưa có văn đã hiện nào để đọc (`events.jsonl` không có `scene_ready`).
- Hai lượt còn lại chạy một mạch, không bị ngắt do máy khởi động lại. Luna có 1 lần tự bấm thử lại: bộ lựa chọn chương 5 bị chặn kiểm duyệt `over_darkness [violence]` rồi thử lại được (log lượt `bakeoff-luna`, mục "tự bấm thử lại: choices ×1").
- Cấu hình: cùng một khởi tạo (`2026-10-22-run-bakeoff-setup`, kế hoạch 6 chương), cùng đề `model-bakeoff.yaml` v1, seed 20261022, `--chapters 6`, suy luận viết `none`, dàn ý `low`. Chỉ đổi model viết và model dàn ý. Mọi vai khác (trích, tóm tắt, lựa chọn, kiểm duyệt) là DeepSeek V4 Flash theo `main` cho cả hai lượt.
- Chấm: Claude Sonnet 5.5, nhãn A/B xáo theo seed (`A` = deepseek, `B` = luna, từ `key.json`); `solo` ×2, `compare` ×2 thứ tự đảo, rồi `value`. `judge.yaml` v2 không nêu số truyện (hai truyện thay vì ba).

## Chi phí thật
| | deepseek-v4-flash (A) | gpt-6-luna (B) | hy3 (dừng) |
|---|---|---|---|
| Tổng OpenRouter | 0,0814 USD (6 chương) | 0,0672 USD (6 chương) | 0,0097 USD (0 chương) |
| USD/chương, tất cả vai | 0,01357 | 0,01119 | - |
| Phần model ứng viên (viết + dàn ý) | 0,0271 USD = 0,00452/chương | 0,0278 USD = 0,00464/chương | - |
| Viết / dàn ý | 0,0145 / 0,0126 | 0,0164 / 0,0114 | - |
| Vai dùng chung: trích | 0,0403 | 0,0257 | - |
| Token ra của dàn ý | 43.093 | 9.217 | - |
| Token ra của viết | 28.425 | 13.364 | - |
| Viết lại / cảnh bị chặn | 7 / 0 | 4 / 0 | - |

Khởi tạo chung 0,0060 USD. **Tổng OpenRouter 0,1643 USD** (trần giao 0,15 mỗi lượt viết, 0,50 tổng). **Anthropic (giám khảo) 0,4921 USD** (trần 1,25): `solo` 0,0778 + 0,0598, `compare` 0,1230 + 0,1156, `value` 0,1159.

Đọc được: phần model ứng viên **gần như ngang giá** (0,00452 so với 0,00464 USD/chương). Chênh USD/chương tổng (~17%) đến từ các vai dùng chung, chủ yếu vai trích: DeepSeek sinh thêm khoảng 46.000 token ra ở vai trích trên văn của nó (128.855 so với 82.959), vì truyện A dài hơn (39.794 so với 31.999 ký tự) và có nhiều lỗi định dạng hơn bị bộ trích dọn. Dàn ý của DeepSeek sinh gấp ~4,7 lần token ra so với Luna (43.093 so với 9.217) nhưng rẻ ngang vì giá/token thấp hơn.

## Kết quả giám khảo (đọc từ `summary.md`)
| Model | Tiếng Việt | Giọng/sáng tạo | Bám nhân vật | Liền mạch | Nhịp | Lựa chọn | Lỗi | TB | Hạng so sánh | USD/chương | Lỗi code | Lỗi gọi |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gpt-6-luna (B) | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3,00 | 1,0 | 0,0112 | 8 | 0 |
| deepseek-v4-flash (A) | 3 | 3 | 3 | 2 | 3 | 3 | 2 | 2,71 | 2,0 | 0,0136 | 8 | 0 |

Hai thứ tự trình bày đồng ý (B > A cả hai). Khuyến nghị của giám khảo: **Luna**, "không có lý do để trả thêm cho A". Trong `compare`, A thắng ở "giọng và sáng tạo" (cả hai chiều) và ở "nhịp" chiều AB; B thắng các mục còn lại. Câu trích của giám khảo không tìm thấy trong truyện: 3 trên 28 (G3); ví dụ `solo:A` mục "bám nhân vật" trích câu "Thay vì chạy, ngươi quyết định dùng uy quyền Chấp Pháp", có trong `brief.md` nhưng không có trong truyện nào.

## Đoạn cùng một cảnh, đặt cạnh nhau (mở đầu chương 1: Huyền Cơ bị xét xử, rút Tông Chủ Ấn)
**deepseek** (`run-bakeoff-deepseek/chapters/ch01.md:3-9`): "Ánh đèn dầu trong Vạn Đạo Điện chập chờn như hơi thở của kẻ hấp hối. Tôi đứng giữa điện, ba bóng người trước mặt khuất nửa trong bóng tối… Tôi rút từ trong lòng ra Tông Chủ Ấn. Khối ngọc tím nặng trịch trong tay, mặt ấn lạnh buốt, con rồng chạm nổi quấn quanh đế hứng lấy ánh đèn dầu yếu ớt… - Ba vị trưởng lão, ai trong các ngươi dám đường hoàng cầm nó? Tôi cười nhạt."

**luna** (`run-bakeoff-luna/chapters/ch01.md:3-9`): "Bản án vừa dứt, tiếng vọng còn lẩn quẩn dưới mái điện cao. Tôi siết Tông Chủ Ấn trong tay áo, cạnh ấn cấn vào lòng bàn tay. Ba trưởng lão đứng đối diện, không ai nhìn sang ai. - Các người đã định tội ta trước khi cho ta mở miệng."

Đọc tay: DeepSeek mở bằng hình ảnh và hành động, lời thoại gay gắt hơn, câu dài hơn, có mảnh vụn kiểu "Nhìn chăm chú vào viên ngọc tím." (`ch01.md:17`) và nhãn "Tôi cười nhạt" quen thuộc. Luna mở từ hậu quả của bản án, đối đáp ngắn, thủ tục ("Đọc lại căn cứ kết án", `ch01.md:9`), ít hình ảnh hơn, đều tay. Khớp với điểm của giám khảo: A hơn ở giọng, B hơn ở độ sạch. Cuối truyện: DeepSeek kết bằng hình ảnh và nhịp chậm ("Tôi cầm Tông Chủ Ấn.", cuối `ch06.md`); Luna kết bằng một tuyên bố thủ tục ("quyền điều hành Vạn Đạo Tông tạm thời thuộc về ta…", cuối `ch06.md`). Cả hai đều có `_Hết truyện._`.

## Điều tôi kiểm lại điều giám khảo nói
- **Mâu thuẫn chi tiết ở deepseek: đúng.** Tông Chủ Ấn là "khối ngọc tím" ở `ch01.md:7`, `:53`, `:117` nhưng "khối ngọc đen" ở `ch06.md:53`, `:71`.
- **Lựa chọn bị hỏng chữ ở chương 1 của deepseek: đúng, nhưng lỗi này KHÔNG phải của model viết.** `ch01.md:140`: "Ép Lục Thanh Phong phải giảii thíích về trận pháp trước mặ mọ ngưi." (lựa chọn này còn được chọn và lặp lại ở đầu `ch02.md:3`). Bộ lựa chọn là vai dùng chung, DeepSeek V4 Flash cho cả hai lượt, nên giám khảo gán nhầm cho "tác giả A" ở mục "lỗi" (điểm 2 so với 3) và có thể cả mục "lựa chọn". Điều này nghiêng điểm A xuống mà không do model đang so.
- **Hai truyện không cùng cốt truyện:** cùng seed và cùng luật chọn ngẫu nhiên, nhưng lựa chọn cuối chương do model lựa chọn tạo ra khác nhau theo văn, nên truyện rẽ nhánh từ chương 2 (deepseek ra sân kiểm tra dấu trận pháp, `run-bakeoff-deepseek/chapters/ch03.md:3-5`; luna ở lại điện và ra lệnh cho Lục Thanh Phong, `run-bakeoff-luna/chapters/ch03.md:3-6`). Giám khảo so hai truyện khác nhau về cốt truyện, không chỉ về cách viết.

## Lỗi quan sát được trong lúc chạy (`report.json` của từng lượt)
- deepseek: `quality:dialogue_format` ×24 (bộ kiểm văn bắt và buộc viết lại, còn 0 khi hiện), `guard:sudden_relationship` ×6, `quality:length` ×2 (1 còn khi hiện), `quality:narration_person` ×2, `guard:early_reveal` ×1, `leak:secret` ×1; bộ trích bỏ 85 cạnh (Fact mới ×47, câu trích không nguyên văn ×19).
- luna: `guard:sudden_relationship` ×3, `guard:teller_does_not_know` ×1, `quality:repetition` ×2 (1 còn khi hiện); bộ trích bỏ 41 cạnh (Fact mới ×13, thiếu ABOUT ×13, câu trích không nguyên văn ×8). Kiểm văn cuối truyện của repo đếm cùng 8 lỗi lặp ở cả hai.
- Lỗi định dạng lời thoại của DeepSeek là điểm yếu riêng của model viết (24 so với 0 ở Luna); giám khảo thấy nó còn sót ("lời thoại thiếu dấu gạch ngang").

## Kết luận (tách đọc được và suy luận)
Đọc được: (1) về chi phí, phần model ứng viên hai bên ngang nhau; DeepSeek không rẻ hơn Luna tính cả đường chạy (0,0136 so với 0,0112 USD/chương). (2) Trên thang giám khảo, Luna hơn rõ ở liền mạch và lỗi; DeepSeek hơn ở giọng. (3) Luna cần ít lần viết lại hơn (4 so với 7) và 0 lỗi định dạng lời thoại so với 24.

Suy luận (chưa kiểm): chênh "lỗi" bị khuếch đại bởi lựa chọn hỏng chữ của vai dùng chung; nếu loại nó, khoảng cách có thể nhỏ hơn. Một thế giới, một seed, 6 chương, một giám khảo, điểm toàn 2-3 nên không phân biệt chắc; hy3 không có dữ liệu.

Khuyến nghị tổng hợp: nghiêng về **Luna** cho vai viết và dàn ý nếu chủ dự án ưu tiên độ sạch và liền mạch; chọn **DeepSeek** chỉ nếu ưu tiên giọng văn và chấp nhận thêm bước dọn định dạng. Quyết định cuối thuộc chủ dự án.

## Chưa kiểm
Cách loại bỏ yếu tố "lựa chọn dùng chung" (chạy lại hai lượt với lựa chọn cố định, hoặc bỏ điểm mục lựa chọn); chạy lại lượt hy3 để có dữ liệu; chạy lại với seed khác để đo nhiễu; hiệu chuẩn thang giám khảo với người đọc.
