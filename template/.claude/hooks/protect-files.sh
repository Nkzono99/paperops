#!/usr/bin/env bash

set -euo pipefail

INPUT="$(cat)"

FILE_PATH="$(python3 - <<'PY' "$INPUT"
import json
import sys

payload = json.loads(sys.argv[1] or "{}")
tool_input = payload.get("tool_input", {})
print(tool_input.get("file_path") or tool_input.get("path") or "")
PY
)"

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

PROTECTED_PATTERNS=(
  "manuscript/shared/figures/generated/"
  "refs/local/locations.toml"
)

for pattern in "${PROTECTED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    echo "Blocked edit to protected path: $FILE_PATH" >&2
    echo "Use source files, local overrides, or explicit human action instead." >&2
    exit 2
  fi
done

if [[ "$FILE_PATH" == *"manuscript/shared/style/journal.cls"* ]] && [[ "${ALLOW_JOURNAL_CLASS_EDIT:-0}" != "1" ]]; then
  echo "Blocked edit to manuscript/shared/style/journal.cls without ALLOW_JOURNAL_CLASS_EDIT=1." >&2
  exit 2
fi

exit 0
