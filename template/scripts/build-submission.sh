#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

_TEX_ENV_ROOT="$ROOT" source "$ROOT/scripts/tex-env.sh"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif [[ -x "$ROOT/.venv/Scripts/python.exe" ]]; then
  PYTHON="$ROOT/.venv/Scripts/python.exe"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="python3.11"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  PYTHON="python"
fi

VENUE="${1:-${PAPEROPS_SUBMISSION_VENUE:-}}"
if [[ -z "$VENUE" ]]; then
  mapfile -t _submission_mains < <(find "$ROOT/submission" -mindepth 2 -maxdepth 2 -name main.tex -print 2>/dev/null | sort)
  if [[ "${#_submission_mains[@]}" -eq 1 ]]; then
    VENUE="$(basename "$(dirname "${_submission_mains[0]}")")"
  else
    echo "submission venue を指定してください: scripts/build-submission.sh <venue>"
    exit 1
  fi
fi

SLOT_DIR="$ROOT/submission/$VENUE"
MAIN_TEX="$SLOT_DIR/main.tex"
BUILD_DIR="$SLOT_DIR/build"

if [[ ! -f "$MAIN_TEX" ]]; then
  echo "`submission/$VENUE/main.tex` が見つかりません。"
  exit 1
fi

mkdir -p "$BUILD_DIR"

"$PYTHON" "$ROOT/scripts/check-tex-structure.py" --root "$ROOT" --main "$MAIN_TEX" --label "投稿版 $VENUE"

run_with_runner() {
  if [[ -n "${PAPEROPS_RUNNER_PREFIX:-}" ]]; then
    # shellcheck disable=SC2086
    $PAPEROPS_RUNNER_PREFIX "$@"
  else
    "$@"
  fi
}

submission_tex_paths() {
  export TEXINPUTS=".///:style//:../../manuscript/en//:../../manuscript/shared/style//:${TEXINPUTS:-}"
  export BIBINPUTS=".///:../../manuscript/shared/bib//:../../refs/bib/curated//:../../refs/bib/imported//:${BIBINPUTS:-}"
  export BSTINPUTS=".///:style//:../../manuscript/shared/style//:${BSTINPUTS:-}"
}

audit_build_log() {
  if [[ -f "$BUILD_DIR/main.log" ]]; then
    "$PYTHON" "$ROOT/scripts/audit-build-log.py" --log "$BUILD_DIR/main.log" --label "投稿版 $VENUE PDF"
  fi
}

latexmk_mode_flag() {
  case "${1:-pdf}" in
    -*)
      printf "%s\n" "$1"
      ;;
    pdf | pdfdvi | dvi | ps | pdfps | pdfxe | pdflua)
      printf -- "-%s\n" "$1"
      ;;
    *)
      printf "%s\n" "-pdf"
      ;;
  esac
}

latexmk_args() {
  local output_dir="$1"
  local mode_flag
  mode_flag="$(latexmk_mode_flag "${PAPEROPS_SUBMISSION_LATEXMK_MODE:-pdf}")"
  LATEXMK_ARGS=(latexmk -interaction=nonstopmode -halt-on-error "$mode_flag")
  if [[ -n "${PAPEROPS_SUBMISSION_LATEX:-}" ]]; then
    LATEXMK_ARGS+=("-latex=${PAPEROPS_SUBMISSION_LATEX}")
  fi
  if [[ -n "${PAPEROPS_SUBMISSION_DVIPDF:-}" ]]; then
    LATEXMK_ARGS+=("-e" "\$dvipdf = \"${PAPEROPS_SUBMISSION_DVIPDF}\";")
  fi
  LATEXMK_ARGS+=("-output-directory=$output_dir" main.tex)
}

run_engine_once() {
  local engine="$1"
  (
    cd "$SLOT_DIR"
    submission_tex_paths
    run_with_runner "$engine" -interaction=nonstopmode -halt-on-error "-output-directory=$BUILD_DIR" main.tex
  )
}

run_direct_engine_build() {
  local engine="$1"
  if ! command -v "$engine" >/dev/null 2>&1; then
    return 1
  fi
  echo "latexmk が見つからないため、投稿版を ${engine} + bibtex の direct-engine fallback でビルドします。"
  run_engine_once "$engine"
  if command -v bibtex >/dev/null 2>&1; then
    (
      cd "$BUILD_DIR"
      run_with_runner bibtex main || true
    )
  else
    echo "bibtex が見つからないため、参考文献処理をスキップします。"
  fi
  run_engine_once "$engine"
  run_engine_once "$engine"
  audit_build_log
  if [[ ! -f "$BUILD_DIR/main.pdf" ]]; then
    echo "direct-engine fallback は完了しましたが、PDF は生成されませんでした。"
    return 1
  fi
  echo "投稿版 PDF を direct-engine fallback で生成しました: $BUILD_DIR/main.pdf"
  return 0
}

try_direct_engine_build() {
  local engines=()
  if [[ -n "${PAPEROPS_SUBMISSION_DIRECT_ENGINE:-}" ]]; then
    engines+=("$PAPEROPS_SUBMISSION_DIRECT_ENGINE")
  else
    engines+=(lualatex xelatex pdflatex)
  fi
  for engine in "${engines[@]}"; do
    if run_direct_engine_build "$engine"; then
      return 0
    fi
  done
  return 1
}

if [[ "${PAPER_TEMPLATE_RUN_LATEX:-0}" == "1" ]]; then
  latexmk_args "$BUILD_DIR"
  if [[ -n "${TEX_DOCKER_IMAGE:-}" ]]; then
    latexmk_args "/work/submission/$VENUE/build"
    docker run --rm -v "$ROOT:/work" -w "/work/submission/$VENUE" \
      "$TEX_DOCKER_IMAGE" \
      env TEXINPUTS=".///:style//:../../manuscript/en//:../../manuscript/shared/style//:" \
          BIBINPUTS=".///:../../manuscript/shared/bib//:../../refs/bib/curated//:../../refs/bib/imported//:" \
          BSTINPUTS=".///:style//:../../manuscript/shared/style//:" \
      "${LATEXMK_ARGS[@]}"
    audit_build_log
  elif command -v latexmk >/dev/null 2>&1; then
    (
      cd "$SLOT_DIR"
      submission_tex_paths
      run_with_runner "${LATEXMK_ARGS[@]}"
    )
    audit_build_log
  else
    if ! try_direct_engine_build; then
      echo "latexmk と direct-engine fallback が見つかりません。tex-env.toml で TeX Live path を設定してください。"
      exit 1
    fi
  fi
else
  echo "PAPER_TEMPLATE_RUN_LATEX=1 が未設定です。投稿版 $VENUE の構造検証を完了しました。"
fi
