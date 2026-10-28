# Chẩn đoán giọng văn và mạch truyện: Ngắn và Vừa do GPT-6 Luna viết

Người viết: Claude (phiên 2), 28/10/2026, theo yêu cầu của writory-3c. Không sửa code, không commit, không viết truyện mới.
Dữ liệu: ba thư mục kết quả đã có (commit, hash config và model của từng lượt: `meta.json` trong thư mục đó; tất cả GPT-6 Luna). Không gọi model viết nào cho ghi chú này; chỉ có hai lời gọi Meta Muse Wonder (mục 4).
Biến thể đề dựng từ chẩn đoán này: D-110 (`evals/scenarios/quality/style_guide_vi_v3.md`, `evals/scenarios/prompts/v3/`). Các đề xuất ở §5 là dự thảo gốc; bản vào repo là bản đã rút gọn, nên lệch chữ đôi chỗ.

## 0. Phạm vi và độ tin cậy

**Đã đọc nguyên văn từng dòng:** 8 chương trong 3 truyện, và đọc một phần 2 chương nữa.
- `tu-tien-4` (Ngắn, 6 chương): ch01, ch03, ch06 đọc hết.
- `ky-ao-3` (= `2026-10-22-run-ky-ao-vua-3`, Vừa, kế hoạch 12 chương, chạy 10): ch05, ch10 đọc hết; ch01 chỉ cảnh 1; ch07 chỉ 30 dòng đầu.
- `bakeoff-luna` (= `2026-10-22-run-bakeoff-luna`, Ngắn, 6 chương): ch01, ch03, ch06 đọc hết.
- Mở và kết của cả 22 chương, và toàn bộ lựa chọn cuối chương của `ky-ao-3` và `bakeoff-luna`, đọc bằng script rồi đọc tay. Các chương còn lại (ch02, ch04, ch05 của `tu-tien-4`; ch02–ch04, ch06, ch08, ch09 của `ky-ao-3`; ch02, ch04, ch05 của `bakeoff-luna`) chỉ qua script và dòng mở/kết: nếu điểm nào dưới đây nói "chương X" mà tôi chưa đọc hết chương đó, tôi ghi rõ.

**Đo bằng script:** `stats.py`, `stats2.py` cùng thư mục này; chạy `cd evals/results && PYTHONIOENCODING=utf-8 python 2026-10-28-prose-diagnosis/stats.py` (và `stats2.py`), cần ba thư mục `2026-10-21-run-tu-tien-4`, `2026-10-22-run-ky-ao-vua-3`, `2026-10-22-run-bakeoff-luna`. Chạy trên 22 chương (khoảng 28.000 từ). Con số là số đếm từ bề mặt chữ (regex), không phải phán đoán văn học.

**Giới hạn (nói thẳng):**
1. Ba lượt chạy, ba thế giới, một mô hình. Mẫu nhỏ; "tật chung" ở đây là tật chung của ba lượt này.
2. Ba lượt chạy ở các commit khác nhau (`tu-tien-4`: 21/10, `ky-ao-3`: 22/10 sáng, `bakeoff-luna`: 22/10). Style guide không đổi từ v2 (20/10; `git log` file chỉ có hai commit bài D). `ky-ao-3` và `tu-tien-4` chạy TRƯỚC D-98 (cờ "ở yên"); lượt dài `long-tu-tien-2` (23/10) có D-98 nhưng vẫn giậm chân (ghi chú của chính tôi trong `evals/results/2026-10-22-run-long-tu-tien-2/notes.md`).
3. Cả ba truyện thuộc cùng một dạng: người ghi chép hay người giữ vật bị ba phe giằng co trong một căn phòng. Tôi không có truyện hành động, tình cảm hay hiện đại của Luna để so, nên khẳng định "Luna tật gì" bị lẫn với "đề kiểu thương nghị gây tật gì".
4. Phần "nguyên nhân" dựa trên việc đọc `scene.py`, `pacing.py`, `choices.py`, `graph/context.py`, `setup.py` tại HEAD `0101de1` để biết mô hình viết nhìn thấy gì. Tôi không chạy lại mô hình để kiểm nguyên nhân; chúng là chẩn đoán đọc được từ prompt và dữ liệu, chưa phải thí nghiệm.

## 1. Bảng đo chính

| | tu-tien-4 (Ngắn) | ky-ao-3 (Vừa) | bakeoff-luna (Ngắn) |
|---|---|---|---|
| Chương / từ / cảnh | 6 / 10.109 / 12 | 10 / 11.040 / 20 | 6 / 6.826 / 12 |
| Dòng thoại / dòng kể | 230 / 250 | 138 / 271 | 174 / 202 |
| Câu kể: TB từ, độ lệch chuẩn | 11,8 / 6,8 | 12,3 / 5,6 | 9,8 / 4,9 |
| Câu kể ≤ 6 từ | 19% | 18% | 28% |
| Lời thoại: TB từ; ≤ 6 từ | 20,2; 7% | 17,8; 12% | 16,6; 13% |
| Lời thoại có từ vựng thủ tục (xác nhận, đối chiếu, căn cứ, điều khoản, ghi rõ, bảo lưu, hồ sơ…) | 57% | 47% | 43% |
| Đoạn kể mở bằng một trong 6 chữ đầu thường gặp (tên nhân vật / "Tôi" / "Nàng"…) | 198/250 = 79% | 167/271 = 62% | 174/202 = 86% |
| Cảnh có đoạn cuối kiểu treo ("không ai", "vẫn", "chưa", "chờ") | 6/12 | 9/20 | 9/12 |
| "ngón tay" / 1000 từ | 2,4 | 1,6 | 0,6 |
| "Không ai" / 1000 từ | 2,0 | 1,0 | 1,5 |
| "ánh mắt" / 1000 từ | 0,8 | 0,6 | 2,5 |
| "khô khốc" + "lạnh ngắt/buốt" / 1000 từ | 0,4 | 1,5 | 1,2 |
| Giác quan trong lời kể (/1000 từ kể): mùi; nóng-ấm; đau-nhói-run | 0,9; 0,0; 0,0 | 0,8; 0,0; 0,8 | 0,3; 0,3; 2,5 |
| "tiếng" (âm thanh) / 1000 từ kể | 3,3 | 10,4 | 6,4 |
| Từ cảm xúc trực tiếp / 1000 từ | 3,8 | 0,9 | 1,8 |
| Lựa chọn lời thoại: nói thật / im lặng / nói dối | 5 / 0 / 0 | 4 / 1 / 0 | 5 / 0 / 0 |
| Độ dài chữ lựa chọn (TB từ) | 17,5 | 16,0 | 18,1 |

Cách đọc: số rủi ro thấp (ví dụ "nóng-ấm = 0,0") là bằng chứng mạnh, vì regex không bỏ sót chữ "nóng". Số "thủ tục 43–57%" là tỉ lệ có chứa ít nhất một từ trong danh sách, dễ phóng đại với truyện về giấy tờ; dùng để so sánh giữa các lần, không để kết luận tuyệt đối.

Ghi chú cách tính còn yếu: (a) cột "cảnh có đoạn cuối kiểu treo" là regex thô; đọc tay xem §2.1 để có số chắc hơn. (b) Phép đo "lời thoại đầu = chép lại lựa chọn" của tôi bỏ sót một ca (xem §2.8); đếm tay: 2 ca trong 22 chương.

## 2. Mười hai điểm yếu (xếp theo mức nặng)

Mỗi mục: biểu hiện, trích (đường dẫn trong `evals/results/`), nguyên nhân (đọc được / suy luận), sửa ở đâu.

### 2.1 Chương nào cũng kết bằng một bức tranh đứng yên, không có biến cố
Đọc tay 20 câu cuối chương không phải chương cuối: 15 chương kết rõ ràng bằng chờ / đứng yên / "vẫn chưa" / "không ai"; 5 chương còn lại chỉ có chuyển động nhỏ (ky-ao ch04, ch07, ch08; bakeoff ch04, ch05). Không chương nào kết bằng điều không thể rút lại.
- `2026-10-21-run-tu-tien-4/chapters/ch03.md:173`: "Việc kiểm tra quyền tiếp cận đã thành điều kiện để giữ nhánh linh mạch khỏi bị khai thác trước; nhưng ngay trong điện, chẳng ai chịu xác nhận điều kiện ấy bằng chữ ký."
- `2026-10-22-run-ky-ao-vua-3/chapters/ch05.md:67`: "Tôi đứng ngay ngưỡng cửa, ôm chiếc hộp khóa kín chờ họ trả lời."
- `…/ky-ao-vua-3/chapters/ch10.md:95`: "chỗ ghi người nhận Mảnh Thiên Khuyết vẫn còn bỏ trống."
- `2026-10-22-run-bakeoff-luna/chapters/ch03.md:155`: "Bản ghi nằm giữa chúng tôi, chờ được hỏi đến."

Nguyên nhân (đọc được): (1) `OUTLINE_SYSTEM_PROMPT` bắt model điền `ends_at: "cảnh kết ở đâu, một câu"` (`scene.py:363`): đó là một vị trí, không phải một biến cố; (2) prompt viết dặn "không kết thúc cảnh sớm hay muộn hơn nhịp cuối" (style guide v2, mục Bám dàn ý), nên bản viết dừng đúng ở trạng thái `ends_at` nêu; (3) không dòng nào trong style guide hay dàn ý nói kết cảnh phải là một biến cố. Luật duy nhất về kết cảnh là cấm "câu triết lý" (và luật ấy được tuân thủ về hình thức: câu cuối không đúc kết, nhưng thành tranh tĩnh). Đây là thiếu chỉ dẫn, không phải bỏ qua chỉ dẫn.
Sửa: dàn ý (`ends_at`), style guide (mục "Kết cảnh và mở chương").

### 2.2 Chương giậm chân: cả truyện là một căn phòng, một cuộc cãi, và kế hoạch có khe hở
- Ngắn `tu-tien-4`: 6 chương hầu như chỉ ở Điện Thương Nghị (ch03 có một chuyến ngắn sang Kho Văn Thư rồi quay lại, `ch03.md:99-101`); bàn về ai giữ bản ghi (ch01), điều khoản tạm thời (ch03), bàn giao lối xuống (ch06). Chương 6 là chương cuối mà vẫn đang soạn điều khoản.
- Vừa `ky-ao-3`: ch01 đến ch05 là đường tới đại điện (tháp, cầu thang, trạm); từ ch05 đến ch10 (6 chương liên tiếp) nhân vật chính đứng ở cửa hoặc trong đại điện (các chương tôi chưa đọc hết ghi theo dòng mở/kết: ch06 "điểm chờ", ch08 "ngoài ngưỡng", ch09 "tiếng tranh luận vẫn dội qua những hàng cột đá"). Trích `ch05.md:57`: "Không có tiếng hỏi lệnh nào, cũng không ai xác nhận lời gọi tôi đến thuộc thủ tục nào. Cánh cửa vẫn đóng."
- **Tiền đề người chơi chọn không được giữ.** `setup.json` của `ky-ao-3` chọn cốt truyện "Con Đường Dưới Tháp Nghiêng" (`plots.picked` = 1, chỉ số từ 0), mô tả: "nhịp phiêu lưu căng thẳng, những cuộc đối đáp sắc bén và các cuộc luận kiếm ngắn mà quyết liệt". Trong 10 chương, chữ "luận kiếm" và chữ "kiếm" xuất hiện 0 lần (grep trên `chapters/ch*.md`); cuộc phiêu lưu kết thúc ở ch05 và sau đó là ngồi chờ rồi nghe hội nghị.
- `bakeoff-luna`: các chương đã đọc hết (ch01, ch03, ch06) và dòng mở/kết các chương khác đều trong Vạn Đạo Điện, cùng ba trưởng lão và một đối thủ; ch04 cuối chỉ "chuẩn bị dẫn hắn ra cửa điện".
- Kế hoạch `ky-ao-3` (`truth_dump.json`, `plan.milestones`): các mốc ở chương 1–2, 4–5, 7–8, 10–11, 12. Ba chương không có mốc nào là chương 3, 6, 9. Cả ba chương đó kết bằng chờ: ch03 "Tôi đứng yên dưới mái đá, nghe ngóng phía sau cánh cửa.", ch06 "cánh cửa đại điện ở cuối hành lang vẫn chưa mở.", ch09 "phán nghị vẫn chưa đến."
- Mục tiêu chương cho chương ngoài mốc chỉ có: "Mốc kế tiếp, chuẩn bị dần" (`pacing.py:207`) và "Chương này phải đẩy truyện tới: kết chương ở một tình thế mới" (`pacing.py:261`). "Chuẩn bị dần" tự nó là chỉ dẫn để chờ.
- Cờ ở yên D-98 (`pacing.py:127`, ngưỡng trong `config/limits.yaml`) không hiện trong `ky-ao-3` và `tu-tien-4` (chạy trước). Lượt dài `long-tu-tien-2` có cờ và vẫn có chương giậm chân (ghi chú ở đó). Nên cờ một mình chưa đủ.

Nguyên nhân (suy luận có căn cứ): đề ra từ khâu khởi tạo đã là kiểu "hồ sơ/thương nghị" (xem §2.12), kế hoạch mốc có khe, và prompt dàn ý không đòi "mỗi cảnh phải đổi một thứ". Dạng "đẩy truyện tới" mà không cụ thể hóa thì "kết ở một tình thế mới" dễ đạt bằng chữ: một văn bản được ký / đặt xuống / "chưa ký" đều trông như "tình thế mới" với model.
Sửa: mục tiêu chương, dàn ý, kế hoạch (mốc cho mọi chương), style guide.

### 2.3 Cảnh 2 diễn lại cảnh 1; một câu hỏi được hỏi lại nhiều lần trong một chương
- `bakeoff-luna/chapters/ch03.md`: câu "Ai giao bản ghi?" được hỏi ở dòng 61 (Triệu), 105 (Vương) và 113 (nhân vật chính), còn được nhắc ở 19, 57, 87 và ở lựa chọn cuối chương (160). Cảnh 2 (dòng 73) mở lại gần như cùng thế với cảnh 1 (dòng 5): nhân vật chính giữ Tông Chủ Ấn, Lục đứng trước án, "vẫn không chịu nhúc nhích".
- `bakeoff-luna/chapters/ch01.md`: "Ai kiểm chứng?" ở dòng 9 ("Nói rõ ai kiểm chứng từng chứng cứ"), 15 ("Ta hỏi chứng cứ do ai kiểm chứng"), rồi cảnh 2 lại ở dòng 77 và 83 ("Ai kiểm chứng lời khai? Ai đối chiếu chứng vật?"). Cảnh 1 kết ở "lời buộc tội đã bị chặn lại, chờ đối chiếu căn cứ" (:71); cảnh 2 mở bằng đòi Triệu đọc căn cứ (:77): cùng nhịp.
- `tu-tien-4/chapters/ch01.md:71` ("Tôi đặt bản ghi lên giữa án, song vẫn giữ một bàn tay trên bìa.") và `:79` ("Tôi đặt bản ghi giữa án, bàn tay vẫn ghì trên bìa.") là cùng một động tác, cách nhau một dấu `* * *`. Cả ba bên cũng lặp đề nghị giữ bản ghi ở cả hai cảnh (`:25`, `:57`, `:59` rồi `:99`).
- `ky-ao-3/chapters/ch10.md`: tuyên bố "cả hai lệnh mang dấu của ta nhưng không chứng minh ta chấp thuận" xuất hiện ở dòng 5, 21 ("Ta không phủ nhận con dấu ấy. Ta chỉ không muốn người ta lấy nó thay cho lời ta chưa từng nói.") và 45, rồi lại thành lựa chọn cuối chương; chữ "ghi" xuất hiện 10 lần trong một chương.
- `ky-ao-3/chapters/ch05.md:27` và `:35`: cảnh 1 kết bằng "Tôi cất thẻ, ôm hộp sát người rồi đứng dậy.", cảnh 2 mở bằng "Tôi rời khe chuyển vật còn hé mở, men theo khúc tường gãy trở lại cầu thang chính." (cùng việc, kể lại).
Số đo: độ giống Jaccard trung bình giữa hai đoạn cuối cảnh 1 và hai đoạn đầu cảnh 2 là 0,19–0,21; chỉ số này không tách được vì dùng chung từ vựng một truyện. Lời thoại trùng (J > 0,7) giữa hai cảnh chỉ 1/252 dòng, nghĩa là lặp ở mức ý và nhịp, không phải chép chữ. Vì vậy bộ kiểm lặp theo chữ (`quality.repetition`, `max_repeats` theo cảnh) không thấy.

Nguyên nhân (đọc được): cảnh 2 được viết bằng một lời gọi riêng, cảnh 1 đưa vào dưới "Các cảnh trước trong chương" và dàn ý chỉ dặn "Cảnh nối tiếp đúng những gì đã xảy ra" (`scene.py:353`). Không có dòng "bắt đầu SAU nhịp cuối, không diễn lại". Model nối tiếp theo nghĩa đen: bắt đầu bằng việc nhìn lại.
Sửa: dàn ý (một dòng), style guide (Bám dàn ý), tuỳ chọn kiểm bằng code.

### 2.4 Giọng nhân vật giống nhau; lời thoại là biên bản
- 43–57% lời thoại chứa từ vựng thủ tục; lời thoại dài (16–20 từ TB), chỉ 7–13% là câu ≤ 6 từ.
- `tu-tien-4/chapters/ch03.md:41`: "Có quyền vào kho không đồng nghĩa với có tội." (Hàn Khắc) và `:109`: "Người có quyền vào kho không đồng nghĩa với kẻ tráo văn thư." (Hàn Khắc, lặp lại) và `:63`: "Đúng. Còn sổ kho không thể thay bản ghi buổi thương nghị." (nhân vật chính). Cùng khuôn "X không đồng nghĩa/không thể thay Y" ở ba miệng.
- `ky-ao-3/chapters/ch10.md:11` (Đoàn Ngọc Kỳ): "Hội nghị phải xét ai có thẩm quyền dùng dấu ấy, và dùng theo thủ tục nào." và `:17` (Lý Vân Thư): "Ghi nhận con dấu không trả lời được ai đã dùng nó." Che tên đi thì không phân biệt được người nói.
- Điểm riêng đáng chú ý: những người đối diện nhân vật chính hầu như luôn dùng câu đủ chủ vị, lịch sự, đối xứng, không ngắt lời, không nói dở, không nói lạc.

Nguyên nhân (đọc được, và là phát hiện quan trọng): **mô hình viết không nhận được tính cách của bất kỳ nhân vật phụ nào.** `CharacterInfo` chỉ có `id, name, aliases, alive, location, holds, user_authored` (`graph/context.py:50-57`) và `render_writer_context` chỉ in tên, còn sống hay chết, nơi ở, đồ đang giữ (`graph/context.py:491-495`). Khởi tạo có lưu `personality` và `backstory` cho nhân vật phụ vào nút (`setup.py:808`), nhưng chúng không bao giờ tới model viết. Tính cách nhân vật chính tới model qua `story_brief` (`setup.py:681`). Style guide v2 đòi "Mỗi nhân vật có giọng riêng: từ ngữ, độ dài câu, cách né tránh" nhưng không cho dữ liệu để làm; một dòng đòi mà thiếu nguyên liệu thì model rơi về giọng mặc định chung.
Sửa: (a) code: in `personality` (và `speech` nếu thêm) của nhân vật có mặt vào mục "Nhân vật có mặt"; (b) style guide (mục Lời thoại). Cả (a) lẫn (b) cần thiết: (b) không tự làm được.

### 2.5 Tật cử chỉ lặp, một phần do chính luật v2 gây ra
- "ngón tay" 24 lần / 10.109 từ ở `tu-tien-4`: "gõ ngón tay lên mặt bàn" (`ch01.md:23`, `ch03.md:131`, `ch06.md:73`…), "ánh mắt" 17 lần / 6.826 từ ở `bakeoff-luna`.
- `bakeoff-luna/chapters/ch03.md:5` và `ch05.md:5` mở bằng đúng hai câu giống nhau: "Tôi siết Tông Chủ Ấn trong lòng bàn tay. Cạnh ấn cấn vào da, lạnh ngắt." Còn `ch01.md:5` ("Tôi siết Tông Chủ Ấn trong tay áo, cạnh ấn cấn vào lòng bàn tay") và `ch04.md` ("Cạnh ấn cấn vào lòng bàn tay, đau đến tỉnh táo") là biến thể. "Tông Chủ Ấn" có mặt trên 46 dòng trong 6.826 từ; "siết … Tông Chủ Ấn" sáu lần, thêm một biến thể ("siết ngón tay quanh Tông Chủ Ấn", ch02). Hai chương cách nhau một chương (ch03 và ch05) mở bằng cùng hai câu: model viết không thấy câu mở chương trước.
- `ky-ao-3`: "hộp đá" + "chiếc hộp" 85 lần / 11.040 từ; "Khóa vẫn nguyên, niêm vẫn kín." (`ch05.md:21`) và "Khóa vẫn khép, niêm vẫn còn nguyên." (`ch05.md:41`) trong cùng một chương.

Nguyên nhân (đọc được): luật v2 "Xen giữa các lượt thoại những dòng ngắn tả cử chỉ" kèm "Cảm xúc hiện qua hành động, cử chỉ" đòi cử chỉ nhưng không nêu thực đơn nào, nên model chọn cử chỉ rẻ nhất (tay, mắt, bàn). Không có luật chống lặp qua chương: kiểm lặp của code là theo cảnh (`config/quality.yaml`: `max_repeats` "trong một cảnh"). Prompt viết không thấy câu mở của các chương trước (chỉ tóm tắt; đoạn đã hiện mặc định tắt, D-85).
Sửa: style guide (mục Nhịp và giọng; sửa luật xen cử chỉ), tuỳ chọn code: đưa câu mở của hai chương gần nhất vào đề viết với nhãn "không dùng lại".

### 2.6 Lựa chọn cuối chương không rẽ hướng, và lời thoại luôn là nói thật
- `ky-ao-3/chapters/ch05.md:71-73`: "Tiếp tục đứng ngoài cửa, giữ chặt chiếc hộp và chờ bên trong trả lời." / "Gõ cửa lần nữa, nhắc rằng tôi vẫn đang chờ cùng chiếc hộp và hai tờ lệnh." / "Tự nhủ phải giữ lấy chiếc hộp, dù hội nghị có thể kết thúc mà không gọi tôi vào." Ba cách của cùng việc chờ. Đọc tay cả 10 bộ lựa chọn của `ky-ao-3`: ch01, ch05, ch06, ch07, ch10 là ba cách của cùng việc giữ hộp và chờ (5/10).
- Lựa chọn lời thoại: 14 nói thật, 1 im lặng, 0 nói dối trong 15 (cả ba truyện), dù `TONE_GUIDANCE` (`choices.py:171`) nhắc "cân nhắc" lie/silence. Ghi chú `tu-tien-4/notes.md` mục 3 đã nêu điểm này từ 21/10: đề `choices-2` không đủ.
- Lựa chọn nội tâm là "Tự nhủ…", "Thầm lo…", "Thầm nghĩ…" (ví dụ `bakeoff-luna/ch02`: "Thầm nghĩ: 'Hắn có gì đó không đúng. Càng chống đối, càng đáng nghi.'"): không đổi gì trong cảnh kế, nên nút này chỉ là trang trí. Hai lần nút "nội tâm" được chọn trong `ky-ao-3` (ch05 "Tự nhủ phải giữ lấy chiếc hộp…", ch06 "Tự nhắc mình không được lơ là…"), chương sau mở đúng như cũ: ch06 "Tôi ghì chiếc hộp đá vào ngực", ch07 "Tôi đặt hộp đá trên đùi… Cửa đại điện vẫn khép."
- Chữ lựa chọn dài như câu thoại hoàn chỉnh (TB 16–18 từ) và được dùng làm mở chương: `tu-tien-4/chapters/ch03.md:3` rồi `:5` ("Tôi đề nghị rồi: ba bên cùng đối chiếu dấu mục này với bản ghi trước khi xác nhận câu chữ."); `ky-ao-3/chapters/ch10.md:3` rồi `:5` (cả lời được lặp nguyên văn, kèm câu thứ hai).

Nguyên nhân (đọc được): `SYSTEM_PROMPT` của lựa chọn đòi "đúng 3 lựa chọn… mỗi lựa chọn một hướng khác nhau, … ít nhất 2 loại khác nhau; nên đủ cả 3 loại" (`choices.py:175`). Điều ép là loại, không phải hậu quả: cảnh đứng yên thì cả ba đều đứng yên, chỉ khác loại. `STALLED_NOTE` (`choices.py:194`) chỉ bật khi cạnh `LOCATED_AT` của nhân vật chính không đổi nhiều chương; khi bộ trích bỏ cạnh vị trí thì cờ mù (ghi chú đã có ở `long-tu-tien-2`). Lượt `ky-ao-3` chạy trước D-98 nên không có ghi chú này. Việc mở chương bằng lựa chọn: `scene.py:256` đưa "Lựa chọn của người chơi dẫn tới chương này" vào đề mà không nói phải làm gì với nó; model thực thi nó nguyên văn.
Sửa: prompt lựa chọn; dàn ý/style guide (mở chương).

### 2.7 Xung đột bị thủ tục hóa; không có rủi ro thật
- `ky-ao-3/chapters/ch10.md`: "Ghi nguyên lời khai", "Ghi rõ giới hạn lời thề ấy", "Ghi phản đối ấy", "Xin ghi riêng trách nhiệm…", mười lần chữ "ghi" trong một chương. Mọi đòn đối đáp thành yêu cầu thư lại ghi thêm một dòng.
- Đề bài `ky-ao` khai tag `darkness` "vừa phải, có phản bội, hy sinh và chết chóc, không tả máu me"; trong các chương đã đọc và qua dòng kết của cả 10 chương, tôi không thấy ai bị thương, bị bắt, hay chết sau ch01 (người hộ tống ngã xuống), chưa thấy ai mất vật. Hộp vẫn nguyên ở chương cuối (`ch10.md:35`: "khóa nguyên vẹn"). Chưa kiểm hết dòng giữa của ch02–ch04, ch06, ch08, ch09.
- `tu-tien-4`: 6 chương mà chỉ có giấy; sự thật "Phạm Đức Hành tráo văn thư" (bí mật, lộ ch04) giải quyết bằng thêm một điều khoản.

Nguyên nhân (suy luận): (1) tiền đề trận (§2.12); (2) beat dàn ý "chuyện gì xảy ra, ai nói gì" khuyến khích hội thoại nối hội thoại; (3) không dòng nào trong prompt nói "xung đột phải có giá". Muse Wonder cũng nêu (điểm 4 của nó).
Sửa: dàn ý (beats phải là hành động hoặc đòn có hậu quả), style guide (mục "Xung đột có giá").

### 2.8 Bên trong người kể bị thay bằng phân tích lập trường
- `tu-tien-4/chapters/ch06.md:69`: "Tôi nhìn từng người. Hàn Khắc muốn biết ai được xuống; Lưu Thanh Đào muốn mọi dấu vết đều có tên; Vân Tiêu Lan muốn việc kiểm tra không biến thành quyền khai thác." Đây là điểm danh động cơ, đúng thứ v2 cấm ("không giải thích lại điều vừa cho thấy"). Cùng kiểu ở `ch01.md:35`.
- Từ cảm xúc trực tiếp ít (0,9–3,8 / 1000 từ), nhưng cũng không có phản ứng cơ thể thay thế: giác quan nóng/ấm = 0 ở hai truyện; đau/nhói/run = 0 ở hai truyện. Phản ứng duy nhất của cơ thể là bàn tay. Không đoạn nào nói điều nhân vật chính sợ, muốn riêng, hay nhớ.
- Hai lần khởi tạo (`setup.json`, `characters.options[0]`) đều đề xuất ứng viên đầu tiên là người "điềm tĩnh… giỏi nhận ra kẽ hở trong lời nói" (Tạ Cảnh Hoài ở `tu-tien-4`, Tạ Vân Chi ở `ky-ao-3`): cùng nguyên mẫu. Nhân vật được chọn (Đường Tử Mặc, Ninh Tố Hành) có tính cách khác, tôi chưa đọc nên không nói gì về họ.

Nguyên nhân (đọc được): luật "cho thấy, đừng kể" được tuân thủ bằng cách cắt hết lời gọi tên cảm xúc, nhưng không có luật nào đòi một thứ thay vào. Không có chỗ nào đòi người kể có điều riêng.
Sửa: style guide (một gạch).

### 2.9 Giác quan nghèo và đơn điệu
- Tiếng động chiếm hết: "tiếng" 3,3–10,4 / 1000 từ kể; mùi 0,3–0,9; vị 0; nóng/ấm 0–0,3.
- "lạnh" là nhãn: `ky-ao-3/ch10.md:23` "Cạnh khóa lạnh ngắt dưới lòng bàn tay.", `:73` "Mặt kim loại lạnh buốt."; `bakeoff-luna/ch03.md:5` "lạnh ngắt".
- Điểm mạnh liền kề: khi cảnh có việc vật chất, hình ảnh tốt. `ky-ao-3/ch05.md:7`: "Mép đá nhẵn hơn phần tường xung quanh, có vết xước mảnh chạy ngang như dấu của những chiếc hộp đã qua đây." và `tu-tien-4/ch03.md:29`: "Lớp giấy nham nhở, mực còn sót lại thành vài vệt xám, chẳng thành nổi một nét chữ hoàn chỉnh."

Nguyên nhân: cảnh luôn trong một phòng kín; `Cho thấy, đừng kể` của v2 đã có "có mùi, có tiếng, có chạm" và model làm đúng hai trong ba. Phần "mùi" gần như không xuất hiện.
Sửa: style guide (một câu thêm, nhỏ). Hiệu quả lớn hơn khi đổi bối cảnh (§2.2).

### 2.10 Nhịp: gọn, đều, an toàn
- Câu kể TB 9,8–12,3 từ, độ lệch chuẩn 4,9–6,8; ít câu dài (≥ 25 từ: 1–5%); câu ngắn (≤ 6 từ) 18–28%. Văn "cụt" nhưng không đổi nhịp theo cảnh: cảnh khống chế tính mạng (`bakeoff-luna/ch06.md:61-71`) có nhịp như cảnh bàn giấy tờ.
- 62–86% đoạn kể mở bằng tên người hoặc "Tôi". v2 đã có luật "không mở nhiều câu liền nhau bằng cùng một chủ ngữ", nhưng luật nói về câu liền nhau, không nói về đoạn; chưa thấy nó thay đổi gì.
- Aphorism cuối đoạn, dù v2 cấm câu đúc kết ở cuối cảnh: `tu-tien-4/ch03.md:99` "Mục ghi tên theo chúng tôi ra khỏi kho, nhưng cái tên thì không." và `:47` "người thắng cuối cùng không hẳn là kẻ nói thật, mà thường là kẻ khiến câu chữ không còn chỗ để lách." (cấu trúc "không… mà…" mà v2 cấm). Số lượng nhỏ (chỉ 1 ca "không… mà" trong tập `chapters/` của ba truyện), nên đây là điểm nhẹ.

Sửa: style guide (Nhịp và giọng), nhẹ.

### 2.11 Kết truyện trống
- `tu-tien-4/chapters/ch06.md:167-173`: kết bằng "Ta chỉ ghi chép và đối chiếu văn bản. Ta không làm người bảo chứng riêng cho bất kỳ tông môn nào." rồi "Không ai giữ tôi lại." rồi `_Hết truyện._`. Không có cái giá hay cái được cho nhân vật chính.
- `bakeoff-luna/ch06.md:93`: "- Thu trận." (Lục chịu thua sau một câu răn đe), rồi tuyên bố quyền điều hành (`:117`). Kẻ thù đầu hàng vì bị chỉ ra rằng lời đe dọa là chứng cứ chống lại hắn; Muse Wonder cũng thấy điều này (điểm 10 của nó).
- Mục tiêu chương cuối (`pacing.py:305`): "gỡ mọi mạch còn mở… hé lộ các bí mật còn lại… không mở tình huống mới" và cảnh kết "khép lại trọn vẹn". Không có chữ nào đòi cái giá hay thay đổi của nhân vật chính.
Sửa: mục tiêu chương cuối (một câu), style guide (mục Cảnh kết truyện).

### 2.12 Tiền đề thiên về "đối đáp trong một phòng", và model chỉ giữ phần đối đáp
- `tu-tien-4`: thiết lập "Canh bạc dưới thủy phủ" (`settings.picked` = 1) và cốt truyện "Khế ước chia dòng" (`plots.picked` = 2, chỉ số từ 0): "Những điều khoản mơ hồ, lời thề tu sĩ… từng câu chữ đều có thể đổi lấy sinh mạng". Tiền đề tự nó là ngồi soạn điều khoản. Truyện giữ đúng tiền đề.
- `ky-ao-3`: tiền đề được chọn có phiêu lưu và luận kiếm nhưng bản viết bỏ phần đó (§2.2). Tag `voice` của đề `ky-ao-vua.yaml`: "hùng tráng mà lạnh, nhiều mưu kế, đối đáp sắc"; tag này nghiêng về đối đáp, và đối đáp là phần model làm ổn nhất (và dễ nhất), nên nó dồn vào đó.
- `bakeoff-luna`: cốt truyện phiên tòa trong một điện. Tiền đề là phòng xử án.
- Việc này thuộc khâu khởi tạo, ngoài phạm vi style guide. Viết lại bằng v3 không cứu được truyện mà tiền đề là "ngồi cãi nhau trong một căn phòng". Tôi ghi để 3c cân nhắc; chưa đề xuất chi tiết vì ngoài phạm vi được giao.
Sửa (gợi ý, chưa thử): prompt đề xuất cốt truyện (`setup.py`) đòi ít nhất hai nơi chốn khác nhau và một mối đe doạ vật chất có thời hạn; mục tiêu chương nhắc cốt truyện đã chọn khi chương không có mốc (§5.3).

## 3. Điều nên giữ

(Đọc tay; Muse Wonder đồng ý ở hai trong ba.)
1. Chi tiết vật chứng kể chuyện: `tu-tien-4/ch03.md:29` (tên bị cạo); `ky-ao-3/ch05.md:7` (đá nhẵn, vết xước). Model làm tốt khi có vật thể để quan sát.
2. Ch01 của `ky-ao-3` là chương hay nhất trong số đọc: thân thể mệt, địa hình có nguy hiểm, quyết định trả giá bằng sức. Mở đầu "Đoàn Khương khuỵu xuống giữa đường." (`ch01.md:3`) là câu mở tốt nhất trong 22 chương: ngắn, cụ thể, bắt đầu giữa biến cố.
3. Tiếng Việt sạch: không chữ khác hệ, không văn dịch rõ rệt, xưng hô nhất quán, định dạng thoại đúng "- " (so với DeepSeek: 24 lỗi định dạng, `2026-10-22-model-bakeoff-1/notes.md`).

## 4. Góc nhìn thứ hai: Meta Muse Wonder (`muse-wonder-1.0`)

Gửi 4 chương (A = tu-tien-4 ch03, B = ky-ao-3 ch05, C = ky-ao-3 ch10, D = bakeoff-luna ch06), không kèm prompt của dự án, không kèm giả thuyết của tôi. Trục như yêu cầu. Kết quả nguyên văn không đưa vào repo; các ý chính và đối chiếu ở dưới.
Kiểm trích: 50/50 câu trích từ chương của Muse tìm thấy nguyên văn trong chương (kiểm bằng script; các chuỗi còn lại trong dấu “ ” là nhãn hay đề xuất prompt của nó, không phải trích chương).

Chi phí thật (giá niêm yết 4 USD vào / 20 USD ra mỗi triệu token): lần 1 7.084 vào + 7.000 ra (6.998 token suy luận, không có chữ nào ra, `finish_reason=length`) = 0,168 USD; lần 2 (`reasoning_effort: low`, `max_tokens` 16.000) 7.084 vào + 3.322 ra (724 suy luận) = 0,095 USD. **Tổng 0,263 USD**, không dùng cache.
Bài học kỹ thuật cho người dùng Muse sau này: mặc định mô hình dùng hết ngân sách đầu ra cho suy luận nếu `max_tokens` thấp; đặt `reasoning_effort: low` và `max_tokens` đủ rộng.

### 4.1 Muse đồng ý với Claude
- Kết chương bằng vật bất động / bế tắc lặp lại (Muse #1, #7; Claude §2.1).
- Lựa chọn giả (Muse #2; Claude §2.6), và lựa chọn bị chương sau nhắc lại nguyên ý (Muse #3, #8; Claude §2.6).
- Xung đột hành chính hóa (Muse #4; Claude §2.7).
- Nhân vật phụ cùng một giọng pháp lý (Muse #5; Claude §2.4).
- Giác quan lặp (lạnh, giấy, đá, "khóa vẫn nguyên") (Muse #9; Claude §2.5, §2.9).
- Nhịp ngắn, đều, kể cả khi nguy hiểm (Muse #10; Claude §2.10).
- Điểm mạnh: chi tiết vật chứng "giấy bị cạo" (Muse S1; Claude §3.1), quan sát cơ cấu bằng mắt và tay (Muse S2; Claude §3.1).
- Nó tự phân loại lỗi: "cấp câu chữ" (lặp, đồng giọng, nhịp, mở chương) và "cấp cốt truyện/nhịp truyện" (đứng yên, lựa chọn không rẽ, nhân vật chính thụ động, kết quá gọn). Trùng với phân loại của tôi ở §5.

### 4.2 Muse nói mà tôi chưa nói hoặc nhấn khác
- **Nhân vật chính thụ động** (Muse #6, "chủ yếu ghi chép, giữ đồ và nhắc giới hạn của mình"): tôi chưa tách thành một điểm riêng; nó nằm lẫn trong §2.2 và §2.7. Muse đúng: ở ky-ao ch05–ch10 nhân vật chính chủ yếu phản ứng. Tôi thêm vào style guide thông qua mục "Mỗi cảnh đổi một điều" (nhân vật làm điều không thể rút lại), và đề xuất cho dàn ý (§5.2).
- **Đối thủ đầu hàng quá dễ ở cảnh kết** ("Thu trận.", Muse #10): tôi đưa vào §2.11.
- Muse xếp "lựa chọn giả" ngay thứ hai và nặng; tôi xếp "giậm chân + kết tĩnh" ở trên. Khác thứ tự, đồng ý nội dung.

### 4.3 Tôi thấy mà Muse không thấy (vì nó chỉ nhận 4 chương, không có prompt, không có dữ liệu)
- Cảnh 2 diễn lại cảnh 1; cùng một câu hỏi được hỏi lại ba lần trong lời thoại của một chương (§2.3).
- Hai chương liền nhau mở bằng cùng hai câu (`bakeoff-luna` ch03 và ch05; §2.5).
- Mô hình viết không nhận tính cách nhân vật phụ (§2.4): đây là nguyên nhân gốc của "cùng một giọng", và là nguyên nhân Muse không thể thấy.
- Luật v2 "xen cử chỉ" gây tật cử chỉ (§2.5).
- Lời thoại luôn là nói thật: 14/15 (§2.6); Muse chỉ thấy 4 lựa chọn của một chương.
- Khe hở trong kế hoạch mốc (chương 3, 6, 9 của ky-ao-3) trùng với ba chương chờ (§2.2).
- Mở chương bằng chữ người chơi đã chọn: Muse thấy hiện tượng (#8); tôi tìm được chỗ phát sinh (`scene.py:256`).

### 4.4 Muse sai hoặc không áp dụng được
- Muse đề nghị **"Bỏ: chỉ dẫn ngầm 'kết chương bằng hình ảnh vật trung tâm còn nguyên vẹn'"** và **"Bỏ: chỉ dẫn ngầm 'mở chương bằng cách thực thi nguyên văn lựa chọn'"**. Cả hai chỉ dẫn này **không tồn tại** trong prompt hiện tại (tôi đã đọc `style_guide_vi.md`, `scene.py`, `pacing.py`, `choices.py`). Nó đoán nguyên nhân khi chưa thấy prompt. Hiện tượng đúng, chẩn đoán nguyên nhân sai: nguyên nhân là chỉ dẫn THIẾU (và `ends_at`, `player_action` đưa thẳng).
- Muse đề nghị **"Trước khi viết, gán cho mỗi nhân vật phụ một mục tiêu riêng, một điều không nói thẳng, một thói quen câu nói và một cách nói dối"**: không làm được trong prompt viết vì "Đầu ra" cấm viết ra kế hoạch; phải làm ở khâu khởi tạo (đặt dữ liệu cho nhân vật) rồi đưa vào ngữ cảnh. Tôi giữ ý, đổi nơi làm (§5.4).
- Muse đề nghị cấm cứng "mỗi chương tối đa một lần các cụm 'vẫn nguyên', 'không ai'…". Tôi giữ ý nhưng nói theo nhóm (cử chỉ và cụm tĩnh) để model không tránh đúng cụm đó rồi bịa cụm tương đương.
- Một số đề xuất của Muse là luật cứng cho cốt truyện ("nhân vật chính phải gây ít nhất một hậu quả") mà prompt viết một cảnh khó thi hành nếu dàn ý không có. Phần đó chuyển sang dàn ý.

## 5. Bốn chỗ sửa: trước → sau

Nguyên tắc của tôi: mỗi thay đổi phải gắn với một số đo ở §6; không thêm số của `config/` vào prompt; giữ mọi luật an toàn đang có (G4, G6, ngôi kể, không chữ khác hệ, bí mật). Phần nào cần đổi code, ghi rõ "(code)".

### 5.1 Style guide: v2 → v3 (bản rút gọn: `evals/scenarios/quality/style_guide_vi_v3.md`)
Giữ nguyên: Bám dàn ý (thêm một gạch), Bí mật, Tiếng Việt tự nhiên, Thể loại, Đầu ra. Đổi:

| Mục | v2 | v3 | Lý do (mục) |
|---|---|---|---|
| (mới) Mỗi cảnh đổi một điều | không có | cuối cảnh khác đầu cảnh ở một điều chỉ ra được; văn bản đọc / ký / đặt xuống / hẹn để sau không tính; không lặp câu hỏi hay lập trường lần hai trong cảnh | §2.2, §2.3 |
| (mới) Kết cảnh và mở chương | chỉ cấm câu triết lý ở cuối cảnh | kết ở lúc điều gì vừa xảy ra, không kết bằng bức tranh đứng yên; mở chương bằng hậu quả của lựa chọn, không chép lại lựa chọn; không dùng lại câu mở chương trước | §2.1, §2.6 |
| Cho thấy, đừng kể | "có mùi, có tiếng, có chạm" | mỗi cảnh có một chi tiết không phải tiếng hoặc lạnh; không điểm danh động cơ; người kể bị chạm mỗi chương | §2.8, §2.9 |
| Lời thoại / xen cử chỉ | "xen những dòng ngắn tả cử chỉ, nét mặt…" | xen khi cần, mỗi lần một thứ khác (giọng, hơi thở, bước chân, đồ vật, ngoại cảnh, ý nghĩ), không mặc định tay và mắt | §2.5 |
| Lời thoại / giọng | "Mỗi nhân vật có giọng riêng: từ ngữ, độ dài câu, cách né tránh" | cụ thể hóa (cụt, vòng vo, mỉa, hỏi ngược, ngắt lời, nói dở); che tên người nói vẫn đoán được; tránh khuôn "X không đồng nghĩa Y" | §2.4 |
| (mới) Xung đột có giá | không có | thủ tục là công cụ, không là cả cảnh; mỗi bên có thể mất thứ cụ thể; đối thủ không đầu hàng vì lẽ phải | §2.7, §2.11 |
| Nhịp và giọng | "đổi độ dài câu… không mở nhiều câu liền nhau bằng cùng chủ ngữ" | thêm: đừng mở phần lớn đoạn bằng tên người hay "Tôi"; mỗi cử chỉ, hình ảnh chỉ dùng một lần mỗi chương (có ví dụ); cụm tĩnh ("không ai", "vẫn") cũng vậy | §2.5, §2.10 |
| Sáo ngữ | danh sách 7 ví dụ | thêm "cạnh vật cấn vào lòng bàn tay", "tiếng khô khốc" (có thật trong 3 truyện) | §2.5 |
| (mới) Cảnh kết truyện | không có | kết bằng cái giá hoặc cái được cụ thể, không bằng tuyên bố hay thủ tục | §2.11 |

Kích thước (đo bằng `load_style_guide`, đã bỏ khối chú thích): v2 = 3.741 ký tự, v3 = 7.277 ký tự (1,95 lần). Chi phí thêm cho mỗi lời gọi viết ở giá Luna: không đáng kể. Rủi ro thật là loãng chú ý: v3 dài gần gấp đôi. Nếu 3c muốn ngắn hơn, thứ tự cắt (ít mất nhất trước): ví dụ sáo ngữ mới → "Cảnh kết truyện" → câu cuối của "Xung đột có giá".

### 5.2 Dàn ý: `OUTLINE_SYSTEM_PROMPT` (`scene.py:350`)
Trước (trích): `Quy tắc: - Cảnh nối tiếp đúng những gì đã xảy ra: các cảnh trước trong chương, và lựa chọn của người chơi dẫn tới chương này. …` và `- beats: 3 đến 6 nhịp theo thứ tự, mỗi nhịp một câu: chuyện gì xảy ra, ai nói gì. - ends_at: cảnh kết ở đâu, một câu.`

Sau (thêm / đổi):
1. Thêm quy tắc: "Mỗi cảnh phải đổi ít nhất một điều chỉ ra được (ai biết gì, ai giữ vật gì, ai ở đâu, quan hệ nào đổi, ai bị thương hay bị bắt, thời hạn nào bắt đầu). Một văn bản được ghi, đọc, ký hay đặt xuống bàn, hoặc hai bên hẹn để sau, không tính." (§2.2)
2. Đổi `ends_at`: "cảnh kết ở đâu, một câu" → "khoảnh khắc cuối: điều gì vừa xảy ra hoặc vừa tới khiến tình thế khác đầu cảnh, một câu. Không phải lúc mọi người đứng chờ." (§2.1)
3. Đổi `beats`: "chuyện gì xảy ra, ai nói gì" → "mỗi nhịp là một việc làm hoặc một đòn đối đáp có hậu quả; không có hai nhịp cùng một lập trường; tối đa một nhịp thủ tục (ghi, đối chiếu, xác nhận) mỗi cảnh." (§2.3, §2.7)
4. Thêm: "Cảnh 2 trở đi bắt đầu SAU nhịp cuối của cảnh trước; không lặp việc đã làm hay câu đã hỏi." (§2.3)
5. Thêm: "Lựa chọn của người chơi: nhịp đầu của chương là hậu quả hay phản ứng ngay sau lựa chọn; không dựng lại việc người chơi đã chọn, không chép lại lời họ chọn." (§2.6)
6. Thêm: "Nhân vật chính phải làm ít nhất một việc không thể rút lại trong chương (mất, lộ, bỏ đi, ra tay), không chỉ chờ hay trả lời." (Muse #6)
Giữ nguyên: tất cả các quy tắc cũ (G6, bí mật, nhân vật mới, JSON schema).
Tùy chọn (code): thêm trường `turn` vào `SceneOutline` ("điều khác đi"), để kiểm được bằng code là không rỗng. Đổi schema nên cần quyết định riêng; phương án chỉ-prompt ở trên là đủ để thử.

### 5.3 Mục tiêu chương: `pacing.py`
| Chỗ | Trước | Sau | Lý do |
|---|---|---|---|
| `pacing.py:261` | "Chương này phải đẩy truyện tới: kết chương ở một tình thế mới, không lặp lại tình huống hay thế khó của chương trước." | giữ câu, thêm: "Tình thế mới nghĩa là cuối chương có một điều mà đầu chương chưa xảy ra hoặc chưa ai biết: người bị thương hay bị bắt, vật đổi chủ, bí mật lộ, người đổi phe, thời hạn bắt đầu, nơi chốn đổi. Ký, ghi, đặt xuống hay hẹn để sau không tính." | §2.2 |
| `pacing.py:207` (`_MILESTONE_TEXT["next"]`) | "Mốc kế tiếp, chuẩn bị dần" | "Mốc kế tiếp: chương này đưa vào một sự kiện hay áp lực cụ thể đẩy nhân vật chính về phía đó" | §2.2: ba chương ngoài mốc đều chờ |
| `pacing.py:305` (chương cuối) | "Truyện kết trong chương này… không mở tình huống mới" | thêm: "Nhân vật chính phải trả hoặc nhận một thứ cụ thể mà chương đầu chưa có (một người, một vật, một chỗ đứng); cảnh kết cho thấy điều đó, không kết bằng thủ tục hay tuyên bố." | §2.11 |
| (code, kế hoạch) | mốc chỉ ở một số chương | mỗi chương một dòng "điều sẽ khác ở cuối chương" khi `story_plan` dựng; hoặc `chapter_goals` báo "chưa có mốc nào ở chương này" và sinh yêu cầu thay đổi mặc định | §2.2: kế hoạch ky-ao-3 trống ở 3, 6, 9 |
| (code) | `standstill` chỉ theo `LOCATED_AT` | tuỳ chọn: thêm tín hiệu thứ hai (ví dụ cảnh cuối chương nào cũng khớp mẫu treo) hoặc tín hiệu từ bộ kiểm văn; hiện cờ một mình chưa đủ (long-tu-tien-2) | §2.2 |

### 5.4 Lựa chọn: `choices.py`
| Chỗ | Trước | Sau | Lý do |
|---|---|---|---|
| `choices.py:175` | "mỗi lựa chọn một hướng khác nhau, … Có ít nhất 2 loại khác nhau; nên đủ cả 3 loại" | giữ loại; thêm: "Ba lựa chọn phải dẫn tới ba hậu quả khác nhau mà người đọc hình dung được: đổi nơi, đổi người đối diện, hay đổi cái giá phải trả. Không đưa ba cách khác nhau của cùng một việc chờ hay giữ yên. Không chọn lại việc nhân vật vừa làm hay vừa nói trong cảnh." | §2.6 |
| `choices.py:178` (inner) | "một cảm xúc hay ý định thầm … feeling là cảm xúc đó (vài chữ)" | thêm: "ý định phải là một quyết định làm hay giấu điều gì ở bước sau, không phải 'tự nhủ', 'thầm lo'." | §2.6 |
| `choices.py:183` (text) | "câu ngắn tiếng Việt mô tả lựa chọn, như người chơi sẽ đọc trên nút bấm" | thêm: "với lời thoại, ghi ý chính của câu định nói ('Hỏi thẳng Lục ai đưa bản ghi'), không viết sẵn nguyên câu nhân vật sẽ nói." | §2.6: chương sau chép nguyên câu |
| `TONE_GUIDANCE` (`choices.py:171`) | "hãy cân nhắc cho lời thoại là lie … hoặc silence" | "Khi cảnh có người dò hỏi, nghi ngờ hay ép, ít nhất một lựa chọn lời thoại phải là nói dối hoặc im lặng; nói thật không phải mặc định." | §2.6: 0 nói dối / 15; D-51 đã thử bản mềm |
| `STALLED_NOTE` | chỉ khi `LOCATED_AT` ở yên | giữ; chạy thử cùng điều kiện "cả ba lựa chọn cùng giữ yên" nếu 3c muốn kiểm bằng code | §2.6 |

### 5.5 Viết (`writer_messages`, `scene.py:386`) và dữ liệu cho viết
- (code) Đưa `personality` của nhân vật có mặt vào mục "Nhân vật có mặt": thêm trường vào `CharacterInfo` (`graph/context.py:50`) và in ở `graph/context.py:491-495`. Đây là sửa nguyên nhân gốc của §2.4, không prompt nào thay được. Lưu ý G1/G2: `personality` do khởi tạo viết (lớp truth) nên được phép vào đề viết như các sự thật khác; `backstory` có thể chứa bí mật, nên bắt đầu bằng `personality` và để `backstory` ra ngoài đến khi có kiểm tra dò lộ cho nó.
- (code, tuỳ chọn) Thêm "câu mở của hai chương gần nhất, không dùng lại" vào đề viết (nguồn: chữ đã hiện, G1 không đổi). Cho §2.5.
- (khởi tạo, tuỳ chọn) Một trường `speech` (một câu về cách nói) cho mỗi nhân vật khi dựng. Cần quyết định riêng.
- Khối "Dàn ý cảnh này" trong đề viết: thêm một dòng ngay sau "Kết cảnh:": "Kết cảnh là lúc điều này vừa xảy ra, không phải lúc mọi người đứng chờ." Dòng này lặp lại luật của style guide ngay tại chỗ model đọc dàn ý (vị trí gần hơn, dễ bám hơn system prompt). Nếu 3c thấy loãng thì bỏ; dàn ý mới (5.2) đã đòi `ends_at` là biến cố.

## 6. Số đo để biết sửa có tác dụng

Chạy bằng `stats.py`/`stats2.py` (sửa `sets` ở đầu file trỏ vào thư mục kết quả mới) trên cùng loại đề (nên giữ đề thương nghị và thêm ít nhất một đề hành động để tách tật của đề với tật của model). Ngưỡng ở cột "mục tiêu" là đề xuất của tôi cho lần thử, KHÔNG phải số của `config/`.

| Số đo | Hiện (3 truyện) | Mục tiêu đề xuất | Gắn với |
|---|---|---|---|
| Chương không-cuối kết bằng tranh đứng yên (đọc tay, 2 người nếu được) | 15/20 | ≤ 5/20 | 5.1 "Kết cảnh", 5.2 `ends_at` |
| Cảnh có đoạn cuối khớp regex treo (`không ai|vẫn|chưa|chờ`) | 24/44 (55%) | ≤ 20% | như trên |
| Số lần "Không ai" / 1000 từ | 1,0–2,0 | ≤ 0,5 | 5.1 "Nhịp và giọng" |
| "ngón tay" + "ánh mắt" / 1000 từ | 2,2–3,2 | ≤ 1,0 | 5.1 xen cử chỉ |
| Câu mở trùng giữa hai chương (J ≥ 0,5) | 0 theo Jaccard, nhưng 1 ca trùng nguyên văn (bakeoff ch03/ch05) | 0 ca trùng nguyên văn | 5.5 câu mở chương |
| Lời thoại chứa từ vựng thủ tục | 43–57% | ≤ 30% (truyện thương nghị) | 5.1, 5.2 |
| Lời thoại ≤ 6 từ | 7–13% | ≥ 20% | 5.1 Lời thoại |
| Đoạn kể mở bằng tên / "Tôi" | 62–86% | ≤ 50% | 5.1 Nhịp |
| Chương có cùng một câu hỏi hay tuyên bố lặp ≥ 3 lần (đọc tay) | ≥ 1 chương ở 3/3 truyện (tu-tien ch01; ky-ao ch10; bakeoff ch01, ch03) | 0 | 5.1/5.2 "không lặp" |
| Lựa chọn: tỉ lệ lời thoại là nói dối hoặc im lặng | 1/15 | ≥ 30% khi cảnh có ép | 5.4 |
| Bộ ba lựa chọn cùng giữ yên (đọc tay) | ky-ao-3: 5/10 (ch01, 05, 06, 07, 10) | ≤ 1/10 | 5.4 |
| Số chương liên tiếp nhân vật chính ở cùng một nơi | ky-ao-3: 6 (ch05–ch10) | không quá 3 | 5.3, kế hoạch |
| Nhân vật phụ: che tên người nói, người chấm đoán đúng | chưa đo | ≥ 80% trên 20 lời thoại (hai người chấm) | 5.5 `personality` |

Bài đo D (`docs/eval.md`) đã có giám khảo; thêm trục "cảnh có đổi tình thế không" (giám khảo Claude, thang 1–3) là rẻ nhất. Tôi không chạy, vì không được giao chạy gọi trả tiền ngoài Meta.

## 7. Thứ tự đề xuất thử (rẻ → đắt)

1. Style guide v3 + dàn ý (5.1, 5.2): chỉ prompt, thử ngay trên `bench_run` đề ngắn cùng seed; so 6 số đo ở §6.
2. Mục tiêu chương và lựa chọn (5.3, 5.4): chỉ chữ cố định; chạy cùng bộ.
3. `personality` vào đề viết (5.5, code nhỏ, có test G1/G2): sửa nguyên nhân gốc của giọng nhân vật.
4. Kế hoạch mốc mọi chương, khởi tạo yêu cầu đa nơi chốn (ngoài phạm vi).

Rủi ro đã biết: v3 sửa tật tĩnh có thể đẩy model sang chiều ngược lại (biến cố vô cớ, nhân vật chính hành động mà không có động cơ, và vi phạm dàn ý/kế hoạch). Luật "không thêm sự kiện lớn ngoài dàn ý" vẫn còn; thay đổi phải nằm trong dàn ý (5.2), không do bản viết tự thêm. Người canh (`guard`) và kiểm bí mật không bị chạm.
