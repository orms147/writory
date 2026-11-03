# Danh mục thể loại: Muse Wonder soạn, Sonnet 5.5 chấm (D-161)

Người chạy: Claude (nhánh feature/genres-idea), 3/11/2026. Thang chấm khai trước: `rubric.md` (commit fd5397c). Script:
`tools/gen_genres.py`, chạy ở fd5397c (script commit cùng kết quả này).

- Model soạn: Meta `muse-wonder-1.0` (Meta API), `reasoning_effort` xhigh. Danh sách model của Meta API (`GET /v1/models`,
  3/11/2026): `muse-wonder-1.0`, `muse-spark-1.1/1.2/1.3` (bỏ bản `-contributor`); Wonder là bản cao cấp, Wonder Full chỉ có
  trong Muse Code.
- Giám khảo: Anthropic `claude-sonnet-5-5`, effort high, JSON theo schema (`output_config.format`).
- Không trần chi phí: chủ dự án quyết, chỉ lượt này. Số lời gọi cố định: 3 lời gọi soạn, 23 lời gọi chấm vòng 1, 3 lời gọi sửa,
  3 lời gọi chấm vòng 2 (32 lời gọi, 0 lỗi, 0 lần thử lại; `calls.jsonl`).
- `config/genres.yaml`: sha256 (16 ký tự đầu) `595e9f170416a8dc` trước (bản 8 thể loại, commit 67cdf02), `63705683149efc87`
  sau (bằng `final_genres.yaml`).

## Kết quả
- Ứng viên: 7 thể loại đang có soạn lại (giữ khoá, nhãn, quy ước tên) và 16 thể loại mới (`candidates_round1.yaml`).
- Vòng 1 (`verdicts_round1.jsonl`): 20 `pass`, 3 `fix`, 0 `reject`. Ba mục `fix`:
  - `do_thi`: dàn ý ép một đường cong cố định cho mọi truyện;
  - `linh_di_dan_gian`: dàn ý ép mọi cao trào thành một nghi thức trước đám đông;
  - `tam_ly_toi_pham`: giọng văn tự dặn về an toàn và mức u tối, việc hệ thống giữ.
- Vòng 2 (`verdicts_round2.jsonl`): cả 3 mục sửa được `pass`.
- Danh mục cuối 24 thể loại, qua bộ kiểm của app (`load_config`):
  - 7 thể loại soạn lại;
  - `sang_van` giữ nguyên;
  - 16 thể loại mới: mạt thế, võ hiệp, ngôn tình hiện đại, trọng sinh, hệ thống, học đường, điền văn, xuyên không, cung đấu,
    hài đời thường, thể thao, ẩm thực, phiêu lưu, quân sự hư cấu, kinh dị dân gian, tâm lý tội phạm.
- Bốn thể loại chỉ mở cho truyện chữ, theo đánh giá của model soạn: hệ thống, ẩm thực, quân sự, tâm lý tội phạm.
- Chi phí (`cost.json`): Meta 1,0338 USD, Anthropic 0,7139 USD.

## Đọc kết quả
- Claude đọc và kiểm bằng script trên mọi mục: không có tên riêng cố định, không nói số chương, định dạng hay ngôi kể, không
  có chữ tiếng Anh lọt vào gợi ý.
- Claude đọc đủ hai mục (kinh dị dân gian, hài đời thường): có kho xung đột và cú lật cụ thể, giọng rõ.
- Một giám khảo, một lượt, nên độ nghiêm của nó chưa đo. 20/23 mục qua ngay vòng 1 là con số cần đọc cùng điều đó.
- Chưa kiểm: truyện viết thật bằng thể loại mới (chưa chạy app trả phí). Chủ dự án đọc danh sách và xoá được bất kỳ mục nào
  (docs/runbook.md, mục "Thêm hay sửa thể loại").
