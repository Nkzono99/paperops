"""Canonical DTO and storage surface for PaperOps 2 P3."""

from __future__ import annotations

from .contracts import (
    ContractLayerSnapshot,
    ResolvedContract,
    resolve_section_contract,
)
from .materialize import (
    CompileBundleCandidate,
    CompileContractSnapshot,
    compute_compile_id,
    materialize_compile,
)
from .privacy import (
    PrivacyHit,
    contains_private_material,
    redact_private_material,
    scan_private_material,
)
from .storage import (
    atomic_write_json,
    canonical_json_bytes,
    compile_paths,
    semantic_hash,
    writer_paths,
)
from .tex import (
    AnalysisRequestSnapshot,
    BibliographyFileSnapshot,
    ManuscriptSnapshot,
    MirrorFilePairSnapshot,
    MirrorFreshnessFact,
    TerminologyRule,
    TexBindingResult,
    TexBlockBinding,
    TexFileSnapshot,
    bind_typed_tex_blocks,
    parse_tex_bytes,
    scan_manuscript,
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
    "AnalysisRequestSnapshot",
    "AuthoritySnapshot",
    "BibliographyFileSnapshot",
    "CompileBundle",
    "CompileBundleCandidate",
    "CompileContractSnapshot",
    "CompileFinding",
    "CompilePaths",
    "CompileRequest",
    "ContractLayerSnapshot",
    "InputSnapshot",
    "ManuscriptSnapshot",
    "MirrorFilePairSnapshot",
    "MirrorFreshnessFact",
    "PrivacyHit",
    "ResolvedContract",
    "SectionPlan",
    "TerminologyRule",
    "TexBindingResult",
    "TexBlockBinding",
    "TexFileSnapshot",
    "WriteScope",
    "WriterPacket",
    "WriterPaths",
    "atomic_write_json",
    "bind_typed_tex_blocks",
    "canonical_json_bytes",
    "compile_paths",
    "compute_compile_id",
    "contains_private_material",
    "materialize_compile",
    "parse_tex_bytes",
    "resolve_section_contract",
    "redact_private_material",
    "scan_manuscript",
    "scan_private_material",
    "semantic_hash",
    "writer_paths",
]
