# SafeGuard — Quick Start
# Run this PowerShell script to set up and launch the project

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Definition

function Banner($msg) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  $msg" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
}

# ── Step 1: Python venv ───────────────────────────────────────────────────────
Banner "Step 1: Setting up Python virtual environment"
if (-not (Test-Path "$Root\.venv")) {
    python -m venv "$Root\.venv"
}
& "$Root\.venv\Scripts\Activate.ps1"

# ── Step 2: Install dependencies ──────────────────────────────────────────────
Banner "Step 2: Installing Python dependencies"
pip install -r "$Root\data-science\requirements.txt" --quiet
pip install -r "$Root\backend\requirements.txt" --quiet
Write-Host "Dependencies installed." -ForegroundColor Green

# ── Step 3: Generate dataset ──────────────────────────────────────────────────
Banner "Step 3: Generating synthetic accident dataset"
python "$Root\data-science\src\generate_dataset.py"

# ── Step 4: Preprocess ────────────────────────────────────────────────────────
Banner "Step 4: Running data preprocessing"
python "$Root\data-science\src\preprocess.py"

# ── Step 5: Hotspot detection ─────────────────────────────────────────────────
Banner "Step 5: Running DBSCAN hotspot detection"
python "$Root\data-science\src\hotspot.py"

# ── Step 6: Train ML model ────────────────────────────────────────────────────
Banner "Step 6: Training ML risk model"
python "$Root\data-science\src\train.py"

# ── Step 7: Copy .env ─────────────────────────────────────────────────────────
Banner "Step 7: Setting up environment config"
if (-not (Test-Path "$Root\.env")) {
    Copy-Item "$Root\.env.example" "$Root\.env"
    Write-Host ".env created from .env.example — edit API keys if needed." -ForegroundColor Yellow
} else {
    Write-Host ".env already exists." -ForegroundColor Green
}

# ── Step 8: Start backend ─────────────────────────────────────────────────────
Banner "Step 8: Starting FastAPI backend"
Write-Host "Backend will run at http://localhost:8000" -ForegroundColor Green
Write-Host "API docs at    http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""
Write-Host "To start the Streamlit dashboard in another terminal:" -ForegroundColor Yellow
Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
Write-Host "  streamlit run dashboard\app.py" -ForegroundColor Yellow
Write-Host ""
Start-Process powershell -ArgumentList "-NoExit", "-Command", "& '$Root\.venv\Scripts\Activate.ps1'; uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000"
