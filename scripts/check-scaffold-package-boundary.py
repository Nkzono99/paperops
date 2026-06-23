from __future__ import annotations

import argparse
import fnmatch
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Iterable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paperops.cli.constants import (  # noqa: E402
    EXCLUDED_SCAFFOLD_PATTERNS,
    SCAFFOLD_INCLUDE_EXCEPTIONS,
)


PACKAGE_SCAFFOLD_PREFIX = "paperops/_data/scaffold/"
CANARY_RELS = (
    "notes/session-context.generated.md",
    "_handoff/secret.txt",
    "refs/source-reach/canary/raw/cookie.txt",
    "refs/source-reach/canary/doctor.generated.json",
    "refs/source-reach/canary/capture.generated.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check generated scaffold artifacts do not cross package boundaries."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        help="Optional directory for temporary build output.",
    )
    args = parser.parse_args()

    tmp_root = args.out_dir or Path(tempfile.mkdtemp(prefix="paperops-scaffold-boundary-"))
    tmp_root.mkdir(parents=True, exist_ok=True)
    dist_dir = tmp_root / "dist"
    init_dir = tmp_root / "init" / "paper-demo"

    canaries = [ROOT / "template" / rel for rel in CANARY_RELS]
    previous = {path: path.read_bytes() for path in canaries if path.exists()}
    try:
        for canary in canaries:
            canary.parent.mkdir(parents=True, exist_ok=True)
            canary.write_text(
                "generated canary for scaffold package boundary check\n",
                encoding="utf-8",
            )
        wheel = build_wheel(dist_dir)
        check_wheel_contents(wheel)
        run_from_wheel(wheel, init_dir)
        check_init_contents(init_dir)
    finally:
        for canary in canaries:
            if canary in previous:
                canary.write_bytes(previous[canary])
            else:
                canary.unlink(missing_ok=True)
        if args.out_dir is None:
            shutil.rmtree(tmp_root, ignore_errors=True)

    print("scaffold package boundary: ok")
    return 0


def build_wheel(dist_dir: Path) -> Path:
    dist_dir.mkdir(parents=True, exist_ok=True)
    uv = shutil.which("uv")
    if uv:
        command = [uv, "build", "--wheel", "--out-dir", str(dist_dir)]
    else:
        command = [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(dist_dir),
        ]
    run(command, cwd=ROOT)

    wheels = sorted(dist_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"expected one wheel in {dist_dir}, found {len(wheels)}")
    return wheels[0]


def check_wheel_contents(wheel: Path) -> None:
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())

    blocked = [
        name
        for name in names
        if name.startswith(PACKAGE_SCAFFOLD_PREFIX)
        and is_excluded_package_scaffold_path(name)
    ]
    if blocked:
        formatted = "\n".join(f"  - {name}" for name in sorted(blocked))
        raise SystemExit(
            "excluded scaffold artifacts were bundled in the wheel:\n" + formatted
        )


def run_from_wheel(wheel: Path, init_dir: Path) -> None:
    uvx = shutil.which("uvx")
    if not uvx:
        raise SystemExit("uvx is required to verify wheel-installed pops init")
    run([uvx, "--from", str(wheel), "pops", "init", str(init_dir)], cwd=ROOT)


def check_init_contents(init_dir: Path) -> None:
    blocked = [
        normalize_rel(path.relative_to(init_dir))
        for path in init_dir.rglob("*")
        if is_excluded_scaffold_path(normalize_rel(path.relative_to(init_dir)))
    ]
    if blocked:
        formatted = "\n".join(f"  - {name}" for name in sorted(blocked))
        raise SystemExit(
            "excluded scaffold artifacts were copied by wheel-installed pops init:\n"
            + formatted
        )


def is_excluded_package_scaffold_path(name: str) -> bool:
    rel = name.removeprefix(PACKAGE_SCAFFOLD_PREFIX)
    return is_excluded_scaffold_path(rel)


def is_excluded_scaffold_path(rel: str) -> bool:
    if any(fnmatch.fnmatch(rel, pattern) for pattern in SCAFFOLD_INCLUDE_EXCEPTIONS):
        return False
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDED_SCAFFOLD_PATTERNS)


def normalize_rel(path: Path) -> str:
    return path.as_posix()


def run(command: Iterable[str], *, cwd: Path) -> None:
    result = subprocess.run(
        list(command),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
