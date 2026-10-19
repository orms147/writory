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
uv run pytest -m graph        # test đồ thị: cần Neo4j ở trên
```

## CI
GitHub Actions, file `.github/workflows/ci.yml`. Chạy trên mỗi PR và mỗi lần push lên `main`.

| Job | Làm gì |
|---|---|
| `fast` | `uv sync --locked`, `uv run ruff check .`, `uv run pytest -m "not graph"` trong `backend/` |
| `graph` | dựng service container `neo4j:5.26-community`, chờ cổng 7474, rồi `uv run pytest -m graph` |

- Job `graph` đặt `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` qua biến môi trường của job; mật khẩu chỉ dùng cho container CI. Test đồ thị đọc kết nối từ các biến này, giống `.env` khi chạy local.
- Khi chưa có test nào mang marker `graph`, pytest trả mã 5; job coi đó là đạt.
- `uv sync --locked` báo lỗi nếu `uv.lock` lệch `pyproject.toml`: chạy `uv lock` ở máy rồi commit lại.
- Chạy giống CI ở máy: các lệnh `ruff`/`pytest` ở mục trên.

## Biến môi trường
Danh sách đầy đủ: `.env.example`. Không commit `.env`.

## Deploy
*(chưa có. Lưu ý: AuraDB Free tự tạm dừng sau 3 ngày không dùng, nên không hợp cho người chơi thật. Xem design §11.)*
