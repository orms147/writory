# Nhận xét đọc tay: video-export-demo

Người đọc: Claude, 29/10/2026. Đây là kết quả đo của bộ xuất kịch bản video (D-125, thực hiện D-118): MỘT lần chạy, MỘT truyện, một ngôn ngữ thoại. File xuất có lộ bí mật (dựng từ toàn bộ lớp `truth`), có cảnh báo ở đầu `script.md` và `script.json`; thư mục này là kết quả đo được commit theo quyết định của chủ dự án, bản xuất thật mặc định nằm ở `exports/` (git bỏ qua).

## Lần chạy được commit
- **Lưu ý:** kết quả này chạy TRƯỚC các sửa sau review độc lập (cảnh bị kiểm duyệt giữ lại mọi chữ model sinh, kiểm duyệt fail-closed, `maybe_billed`, tên trong kiểm tiếng Anh, thư mục đã có kết quả bị từ chối, cảnh báo ở `prompts.txt` và `calls.jsonl`). Không gọi lại model: các thay đổi đó không đổi cách đo ở đây, nhưng `prompts.txt` và `calls.jsonl` ở thư mục này chưa có dòng cảnh báo đầu file mà mã hiện tại ghi.
- Lệnh (chạy trong `backend/`): `uv run python -m writory.export.video --story run-20261021-ky-ao-vua-2-f8a61160 --dialogue-lang zh --chapters 1-3 --budget 0.10 --env-file <.env của chủ dự án> --out ../evals/results/2026-10-29-video-export-demo`.
- Mã: commit `cff6553` (nhánh `feature/video-export`). Hash cấu hình: `config/models.yaml` sha256 `85a93003c31cb257e51255fc98da992def730358332e8f9b5bc26f6d54e11a11`, `config/limits.yaml` sha256 `2e2fb8d677dac59d74f6a5329c7305f66d65779c66b55612cbfc5521efa53d68`. Model vai `video` và `moderate`: `openai/gpt-6-luna` (suy luận low). Phiên bản đề: `video-1`.
- Truyện: `run-20261021-ky-ao-vua-2-f8a61160` (10 chương do pipeline viết, khởi tạo trước D-120 nên KHÔNG có `appearance`/`visual`; đường "sinh bù" được dùng cho cả sáu nhân vật và bốn nơi chốn, cờ `inferred`). Chương 1–3, sáu cảnh.
- Chi phí thật (`usage.cost` trong `calls.jsonl`): 0,012754 USD, 14 lời gọi: 1 bảng, 6 cảnh (một cảnh thử lại một lần vì sai kiểm bằng code), 6 kiểm duyệt G9 (cả sáu cho qua). Trần `--budget` 0,10.
- Tổng chi cho demo, kể cả các lần chạy đã bỏ (không commit): lần đầu trước khi sửa 0,012062 USD (13 lời gọi); một lần mạng đứt giữa chừng 0,000573 USD (một lời gọi xong, mười tám lời gọi `LLM_UNAVAILABLE` mà không rõ có bị tính tiền hay không: lúc đó bộ xuất chưa dùng `maybe_billed`, nên ghi 0); một lần sau khi sửa tên 0,012073 USD (13 lời gọi); lần cuối này 0,012754 USD. Cộng khoảng 0,0375 USD.

## Số đo bằng code (trên `script.json`)
- Sáu cảnh đều `ok`, 68 shot (mỗi cảnh 10–12 shot, trần 12; 3 cảnh chạm trần), tổng 80–110 giây mỗi cảnh. Lời thoại: 72 câu trong 54 shot.
- Mỗi shot có `covers` (cụm nguyên văn trong cảnh): 67/68 có nguyên văn trong cảnh; một shot có cụm trích không tìm thấy nguyên văn (đánh dấu `covers_verified: false` và ghi chú trong `script.md`). Shot đầu và shot cuối cho thấy phủ tới 77–96% độ dài cảnh theo vị trí `covers` cuối; năm cảnh có thứ tự `covers` tăng dần, riêng cảnh 1.2 có một shot ra ngoài thứ tự.
- 7 shot có nhân vật được code bổ sung vào `appears` vì `action_en` nhắc tên mà model quên (`appears_added`); không có prompt nào còn ".." hay tên phiên âm (Bai Jinglun, Duong An Lac…) trong `action_en`.
- Mô tả cố định chép nguyên văn vào mọi prompt có nhân vật đó (test kiểm); tên trong lời thoại viết bằng chữ Hán cố định (陆明薇, 白景伦, 韩星洲…).

## Đọc tay 5 shot (so với `chương.cảnh` trong văn)
1. **1.1.3** (Hàn Tinh Châu cắt ngang). Đúng văn: người nói đúng, câu thoại dịch sát ("一个低阶弟子也值得如此信任吗？"), hành động chỉ gồm điều thấy được. Dùng được.
2. **1.2.5**. Câu "Lời khai như thế thì phân định được đúng sai gì?" đúng là của Hàn Tinh Châu và phần hành động (khoé miệng Bạch Kinh Luân nhích, Hàn Tinh Châu gõ ngón tay) đúng đoạn văn ngay trước đó. Dùng được.
3. **2.2.4**. Hành động đúng văn (đặt hai tay lên mép bàn, chừa một khoảng với tờ chứng từ); Bạch Kinh Luân vốn bị model bỏ khỏi `appears`, code bổ sung nên prompt có mô tả của ông ta. Dùng được; chứng tỏ bước bổ sung có ích.
4. **3.1.6**. Hai lượt thoại giữa Lục Minh Vi và Lão Thành Nguyên đúng người nói, dịch sát. Hành động thêm "gõ đầu gậy" là chi tiết có trong văn kế cận. Dùng được.
5. **3.2.8**. Bốn người nói bốn câu dài trong 9 giây. Người nói và nội dung đều đúng văn, nhưng một clip 9 giây không chứa nổi chừng 80 chữ Hán thoại: **không dùng được nguyên shot**, phải tách theo câu thoại.
Kết luận trên năm shot: bốn dùng được ngay, một cần tách. Đây là mẫu nhỏ chọn trải đều các cảnh, không phải ước lượng tỉ lệ.

## Điều đo được ở cả bộ
- **Lời thoại dày hơn thời lượng:** 22 trong 54 shot có thoại vượt khoảng 5 chữ Hán mỗi giây (đếm bằng code: số chữ của `text` chia `duration_s`). Đề đã dặn "đủ ngắn cho thời lượng" nhưng model không giữ, và code chưa kiểm. Việc sau: tách shot theo câu thoại hoặc kiểm mật độ lời thoại.
- **Thời điểm cảnh:** `time_of_day` là `unknown` ở cả 68 shot: các cảnh chủ yếu trong đại sảnh không nói ngày hay đêm, và khởi tạo chưa sinh thời điểm (D-120 để lại), nên trường này chưa có tác dụng với truyện này.
- **Giới hạn thời lượng shot** 3–12 giây là số tạm, chưa tra giới hạn thật của app video.
- **Mô tả sinh bù** hợp văn (Lục Minh Vi mặc áo đường xa sờn, quai da đeo vai vì từng đi hộ tống; Hàn Tinh Châu áo xanh băng có cổ lông trắng hợp Băng Tâm Môn; mỗi người một dấu nhận diện) nhưng là bịa theo gợi ý, và có thể đổi giữa các lần chạy; truyện có `appearance` do khởi tạo sinh thì được dịch và gọn lại, chưa chạy thử trong demo này.
- **Kiểm duyệt G9** cho qua cả sáu cảnh (truyện không có nội dung cần chặn); đường chặn cứng chỉ được kiểm bằng test với model giả, chưa đo với model thật trên prompt tiếng Anh.

## Chưa kiểm
- Một lần chạy, một truyện, một ngôn ngữ (zh); chưa thử `vi` và `en` với model thật.
- Chưa dán prompt vào Seedance hay app video nào nên chưa biết video ra có giống mô tả không.
- Chất lượng bản dịch thoại tiếng Trung chỉ đọc tay một phần (người đọc không phải người bản ngữ); các từ riêng (ví dụ "Mảnh Thiên Khuyết") có thể được dịch khác nhau giữa các cảnh vì bảng chỉ cố định tên nhân vật và nơi chốn, không cố định đồ vật.
- Truyện dài hơn: số lời gọi tăng theo số cảnh (một lời gọi chia shot và một lời gọi kiểm duyệt mỗi cảnh); dùng `--chapters`.
