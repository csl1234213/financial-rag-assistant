# PowerShell
# ============================================================
# start.ps1 — One-Command Deploy for Windows
# ============================================================
# Usage:
#   .\scripts\start.ps1          # production mode
#   .\scripts\start.ps1 dev      # development mode
# ============================================================
param(
    [string]$Mode = "prod"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path "$ScriptDir\..").Path

$EnvFile     = "$ProjectRoot\.env"
$EnvExample  = "$ProjectRoot\.env.example"

$ApiUrl    = "http://localhost:8000"
$UiUrl     = "http://localhost:8501"
$HealthUrl = "$ApiUrl/api/v1/health"
$MaxRetries = 30
$RetryInterval = 2

# ============================================================
# Step 1: Auto .env initialization
# ============================================================
if (-not (Test-Path $EnvFile)) {
    Write-Host "=========================================="
    Write-Host "  .env not found — creating from .env.example"
    Write-Host "=========================================="
    Copy-Item $EnvExample $EnvFile
    Write-Host ""
    Write-Host "  IMPORTANT: Please edit .env to set your DEEPSEEK_API_KEY before proceeding."
    Write-Host "  File: $EnvFile"
    Write-Host ""
    Read-Host "  Press Enter to continue after editing, or Ctrl+C to abort"
}

# ============================================================
# Step 2: Select compose files
# ============================================================
if ($Mode -eq "dev") {
    Write-Host "=========================================="
    Write-Host "  Starting in DEVELOPMENT mode (hot-reload)"
    Write-Host "=========================================="
    $ComposeArgs = @("-f", "docker-compose.base.yml", "-f", "docker-compose.dev.yml")
} else {
    Write-Host "=========================================="
    Write-Host "  Starting in PRODUCTION mode"
    Write-Host "=========================================="
    $ComposeArgs = @("-f", "docker-compose.base.yml", "-f", "docker-compose.prod.yml")
}

# ============================================================
# Step 3: Build & Start
# ============================================================
Set-Location "$ProjectRoot\deploy"

Write-Host ""
Write-Host "Building and starting containers..."
docker compose @ComposeArgs up -d --build

# ============================================================
# Step 4: Health check loop
# ============================================================
Write-Host ""
Write-Host "Waiting for API to become healthy..."
for ($i = 1; $i -le $MaxRetries; $i++) {
    try {
        $response = Invoke-RestMethod -Uri $HealthUrl -Method Get -TimeoutSec 3
        if ($response.status -eq "ok") {
            Write-Host ""
            Write-Host "=========================================="
            Write-Host "  Financial Research Copilot Ready!"
            Write-Host "=========================================="
            Write-Host ""
            Write-Host "  API:      $ApiUrl"
            Write-Host "  Swagger:  $ApiUrl/docs"
            Write-Host "  UI:       $UiUrl"
            Write-Host ""
            Write-Host "  Status:   docker ps"
            Write-Host "  Logs:     .\scripts\logs.ps1"
            Write-Host "  Stop:     .\scripts\stop.ps1"
            Write-Host ""
            exit 0
        }
    } catch {
        # Retry
    }
    Write-Host "  [$i/$MaxRetries] Waiting..." -NoNewline
    Write-Host "`r" -NoNewline
    Start-Sleep -Seconds $RetryInterval
}

Write-Host ""
Write-Host "=========================================="
Write-Host "  WARNING: API did not become healthy within $($MaxRetries * $RetryInterval)s"
Write-Host "=========================================="
Write-Host "  Check logs: docker compose logs"
Write-Host ""
exit 1