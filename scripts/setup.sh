#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Code Weave setup (macOS/Linux)"

if ! command -v python3 >/dev/null; then
  echo "python3 is required"
  exit 1
fi

if [ ! -d backend/venv ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv backend/venv
fi

# shellcheck disable=SC1091
source backend/venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt

if [ ! -f backend/.env ]; then
  cp backend/.env.example backend/.env
  echo "Created backend/.env — set DB_USER, DB_PASSWORD, GROQ_API_KEY"
fi

echo "Initializing database (requires PostgreSQL)..."
cd backend
PYTHONPATH=. python -c "from infrastructure.db.bootstrap import ensure_db_ready; ensure_db_ready()"
cd "$ROOT"

echo "Verifying tree-sitter..."
PYTHONPATH=backend python -c "import tree_sitter_languages; print('tree-sitter OK')"

if command -v flutter >/dev/null; then
  echo "Installing Flutter dependencies..."
  (cd frontend && flutter pub get)
else
  echo "Flutter not found — install Flutter SDK for the web UI"
fi

echo "Setup complete."
echo "Start API:  cd backend && source venv/bin/activate && PYTHONPATH=. uvicorn app.server:app --reload --reload-exclude 'data/**' --host 0.0.0.0 --port 8000"
echo "Start UI:   cd frontend && flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000"
