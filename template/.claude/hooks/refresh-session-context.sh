#!/usr/bin/env bash

set -euo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "$0")/../.." && pwd)}"
python3 "$ROOT/scripts/collect-note-context.py" --root "$ROOT"
