# Đo lại khởi tạo `setup-9` (D-118, D-120)

Người đọc: Claude và chủ dự án, 29/10/2026. Commit `9a26d59` (sạch), model `openai/gpt-6-luna` (`reasoning: low`) cho vai `setup`, hash config trong `meta.json` của từng lượt. Lệnh mỗi lượt: `bench_run --scenario <đề> --setup-only --budget 0.05 --seed <seed> --env-file <.env>`, năm đề (ab-tu-tien, ab-ky-ao, ab-trinh-tham, long-tu-tien, long-ky-ao-hanh-trinh), mỗi đề hai seed (seed của đề và seed+1), một chuỗi nối tiếp. Mười thư mục `../2026-10-29-run-setup9-*`; số liệu gộp ở `compare.json`.

So với năm lượt `setup-8` cùng đề, seed của đề: `2026-10-28-run-ab-{tu-tien,ky-ao,trinh-tham}-setup`, `2026-10-29-run-long-tu-tien-3`, `2026-10-29-run-long-ky-ao-hanh-trinh-1` (lượt `-2` dùng lại khởi tạo của `-1` nên bỏ).

## Số đo
| | setup-8 (5 lượt) | setup-9 (10 lượt) |
|---|---|---|
| Lượt cần sửa D-54 | 1/5 (`pacing`) | 3/10 (`package` 1, `plan` 1, `id` 1 + `package` 7) |
| Lượt khởi tạo hỏng (`SetupInvalidError`) | 0 | 0 |
| Chi phí khởi tạo trung bình mỗi lượt (USD) | 0.00403 | 0.00473 |
| Token ra của lời gọi `build` đầu, trung bình | 3936 | 4568 |
| Nhân vật có `appearance` (gồm nhân vật chính) | — | 54/54 (nhân vật chính 10/10) |
| Nơi chốn có `visual` | — | 48/48 |
| Độ dài `appearance` (ký tự) | — | 119–254, trung bình 171.5 |
| Độ dài `visual` (ký tự) | — | 104–191, trung bình 141.1 |
| Văn bản dài hơn 3 câu | — | 0/102 |

Tổng chi của mười lượt: 0.0473 USD (chỉ vai `setup`). Ở lượt ab-tu-tien seed của đề, đề `build` dài thêm 299 token (3831 → 4130, +7.8%).

## Đọc được
- Cả ba lượt sửa của `setup-9` là lỗi cũ về id và kế hoạch (id nút trùng, hồi không có mốc, id có dấu trùng sau khi chuẩn hoá), không lượt nào do `appearance`/`visual` (bộ kiểm chưa có luật cho hai trường này, D-120). Mỗi lượt sửa một lần là xong.
- Không thiếu trường nào: model luôn điền cả `appearance` lẫn `visual`, kể cả `protagonist_appearance`.
- Độ dài nằm trong 1–3 câu như đề dặn. Chi phí tăng khoảng 17%, token ra của `build` tăng khoảng 16%, cùng cỡ với phần văn thêm vào (khoảng 170 ký tự mỗi nhân vật, 140 mỗi nơi).
- Đọc tay mười lăm ngoại hình (ba nhân vật mỗi đề của năm lượt seed+0 hoặc seed+1) và năm cảnh sắc, đối chiếu với bí mật và tính cách trong `truth_dump.json`: không ngoại hình nào nói ra bí mật hay quan hệ ẩn; bộ cụm `leak_terms` của kế hoạch không khớp văn bản nào trong 102 văn bản (kiểm bằng code). Tả ngoại hình đúng kiểu nhìn thấy được (tuổi trông, vóc dáng, mặt, tóc, trang phục, một dấu hiệu).
- Lệch nhẹ khỏi đề: vài chi tiết là thói quen chứ không phải hình dáng (`áo dài xanh sẫm luôn phẳng phiu`, `cổ áo luôn cài lệch một khuy`, `đi hơi khập khiễng`); ngoại hình nhân vật chính của ab-ky-ao seed+1 chép lại nghề trong quá khứ (`quen cúi sửa mái chèo`), tức lấy từ chữ người chơi. Không phải bí mật, nhưng cho thấy `protagonist_appearance` bám vào quá khứ do người chơi viết.
- Độ đa dạng thấp: 54/102 văn bản mở bằng `Trông…`, 43/102 nhắc `tóc đen`. Cho video, nhiều nhân vật sẽ giống nhau ở tóc và cách mở câu; chưa phải lỗi, nhưng là chỗ nên sửa đề nếu bộ xuất cần phân biệt mặt nhân vật.

## Chưa kiểm
- Hai thế giới cùng seed không giống nhau: model không tất định, nên 3 lượt ab của `setup-8` không đối chiếu từng nhân vật được với lượt `setup-9` cùng seed. So sánh chỉ ở mức tỉ lệ.
- Mẫu nhỏ: 3/10 và 1/5 không phân biệt được. Muốn biết `setup-9` có làm tăng tỉ lệ sửa thật thì cần nhiều lượt hơn.
- Chưa đo ảnh hưởng lên văn khi bật `limits.context.character_appearance_max_chars`, và chưa đo ngoại hình có khớp giữa các cảnh không. Cờ vẫn tắt mặc định.
- Chưa kiểm khi dùng model khác cho vai `setup`.
