#!/usr/bin/env bash

set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="python3.11"
else
  PYTHON="python3"
fi

"$PYTHON" "$ROOT/scripts/mirror-check.py" \
  --root "$ROOT/manuscript" \
  --report "$ROOT/manuscript/mirror/reports/latest.md"
