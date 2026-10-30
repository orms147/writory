# Lượt thử đường đi Anthropic API, lần một (D-145): `bench_run --setup-only` bằng Claude Haiku 5.5

Người đọc: Claude, 30/10/2026. Lượt thật ĐẦU TIÊN qua `AnthropicClient`; dừng ở bước thứ tư. Lỗi là của client (chưa có đường lùi cho schema lớn), đã sửa; chạy lại ở `evals/results/2026-10-30-run-anthropic-thu-2/`.

- **Lệnh** (trong `backend/`, `PYTHONIOENCODING=utf-8`): `uv run python -m writory.pipeline.bench_run --label anthropic-thu --setup-only --config-dir ../evals/config/anthropic --env-file <.env của chủ dự án> --budget 0.50`
- **Mã:** commit `20a3b61ee2c85d9eeeb4e85bc6b9a0b2fc1e4b76` (nhánh `feature/anthropic-bench-provider`, cây sạch). Hash config đã gộp: `config.sha256.combined` trong `meta.json`.
- **Model:** `anthropic-api/claude-haiku-5-5` mọi vai, suy luận `low` (effort `low`).
- **Kết quả:** `settings`, `plots`, `characters` qua (`status: ok`, `finish_reason: stop`; 0,0009 + 0,0006 + 0,0009 USD). Bước `build` bị HTTP 400 `invalid_request_error`: "The compiled grammar is too large, which would cause performance issues". Structured output (`output_config.format`) của Anthropic biên dịch schema thành ngữ pháp và có giới hạn kích thước; `BuildOutput` vượt. Lời gọi 400 không tạo ra gì, không bị tính tiền. Tổng đã tiêu 0,0025 USD.
- **Cách sửa:** client lùi về schema trong `system`, bỏ `output_config.format`, và nhớ tên schema đó; pydantic vẫn kiểm câu trả lời (xem lần hai).
