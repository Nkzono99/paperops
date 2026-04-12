#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/dist/arxiv-export"

rm -rf "$DEST"
mkdir -p "$DEST/manuscript/en"
mkdir -p "$DEST/manuscript/shared/bib"
mkdir -p "$DEST/manuscript/shared/style"
mkdir -p "$DEST/manuscript/shared/figures"

cp -R "$ROOT/manuscript/en/." "$DEST/manuscript/en/"
cp -R "$ROOT/manuscript/shared/bib/." "$DEST/manuscript/shared/bib/"
cp -R "$ROOT/manuscript/shared/style/." "$DEST/manuscript/shared/style/"
cp -R "$ROOT/manuscript/shared/figures/generated" "$DEST/manuscript/shared/figures/generated"

cat >"$DEST/README.md" <<'EOF'
# arXiv export bundle

This directory was created by `scripts/export-arxiv.sh`.
Review the contents before submission and remove starter assets that are not needed.
EOF

echo "Prepared export bundle at $DEST"
