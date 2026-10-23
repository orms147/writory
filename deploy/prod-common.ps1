# Phần chung của prod-up, prod-down, prod-status, prod-backup, prod-restore (D-103). Không chạy riêng.
# Chạy được trên Windows PowerShell 5.1 và PowerShell 7.
$ErrorActionPreference = 'Continue'   # lệnh docker ghi tiến độ ra stderr; kiểm $LASTEXITCODE
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$Root = Split-Path -Parent $PSScriptRoot
# Mặc định là chồng prod thật. Biến WRITORY_PROD_* chỉ để thử script trên project thử
# (docs/runbook.md, mục Deploy); đừng đặt khi chạy thật.
$Project = if ($env:WRITORY_PROD_PROJECT) { $env:WRITORY_PROD_PROJECT } else { 'writory-prod' }
$EnvFile = if ($env:WRITORY_PROD_ENV_FILE) { $env:WRITORY_PROD_ENV_FILE } else { Join-Path $Root '.env.prod' }
$ComposeArgs = @('compose', '-p', $Project, '-f', (Join-Path $Root 'docker-compose.prod.yml'))
if ($env:WRITORY_PROD_EXTRA_COMPOSE) { $ComposeArgs += @('-f', $env:WRITORY_PROD_EXTRA_COMPOSE) }
$ComposeArgs += @('--env-file', $EnvFile)

$RequiredVars = @('CLOUDFLARE_TUNNEL_TOKEN', 'NEO4J_PASSWORD', 'POSTGRES_PASSWORD',
                  'PLAYER_KEY_ENCRYPTION_KEY')

function Invoke-Compose {
    & docker @script:ComposeArgs @args
}

function Assert-Docker {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Docker chưa chạy. Mở Docker Desktop, đợi đến khi nó báo "Engine running", rồi chạy lại lệnh này.' -ForegroundColor Yellow
        exit 1
    }
}

function Read-EnvFile {
    $values = @{}
    if (-not (Test-Path $script:EnvFile)) { return $null }
    foreach ($line in Get-Content -Encoding UTF8 $script:EnvFile) {
        $t = $line.Trim()
        if ($t -eq '' -or $t.StartsWith('#') -or -not $t.Contains('=')) { continue }
        $i = $t.IndexOf('=')
        $values[$t.Substring(0, $i).Trim()] = $t.Substring($i + 1).Trim()
    }
    return $values
}

function Test-ProdHealth {
    # Đi đủ đường proxy → backend → Neo4j, Postgres, trong mạng docker (không cần tunnel).
    $code = "import urllib.request; urllib.request.urlopen('http://proxy:80/api/health', timeout=5)"
    Invoke-Compose exec -T backend python -c $code *> $null
    return ($LASTEXITCODE -eq 0)
}

function Get-HeldJobs {
    # Số việc đang gọi model (khoá chạy đôi D-46 trong Postgres). $null: không đọc được.
    $out = Invoke-Compose exec -T backend python -m writory.db.locks 2> $null
    if ($LASTEXITCODE -ne 0) { return $null }
    $last = ($out | Select-Object -Last 1)
    $n = 0
    if ([int]::TryParse("$last".Trim(), [ref]$n)) { return $n }
    return $null
}

function Get-RunningServices {
    $names = Invoke-Compose ps --services --status running 2> $null
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($names | Where-Object { $_ })
}
