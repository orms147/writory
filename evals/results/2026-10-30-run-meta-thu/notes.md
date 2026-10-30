# Lượt thử đường đi Meta (D-140): `bench_run --setup-only` bằng Muse Wonder

Người đọc: Claude, 30/10/2026. Lượt chạy thật ĐẦU TIÊN qua `MetaClient`; dừng giữa chừng vì trần chi phí của config, không phải lỗi của client.

- **Lệnh** (trong `backend/`, `PYTHONIOENCODING=utf-8`): `uv run python -m writory.pipeline.bench_run --label meta-thu --setup-only --config-dir ../evals/config/meta --env-file <.env của chủ dự án> --budget 0.80`
- **Mã:** commit `65384bed2836308c2b4095a84db4025be31a2091` (nhánh `feature/meta-bench-provider`, cây sạch). **Hash config** (có hiệu lực): `config.sha256.combined` trong `meta.json` (`models.yaml` là của `evals/config/meta`, các file còn lại của `config/`).
- **Model:** `meta/muse-wonder-1.0` cho mọi vai, suy luận `low` (`meta.json`: `provider: meta`); phản hồi báo `served_model: muse-wonder-1.0`. Đề `evals/scenarios/story_run/tu-tien-ngan.yaml`, `max_tokens_per_call` 16000. Truyện `run-20261030-meta-thu-4544fdb4` nằm trong Neo4j + Postgres dev (dừng ở khởi tạo, chưa có chương 0).

## Kết quả
- **Ba trong bốn bước khởi tạo chạy đúng**: `settings`, `plots`, `characters` đều `status: ok`, `finish_reason: stop` (không bị cắt vì `max_tokens`), JSON qua schema `strict` của `strict_schema` và qua kiểm pydantic. Mỗi lời gọi ~21 đến 25 giây.
- **Bước thứ tư `build` KHÔNG được gọi trong lượt này (đã chạy lại ở `2026-10-30-run-meta-thu-2`)**: `COST_LIMIT_CHAPTER`. Ba bước đã tiêu 0,0818 USD, chạm `limits.cost_usd.per_chapter` (0,08), mà trần này (và `per_scene` 0,02) đặt theo giá Luna (D-47, D-131). Giá Meta cao hơn Luna khoảng 40 lần, nên ba bước đầu đã đủ chạm trần chương 0. Schema `strict` của `BuildOutput` (lớn nhất, có `$defs` lồng nhau) vì vậy **chưa kiểm**.
- **Chi phí thật 0,0818 USD** (tính từ token x giá trong config, cả ba lời gọi `cost_usd` có giá trị; không có chi phí ước tính): 0,0328 + 0,0265 + 0,0225.
- **Token** (`prompt` / `completion`, `cached` luôn 0): 768 / 1486, 943 / 1136, 1151 / 896; tổng 2862 vào, 3518 ra. `completion_tokens` của Meta gồm cả token suy luận; **token suy luận không được tách riêng** vì `MetaClient` chưa chuyển `completion_tokens_details.reasoning_tokens` vào `usage` (chưa kiểm xem Meta có báo trường này).
- **Giữ chỗ trần:** mỗi lời gọi giữ ~0,33 USD (16000 x giá ra), nên `--budget 0.80` đủ cho hai lời gọi liền mà không chạm trần tổng; trần `--budget` không phải thứ dừng lượt này.

## Chưa kiểm
- Schema `strict` cho `BuildOutput`, và các vai khác (outline, extract, choices, summary, moderate, overreach).
- Token suy luận của Muse; chất lượng và độ ổn định văn so với Luna (chưa viết chương nào).
- `max_tokens` bị cắt ở các bước lớn (outline, viết, extract).
