#!/usr/bin/env bash

set -euo pipefail

ROOT="${1:-$(pwd)}"

try_python() {
  local candidate="$1"
  if [[ -x "$candidate" ]] || command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' >/dev/null 2>&1; then
      command -v "$candidate" 2>/dev/null || printf "%s\n" "$candidate"
      return 0
    fi
  fi
  return 1
}

candidates=(
  "$ROOT/.venv/bin/python"
  "$ROOT/.venv/Scripts/python.exe"
  "python3.11"
  "python3"
  "python"
)

for candidate in "${candidates[@]}"; do
  if try_python "$candidate"; then
    exit 0
  fi
done

printf "%s\n" "error: paperops requires Python 3.11 or newer." >&2
printf "%s\n" "hint: install python3.11, create .venv with Python 3.11+, or set PYTHON to a compatible interpreter." >&2
exit 1
