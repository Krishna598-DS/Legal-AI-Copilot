#!/usr/bin/env bash
# Free-tier friendly single-process start (Render / Fly / Railway / local).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${PYTHONPATH:-$ROOT/backend}"
export FRONTEND_DIR="${FRONTEND_DIR:-$ROOT/frontend}"
PORT="${PORT:-8000}"
exec uvicorn src.api.main:app --host 0.0.0.0 --port "$PORT"
