#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

VENV="$DIR/.venv"
PORT="${1:-8080}"

if [[ ! -d "$VENV" ]]; then
  echo "[setup] Creating virtualenv ..."
  python3 -m venv "$VENV"
fi

source "$VENV/bin/activate"

if ! python -c "import mock_server" 2>/dev/null; then
  echo "[setup] Installing dependencies ..."
  pip install -e ".[dev]" -q
fi

echo "━━━ Mock Server ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  URL:  http://localhost:$PORT/admin/"
echo "  User: admin / admin123"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
mock-server start --port "$PORT"
