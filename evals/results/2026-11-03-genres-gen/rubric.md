# Thang chấm danh mục thể loại (D-161)

Khai TRƯỚC lời gọi model đầu tiên của lượt này. Model soạn: Meta Muse Wonder (`muse-wonder-1.0`). Giám khảo: Claude Sonnet 5.5
(`claude-sonnet-5-5`, Anthropic API). Chủ dự án chọn hai model và quyết lượt này không đặt trần chi phí (3/11/2026).

## Đầu vào của model soạn
- Chú thích yêu cầu ở đầu `config/genres.yaml` (bản ở commit của lượt chạy), nguyên văn.
- Thể loại `sang_van` làm mẫu định dạng (không soạn lại nó).
- Việc 1: soạn lại đề cho 7 thể loại đang có (giữ `key`, `label`, `naming`; viết mới `hint`, `setup_brief`, `outline_brief`, `voice_brief`, `styles`).
- Việc 2: soạn 16 thể loại mới, khác nhau rõ và khác 8 thể loại đang có, hợp người đọc truyện mạng tiếng Việt.

## Giám khảo chấm từng thể loại
Ra đúng một nhãn:
- `pass`: dùng được ngay.
- `fix`: có lỗi sửa được; kèm lý do và việc phải sửa.
- `reject`: hỏng từ gốc (trùng thể loại khác, không chơi được, vi phạm luật an toàn mà sửa không hết).

Tiêu chí (một tiêu chí hỏng là ít nhất `fix`):
1. **Tuân yêu cầu đầu file:** không nói định dạng, JSON, số chương, độ dài, ngôi kể, quy ước tên, mức u tối; không tên riêng cố định cho nhân vật hay nơi chốn; không chép tác phẩm, nhân vật, thương hiệu hay người có thật.
2. **An toàn:** không đòi nội dung tình dục; không đòi u tối hơn mức người chơi chọn; không có gì vượt luật hệ thống.
3. **Dùng được:** `setup_brief` có kho cụ thể (vài kiểu xung đột, vài kiểu cú lật hay bí mật, kiểu kết) chứ không chung chung.
4. **Đẩy truyện khác nhau:** là khuynh hướng và kho lựa chọn, không phải một cốt cố định.
5. **Hợp lối chơi:** một góc nhìn nhân vật chính, có lựa chọn mỗi chương, bí mật lộ dần, kết gỡ hết mạch.
6. **Khác các thể loại khác** trong danh mục (giám khảo thấy nhãn và gợi ý của mọi thể loại).
7. **Tiếng Việt tự nhiên**, có dấu, không văn dịch.
8. **`styles` hợp lý:** có `audio` chỉ khi thể loại hay khi nghe.

## Quy trình
- Vòng 1: Wonder soạn, code kiểm schema và trần ký tự (`GenresConfig`), Sonnet chấm. Thể loại vượt trần ký tự tự thành `fix` kèm lý do của code.
- Vòng 2: Wonder sửa một lượt mỗi mục `fix` theo lý do; Sonnet chấm lại. Sau vòng 2, mục còn `fix` hay `reject` bị bỏ.
- Thể loại đang có mà bản soạn lại bị bỏ thì giữ bản cũ.
- Danh mục cuối phải qua bộ kiểm của app (`load_config`). Chủ dự án đọc danh sách cuối và xoá được bất kỳ mục nào.

## Ghi lại
`candidates_round1.yaml`, `verdicts_round1.jsonl`, `candidates_round2.yaml`, `verdicts_round2.jsonl`, `cost.json`, `notes.md`
(commit SHA, hash `genres.yaml` trước và sau, id model, mức suy luận, tổng chi phí từng bên). Script: `tools/gen_genres.py`.
