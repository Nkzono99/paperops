#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# tex-env.toml があれば PATH/TEXINPUTS を設定
_TEX_ENV_ROOT="$ROOT" source "$ROOT/scripts/tex-env.sh"

LANG_DIR="$ROOT/manuscript/en"
BUILD_DIR="$ROOT/manuscript/shared/build/en"
MAIN_TEX="$LANG_DIR/main.tex"

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

mkdir -p "$BUILD_DIR"

"$PYTHON" "$ROOT/scripts/check-tex-structure.py" --root "$ROOT" --main "$MAIN_TEX" --label "英語原稿"

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
  mode_flag="$(latexmk_mode_flag "${PAPEROPS_EN_LATEXMK_MODE:-pdf}")"
  LATEXMK_ARGS=(latexmk -interaction=nonstopmode -halt-on-error "$mode_flag")
  if [[ -n "${PAPEROPS_EN_LATEX:-}" ]]; then
    LATEXMK_ARGS+=("-latex=${PAPEROPS_EN_LATEX}")
  fi
  if [[ -n "${PAPEROPS_EN_DVIPDF:-}" ]]; then
    LATEXMK_ARGS+=("-e" "\$dvipdf = \"${PAPEROPS_EN_DVIPDF}\";")
  fi
  LATEXMK_ARGS+=("-output-directory=$output_dir" main.tex)
}

run_engine_once() {
  local engine="$1"
  (
    cd "$LANG_DIR"
    export TEXINPUTS="../shared/style//:${TEXINPUTS:-}"
    export BIBINPUTS="../shared/bib//:${BIBINPUTS:-}"
    export BSTINPUTS="../shared/style//:${BSTINPUTS:-}"
    "$engine" -interaction=nonstopmode -halt-on-error "-output-directory=$BUILD_DIR" main.tex
  )
}

run_direct_engine_build() {
  local engine="$1"
  if ! command -v "$engine" >/dev/null 2>&1; then
    return 1
  fi
  echo "latexmk が見つからないため、${engine} + bibtex の direct-engine fallback を実行します。"
  run_engine_once "$engine"
  if command -v bibtex >/dev/null 2>&1; then
    (
      cd "$BUILD_DIR"
      bibtex main || true
    )
  else
    echo "bibtex が見つからないため、参考文献処理をスキップします。"
  fi
  run_engine_once "$engine"
  run_engine_once "$engine"
  if [[ -f "$BUILD_DIR/main.log" ]] && grep -q "Missing character" "$BUILD_DIR/main.log"; then
    echo "PDF 生成ログに Missing character が含まれています。font / engine 設定を確認してください。"
    return 1
  fi
  if [[ ! -f "$BUILD_DIR/main.pdf" ]]; then
    echo "direct-engine fallback は完了しましたが、PDF は生成されませんでした。"
    return 1
  fi
  echo "英語 PDF を direct-engine fallback で生成しました: $BUILD_DIR/main.pdf"
  return 0
}

try_direct_engine_build() {
  local engines=()
  if [[ -n "${PAPEROPS_EN_DIRECT_ENGINE:-}" ]]; then
    engines+=("$PAPEROPS_EN_DIRECT_ENGINE")
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
    latexmk_args "/work/manuscript/shared/build/en"
    docker run --rm -v "$ROOT:/work" -w /work/manuscript/en \
      "$TEX_DOCKER_IMAGE" \
      env TEXINPUTS="../shared/style//:" BIBINPUTS="../shared/bib//:" BSTINPUTS="../shared/style//:" \
      "${LATEXMK_ARGS[@]}"
  elif command -v latexmk >/dev/null 2>&1; then
    (
      cd "$LANG_DIR"
      export TEXINPUTS="../shared/style//:${TEXINPUTS:-}"
      export BIBINPUTS="../shared/bib//:${BIBINPUTS:-}"
      export BSTINPUTS="../shared/style//:${BSTINPUTS:-}"
      "${LATEXMK_ARGS[@]}"
    )
  else
    if ! try_direct_engine_build; then
      echo "latexmk と direct-engine fallback が見つかりません。tex-env.toml で TeX Live パスを設定するか、Docker イメージを指定してください。"
      echo "PDF は未生成です。英語原稿の構造検証だけを完了しました。"
      exit 1
    fi
  fi
else
  echo "PAPER_TEMPLATE_RUN_LATEX=1 が未設定です。英語原稿の構造検証を完了しました。"
fi
