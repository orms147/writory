# Lượt thử đường đi Meta, lần hai (D-140): `bench_run --setup-only` bằng Muse Wonder

Người đọc: Claude, 30/10/2026. Chạy lại lượt `evals/results/2026-10-30-run-meta-thu/` (dừng ở bước 4 vì trần chi phí theo giá Luna) sau khi thư mục config bộ đo gộp từng khoá và có trần chi phí riêng.

- **Lệnh** (trong `backend/`, `PYTHONIOENCODING=utf-8`): `uv run python -m writory.pipeline.bench_run --label meta-thu-2 --setup-only --config-dir ../evals/config/meta --env-file <.env của chủ dự án> --budget 0.80`
- **Mã:** commit `3fbc4d7f006795c9a87792a04ed81632c2d67f00` (nhánh `feature/meta-bench-provider`, cây sạch). **Hash config đã gộp:** `config.sha256.combined` trong `meta.json` (`e09444a2…`); `models.yaml` và `limits.yaml` là nền `config/` cộng phần đè của `evals/config/meta` (`cost_usd` nhân 40).
- **Model:** `meta/muse-wonder-1.0` mọi vai, suy luận `low`; `meta.json`: `provider: meta`, `status: done`. Đề `evals/scenarios/story_run/tu-tien-ngan.yaml`, `max_tokens_per_call` 16000.
- **Truyện:** `run-20261030-meta-thu-2-9dd36479` (kế hoạch 6 chương, có chương 0) trong Neo4j + Postgres dev. Truyện của lượt trước `run-20261030-meta-thu-4544fdb4` còn nằm ở DB dev, dừng ở khởi tạo, chưa xoá.

## Kết quả
- **Cả bốn bước khởi tạo qua**, `status: ok`, `finish_reason: stop` (không bị cắt vì `max_tokens`), không lượt sửa nào (`setup_repairs`: 0). Bước `build` (BuildOutput, schema lớn nhất, có `$defs` lồng) qua schema strict và qua kiểm pydantic và kiểm quy tắc khởi tạo ngay lần đầu.
- **Chi phí thật 0,2351 USD** (token x giá, không có chi phí ước tính): 0,0329 + 0,0266 + 0,0247 + 0,1509. Trần `--budget` 0,80 không chạm.
- **Token** (vào / ra / trong đó suy luận; cached luôn 0): `settings` 768 / 1489 / 1016, `plots` 928 / 1146 / 647, `characters` 1118 / 1013 / 447, `build` 3188 / 6905 / 1881. Tổng 6002 vào, 10553 ra, trong đó 3991 token suy luận (khoảng 38% token ra). **Meta báo `reasoning_tokens`** (`completion_tokens_details.reasoning_tokens`); `calls.jsonl` ghi từ nay.
- **Thời gian:** 20 đến 27 giây cho ba bước đầu, 75 giây cho `build`.
- **`meta.json`:** `provider: meta`, model từng vai `meta/muse-wonder-1.0`, `cost_limits` là trần đã gộp (0,8 / 3,2 / 40).

## Chưa kiểm
- Các vai khác ngoài khởi tạo: outline, viết, extract, choices, summary, moderate, overreach (schema strict và `max_tokens` của chúng); chưa viết chương nào, nên chất lượng và độ ổn định văn so với Luna chưa biết.
- Chi phí cả một truyện: mới có khởi tạo (0,24 USD với Muse; cùng bước với Luna khoảng 0,007 USD ở các lần đo gần đây).
- Một lần chạy, một đề: không nói được độ ổn định của schema strict qua nhiều lần.
