# WriTory: lệnh nhanh cho máy dev (GNU Make trên Windows, công thức chạy bằng PowerShell 7 `pwsh`).
#   make run    cài phụ thuộc, bật Neo4j + Postgres (Docker), chạy migration, rồi chạy backend (:8000) và
#               giao diện (:5173) cùng lúc. Mở http://localhost:5173. Ctrl+C để dừng cả hai.
#   make start  như make run, rồi tự mở trình duyệt khi app sẵn sàng; app đang chạy thì chỉ mở trình duyệt.
#   make desktop  tạo icon WriTory trên Desktop, bấm đúp là chạy make start (D-158).
#   make help   xem các lệnh khác.
# Lần đầu: cần Docker Desktop (lệnh tự bật nếu nó chưa chạy), uv, Node 20.19+; `.env` ở gốc repo (lệnh tự chép từ .env.example nếu
# chưa có, rồi dừng để bạn điền). Chi tiết: docs/runbook.md, mục "Chạy máy local" và "Chạy backend cho frontend dev".
# Câu in ra màn hình viết không dấu: make trên Windows truyền lệnh qua mã ANSI, chữ có dấu dễ hỏng.

SHELL := pwsh.exe
.SHELLFLAGS := -NoProfile -NonInteractive -Command
.DEFAULT_GOAL := help
.PHONY: help run start start-app open desktop setup env deps docker-up db migrate backend frontend mock test stop

help:
	@Write-Host 'make run       cai dat + bat DB + migration + backend :8000 + giao dien :5173 (Ctrl+C de dung)'
	@Write-Host 'make start     nhu make run, roi tu mo trinh duyet; app dang chay thi chi mo trinh duyet'
	@Write-Host 'make desktop   tao icon WriTory tren Desktop (bam dup = make start)'
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

# Icon desktop gọi lệnh này (D-158). Cửa sổ có tên WriTory; đóng cửa sổ hay Ctrl+C là dừng app (Docker vẫn chạy).
# Giao diện đang chạy thì chỉ mở trình duyệt. Có lỗi thì giữ cửa sổ cho đọc lỗi.
start:
	@$$Host.UI.RawUI.WindowTitle = 'WriTory - dong cua so hoac Ctrl+C de dung'; if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { Write-Host 'WriTory dang chay: mo trinh duyet.'; Start-Process 'http://localhost:5173'; exit 0 }; if (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue) { Write-Host 'Cong 8000 dang ban (mot backend khac dang chay?). Tat no roi mo lai.'; cmd /c pause; exit 1 }; $(MAKE) --no-print-directory start-app; $$code = $$LASTEXITCODE; if ($$code) { Write-Host 'Co loi o tren (docs/runbook.md, muc Chay may local).'; cmd /c pause }; exit $$code

start-app: setup db migrate
	@Write-Host 'Backend http://127.0.0.1:8000 | Giao dien http://localhost:5173 | dong cua so hoac Ctrl+C de dung'
	@$(MAKE) --no-print-directory -j3 backend frontend open

# Đợi backend /health trả 200 và giao diện nghe cổng 5173 (tối đa khoảng 3 phút) rồi mở trình duyệt; không bao giờ
# làm hỏng make. Không gọi HTTP tới localhost:5173: Vite chỉ nghe 127.0.0.1, .NET thử ::1 trước và mất vài giây.
open:
	@for ($$i = 1; $$i -le 90; $$i++) { try { Invoke-WebRequest http://127.0.0.1:8000/health -TimeoutSec 3 | Out-Null; if (Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue) { Start-Process 'http://localhost:5173'; exit 0 } } catch {}; Start-Sleep -Seconds 2 }; Write-Host 'Chua thay app tra loi sau 3 phut: doc loi o tren, hoac tu mo http://localhost:5173'; exit 0

# Tạo (hoặc ghi đè) WriTory.lnk trên Desktop: chạy `make start` ở thư mục repo này, icon deploy/writory.ico.
desktop:
	@$$lnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'WriTory.lnk'; $$s = (New-Object -ComObject WScript.Shell).CreateShortcut($$lnk); $$s.TargetPath = (Get-Command make).Source; $$s.Arguments = 'start'; $$s.WorkingDirectory = (Get-Location).Path; $$s.IconLocation = (Resolve-Path deploy/writory.ico).Path + ',0'; $$s.Description = 'Mo WriTory (make start)'; $$s.Save(); Write-Host "Da tao $$lnk"

setup: env deps

# Không đọc giá trị trong .env: chỉ kiểm file có chưa. Chưa có thì chép mẫu rồi dừng để bạn điền.
env:
	@if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host 'Da tao .env tu .env.example. Dien mat khau local va PLAYER_KEY_ENCRYPTION_KEY (docs/runbook.md, muc Bien moi truong) roi chay lai make run.'; exit 1 }

deps:
	uv --directory backend sync
	@if (-not (Test-Path frontend/node_modules)) { npm --prefix frontend ci; if ($$LASTEXITCODE) { exit $$LASTEXITCODE } }

# Docker chưa chạy thì bật Docker Desktop (tìm từ chỗ cài lệnh docker) và đợi engine sẵn sàng (tối đa khoảng 3 phút).
docker-up:
	@docker info *> $$null; if ($$LASTEXITCODE -eq 0) { exit 0 }; $$cli = Get-Command docker -ErrorAction SilentlyContinue; $$exe = if ($$cli) { Join-Path (Split-Path (Split-Path (Split-Path $$cli.Source))) 'Docker Desktop.exe' }; if (-not $$exe -or -not (Test-Path $$exe)) { Write-Host 'Docker chua chay va khong tim thay Docker Desktop: mo Docker Desktop roi chay lai.'; exit 1 }; Write-Host 'Dang bat Docker Desktop...'; Start-Process $$exe; for ($$i = 1; $$i -le 60; $$i++) { Start-Sleep -Seconds 3; docker info *> $$null; if ($$LASTEXITCODE -eq 0) { Write-Host 'Docker da san sang.'; exit 0 } }; Write-Host 'Docker Desktop chua san sang sau 3 phut: mo no xem loi roi chay lai.'; exit 1

db: docker-up
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
