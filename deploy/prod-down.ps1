# Tắt server WriTory, GIỮ NGUYÊN dữ liệu (D-103). Chạy từ gốc repo:
#   powershell -ExecutionPolicy Bypass -File deploy\prod-down.ps1          # hỏi nếu đang có việc chạy
#   powershell -ExecutionPolicy Bypass -File deploy\prod-down.ps1 -Force   # tắt luôn
# Dùng `docker compose stop` (không bao giờ `down -v`): container, volume còn nguyên; đã tắt bằng
# lệnh này thì mở lại Docker Desktop hay khởi động lại máy cũng không tự lên. Bật lại: prod-up.ps1.
param(
    [switch]$Force
)
. (Join-Path $PSScriptRoot 'prod-common.ps1')

Assert-Docker

$running = Get-RunningServices
if ($running.Count -eq 0) {
    Write-Host "Chồng $Project không có container nào đang chạy."
    exit 0
}

if (-not $Force -and ($running -contains 'backend')) {
    $jobs = Get-HeldJobs
    if ($null -eq $jobs) {
        Write-Host 'Không đọc được số việc đang chạy (backend hay Postgres chưa sẵn sàng).' -ForegroundColor Yellow
    } elseif ($jobs -gt 0) {
        Write-Host "Đang có $jobs việc gọi model (viết chương, hỏi người kể, khởi tạo...)." -ForegroundColor Yellow
        Write-Host 'Tắt bây giờ thì chương đang viết không được ghi; người chơi phải bấm viết lại.'
        $answer = Read-Host 'Vẫn tắt? (gõ y để tắt)'
        if ($answer -ne 'y') {
            Write-Host 'Không tắt. Chạy lại sau, hoặc thêm -Force.'
            exit 1
        }
    }
}

Write-Host "Tắt chồng $Project (dữ liệu giữ nguyên) ..."
Invoke-Compose stop
if ($LASTEXITCODE -ne 0) {
    Write-Host 'docker compose stop lỗi.' -ForegroundColor Red
    exit 1
}
Invoke-Compose ps --all
Write-Host 'Đã tắt. Bật lại: deploy\prod-up.ps1' -ForegroundColor Green
