# Stop the EchoscopeAI stack started by run-all.ps1.
#   powershell -ExecutionPolicy Bypass -File scripts\stop-all.ps1

$ErrorActionPreference = "SilentlyContinue"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "Stopping backend services + frontend (uvicorn / next dev)..." -ForegroundColor Cyan
# kill the uvicorn workers and the next dev server (node) started for this app
Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match "uvicorn.*main:app" -or $_.CommandLine -match "next(\\| )dev"
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Write-Host "Stopping docker infrastructure..." -ForegroundColor Cyan
docker compose -f (Join-Path $root "docker-compose.yml") stop | Out-Null

Write-Host "Done. (Data volumes are preserved.)" -ForegroundColor Green
