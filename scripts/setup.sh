#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Code Weave setup (macOS / Linux)"

if ! command -v python3 >/dev/null; then
  echo "Error: python3 is required (Python 3.11+)."
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Error: Python 3.11+ is required ($(python3 --version 2>/dev/null || echo 'unknown version'))."
  exit 1
fi

if [ ! -d backend/venv ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv backend/venv
fi

# shellcheck source=/dev/null
source backend/venv/bin/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env from backend/.env.example"
fi

env_needs_config() {
  grep -qE 'your_db_user|your_db_password|your_groq_api_key' backend/.env 2>/dev/null
}

if env_needs_config; then
  echo ""
  echo "Configure backend/.env before database bootstrap:"
  echo "  DB_USER, DB_PASSWORD, GROQ_API_KEY (and DB_HOST/DB_PORT/DB_NAME if not using defaults)"
  echo ""
  echo "Skipping database bootstrap until .env is configured."
  echo "After editing .env, run:"
  echo "  cd backend && source venv/bin/activate && PYTHONPATH=. python -c \"from infrastructure.db.bootstrap import ensure_db_ready; ensure_db_ready()\""
else
  echo "Initializing database (requires PostgreSQL running)..."
  (
    cd backend
    PYTHONPATH=. python -c "from infrastructure.db.bootstrap import ensure_db_ready; ensure_db_ready()"
  )
fi

echo "Verifying tree-sitter..."
python -c "import tree_sitter_languages; print('tree-sitter OK')"

if command -v flutter >/dev/null; then
  echo "Installing Flutter dependencies..."
  (cd frontend && flutter pub get)
else
  echo "Flutter not found — install the Flutter SDK (web target) for the UI."
fi

echo ""
echo "Setup complete."
echo ""
echo "Terminal 1 — API:"
echo "  cd backend && source venv/bin/activate && PYTHONPATH=. uvicorn app.server:app --reload --reload-exclude 'data/**' --host 0.0.0.0 --port 8000"
echo ""
echo "Terminal 2 — Web UI:"
echo "  cd frontend && flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000"
echo ""
echo "API docs: http://127.0.0.1:8000/docs"
