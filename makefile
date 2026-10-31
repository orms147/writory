# WriTory: lệnh nhanh cho máy dev (GNU Make trên Windows, công thức chạy bằng PowerShell 7 `pwsh`).
#   make run    cài phụ thuộc, bật Neo4j + Postgres (Docker), chạy migration, rồi chạy backend (:8000) và
#               giao diện (:5173) cùng lúc. Mở http://localhost:5173. Ctrl+C để dừng cả hai.
#   make help   xem các lệnh khác.
# Lần đầu: cần Docker Desktop đang chạy, uv, Node 20.19+; `.env` ở gốc repo (lệnh tự chép từ .env.example nếu
# chưa có, rồi dừng để bạn điền). Chi tiết: docs/runbook.md, mục "Chạy máy local" và "Chạy backend cho frontend dev".
# Câu in ra màn hình viết không dấu: make trên Windows truyền lệnh qua mã ANSI, chữ có dấu dễ hỏng.

SHELL := pwsh.exe
.SHELLFLAGS := -NoProfile -NonInteractive -Command
.DEFAULT_GOAL := help
.PHONY: help run setup env deps db migrate backend frontend mock test stop

help:
	@Write-Host 'make run       cai dat + bat DB + migration + backend :8000 + giao dien :5173 (Ctrl+C de dung)'
	@Write-Host 'make mock      chi giao dien voi may chu gia (khong can backend, khong goi model)'
	@Write-Host 'make setup     kiem .env, cai phu thuoc backend (uv sync) va frontend (npm ci lan dau)'
	@Write-Host 'make db        bat Neo4j + Postgres (docker compose up -d)'
	@Write-Host 'make migrate   chay migration Postgres (doi Postgres san sang)'
	@Write-Host 'make backend   chi backend :8000 (ENABLE_DEV_ROUTES=true)'
	@Write-Host 'make frontend  chi giao dien :5173, goi backend qua proxy /api'
	@Write-Host 'make test      test nhanh backend (khong mang, khong goi model)'
	@Write-Host 'make stop      tat Neo4j + Postgres (docker compose stop, giu du lieu)'

run: setup db migrate
	@Write-Host 'Backend http://127.0.0.1:8000 | Giao dien http://localhost:5173 | Ctrl+C de dung'
	@$(MAKE) --no-print-directory -j2 backend frontend

setup: env deps

# Không đọc giá trị trong .env: chỉ kiểm file có chưa. Chưa có thì chép mẫu rồi dừng để bạn điền.
env:
	@if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host 'Da tao .env tu .env.example. Dien mat khau local va PLAYER_KEY_ENCRYPTION_KEY (docs/runbook.md, muc Bien moi truong) roi chay lai make run.'; exit 1 }

deps:
	uv --directory backend sync
	@if (-not (Test-Path frontend/node_modules)) { npm --prefix frontend ci; if ($$LASTEXITCODE) { exit $$LASTEXITCODE } }

db:
	docker compose up -d

# docker-compose.yml không có healthcheck: thử lại tới khi Postgres nhận kết nối (tối đa khoảng 60 giây).
migrate:
	@for ($$i = 1; $$i -le 30; $$i++) { uv --directory backend run python -c "from writory.config import Settings; from writory.db import connect, migrate; print(migrate(connect(Settings())))"; if ($$LASTEXITCODE -eq 0) { exit 0 }; Write-Host "Postgres chua san sang, thu lai ($$i/30)..."; Start-Sleep -Seconds 2 }; Write-Host 'Khong chay duoc migration: kiem Docker Desktop va POSTGRES_DSN trong .env'; exit 1

backend:
	@$$env:ENABLE_DEV_ROUTES = 'true'; uv --directory backend run uvicorn writory.api:create_app --factory --reload --host 127.0.0.1 --port 8000

frontend:
	npm --prefix frontend run dev

mock:
	@if (-not (Test-Path frontend/node_modules)) { npm --prefix frontend ci; if ($$LASTEXITCODE) { exit $$LASTEXITCODE } }
	npm --prefix frontend run dev:mock

test:
	uv --directory backend run pytest -m "not graph" -q

stop:
	docker compose stop
