# Runbook

## Yêu cầu
- Docker (có Compose)
- Python ≥ 3.12 và [uv](https://docs.astral.sh/uv/)
- Node 20+ (từ tuần 4, cho frontend)

## Chạy máy local
```bash
cp .env.example .env          # điền mật khẩu local và key OpenRouter của bạn
docker compose up -d          # Neo4j (http://localhost:7474) + Postgres
cd backend
uv sync
uv run pytest -m "not graph"  # test nhanh: không mạng, không gọi model thật
uv run pytest -m graph        # test cần Neo4j + Postgres ở trên; mỗi test dùng story_id riêng và chỉ dọn story_id đó
```

Chạy cả một truyện từ dòng lệnh (`writory.pipeline.bench_run`; lệnh, đề và kết quả: `docs/eval.md`, mục "Chạy cả truyện"). Lệnh đọc `NEO4J_*`, `POSTGRES_DSN` và, khi chạy thật, `OPENROUTER_API_KEY` từ biến môi trường hoặc `.env`; tự chạy migration và tạo ràng buộc Neo4j. Mỗi lần chạy dùng một story_id mới `run-<ngày>-<nhãn>-<mã>`, ghi trong `meta.json`. Truyện của lần chạy thật được giữ lại trong Neo4j + Postgres; xem bằng sổ tay (`ENABLE_DEV_ROUTES`, bên dưới) hoặc xoá bằng `delete_story_record` và `graph.delete_story`.

Chạy API ở máy (đọc biến môi trường từ `.env` ở gốc repo):
```bash
cd backend
uv run uvicorn writory.api:create_app --factory --reload
curl http://127.0.0.1:8000/health   # {"neo4j": "ok"|"down", "postgres": "ok"|"down"}; 503 nếu có phần down
```
App tạo bằng factory (`--factory`), nên import `writory.api` không cần biến môi trường.

API truyện (`/stories/...`) và key người chơi (`/player/key`) chưa có đăng nhập, nên mọi người đều là người chơi dev `dev` và chưa kiểm được truyện thuộc ai (G10). Các router này chỉ được gắn khi đặt `ENABLE_DEV_ROUTES=true` (D-41). Chỉ bật trên máy dev, không bật trên máy chủ thật. Chạy migration trước (mục Migration Postgres).
```bash
ENABLE_DEV_ROUTES=true uv run uvicorn writory.api:create_app --factory --reload
curl -X PUT http://127.0.0.1:8000/player/key -H 'content-type: application/json' -d '{"api_key": "sk-or-v1-..."}'
curl http://127.0.0.1:8000/stories/<story_id>/notebook
```
Lời gọi model (ví dụ `POST /stories/<story_id>/narrator`) trả bằng key người chơi đã lưu qua `/player/key`, không bao giờ bằng `OPENROUTER_API_KEY`. Truyện phải có `story_plan` trong Postgres; truyện mẫu nạp tay không có, nên hỏi người kể trên nó báo lỗi (fail closed, D-44).

## CI
GitHub Actions, file `.github/workflows/ci.yml`. Chạy trên mỗi PR và mỗi lần push lên `main`.

| Job | Làm gì |
|---|---|
| `fast` | `uv sync --locked`, `uv run ruff check .`, `uv run pytest -m "not graph"` trong `backend/` |
| `graph` | dựng service container `neo4j:5.26-community` và `postgres:16`, chờ cổng 7474 của Neo4j (Postgres chờ bằng health check), rồi `uv run pytest -m graph` |

- Marker `graph` đánh dấu mọi test cần dịch vụ Docker: Neo4j, và Postgres cho luồng ghi chương. Test nhanh (`-m "not graph"`) không cần Docker.
- Job `graph` đặt `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` và `POSTGRES_DSN` qua biến môi trường của job; mật khẩu chỉ dùng cho container CI. Test đọc kết nối từ các biến này, mặc định theo `.env.example` khi chạy local.
- Không có test nào mang marker `graph` chạy (pytest trả mã 5) thì job `graph` đỏ.
- `uv sync --locked` báo lỗi nếu `uv.lock` lệch `pyproject.toml`: chạy `uv lock` ở máy rồi commit lại.
- Chạy giống CI ở máy: các lệnh `ruff`/`pytest` ở mục trên.

## Migration Postgres
SQL thuần trong `backend/src/writory/db/migrations/`, chạy theo thứ tự tên file, mỗi file một lần (D-20). Muốn đổi schema thì thêm file mới, không sửa file đã chạy.
```bash
cd backend
uv run python -c "from writory.config import Settings; from writory.db import connect, migrate; print(migrate(connect(Settings())))"
```
Test `-m graph` tự chạy migration trên database trong `POSTGRES_DSN`.

## Ghi chương bị kẹt `pending`
Chương ở lại `pending` khi Neo4j không trả lời hoặc tiến trình chết giữa chừng (D-6). Truyện đó không ghi được chương mới cho tới khi reconcile:
```bash
uv run python -c "from neo4j import GraphDatabase; from writory.config import Settings; from writory.db import connect, reconcile_pending; s = Settings(); d = GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_user, s.neo4j_password.get_secret_value())); print(reconcile_pending(connect(s), d))"
```

## Biến môi trường
Danh sách đầy đủ: `.env.example`. Không commit `.env`.

- `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`: key của chủ dự án, chỉ cho bộ đo và lệnh chạy cả truyện (`bench_run`, chỉ cần `OPENROUTER_API_KEY`). Runner chỉ đọc đúng các tên này; thiếu thì báo lỗi và không gọi model.
- `ANTHROPIC_WORKSPACE_ID` (tuỳ chọn): cần khi key Anthropic không gắn với workspace. Lệnh: `docs/eval.md`.

- `PLAYER_KEY_ENCRYPTION_KEY`: khoá Fernet mã hoá key OpenRouter của người chơi (G7, D-11). Tạo bằng lệnh sau, chạy trong `backend/`:
  ```bash
  uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  Mất hoặc đổi khoá thì key đã lưu không giải mã được nữa, và người chơi phải nhập lại. Khi `ENABLE_DEV_ROUTES=true`, khoá sai định dạng thì app không khởi động (D-11, D-45).
- `ENABLE_DEV_ROUTES` (mặc định `false`): gắn router chưa có đăng nhập (truyện, key người chơi; D-41). Chỉ bật trên máy dev.
- Cấu hình runtime nằm trong `config/*.yaml`, được nạp và kiểm schema bằng `writory.config.load_config()`. Giá trị `null` nghĩa là chưa đặt; code nào cần giá trị đó sẽ báo lỗi.

## Deploy
*(chưa có. Lưu ý: AuraDB Free tự tạm dừng sau 3 ngày không dùng, nên không hợp cho người chơi thật. Xem design §11.)*
