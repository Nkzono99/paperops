#!/usr/bin/env bash

set -euo pipefail

SOURCE_DIR="template"
TARGET_DIR=""
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --source-dir)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --target-dir)
      TARGET_DIR="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "不明な引数: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$TARGET_DIR" ]]; then
  echo "--target-dir は必須です" >&2
  exit 2
fi

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ソースディレクトリが見つかりません: $SOURCE_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"

RSYNC_ARGS=(
  -a
  --delete
  --exclude
  ".git/"
  --exclude
  ".venv/"
  --exclude
  "dist/"
  --exclude
  ".claude/settings.local.json"
  --exclude
  ".github/workflows/publish-scaffold.yml"
  --exclude
  "notes/session-context.generated.md"
  --exclude
  "manuscript/mirror/reports/latest.md"
  --exclude
  "manuscript/mirror/reports/smoke-check.md"
  --exclude
  "manuscript/shared/build/en/"
  --exclude
  "manuscript/shared/build/ja/"
  --exclude
  "refs/local/locations.toml"
)

if [[ "$DRY_RUN" == "1" ]]; then
  RSYNC_ARGS+=(--dry-run --itemize-changes)
fi

rsync "${RSYNC_ARGS[@]}" "$SOURCE_DIR"/ "$TARGET_DIR"/

if [[ "$DRY_RUN" == "1" ]]; then
  echo "ドライラン完了。"
else
  echo "スキャフォールドを $SOURCE_DIR から $TARGET_DIR に公開しました"
fi
