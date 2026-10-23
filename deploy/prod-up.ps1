# Bật server WriTory cho người chơi (D-103). Chạy từ gốc repo:
#   powershell -ExecutionPolicy Bypass -File deploy\prod-up.ps1          # bật
#   powershell -ExecutionPolicy Bypass -File deploy\prod-up.ps1 -Build   # sau khi kéo code mới
# Dữ liệu giữ trong volume của project writory-prod. Tắt: deploy\prod-down.ps1.
param(
    [switch]$Build,
    [int]$TimeoutSeconds = 240
)
. (Join-Path $PSScriptRoot 'prod-common.ps1')

Assert-Docker

$values = Read-EnvFile
if ($null -eq $values) {
    Write-Host "Chưa có $EnvFile. Chép .env.prod.example thành .env.prod rồi điền (docs/runbook.md, mục Deploy)." -ForegroundColor Yellow
    exit 1
}
$missing = @($RequiredVars | Where-Object { -not $values[$_] })
if ($missing.Count -gt 0) {
    Write-Host ("Thiếu giá trị trong .env.prod: " + ($missing -join ', ')) -ForegroundColor Yellow
    exit 1
}

Write-Host "Bật chồng $Project ..."
$upArgs = @('up', '-d')
if ($Build) { $upArgs += '--build' }
Invoke-Compose @upArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host 'docker compose up lỗi. Xem log: deploy\prod-status.ps1' -ForegroundColor Red
    exit 1
}

Write-Host 'Chờ app sẵn sàng (Neo4j khởi động mất khoảng một phút) ...'
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$healthy = $false
while ((Get-Date) -lt $deadline) {
    if (Test-ProdHealth) { $healthy = $true; break }
    Start-Sleep -Seconds 5
}
Invoke-Compose ps
if (-not $healthy) {
    Write-Host "App chưa sẵn sàng sau $TimeoutSeconds giây. Xem log: deploy\prod-status.ps1" -ForegroundColor Red
    exit 1
}
Write-Host 'App sẵn sàng (/api/health qua proxy: ok).' -ForegroundColor Green

if ((Get-RunningServices) -contains 'cloudflared') {
    $tunnelUp = $false
    for ($i = 0; $i -lt 12 -and -not $tunnelUp; $i++) {
        $log = Invoke-Compose logs --since 10m cloudflared 2>&1 | Out-String
        if ($log -match 'Registered tunnel connection') { $tunnelUp = $true } else { Start-Sleep -Seconds 5 }
    }
    if ($tunnelUp) {
        Write-Host 'Tunnel Cloudflare: đã nối.' -ForegroundColor Green
    } else {
        Write-Host 'Tunnel Cloudflare: chưa thấy nối. Kiểm token và log: deploy\prod-status.ps1' -ForegroundColor Yellow
    }
} else {
    Write-Host 'Tunnel Cloudflare: không chạy (người ngoài chưa vào được).' -ForegroundColor Yellow
}

if ($values['PUBLIC_URL']) {
    Write-Host ("Link cho bạn bè: " + $values['PUBLIC_URL']) -ForegroundColor Cyan
} else {
    Write-Host 'Link cho bạn bè: tên miền đã gắn với tunnel trong bảng Cloudflare (đặt PUBLIC_URL trong .env.prod để in ra đây).'
}
