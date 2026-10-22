# Nhận xét đọc tay: long-tu-tien-1 (mức Truyện dài, dừng ở chương 16/24)

Người đọc: Claude, 22/10/2026. Nguồn: `summary.md`, `report.json`, `calls.jsonl`, `truth_dump.json`, `chapters/`. Việc đọc tay làm trên 15 chương đã ghi: đọc kỹ ch01, mở đầu ch11–13 và lựa chọn cuối ch08–15; còn lại dựa vào tóm tắt chương (do model tóm tắt từ chính văn, trong `truth_dump.json`) và đếm cụm từ bằng script. Chưa đọc hết từng dòng văn.

- Lệnh: `bench_run --label long-tu-tien-1 --scenario evals/scenarios/story_run/long-tu-tien.yaml --budget 0.40`, đề `long-tu-tien` v1, seed 20261022, commit `c637659`. Dry-run trước (`--dry-run`) qua đủ 20 chương.
- Kế hoạch dựng 24 chương (mức Dài: 20–35), 2 bí mật, 4 mạch phải gỡ, `tự bấm thử lại` 0.

## Chỗ dừng
- **Dừng ở chương 16, mã `INTERNAL_ERROR`, tốn 0,1565 USD** (trần `--budget` 0,40, trần truyện trong config 1,0: không chạm trần nào). Ghi được 15/24 chương (132.621 ký tự), chưa tới chương kết.
- **Nguyên nhân (đọc từ log, không ở file kết quả):** `ssl.SSLError: [SSL: SSLV3_ALERT_BAD_RECORD_MAC]` trong lời gọi trích của cảnh 1 chương 16 (`calls.jsonl` seq 194, `INTERRUPTED`). Lỗi TLS này đi qua anyio và không bị httpx bọc thành `httpx.HTTPError`, nên `llm/openrouter.py:194,261,273` (`except httpx.HTTPError`) không bắt, rơi xuống `INTERNAL_ERROR` và bộ chạy không tự thử lại (chỉ thử lại các mã trong RETRYABLE). Đây là lỗi mạng tạm, không liên quan độ dài truyện. Chưa sửa (ngoài phạm vi lượt đo); người chơi thật gặp cùng lỗi sẽ thấy lỗi chung thay vì "bấm thử lại".

## Chi phí và ngữ cảnh (đọc từ `calls.jsonl`, `report.json`)
- Chi phí mỗi chương (mọi lượt) gần như phẳng: ch1–5 trung bình 0,0100 USD, ch11–15 trung bình 0,0100 USD (dao động 0,0082–0,0129). Không thấy chi phí tăng theo độ dài trong 15 chương. Lượt chương đắt nhất 0,0129 USD (trần chương 0,08); cảnh đắt nhất 0,0072 (trần cảnh 0,02).
- Token vào trung bình mỗi lời gọi: dàn ý ~4,3k (ch1) → ~5,6k và đứng yên từ ch5 trở đi; viết ~5,4k → ~6,6k, đứng yên; tóm tắt ~2,0–2,8k, đứng yên. **Chỉ lời gọi trích tăng**: 6,9k (ch1) → 14,3k (ch15), khoảng +0,5k token mỗi chương, gần tuyến tính (danh mục thực thể và cạnh đang hiệu lực lớn dần). Chi phí vai trích mỗi chương tăng nhẹ hơn: ch1–5 trung bình 0,0033, ch11–15 trung bình 0,0037 (+13%).
- **Suy luận (chưa đo):** nếu giữ xu hướng tuyến tính, lời gọi trích ở chương 24 vào khoảng 19k token và ở chương 35 khoảng 25k; chi phí cả truyện 24 chương cỡ 0,25 USD, 35 chương cỡ 0,38 USD. Chưa chạy tới đó.
- Theo vai (cả lần chạy): trích 0,0530, dàn ý 0,0327, viết 0,0438, kiểm duyệt 0,0078, lựa chọn 0,0096, tóm tắt 0,0060, khởi tạo 0,0036. Ước tính cho lời gọi bị ngắt: 0,0100.

## Kế hoạch so với kết quả (`plan_vs_result`, tới hết ch15)
- Bí mật 1 (khoảng 8–10) lộ ở ch9: đúng khoảng. Bí mật 2 (15–17): chưa tới hạn.
- Mạch 1 (3–22) gỡ ở ch4, mạch 2 (7–10) ở ch9, mạch 3 (11–18) ở ch14: đúng khoảng cả ba. Mạch 4 (19–24): chưa tới hạn. Không mạch trễ, không gỡ sớm theo bảng.
- **Nhưng "đúng khoảng" không có nghĩa truyện tiến:** mạch 1 ("đoàn có tới được nơi trú an toàn không", khoảng 3–22) gỡ ở ch4 khi đoàn tới Trạm Hạc Tùng, mà ch5–15 vẫn là chuyến đi tiếp. Chỉ 2 bí mật cho 24 chương (mức tối đa 3).

## Lặp nhịp (đọc được, nặng)
- Tóm tắt chương 3–8 và 10–15 cùng một nhịp: nhân vật chính giữ đoàn lại, nhờ Đoàn Khương dò nền đá, Lam Tố Nguyệt nói Đèn Đá Trấn Linh "chỉ báo linh khí, không chứng minh nền an toàn", rồi cho đoàn qua từng người. Ví dụ `chapters/ch11.md:5-9`, `ch12.md:5-9`, `ch13.md:5-9`: ba chương liền mở bằng "Tôi giữ mọi người…" rồi Đoàn Khương cầm cây dò.
- Đếm từ "dò" mỗi chương: ch4 7, ch8 8, **ch10 13, ch11 21, ch12 20, ch13 11, ch14 13, ch15 17**; "lối hẹp/dải đá" ch8 10, ch10 11, ch12 11. Ngoài ch1–2, chỉ ch9 (Võ Thanh Luân thú nhận) không nằm trong vòng lặp này.
- Lựa chọn cuối chương (`chapters/ch10.md:119-121`, `ch14.md:129-131`, `ch15.md:101-103`): cả ba lựa chọn đều là "giữ yên, dò thêm, tự nhắc mình thận trọng". Bộ chạy chọn ngẫu nhiên theo seed nên không tránh được; **không tách được** phần lỗi của bộ tạo lựa chọn, của model viết và của kế hoạch (ít bí mật/mạch trong ch10–18 để kéo truyện đi tiếp).
- Số chương có ít nhất nửa nhịp lặp lại chương liền trước: không đếm chặt từng nhịp; theo tóm tắt, khoảng 12 trong 15 chương (ch3–8, ch10–15).
- **Một phần lặp có sẵn trong kế hoạch** (`truth_dump.json` `plan.milestones`, 8 mốc): mốc ở ch5–6 "chọn tuyến qua Cốc Đèn", ch11–12 "thỏa thuận tạm cho đoàn vượt tuyến tranh chấp", ch15–16 "xác định được lối xuống phong ấn"; giữa ch9 và ch15 hai mốc đều là cùng một cuộc vượt. Mạch 3 ("tìm được lối xuống Môn Ấn Phong", 11–18) gỡ ở ch14. Nên vòng lặp không chỉ do bộ tạo lựa chọn hay model viết.

## Lỗi liền mạch
- Một lỗi: Đoàn Khương gọi là "ông" ở ch1–6, 9, 15 (`ch04.md:11` "Ông dò dọc theo nền đất") nhưng "anh" ở ch7 và ch10–14 (ví dụ `ch11.md:7-8`, `ch12.md:12`). Đồ thị không có thuộc tính tuổi hay giới nên không có gì chặn.
- Ngôi kể thứ nhất đều ở cả 15 chương. Không thấy mâu thuẫn đồ vật hay cửa trong những chỗ đã đọc, nhưng chưa dò kỹ mọi chương.

## Fact mới (D-93), viết lại, chặn
- Fact mới ghi vào đồ thị: 40 (`report.json` `new_facts`), khoảng 2,7 mỗi chương; bộ trích bỏ 5 cạnh vì "Fact mới" (theo lý do bỏ), 7 vì thiếu KNOWS, 1 sai schema.
- Viết lại 6 lần (ch2, 3, 5, 6, 10, 14): `guard:teller_does_not_know` ×7 lần tìm thấy (bốn lượt viết lại ở ch2, 3, 5, 14), còn lại khi hiện ×2 (ch3 cảnh 2 và ch5 cảnh 1: "hiện bản 2 còn lỗi"); `quality:repetition` ×3 (ch6, ch10). Hiện bản trước vì bản viết lại có lỗi chặn: 0.
- Cảnh bị chặn: 0. Không `leak:name`.

## Kết luận: mức Dài chưa đủ để mở cho người chơi
Đọc được (một truyện, một lần chạy, một seed):
1. Chi phí và ngữ cảnh dàn ý/viết không tăng theo độ dài trong 15 chương; chỉ lời gọi trích tăng token vào. Không phải lý do để chưa mở.
2. Gỡ mạch và lộ bí mật đúng khoảng cho 4 trong 4 mục đã tới hạn.
3. **Truyện đứng yên từ ch10 đến ch15 (và rải rác từ ch3):** cùng một cảnh dò đường lặp 6 chương liền. Ở độ dài này người đọc thấy ngay.
4. Một lần chạy chết vì lỗi TLS tạm, và lỗi này sẽ gặp khi chơi thật.
5. Chưa chạy tới chương kết: chưa biết kết truyện dài, chương 16–24 và hai mạch/bí mật cuối.

Suy luận (chưa kiểm):
- Kế hoạch 24 chương chỉ có 2 bí mật và 4 mạch, và các mốc ở giữa truyện (ch5–16) đều xoay quanh cùng một chuyến đi, nên đoạn giữa không có sự kiện mới. Tăng số bí mật tối đa theo mức, hoặc yêu cầu mốc ở đoạn giữa đổi tình huống, là hướng thử (chưa thử).
- Bộ tạo lựa chọn nên có ít nhất một lựa chọn đẩy tình huống đi tiếp khi ba chương liền không đổi nhịp.
- Cần chạy lại ít nhất một lần nữa để biết vòng lặp có phải do thế giới này hay chung cho mức Dài.

Việc cần trước khi mở mức Dài: (a) sửa lỗi SSL thành lỗi tạm có thử lại; (b) thử một cách giữ nhịp cho truyện dài; (c) chạy lại đến chương kết.
