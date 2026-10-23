# Khôi phục chồng prod từ một bản sao lưu của prod-backup.ps1 (D-103). XOÁ dữ liệu hiện có của
# Postgres và Neo4j prod rồi thay bằng bản sao lưu. Chạy từ gốc repo:
#   powershell -ExecutionPolicy Bypass -File deploy\prod-restore.ps1 -From backups\20261023-210000
# Cần .env.prod có đúng PLAYER_KEY_ENCRYPTION_KEY lúc sao lưu, không thì key người chơi đã lưu
# không giải mã được (người chơi nhập lại key là xong, truyện vẫn còn).
param(
    [Parameter(Mandatory = $true)][string]$From,
    [switch]$Force
)
. (Join-Path $PSScriptRoot 'prod-common.ps1')

Assert-Docker

$dir = (Resolve-Path $From -ErrorAction SilentlyContinue).Path
if (-not $dir -or -not (Test-Path (Join-Path $dir 'postgres.dump')) -or
        -not (Test-Path (Join-Path $dir 'neo4j.dump'))) {
    Write-Host "Không thấy postgres.dump và neo4j.dump trong $From" -ForegroundColor Red
    exit 1
}
if (-not $Force) {
    Write-Host "Khôi phục sẽ XOÁ dữ liệu hiện có của $Project và thay bằng $dir." -ForegroundColor Yellow
    $answer = Read-Host 'Gõ khoi-phuc để tiếp'
    if ($answer -ne 'khoi-phuc') { Write-Host 'Không khôi phục.'; exit 1 }
}

$wasUp = (Get-RunningServices) -contains 'backend'

Write-Host 'Dừng cloudflared, proxy, backend, Neo4j ...'
Invoke-Compose stop cloudflared proxy backend neo4j
Invoke-Compose up -d --no-deps postgres
for ($i = 0; $i -lt 30; $i++) {
    Invoke-Compose exec -T postgres pg_isready -U writory -d writory *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
}

Write-Host 'Khôi phục Postgres ...'
Invoke-Compose cp (Join-Path $dir 'postgres.dump') postgres:/tmp/writory-restore.dump
if ($LASTEXITCODE -ne 0) { Write-Host 'Chép bản dump vào container lỗi.' -ForegroundColor Red; exit 1 }
Invoke-Compose exec -T postgres pg_restore -U writory -d writory --clean --if-exists --no-owner `
    /tmp/writory-restore.dump
if ($LASTEXITCODE -ne 0) { Write-Host 'pg_restore lỗi (xem dòng lỗi ở trên).' -ForegroundColor Red; exit 1 }
Invoke-Compose exec -T postgres rm -f /tmp/writory-restore.dump | Out-Null

Write-Host 'Khôi phục Neo4j ...'
Invoke-Compose run --rm --no-deps -v "${dir}:/backups" neo4j `
    neo4j-admin database load neo4j --from-path=/backups --overwrite-destination=true
if ($LASTEXITCODE -ne 0) { Write-Host 'neo4j-admin database load lỗi.' -ForegroundColor Red; exit 1 }

if ($wasUp) {
    Write-Host 'Bật lại server ...'
    Invoke-Compose up -d
} else {
    Invoke-Compose stop postgres
    Write-Host 'Bật server: deploy\prod-up.ps1'
}
Write-Host 'Đã khôi phục.' -ForegroundColor Green
