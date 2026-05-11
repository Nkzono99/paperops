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
if [[ -d "$ROOT/manuscript/shared/figures/generated" ]]; then
    cp -R "$ROOT/manuscript/shared/figures/generated" "$DEST/manuscript/shared/figures/generated"
fi

cat >"$DEST/README.md" <<'EOF'
# arXiv エクスポートバンドル

このディレクトリは `scripts/export-arxiv.sh` によって作成されました。
投稿前に内容を確認し、不要なスターターアセットを削除してください。
投稿先固有の最終 TeX は通常 `submission/<venue>/` で管理し、この export は英語ミラー原稿の軽量な確認用バンドルとして扱ってください。
EOF

echo "エクスポートバンドルを $DEST に準備しました"
