# Launch the full EchoscopeAI stack on the host (Windows PowerShell).
#
#   powershell -ExecutionPolicy Bypass -File scripts\run-all.ps1
#
# Starts: docker infra -> 7 backend services (uvicorn, each in its own window)
#         -> the Next.js frontend. Close the windows (or run scripts\stop-all.ps1)
# to stop. Each backend reads its own .env (host addresses).

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$uvicorn = Join-Path $root ".venv\Scripts\uvicorn.exe"

Write-Host "1/3  Starting infrastructure (postgres, redis, kafka, zookeeper)..." -ForegroundColor Cyan
docker compose -f (Join-Path $root "docker-compose.yml") up -d | Out-Null

# wait for postgres + kafka health
Write-Host "     waiting for containers to be healthy..."
for ($i = 0; $i -lt 30; $i++) {
    $unhealthy = (docker compose -f (Join-Path $root "docker-compose.yml") ps --format "{{.Health}}") -split "`n" | Where-Object { $_ -and $_ -ne "healthy" }
    if (-not $unhealthy) { break }
    Start-Sleep -Seconds 3
}

$services = @(
    @{ name = "api-gateway";          port = 8000 },
    @{ name = "auth-service";          port = 8001 },
    @{ name = "mention-service";       port = 8002 },
    @{ name = "nlp-service";           port = 8003 },
    @{ name = "analytics-service";     port = 8004 },
    @{ name = "notification-service";  port = 8005 },
    @{ name = "report-service";        port = 8006 }
)

Write-Host "2/3  Starting backend services..." -ForegroundColor Cyan
foreach ($s in $services) {
    $dir = Join-Path $root $s.name
    $title = "$($s.name) :$($s.port)"
    Start-Process powershell -ArgumentList @(
        "-NoExit", "-Command",
        "`$host.UI.RawUI.WindowTitle='$title'; Set-Location '$dir'; & '$uvicorn' main:app --port $($s.port)"
    )
    Start-Sleep -Milliseconds 400
}

Write-Host "3/3  Starting frontend (Next.js) on http://localhost:3000 ..." -ForegroundColor Cyan
$fe = Join-Path $root "frontend"
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "`$host.UI.RawUI.WindowTitle='frontend :3000'; Set-Location '$fe'; npm run dev"
)

Write-Host ""
Write-Host "All started. Open http://localhost:3000 (register, then explore)." -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs   |   stop: scripts\stop-all.ps1" -ForegroundColor Green


# email:    user0.sell-sister-job-0@example.com
# password: password123