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
uv run pytest                 # test nhanh: không mạng, không gọi model thật
```

## Biến môi trường
Danh sách đầy đủ: `.env.example`. Không commit `.env`.

- `PLAYER_KEY_ENCRYPTION_KEY`: khoá Fernet mã hoá key OpenRouter của người chơi (G7, D-11). Tạo bằng lệnh sau, chạy trong `backend/`:
  ```bash
  uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
  Mất hoặc đổi khoá thì key đã lưu không giải mã được nữa, và người chơi phải nhập lại.
- Cấu hình runtime nằm trong `config/*.yaml`, được nạp và kiểm schema bằng `writory.config.load_config()`. Giá trị `null` nghĩa là chưa đặt; code nào cần giá trị đó sẽ báo lỗi.

## Deploy
*(chưa có. Lưu ý: AuraDB Free tự tạm dừng sau 3 ngày không dùng, nên không hợp cho người chơi thật. Xem design §11.)*
