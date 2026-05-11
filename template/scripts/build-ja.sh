#!/usr/bin/env bash

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# tex-env.toml があれば PATH/TEXINPUTS を設定
_TEX_ENV_ROOT="$ROOT" source "$ROOT/scripts/tex-env.sh"

LANG_DIR="$ROOT/manuscript/ja"
BUILD_DIR="$ROOT/manuscript/shared/build/ja"
MAIN_TEX="$LANG_DIR/main.tex"

if [[ -x "$ROOT/.venv/bin/python" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PYTHON="python3.11"
else
  PYTHON="python3"
fi

mkdir -p "$BUILD_DIR"

"$PYTHON" "$ROOT/scripts/check-tex-structure.py" --root "$ROOT" --main "$MAIN_TEX" --label "日本語原稿"

if [[ "${PAPER_TEMPLATE_RUN_LATEX:-0}" == "1" ]]; then
  if [[ -n "${TEX_DOCKER_IMAGE:-}" ]]; then
    docker run --rm -v "$ROOT:/work" -w /work/manuscript/ja \
      "$TEX_DOCKER_IMAGE" \
      env TEXINPUTS="../shared/style//:" BIBINPUTS="../shared/bib//:" BSTINPUTS="../shared/style//:" \
      latexmk -interaction=nonstopmode -halt-on-error -pdf \
        -output-directory="/work/manuscript/shared/build/ja" main.tex
  elif command -v latexmk >/dev/null 2>&1; then
    (
      cd "$LANG_DIR"
      export TEXINPUTS="../shared/style//:${TEXINPUTS:-}"
      export BIBINPUTS="../shared/bib//:${BIBINPUTS:-}"
      export BSTINPUTS="../shared/style//:${BSTINPUTS:-}"
      latexmk -interaction=nonstopmode -halt-on-error -pdf -output-directory="$BUILD_DIR" main.tex
    )
  else
    echo "latexmk が見つかりません。tex-env.toml で TeX Live パスを設定するか、Docker イメージを指定してください。"
    echo "日本語原稿の構造検証を完了しました。"
  fi
else
  echo "PAPER_TEMPLATE_RUN_LATEX=1 が未設定です。日本語原稿の構造検証を完了しました。"
fi
