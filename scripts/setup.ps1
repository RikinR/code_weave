$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Code Weave setup (Windows)"

if (-not (Test-Path "backend\venv")) {
    python -m venv backend\venv
}

& "backend\venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r backend\requirements.txt

if (-not (Test-Path "backend\.env")) {
    Copy-Item backend\.env.example backend\.env
    Write-Host "Created backend\.env — set DB_USER, DB_PASSWORD, GROQ_API_KEY"
}

Push-Location backend
$env:PYTHONPATH = "."
python -c "from infrastructure.db.bootstrap import ensure_db_ready; ensure_db_ready()"
Pop-Location

python -c "import tree_sitter_languages; print('tree-sitter OK')"

if (Get-Command flutter -ErrorAction SilentlyContinue) {
    Push-Location frontend
    flutter pub get
    Pop-Location
}

Write-Host "Setup complete."
Write-Host "API: cd backend; .\venv\Scripts\Activate.ps1; `$env:PYTHONPATH='.'; uvicorn app.server:app --reload --reload-exclude 'data/**' --port 8000"
Write-Host "UI:  cd frontend; flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000"
