# Lượt thử đường đi Anthropic API, lần hai (D-145): `bench_run --setup-only` bằng Claude Haiku 5.5

Người đọc: Claude, 30/10/2026. Chạy lại `evals/results/2026-10-30-run-anthropic-thu/` sau khi `AnthropicClient` có đường lùi cho schema quá lớn.

- **Lệnh** (trong `backend/`, `PYTHONIOENCODING=utf-8`): `uv run python -m writory.pipeline.bench_run --label anthropic-thu-2 --setup-only --config-dir ../evals/config/anthropic --env-file <.env của chủ dự án> --budget 0.50`
- **Mã:** commit `659cdef9cbf59e3b40d19a8139035ac14c0c5a3c` (nhánh `feature/anthropic-bench-provider`, cây sạch). **Hash config đã gộp:** `config.sha256.combined` trong `meta.json` (`models.yaml` là nền `config/` cộng `evals/config/anthropic/models.yaml`; trần `cost_usd` của `config/`, vì giá bằng Luna).
- **Model:** `anthropic-api/claude-haiku-5-5` mọi vai, effort `low`; `meta.json`: `provider: anthropic`, `status: done`. Đề `evals/scenarios/story_run/tu-tien-ngan.yaml`, `max_tokens_per_call` 16000.
- **Truyện:** `run-20261030-anthropic-thu-2-42ec2b41` (kế hoạch 6 chương, có chương 0) trong Neo4j + Postgres dev. Truyện lượt một dừng ở khởi tạo, chưa xoá.

## Kết quả
- **Cả bốn bước khởi tạo qua**, `status: ok`, `finish_reason: stop` (không bị cắt vì `max_tokens`), không lượt sửa (`setup_repairs`: 0).
- **`build` qua đường lùi**: schema của `BuildOutput` đi trong `system`, không qua structured output; pydantic và quy tắc khởi tạo vẫn kiểm và chấp nhận ngay lần đầu. Ba bước đầu vẫn dùng structured output (`output_config.format`) và qua. Lời gọi 400 của lượt một không được lặp lại: client chỉ đi đường lùi sau khi gặp lỗi đúng chữ "grammar is too large".
- **Chi phí thật 0,0093 USD** (token x giá; không có chi phí ước tính): 0,0008 + 0,0007 + 0,0010 + 0,0068. Cộng cả lượt một: 0,0118 USD. Trần `--budget` 0,50 không chạm.
- **Token** (vào / ra; cached luôn 0): `settings` 1855 / 1200, `plots` 2180 / 892, `characters` 2719 / 1470, `build` 8243 / 11950. Tổng 14997 vào, 15512 ra. Token suy luận nằm trong token ra, không tách riêng (Anthropic không báo). Token vào nhiều hơn lượt Meta cho cùng bước (1855 so với 768 ở `settings`): tokenizer khác và/hoặc schema của structured output được cộng vào prompt, chưa phân biệt.
- **Thời gian:** 6 đến 12 giây cho ba bước đầu, 54 giây cho `build`.
- **So với Luna (số tham khảo, không so thẳng):** chi phí khởi tạo cùng cỡ các lần đo Luna (khoảng 0,007 USD).

## Chưa kiểm
- Các vai ngoài khởi tạo (outline, viết, extract, choices, summary, moderate, overreach): schema của chúng có qua structured output không, hay phải đi đường lùi (chưa biết cái nào vượt giới hạn ngữ pháp).
- Độ ổn định của đường lùi: với schema lớn, model có luôn trả JSON đúng schema không (mới một lần, một đề); câu trả lời sai đã có `RETRY_SCHEMA` của nơi gọi.
- Chất lượng văn so với Luna và Muse (chưa viết chương nào); prompt dài trên 100 nghìn token (bảng giá dài) và cache (không dùng `cache_control`).
