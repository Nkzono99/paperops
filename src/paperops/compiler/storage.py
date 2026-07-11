"""Canonical JSON and confined generated-state paths for the P3 compiler."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .types import CompilePaths, WriterPaths, _json_compatible, _validate_id


def canonical_json_bytes(value: object) -> bytes:
    """Serialize a JSON value deterministically as UTF-8 with a final newline."""
    compatible = _json_compatible(value)
    rendered = json.dumps(
        compatible,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return (rendered + "\n").encode("utf-8")


def semantic_hash(value: object) -> str:
    """Hash the canonical JSON bytes, including their canonical final newline."""
    return f"sha256:{hashlib.sha256(canonical_json_bytes(value)).hexdigest()}"


def _project_root(root: str | Path) -> Path:
    return Path(root).expanduser().absolute()


def _require_confined(candidate: Path, parent: Path) -> None:
    try:
        candidate.relative_to(parent)
    except ValueError as error:
        raise ValueError(f"generated path escapes {parent.name} state") from error


def compile_paths(root: str | Path, compile_id: str) -> CompilePaths:
    """Return paths below ``.paperops/compile/<compile-id>`` without creating them."""
    _validate_id(compile_id, "compile ID")
    project = _project_root(root)
    state_root = project / ".paperops" / "compile"
    compile_dir = state_root / compile_id
    _require_confined(compile_dir, state_root)
    context_dir = compile_dir / "context"
    return CompilePaths(
        compile_id=compile_id,
        compile_dir=compile_dir,
        bundle_path=compile_dir / "bundle.json",
        report_path=compile_dir / "report.json",
        context_dir=context_dir,
        global_context_path=context_dir / "global.json",
        plans_dir=compile_dir / "plans",
        packets_dir=compile_dir / "packets",
    )


def writer_paths(root: str | Path, session_id: str) -> WriterPaths:
    """Return paths below ``.paperops/writer/<session-id>`` without creating them."""
    _validate_id(session_id, "Writer session ID")
    project = _project_root(root)
    state_root = project / ".paperops" / "writer"
    writer_dir = state_root / session_id
    _require_confined(writer_dir, state_root)
    return WriterPaths(
        session_id=session_id,
        writer_dir=writer_dir,
        workspace_dir=writer_dir / "workspace",
        base_manifest_path=writer_dir / "base-manifest.json",
        patch_path=writer_dir / "patch.json",
        report_path=writer_dir / "report.json",
        journal_path=writer_dir / "journal.json",
    )


def atomic_write_json(path: str | Path, value: Any) -> None:
    """Write canonical JSON through an fsynced same-directory temporary file."""
    target = Path(path)
    content = canonical_json_bytes(value)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor = -1
    temporary_path: Path | None = None
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.tmp-",
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


__all__ = [
    "atomic_write_json",
    "canonical_json_bytes",
    "compile_paths",
    "semantic_hash",
    "writer_paths",
]
