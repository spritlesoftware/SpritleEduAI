#!/usr/bin/env bash
# ./boot.sh (API :8000 + web :5173) | ./boot.sh api | ./boot.sh web (API on :8000, docs at /docs) | ./boot.sh adk (live voice dev UI) | ./boot.sh test | ./boot.sh e2e
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt
command -v ffmpeg >/dev/null || { echo "ffmpeg required: sudo apt install ffmpeg"; exit 1; }
[ -f .env ] || { cp .env.example .env; echo "Created backend/.env - add GEMINI_API_KEY and re-run."; exit 1; }
grep -qE '^GEMINI_API_KEY=.+' .env && ! grep -q 'your-key-here' .env || { echo "Set GEMINI_API_KEY in backend/.env"; exit 1; }
case "${1:-app}" in
  app)  (cd "$ROOT/frontend" && { [ -d node_modules ] || npm install; } && npm run dev) &
        trap 'kill 0' EXIT INT TERM
        .venv/bin/uvicorn api:app --reload --port 8000 --no-access-log ;;
  api)  exec .venv/bin/uvicorn api:app --reload --port 8000 --no-access-log ;;
  web)  cd "$ROOT/frontend" && { [ -d node_modules ] || npm install; } && exec npm run dev ;;
  adk)  exec .venv/bin/adk web . ;;
  test) exec .venv/bin/python -m pytest -q ;;
  e2e)  exec .venv/bin/python e2e.py ;;
esac
