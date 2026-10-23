# Xem trạng thái server WriTory (D-103): container, app có trả lời không, số việc đang chạy, log gần
# nhất. Chạy từ gốc repo:
#   powershell -ExecutionPolicy Bypass -File deploy\prod-status.ps1
#   powershell -ExecutionPolicy Bypass -File deploy\prod-status.ps1 -Lines 100
param(
    [int]$Lines = 20
)
. (Join-Path $PSScriptRoot 'prod-common.ps1')

Assert-Docker

Write-Host "== Container của $Project ==" -ForegroundColor Cyan
Invoke-Compose ps --all

$running = Get-RunningServices
if ($running -contains 'backend') {
    if (Test-ProdHealth) {
        Write-Host 'App: sẵn sàng (/api/health qua proxy: ok).' -ForegroundColor Green
    } else {
        Write-Host 'App: chưa trả lời /api/health (đang khởi động, hoặc Neo4j/Postgres lỗi).' -ForegroundColor Yellow
    }
    $jobs = Get-HeldJobs
    if ($null -eq $jobs) {
        Write-Host 'Việc đang chạy: không đọc được.'
    } else {
        Write-Host "Việc đang gọi model (viết chương, hỏi người kể, khởi tạo...): $jobs"
    }
} else {
    Write-Host 'App: đang tắt. Bật: deploy\prod-up.ps1'
}

foreach ($svc in @('backend', 'cloudflared', 'proxy')) {
    Write-Host "== Log gần nhất: $svc ==" -ForegroundColor Cyan
    Invoke-Compose logs --no-color --tail $Lines $svc 2>&1
}
