# Sao lưu Postgres và Neo4j của chồng prod (D-103). Chạy từ gốc repo:
#   powershell -ExecutionPolicy Bypass -File deploy\prod-backup.ps1
#   powershell -ExecutionPolicy Bypass -File deploy\prod-backup.ps1 -OutDir D:\writory-backups -Force
# Ghi vào backups\<ngày-giờ>\ (không commit): postgres.dump (pg_dump -Fc) và neo4j.dump
# (neo4j-admin database dump, Neo4j Community chỉ dump được khi database dừng).
# Server tắt trong lúc sao lưu (khoảng một phút) để hai kho khớp nhau (chương ghi vào cả hai, D-6);
# đang bật thì bật lại sau. Khôi phục: deploy\prod-restore.ps1.
# Bản sao lưu chỉ dùng được cùng PLAYER_KEY_ENCRYPTION_KEY trong .env.prod: giữ .env.prod ở chỗ an
# toàn riêng (không cùng chỗ với bản sao lưu nếu chỗ đó dùng chung).
param(
    [string]$OutDir = '',
    [switch]$Force
)
. (Join-Path $PSScriptRoot 'prod-common.ps1')

Assert-Docker

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
if (-not $OutDir) { $OutDir = Join-Path $Root 'backups' }
$dir = Join-Path $OutDir $stamp
New-Item -ItemType Directory -Force -Path $dir | Out-Null
$dir = (Resolve-Path $dir).Path

$running = Get-RunningServices
$wasUp = $running -contains 'backend'
if ($wasUp -and -not $Force) {
    $jobs = Get-HeldJobs
    if ($jobs -gt 0) {
        Write-Host "Đang có $jobs việc gọi model; sao lưu sẽ tắt server khoảng một phút." -ForegroundColor Yellow
        $answer = Read-Host 'Vẫn sao lưu? (gõ y để tiếp)'
        if ($answer -ne 'y') { Write-Host 'Không sao lưu.'; exit 1 }
    }
}

function Fail([string]$msg) {
    Write-Host $msg -ForegroundColor Red
    if ($script:wasUp) { Invoke-Compose up -d | Out-Null }
    exit 1
}

Write-Host 'Dừng cloudflared, proxy, backend, Neo4j ...'
Invoke-Compose stop cloudflared proxy backend neo4j
Invoke-Compose up -d --no-deps postgres
for ($i = 0; $i -lt 30; $i++) {
    Invoke-Compose exec -T postgres pg_isready -U writory -d writory *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 2
}

Write-Host 'Sao lưu Postgres ...'
Invoke-Compose exec -T postgres pg_dump -U writory -d writory -Fc -f /tmp/writory-backup.dump
if ($LASTEXITCODE -ne 0) { Fail 'pg_dump lỗi.' }
Invoke-Compose cp postgres:/tmp/writory-backup.dump (Join-Path $dir 'postgres.dump')
if ($LASTEXITCODE -ne 0) { Fail 'Chép bản dump Postgres ra máy lỗi.' }
Invoke-Compose exec -T postgres rm -f /tmp/writory-backup.dump | Out-Null

Write-Host 'Sao lưu Neo4j ...'
Invoke-Compose run --rm --no-deps -v "${dir}:/backups" neo4j `
    neo4j-admin database dump neo4j --to-path=/backups --overwrite-destination=true
if ($LASTEXITCODE -ne 0) { Fail 'neo4j-admin database dump lỗi.' }

if ($wasUp) {
    Write-Host 'Bật lại server ...'
    Invoke-Compose up -d
} else {
    Invoke-Compose stop postgres
}

Get-ChildItem $dir | Format-Table Name, Length -AutoSize
Write-Host "Đã sao lưu vào $dir" -ForegroundColor Green
Write-Host 'Nhớ: bản sao lưu cần đúng PLAYER_KEY_ENCRYPTION_KEY trong .env.prod để đọc được key người chơi.'
