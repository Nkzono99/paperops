from __future__ import annotations

import contextlib
import io
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paperops.cli.main import main  # noqa: E402


def copy_template(tmp: str | Path, name: str = "paper-demo") -> Path:
    target = Path(tmp) / name
    shutil.copytree(ROOT / "template", target)
    return target


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def run_python_script(
    script: Path,
    *args: object,
    encoding: str | None = None,
    errors: str | None = None,
) -> subprocess.CompletedProcess[str]:
    kwargs: dict[str, object] = {}
    if encoding is not None:
        kwargs["encoding"] = encoding
    if errors is not None:
        kwargs["errors"] = errors
    return subprocess.run(
        [sys.executable, str(script), *[str(arg) for arg in args]],
        check=False,
        capture_output=True,
        text=True,
        **kwargs,
    )


def make_var_tokens(makefile: str, name: str) -> list[str]:
    lines = makefile.splitlines()
    value_parts: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith(f"{name} ="):
            continue
        value = line.split("=", 1)[1].strip()
        value_parts.append(value.rstrip("\\").strip())
        next_index = index + 1
        while value.endswith("\\") and next_index < len(lines):
            value = lines[next_index].strip()
            value_parts.append(value.rstrip("\\").strip())
            next_index += 1
        break
    value = " ".join(value_parts)
    return value.split()
