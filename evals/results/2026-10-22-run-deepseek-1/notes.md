# Nhận xét đọc tay: run-deepseek-1 (DeepSeek V4 Flash, truyện ngắn tu tiên)

Người đọc: Claude (nhánh feature/model-deepseek), 22/10/2026. Nguồn: `calls.jsonl`, `events.jsonl`, `chapters/`, `meta.json`. D-100.

Lệnh: `uv run python -m writory.pipeline.bench_run --scenario ../evals/scenarios/story_run/tu-tien-ngan.yaml --label deepseek-1 --budget 0.08 --env-file C:/Work/AI/WriTory/.env`. Cùng đề, cùng seed 20261020 với `2026-10-21-run-tu-tien-4` (Luna). Mọi vai và model viết là `deepseek/deepseek-v4-flash` (viết: reasoning none; các vai khác: low, như config cũ).

## Lượt chạy KHÔNG hoàn tất
- Tiến trình `bench_run` biến mất giữa chừng, không traceback trong log: `meta.json` còn `status: running`, không có `report.json` hay `summary.md`. Nguyên nhân chưa rõ (không phải trần: đã tiêu 0,0621 USD trên trần 0,08). Còn lại ngân sách tổng không đủ chạy lại cả truyện (xem D-100), nên số dưới đây là của **3 chương đã ghi và chương 4 dở** (dàn ý và bản viết đầu), không phải kết truyện.
- Nên không có số: kết truyện, quality chữ khác hệ, cảnh bị chặn, `leak:name` (đó là các số của `report.json`). Đọc được từ `events.jsonl`/`calls.jsonl`: bên dưới.

## Đọc được
- **Lỗi schema / thử lại:** trong 4 lượt viết chương, 2 lượt người chơi phải bấm thử lại:
  - chương 2 lượt 1: `RETRY_LIMIT_REACHED`, lỗi cuối `ModerationOutput: json_invalid` (kiểm duyệt cảnh trả JSON hỏng cả hai lần thử);
  - chương 3: chương đã ghi, nhưng bước tạo lựa chọn lỗi `ChoicesOutput: choices.1: value_error` rồi tạo lại.
  Một lời gọi dàn ý ở chương 3 trả `LLM_UNAVAILABLE` (thử lại được). Lần chạy Luna `tu-tien-4`: chương tự thử lại 0, lựa chọn 0.
- **Nguyên nhân JSON hỏng (thăm dò sau đó, `D-100`):** nhà cung cấp DigitalOcean trả `{"{ "answer": ...}` dù niêm yết `structured_outputs` và dù đã đòi `require_parameters`; bỏ nó thì 8/8 hợp lệ. `calls.jsonl` không ghi nhà cung cấp nên không chứng minh được lượt kiểm duyệt hỏng ở đây cũng do DigitalOcean; `ChoicesOutput value_error` là lỗi nội dung (không phải cú pháp), không giải thích được bằng nhà cung cấp.
- **Chi phí mỗi chương (USD, mọi lời gọi gắn chương, gồm lượt thử lại):** chương 1: 0,0115; chương 2: 0,0258 (có lượt hỏng); chương 3: 0,0151; setup (chương 0): 0,0038. So với Luna `tu-tien-4`: chương 1: 0,0073; 2: 0,0074; 3: 0,0096; setup 0,0093. DeepSeek đắt hơn khoảng 1,5 đến 3,5 lần mỗi chương dù giá niêm yết rẻ hơn, vì token ra: vai trích tốn khoảng 52 nghìn token ra cho 3 chương rưỡi (phần lớn là token suy luận: 1.400 đến 2.300 token suy luận cho một đoạn trích 800 token vào ở thăm dò), dàn ý khoảng 33 nghìn, kiểm duyệt khoảng 7 nghìn.
- **Chữ Hán:** không có trong ba chương (kiểm bằng khoảng mã Hán, Nhật, Hàn trong `chapters/ch01..03.md`).

## Đọc tay văn (ngôi kể, tiếng Việt)
- Ngôi thứ nhất ("tôi") xuyên suốt ba chương, nhất quán. Chương 1 mạch lạc, câu tự nhiên, nhịp tốt.
- Chương 3 có câu vô nghĩa hoặc vụn nghĩa lẫn trong văn trôi chảy: "đánh đổ một ít nước muối trên bậc đá đầu người độ ca", "đàn linh sơn của các ngươi một phần ứng cấp thế nào?", "Tuyết Phong Môn chạy thoát á?". Chất lượng không đều giữa các chương; mẫu nhỏ (3 chương), chưa có điểm bài D cho model này.

## Chưa kiểm
- Một lần chạy dở, một truyện, một seed; model có nhiễu. Chưa biết số lỗi và cảnh bị chặn của cả truyện. Chưa có `quality` chữ khác hệ ở mức báo cáo.
- Chưa so văn với Luna bằng bài D.
