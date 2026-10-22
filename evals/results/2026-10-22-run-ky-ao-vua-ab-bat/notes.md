# So bật/tắt đoạn trên trang (D-85): ky-ao-vua-ab-tat, ky-ao-vua-ab-tat-2, ky-ao-vua-ab-bat

Người đọc: Claude, 22/10/2026. Cách chấm khai trước ở `docs/eval.md` (mục "So bật/tắt đoạn trên trang"), commit `c6db5cc`, trước khi chạy.

## Thiết lập
- Cùng một khởi tạo: `--setup-from evals/results/2026-10-21-run-ky-ao-vua-2` (cùng bản kế hoạch, gói chương 0, ba lựa chọn khởi tạo, cùng đề và seed 20261021). Thế giới là của `ky-ao-vua-2`: Đại Nghị Sảnh bị khoá, Hộp Phong Ấn trống, Thiệu Kiếm Hoài mất tích, Bạch Kinh Luân.
- Hai nhánh: tắt (`--page-quotes-top-k 0`) và bật (`3`). Code, config, model giống nhau; chỉ khác giá trị đó. Model và tự chọn lựa chọn khác nhau theo văn nên truyện rẽ nhánh khác nhau sau chương 1.
- Ba lần chạy, vì lần "tắt" đầu hỏng:
  | Nhãn | Bật? | Kết thúc | Chương ghi | Chi phí |
  |---|---|---|---|---|
  | `ab-tat` | tắt | **HTTP 409 từ OpenRouter ở chương 8** (`LLM_REQUEST_INVALID`, không thử lại) | 7 | 0,0595 USD |
  | `ab-tat-2` | tắt | **chạm trần `--budget 0.10`** ở chương 10 (nhiều lần viết lại) | 9 | 0,0912 USD |
  | `ab-bat` | bật | xong | 10 | 0,0846 USD |
- Tổng đã tiêu 0,2353 USD (trần cứng giao 0,25). Không còn dư để chạy lại nhánh tắt cho đủ 10 chương, nên nhánh tắt có hai lần chạy ngắn hơn.

## Cách đọc, và giới hạn
- Tôi **không đọc từng dòng** cả ba nhánh (khoảng 275 nghìn ký tự). Đã làm: tìm theo từ khoá cho cửa và nơi chốn (`cửa`, `khoá`, `mở`) và cho đồ vật (`Mảnh Thiên Khuyết`, `Ấn Lệnh`, `Hộp Phong Ấn`, `hộp`) trên mọi chương; đọc đầu, giữa, cuối mỗi chương của `ab-tat-2` và `ab-bat`; đếm cụm lặp. Lỗi "ai biết gì" chỉ bắt được khi trúng từ khoá, nên **có thể sót ở cả ba nhánh**.
- Dòng dẫn dưới đây là `chNN.md:dòng` trong thư mục của nhánh đó.

## 1. Lỗi liền mạch
| Nhánh | Lỗi | Chương |
|---|---|---|
| tắt `ab-tat` (7 chương) | **Đồ vật**: hộp trống, nhưng ch04:127 ("Mảnh Thiên Khuyết trong hộp cũng phải có người quản giữ"), ch04:145 ("Mảnh Thiên Khuyết giữ nguyên trong hộp") và ch04:163 tả mảnh vẫn ở trong hộp (ch04:163 là lời kể: "mảnh Thiên Khuyết vẫn ở nguyên trong hộp phía Đại Nghị Sảnh"); ch05:153, ch06:9 và ch06:77 lại tả hộp trống, mảnh chưa tìm thấy | 4–6 |
| tắt `ab-tat-2` (9 chương) | **Cửa**: cửa Đại Nghị Sảnh mở ở ch03:109–113 ("Hai cánh cửa tách ra", "Sau lưng, cửa Đại Nghị Sảnh còn mở") và ch04:5 ("Cánh cửa Đại Nghị Sảnh mở ra… Người trong sảnh lần lượt theo ra"), rồi ch05:69 ("những người đang mắc kẹt trong đại sảnh"), ch06:27 ("Chúng ta đang bị nhốt trong này"), ch06:95, ch07:57, ch08:131, ch09:129, ch10:21 vẫn khoá, cùng cánh cửa | 5–10 |
| tắt `ab-tat-2` | **Nơi chốn / ai biết gì**: ch04:91–105 đã tìm thấy Thiệu Kiếm Hoài còn sống trong Hành Lang Phong Luân cạnh Ấn Lệnh, ông nói rõ vì sao giấu. Từ ch05 truyện quay về như chưa có chuyện đó: tên Thiệu không xuất hiện lần nào ở ch05–ch10, và ch10:51 cả nhóm lại "kiểm tra đoạn lối dẫn về Hành Lang Phong Luân" như đi lần đầu | 5–10 |
| bật `ab-bat` (10 chương) | Không thấy lỗi rõ ràng. **Một chỗ mơ hồ, không tính**: cửa Đại Nghị Sảnh mở ở ch03:129 và "vẫn mở" ở ch04:99, nhưng ch08:149 tả "cánh cửa đá vẫn khoá chặt ở cuối sảnh". Có thể là một cửa đài khác (ch09:21 "Cửa đài hiện ra ở cuối lối đi"), nhưng văn gọi cả hai bằng "cánh cửa đá", người đọc dễ lẫn | — |

Đếm: tắt `ab-tat` 1 lỗi (7 chương), tắt `ab-tat-2` 2 lỗi (9 chương), bật `ab-bat` 0 lỗi rõ, 1 chỗ mơ hồ (10 chương).

## 2. Lặp nhịp (đếm từ đầu, giữa, cuối chương, và cụm lặp)
- **`ab-tat-2`**: ch06–ch10 (5 chương liền) cùng một nhịp "mọi người đứng quanh biên bản, chưa ai được chạm cơ chế cửa, chưa ai thử mở"; cuối chương nào cũng tả cửa đá khoá. Lời thú nhận của Bạch Kinh Luân (bí mật lộ đúng khoảng) được diễn lại ở ch07, ch08 (ba chỗ) và ch09 (năm chỗ, mở bằng đúng câu của lựa chọn).
- **`ab-bat`**: truyện đi tiếp: ch03 mở cửa sảnh, ch04 lần dấu, ch06 tìm thấy ấn lệnh và mảnh giấy, ch07 Thiệu Kiếm Hoài xuất hiện, ch09 thử cửa đài, ch10 cửa đài mở. Lặp ở ch08–ch10: cùng điều khoản ("Không phe nào được tự giữ thần khí. Cũng không ai được dùng Ấn Lệnh Thiên Luật để khóa người trong đài") đọc lại ở ch08:47 và :85, ch09:85, ch10:11 và :95 (ba chương); lời thú nhận ở ch07 và ch08 (hai chương).
- **`ab-tat`** (7 chương): lời thú nhận chỉ ở ch07; không đủ dài để đếm lặp.
- Nhịp lặp qua hai chương trở lên: `ab-tat-2` 5 chương, `ab-bat` 3 chương.

## 3. Token vào thêm (cùng một thế giới, chương 2 trở đi, từ `calls.jsonl`)
| | dàn ý (token/lời gọi) | viết (token/lời gọi) |
|---|---|---|
| tắt `ab-tat` | 5158 (13 lời gọi) | 6286 (14) |
| tắt `ab-tat-2` | 5034 (19) | 6399 (23) |
| bật `ab-bat` | 5786 (19) | 6897 (20) |
- Bật thêm khoảng **630–750 token** cho mỗi lời gọi dàn ý (+12–15%) và **500–610** cho mỗi lời gọi viết (+8–10%). Khớp với ước tính ở `ky-ao-vua-quotes-1` (780 token). Hai nhánh tắt khác nhau 120 token ở mỗi vai, nên nhiễu nhỏ hơn mức tăng.
- Chi phí cả lần chạy: bật 0,0846 USD, tắt 0,0912 USD (chạm trần, nhiều lần viết lại hơn) và 0,0595 USD (7 chương). Phần thêm do đoạn khoảng 0,003 USD, thấp hơn nhiễu giữa các lần chạy.
- Phụ: viết lại tắt `ab-tat` 2, `ab-tat-2` 7, bật `ab-bat` 2. Từ `truth_dump.json` (`plan_progress`): cả ba lần chạy lộ hai bí mật đúng khoảng (chương 4 và 7). Mạch `tim_nguoi_giu_an` (hạn 2–6) gỡ ở ch04 (`ab-tat`, `ab-tat-2`) và ở **ch07, trễ một chương** (`ab-bat`: Thiệu Kiếm Hoài chỉ xuất hiện ở ch07); mạch `loi_khai_cua_min_vi` (hạn 5–12) ghi gỡ ở **ch01, sớm** trong `ab-tat-2`. Chưa đọc đối chiếu nghĩa các mạch này với văn.

## 4. Đoạn nào được chọn (nhánh bật, `truth_dump.json` → `quotes`, 38 lần lấy)
- Id đoạn khớp 100% với chữ dựng lại từ `chapters/` (0 id lệch), nên nhật ký đáng tin.
- **Chương liền trước chiếm phần lớn**: ch02 15/15 đoạn từ ch01, ch04 11/12 từ ch03, ch06 9/11 từ ch05, ch08 9/12 từ ch07; riêng ch09 **0/12** từ ch08 (lấy ch02, ch05, ch06). Kho lấy gần như đúng chương mới nhất vì tên các nhân vật xuất hiện ở mọi đoạn và chương mới nhất vừa nhắc lại chuyện đang diễn ra.
- Đoạn từ ch02 được lấy lại ở ch04–ch10 (ch04 1, ch05 2, ch06 2, ch07 2, ch08 2, ch09 3, ch10 1).
- Đoạn ghi cảnh cửa mở (ch03, đoạn 10) có vào đề ở ch04 (1 lần) và ch05 (2 lần); ở ch06–ch10 không có đoạn nào nhắc cửa mở. Nên "đoạn đúng được chọn" đúng ở hai chương liền sau, không ở các chương sau.

## Kết luận
- **Chiều hướng nghiêng về có lợi, chưa đủ để kết luận.**
  - Theo quy ước khai trước ("có lợi" nếu lần bật ít lỗi liền mạch hơn từ hai lỗi trở lên mà lặp nhịp không tăng): so với `ab-tat-2` (2 lỗi, lặp nhịp 5 chương) nhánh bật đạt (0 lỗi rõ, lặp nhịp 3 chương). So với `ab-tat` (1 lỗi, 7 chương) thì không đạt (chênh 1 lỗi).
  - Hai lần chạy tắt khác nhau gần bằng khoảng cách giữa tắt và bật: `ab-tat` mở cửa ở chương 5 và không lỗi cửa, `ab-tat-2` mở ở chương 3 rồi quên. Với một lần chạy mỗi cấu hình, nhiễu của model lớn hơn hiệu ứng có thể đo.
  - Cái hỏng ở `ab-tat-2` (truyện quên chuyện đã xảy ra ở ch03–04 và giậm chân năm chương) đúng là loại lỗi đoạn trên trang nhắm tới, và ở nhánh bật không xảy ra. Nhưng đoạn không chứa chi tiết cửa mở từ ch06 trở đi, nên không có bằng chứng rằng chính đoạn ấy ngăn lỗi; có thể chỉ do ngẫu nhiên.
  - Giá: khoảng 500–750 token vào mỗi lời gọi dàn ý và viết, chi phí thêm không đáng kể (~0,003 USD cho 10 chương).
- **Khuyến nghị: giữ mặc định tắt**, như D-85 đã ghi, và nếu muốn quyết thì đo thêm: ít nhất 3 lần chạy mỗi nhánh trên cùng khởi tạo (khoảng 0,09 USD mỗi lần, 0,5 USD cả bộ).
- Đáng sửa nếu bật: kho đoạn thiên về chương liền trước (đã nằm trong tóm tắt chương và cảnh trước). Có thể loại đoạn của chương N-1 khỏi kết quả để nhường chỗ cho đoạn xa hơn, hoặc trừ tên nhân vật có mặt ra khỏi câu hỏi (chúng xuất hiện ở mọi đoạn). Chưa thử.
- **Chưa kiểm:** đọc từng dòng (xem giới hạn ở trên); mạch gỡ đúng khoảng của ba nhánh; liệu model viết có dùng các đoạn trong đề (chỉ biết đề có chúng); nguyên nhân HTTP 409 của `ab-tat` (lỗi từ phía nhà cung cấp, không thử lại vì mã không nằm trong `RETRYABLE`); nguyên nhân lần chạy `ky-ao-vua-quotes-1` đầu chết giữa chương 3 (mã thoát 1, không traceback; phiên điều phối báo ba process Python khác cũng chết cùng lúc, nên có thể bị kết thúc từ bên ngoài, nhưng chưa kiểm).
