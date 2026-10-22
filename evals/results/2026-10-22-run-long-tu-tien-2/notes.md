# Nhận xét đọc tay: long-tu-tien-2 (mức Truyện dài, chạy hết 24/24, GPT-6 Luna)

Người đọc: Claude (nhánh eval/long-story-2), 23/10/2026. Nguồn: `summary.md`, `report.json`, `calls.jsonl`, `truth_dump.json`, `chapters/`. So với lần 1 `../2026-10-22-run-long-tu-tien-1/` (dừng ở chương 16 vì lỗi TLS).

**Phạm vi đọc tay:** đọc nguyên văn mở đầu ch01, ch08, ch12, ch13 (một phần), kết ch24 và lựa chọn cuối ch10, 12, 14, 16; đọc tóm tắt do model viết của cả 24 chương (`truth_dump.json`); còn lại chạy script (đếm từ, đếm cạnh). Chưa đọc từng dòng 24 chương.

- Lệnh: `cd backend && uv run python -m writory.pipeline.bench_run --scenario ../evals/scenarios/story_run/long-tu-tien.yaml --label long-tu-tien-2 --budget 0.35 --env-file C:/Work/AI/WriTory/.env`. Đề `long-tu-tien` v1, seed 20261022, commit `96cdf7a` (D-97, D-98, D-102 đã có). Dry-run trước qua 20 chương.
- **Không so thẳng được với lần 1 ở mức nội dung:** cùng đề và seed nhưng model khởi tạo dựng thế giới khác (nhân vật chính Diệp Chiêu Ninh, thương nghị phong ấn ở Bạch Lộ; lần 1 là đoàn đi qua Cốc Đèn). Kế hoạch lần này 24 chương, 8 mốc, 2 bí mật, 6 mạch (lần 1: 8 mốc, 2 bí mật, 4 mạch).

## Số chính (đọc từ `report.json`)
| | lần 2 | lần 1 (tới ch15) |
|---|---|---|
| Chương ghi được | **24/24, có kết truyện** | 15/24, chết ở ch16 (TLS) |
| Chi phí thật | **0,2559 USD** (trần `--budget` 0,35) | 0,1565 USD |
| Lỗi chết giữa chừng / thử lại của người chơi | 0 / 0 | 1 (TLS) / 0 |
| Viết lại | 8 lượt (0,33 mỗi chương) | 6 lượt (0,40 mỗi chương) |
| Lỗi tìm thấy | `teller_does_not_know` ×5, `quality:repetition` ×7, `at_most_one` ×1 | `teller_does_not_know` ×7, `repetition` ×3 |
| Còn khi hiện | `teller_does_not_know` ×1 (ch6), `repetition` ×1 (ch8) | `teller_does_not_know` ×2 |
| Cảnh bị chặn / `leak:name` / dàn ý bỏ mạch | 0 / 0 / 0 | 0 / 0 / — |
| Fact mới | 62 (2,6 mỗi chương) | 40 (2,7) |
| Cạnh bộ trích bỏ | 36 (Fact mới 13, trùng Fact 7, sai schema 6, thiếu KNOWS 5…) | — |

## Mạch và bí mật
- Đúng khoảng cả 2 bí mật (lộ ở ch6 trong 6–10 và ch11 trong 11–15) và cả 6 mạch (gỡ ở ch3, 9, 11, 14, 17, 18).
- **Cả 8 mục đều được xử lý ở chương ĐẦU của khoảng cho phép** (3 trong 3–8; 9 trong 9–16; 11 trong 10–15; 14 trong 14–21; 17 trong 17–24; 18 trong 18–24; bí mật ở 6 và 11). "Đúng khoảng" ở đây không cho biết cách gỡ có đáng kể hay chỉ là một bước thủ tục. Chưa đọc từng cảnh gỡ.

## Chương giậm chân
**Thước đo nơi ở của nhân vật chính** (cùng cách `pipeline/pacing.standstill`, tính lại từ `truth_dump.json`, ngưỡng 4; cờ ở hàng ch N là cờ khi viết ch N+1):

| | lần 1 (15 chương) | lần 2 (24 chương) |
|---|---|---|
| Cờ `standstill` bật khi viết (lần 1 chạy trước D-98 nên đây là tính lại, đề không có cờ) | ch4, ch10–16 (đang bật từ ch10, tới 10 chương ở Cốc Đèn) | ch6 (4 chương ở Điện Nghị An), ch7 (5 chương), ch23 (4 chương ở Trấn Thiên Đàn); ch24 là chương cuối nên không áp |
| Cạnh `LOCATED_AT` của nhân vật chính | luôn có (còn 2 cạnh mở cùng lúc ở ch6–9) | **mất ở ch7–17**: bộ trích đóng cạnh Điện Nghị An ở ch7 mà không mở cạnh mới, mở lại ở ch18 (`truth_dump.json`, gói ch7 và ch18) |
- **Điểm mù của thước đo (đọc được):** 11 chương liền (ch7–17) không có nơi ở nên cờ không thể bật, đúng đoạn dài nhất của vòng lặp dưới đây. Lần 1 thì ngược lại: cờ bật 7 chương liền mà truyện vẫn ở Cốc Đèn.
- **Sau khi cờ bật (đọc được):** ch6 rời Điện Nghị An sang Dinh Hàn gia rồi Trấn Thiên Đàn; ch7 nơi ở rời Điện Nghị An; ch23 nhân vật chính kiệt sức, ra lệnh rời vị trí canh. Ba lần bật, ba lần có đổi nơi hay tình thế trong chương. Không có nhóm đối chứng và các mốc kế hoạch cũng rơi vào đó (ch6–9, 21–23), nên chưa nói được cờ gây ra thay đổi.

**Đọc tóm tắt cả 24 chương và nguyên văn các chương nói trên:**
- ch1–7: thương nghị, mất tích của Tố Nguyệt, lần theo dấu vết: có tiến triển.
- **ch8–17 (10 chương liền) cùng một khuôn:** họp ở Điện Nghị An hoặc đi quanh Trấn Thiên Đàn, nhân vật chính "yêu cầu ghi lại", Lã Tĩnh Thành "ghi sổ, đối chiếu bản ghi, không kết luận", Đoàn Khương đòi phân rõ trách nhiệm. Ví dụ tóm tắt ch10, 11, 12, 13, 14, 15 đều nói "đối chiếu sổ canh gác và sơ đồ, âm vang tạo thành vòng quanh đàn, chưa rõ ai làm". Tiến triển thật trong 10 chương đó rất ít: ch11 Đoàn Khương thú nhận (bí mật 2), ch17 Tố Nguyệt trở về.
- ch18–23: thỏa thuận lượt canh rồi từng người nhận lượt, kiệt sức ở rãnh đá (ch19–23): lặp thủ tục theo từng người nhưng mỗi chương có hậu quả mới.
- **Đếm từ ghi chép** (script): "ghi/ghi lại/ghi nhận" trung bình 2,8 lần mỗi chương ở ch1–4, 3 và 10 ở ch5–6, **6–28 mỗi chương (trung bình 17,7) ở ch7–24**; "sổ/bản ghi/nghị sự/biên bản" 13–27 ở ch10–12.
- **Không phải lặp nguyên văn:** số 6-gram của chương n có trong chương n-1 trung bình 0,3% ở cả hai lần chạy (cao nhất 1,8% ở ch10 lần 2). Vòng lặp là theo nghĩa (cùng một thao tác, câu khác), nên độ giống chữ không bắt được (cùng kết luận với D-98).
- Ước lượng đọc tay: khoảng 14 trong 24 chương (ch8–17, 20–23) là biến thể của cùng một cảnh thủ tục (suy luận từ tóm tắt và các đoạn đã đọc; không đếm chặt từng nhịp). Lần 1 ước 12 trong 15.
- **Lựa chọn cuối chương:** ch10, 12, 14, 16 đều có ba lựa chọn cùng chủ đề "ghi thêm, đối chiếu thêm, giữ nguyên bản ghi" (ví dụ ch12: "Rà lại sơ đồ và các mốc giờ một lần nữa trước khi khép hồ sơ"). Cờ `standstill` không bật ở các chương đó (mất nơi ở), nên `STALLED_NOTE` của D-98 không có mặt. Bộ chạy chọn ngẫu nhiên theo seed.
- Mốc kế hoạch (suy luận, `truth_dump.json` `plan.milestones`): ch1–2 trở lại, ch3–5 phát hiện mất tích, ch6–9 "thương nghị buộc các phe công khai điều kiện", ch10–12 "tìm dấu vết", ch13–15 "các phe nhận ra tranh giành làm vết rạn mở rộng", ch18–20 cao trào, ch21–23, ch24 kết. Không có mốc nào ở ch16–17; ba mốc giữa truyện đều là biến thể của "đàm phán và ghi nhận". Thế giới này vốn tĩnh (phòng họp), nên một phần lặp là do kế hoạch, như lần 1.

## Kết truyện
Có: chương cuối phát `story_finished`, văn kết bằng "_Hết truyện._". **Nhưng cảnh kết là thủ tục** (đọc nguyên văn ch24): Đoàn Khương và nhân vật chính đều kiệt sức, mọi người ghi "chưa có người nhận lượt kế", phù lệnh vẫn do Tố Nguyệt giữ, "nền đàn khẽ rung". Mốc cuối kế hoạch ("quyền giữ ấn được định đoạt và nhân vật chính đối diện hậu quả") được đáp bằng một bản ghi điều kiện, vết rạn không được giải quyết hay hy sinh cụ thể. Đọc được; ý "kết yếu" là đánh giá của tôi.

## Liền mạch, xưng hô, ngôi kể
- Ngôi kể thứ nhất ("tôi") đều ở cả 24 chương (đếm "tôi" mỗi chương 12–50; đọc ch01, 08, 12, 24). Không đổi ngôi trong văn.
- **Tóm tắt chương lại dùng ngôi thứ ba và tên không ổn định** ("nhân vật chính" ở ch3, "Diệp" ở ch4–7, "Chi Ninh" ở ch1 chứ văn gọi "Tôi"; "Chiêu Ninh" ở ch2, 18–20): lỗi của bước tóm tắt, không thấy lọt vào văn (văn gọi "Chiêu Ninh" 15 lần và "Diệp" 17 lần cả truyện, rải rác). Tóm tắt của chương N-1, N-2 vào đề chương N, nên có thể là lý do nhân vật chính ít khi được gọi tên.
- **Xưng hô "ông/anh" (vấn đề đã biết):** bằng regex "tên + ông/anh/nàng/bà/cô trong 60 ký tự": Đoàn Khương và Lã Tĩnh Thành khớp "ông" 21 lần, "anh" 0 lần (8 khớp "nàng/bà/cô" có thể là người khác trong cùng câu); không thấy đảo "ông/anh". Mẫu nhỏ (khớp ít) và mới đọc ba chương; **chưa nói được đã hết lỗi**.
- Lỗi mâu thuẫn đồ vật: `guard:at_most_one` ×1 (ch19, viết lại, hết lỗi). Không cạnh `HOLDS` và `LOCATED_AT` cùng đồ vật còn lại khi hiện.

## Chi phí theo thời gian (đọc từ `calls.jsonl`)
- Trung bình mỗi chương: ch1–5 0,0079; ch6–10 0,0106; ch11–15 0,0099; ch16–20 0,0125; ch21–24 0,0113 USD. Tăng khoảng 40–60% so với ch1–5; chương đắt nhất ch18 (0,0144), cảnh đắt nhất 0,0082 (trần 0,02), chương 0,0144 (trần 0,08).
- Token vào trung bình mỗi lời gọi (ch1–3 → ch22–24): **trích 7,6k → 17,9k**; **tạo lựa chọn 2,7k → 7,0k**; dàn ý 4,8k → 5,5k, viết 5,8k → 6,7k, tóm tắt và kiểm duyệt phẳng (~2k). Hai vai tăng theo truyện: trích (danh mục thực thể và cạnh) và lựa chọn (`player_view`/sổ tay). So với lần 1: trích 6,9k → 14,3k tới ch15; lần này ch12 khoảng 12,1k, cùng quỹ đạo.
- Suy luận (chưa đo): nếu hai vai tăng tuyến tính tiếp, chương 35 tốn khoảng 0,016 USD và cả truyện 35 chương cỡ 0,40 USD, dưới trần truyện 1,0.
- Cache: 188/290 lời gọi có token cache, 19% token vào từ cache.

## Kết luận: mở mức Dài cho người chơi chưa?
Đọc được:
1. **Kỹ thuật ổn:** chạy hết 24 chương, có kết truyện, 0 lỗi người chơi phải thử lại, 0 chặn, 0 `leak:name`, chi phí 0,26 USD, D-97 chặn được lỗi TLS tạm (không gặp lại lần này; chưa chứng minh bằng một lỗi TLS thật).
2. **Truyện giữa vẫn giậm chân:** khoảng một nửa đến hai phần ba số chương là cùng một cảnh thủ tục, nặng ngang lần 1 và dài hơn (ch8–17 thay vì ch10–15). Cờ D-98 chỉ bật ở ba chương và không bật ở đoạn dài nhất.
3. Kết truyện có nhưng yếu về kịch tính.

Suy luận (chưa kiểm):
- Với thế giới này D-98 không chứng minh được tác dụng: thước đo (nơi ở) hỏng ở đoạn cần nhất vì bộ trích không giữ cạnh `LOCATED_AT`. Hướng thử: cờ không dựa vào một cạnh (ví dụ số chương liền không có Fact mới có sự kiện, không có mạch hay mốc đổi trạng thái), hoặc buộc bộ trích luôn có đúng một nơi ở hiện tại của nhân vật chính (như D-90 làm với đồ vật).
- Mốc kế hoạch giữa truyện cần đổi tình huống; mật độ bí mật/mạch/mốc theo số chương chưa làm (D-98 "chưa làm").
- Đã thấy một lần chạy mỗi lần, hai thế giới khác nhau: chưa biết vòng lặp có chung cho mức Dài hay do kiểu thế giới "phòng họp".

**Trả lời "mở mức Dài được chưa": chưa nên mở cho người chơi thường.** Không phải vì kỹ thuật (đã ổn) mà vì chất lượng đoạn giữa; nếu mở thì ghi rõ là bản thử, hoặc làm trước (a) cờ giậm chân không phụ thuộc cạnh `LOCATED_AT`, (b) mốc giữa truyện đổi tình huống, rồi chạy lại một lần. Quyết định mở là của chủ dự án.

## Chưa kiểm
- Một thế giới, một lần chạy, một seed; model có nhiễu. Chưa đọc hết văn.
- Xưng hô "ông/anh" chỉ kiểm bằng regex trên mẫu nhỏ; kết truyện chỉ đánh giá một chương.
- Tóm tắt 24 chương được dùng làm bằng chứng cho vòng lặp: chính tóm tắt cũng có thể nhấn mạnh thủ tục.
