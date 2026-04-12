#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LANG_DIR="$ROOT/manuscript/en"
BUILD_DIR="$ROOT/manuscript/shared/build/en"
MAIN_TEX="$LANG_DIR/main.tex"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="python3.11"
else
  PYTHON="python3"
fi

mkdir -p "$BUILD_DIR"

"$PYTHON" - <<'PY' "$MAIN_TEX"
from pathlib import Path
import re
import sys

main_tex = Path(sys.argv[1])
text = main_tex.read_text(encoding="utf-8")
pattern = re.compile(r"\\input\{(?P<target>[^}]+)\}")
missing = []
for match in pattern.finditer(text):
    target = (main_tex.parent / f"{match.group('target')}.tex").resolve()
    if not target.exists():
        missing.append(str(target))

if missing:
    print("missing inputs:")
    for item in missing:
        print(f"  - {item}")
    raise SystemExit(1)

print(f"validated inputs for {main_tex}")
PY

if [[ "${PAPER_TEMPLATE_RUN_LATEX:-0}" == "1" ]] && command -v latexmk >/dev/null 2>&1; then
  (
    cd "$LANG_DIR"
    export TEXINPUTS="../shared/style//:"
    latexmk -interaction=nonstopmode -halt-on-error -pdf -output-directory="$BUILD_DIR" main.tex
  )
else
  echo "latexmk unavailable or disabled; completed structural validation for en manuscript."
fi
