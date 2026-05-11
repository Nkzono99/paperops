#!/usr/bin/env bash

# tex-env.sh — tex-env.toml から TeX 環境を設定する共通ヘルパー。
# ビルドスクリプトから source して使う。
# tex-env.toml がなければ何もせず、従来通り PATH から探すフォールバック。

_TEX_ENV_ROOT="${_TEX_ENV_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
_TEX_ENV_TOML="$_TEX_ENV_ROOT/tex-env.toml"

if [[ ! -f "$_TEX_ENV_TOML" ]]; then
  return 0 2>/dev/null || exit 0
fi

# Python を特定（ビルドスクリプトと同じ優先順）
if [[ -x "$_TEX_ENV_ROOT/.venv/bin/python" ]]; then
  _TEX_ENV_PYTHON="$_TEX_ENV_ROOT/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  _TEX_ENV_PYTHON="python3.11"
else
  _TEX_ENV_PYTHON="python3"
fi

# TOML を解析し、shell eval なしで値を取り込む
_tex_env_vars=$("$_TEX_ENV_PYTHON" - "$_TEX_ENV_TOML" <<'PY'
import sys
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib
from pathlib import Path

config_path = Path(sys.argv[1])
config = tomllib.loads(config_path.read_text(encoding="utf-8"))

if "texlive" in config:
    root = config["texlive"].get("root", "")
    if root:
        root = str(Path(root).expanduser())
        # TeX Live の標準 bin ディレクトリを探す
        bin_dir = Path(root) / "bin"
        if bin_dir.is_dir():
            # アーキテクチャ別サブディレクトリ（例: x86_64-linux）
            arch_dirs = [d for d in bin_dir.iterdir() if d.is_dir()]
            if arch_dirs:
                print(f"TEXLIVE_BIN\t{arch_dirs[0]}")
            else:
                print(f"TEXLIVE_BIN\t{bin_dir}")
        else:
            print(f"TEXLIVE_BIN\t{root}")

if "docker" in config:
    image = config["docker"].get("image", "")
    if image:
        print(f"TEX_DOCKER_IMAGE\t{image}")
PY
)

while IFS=$'\t' read -r _tex_env_key _tex_env_value; do
  case "$_tex_env_key" in
    TEXLIVE_BIN)
      TEXLIVE_BIN="$_tex_env_value"
      ;;
    TEX_DOCKER_IMAGE)
      TEX_DOCKER_IMAGE="$_tex_env_value"
      ;;
  esac
done <<< "$_tex_env_vars"

if [[ -n "${TEXLIVE_BIN:-}" ]]; then
  export PATH="$TEXLIVE_BIN:$PATH"
fi

if [[ -n "${TEX_DOCKER_IMAGE:-}" ]]; then
  export TEX_DOCKER_IMAGE
fi

unset _TEX_ENV_ROOT _TEX_ENV_TOML _TEX_ENV_PYTHON _tex_env_vars _tex_env_key _tex_env_value
