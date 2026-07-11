"""Canonical DTO and storage surface for PaperOps 2 P3."""

from __future__ import annotations

from .storage import (
    atomic_write_json,
    canonical_json_bytes,
    compile_paths,
    semantic_hash,
    writer_paths,
)
from .types import (
    AuthoritySnapshot,
    CompileBundle,
    CompileFinding,
    CompilePaths,
    CompileRequest,
    InputSnapshot,
    SectionPlan,
    WriteScope,
    WriterPacket,
    WriterPaths,
)


__all__ = [
    "AuthoritySnapshot",
    "CompileBundle",
    "CompileFinding",
    "CompilePaths",
    "CompileRequest",
    "InputSnapshot",
    "SectionPlan",
    "WriteScope",
    "WriterPacket",
    "WriterPaths",
    "atomic_write_json",
    "canonical_json_bytes",
    "compile_paths",
    "semantic_hash",
    "writer_paths",
]
