# Code Weave Windows setup. Run from repo root:
#   powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Code Weave setup (Windows)"

function Get-PythonExe {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in @("3.12", "3.11")) {
            try {
                & py "-$ver" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
                if ($LASTEXITCODE -eq 0) {
                    return @{ Launch = "py"; Version = $ver }
                }
            } catch { }
        }
    }
    foreach ($name in @("python3", "python")) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            & $name -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @{ Launch = $name; Version = $null }
            }
        }
    }
    return $null
}

$pyInfo = Get-PythonExe
if (-not $pyInfo) {
    Write-Host "Error: Python 3.11+ is required."
    exit 1
}

if (-not (Test-Path "backend\venv")) {
    Write-Host "Creating Python virtual environment..."
    if ($pyInfo.Version) {
        & $pyInfo.Launch "-$($pyInfo.Version)" -m venv backend\venv
    } else {
        & $pyInfo.Launch -m venv backend\venv
    }
}

$venvPython = Join-Path $Root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment python not found at $venvPython"
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r backend\requirements.txt

if (-not (Test-Path "backend\.env")) {
    Copy-Item backend\.env.example backend\.env
    Write-Host "Created backend\.env from backend\.env.example"
}

function Test-EnvNeedsConfig {
    $content = Get-Content backend\.env -Raw -ErrorAction SilentlyContinue
    return ($content -match "your_db_user|your_db_password|your_groq_api_key")
}

if (Test-EnvNeedsConfig) {
    Write-Host ""
    Write-Host "Configure backend\.env before database bootstrap:"
    Write-Host "  DB_USER, DB_PASSWORD, GROQ_API_KEY (and DB_HOST/DB_PORT/DB_NAME if not using defaults)"
    Write-Host ""
    Write-Host "Skipping database bootstrap until .env is configured."
    Write-Host "After editing .env, run:"
    Write-Host '  cd backend; $env:PYTHONPATH="."; .\venv\Scripts\python.exe -c "from infrastructure.db.bootstrap import ensure_db_ready; ensure_db_ready()"'
} else {
    Write-Host "Initializing database (requires PostgreSQL running)..."
    Push-Location backend
    $env:PYTHONPATH = "."
    & ".\venv\Scripts\python.exe" -c "from infrastructure.db.bootstrap import ensure_db_ready; ensure_db_ready()"
    Pop-Location
}

Write-Host "Verifying tree-sitter..."
& $venvPython -c "import tree_sitter_languages; print('tree-sitter OK')"

if (Get-Command flutter -ErrorAction SilentlyContinue) {
    Write-Host "Installing Flutter dependencies..."
    Push-Location frontend
    flutter pub get
    Pop-Location
} else {
    Write-Host "Flutter not found — install the Flutter SDK (web target) for the UI."
}

Write-Host ""
Write-Host "Setup complete."
Write-Host ""
Write-Host "Terminal 1 — API:"
Write-Host '  cd backend; .\venv\Scripts\Activate.ps1; $env:PYTHONPATH="."; uvicorn app.server:app --reload --reload-exclude "data/**" --host 0.0.0.0 --port 8000'
Write-Host ""
Write-Host "Terminal 2 — Web UI:"
Write-Host "  cd frontend; flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000"
Write-Host ""
Write-Host "API docs: http://127.0.0.1:8000/docs"
Write-Host ""
Write-Host "Note: ingestion job locking uses fcntl on Unix; on Windows locking is best-effort."
