#!/usr/bin/env bash

set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
python3 "$ROOT/scripts/mirror-check.py" \
  --root "$ROOT/manuscript" \
  --report "$ROOT/manuscript/mirror/reports/latest.md"
