"""Canonical DTO and storage surface for PaperOps 2 P3."""

from __future__ import annotations

from .contracts import (
    ContractLayerSnapshot,
    ResolvedContract,
    resolve_section_contract,
)
from .bundles import (
    BundleVerificationError,
    CompileCacheStatus,
    CompileResult,
    VerifiedBundle,
    inspect_compile,
    load_verified_bundle,
    prepare_bundle,
)
from .compare import CompileComparison, compare_bundles
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
from .requests import CompileRequestError, resolve_compile_request
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
    "BundleVerificationError",
    "CompileCacheStatus",
    "CompileBundle",
    "CompileBundleCandidate",
    "CompileContractSnapshot",
    "CompileComparison",
    "CompileFinding",
    "CompilePaths",
    "CompileRequest",
    "CompileRequestError",
    "CompileResult",
    "ContractLayerSnapshot",
    "InputSnapshot",
    "ManuscriptSnapshot",
    "MirrorFilePairSnapshot",
    "MirrorFreshnessFact",
    "PrivacyHit",
    "ResolvedContract",
    "SectionPlan",
    "TerminologyRule",
    "VerifiedBundle",
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
    "compare_bundles",
    "contains_private_material",
    "materialize_compile",
    "inspect_compile",
    "load_verified_bundle",
    "parse_tex_bytes",
    "resolve_section_contract",
    "resolve_compile_request",
    "redact_private_material",
    "scan_manuscript",
    "scan_private_material",
    "prepare_bundle",
    "semantic_hash",
    "writer_paths",
]
