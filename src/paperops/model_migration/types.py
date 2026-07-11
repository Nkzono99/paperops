"""Immutable domain values shared by migration adapters and transactions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MigrationFinding:
    code: str
    pointer: str
    message: str
    severity: str = "error"
    source_path: str = ""


@dataclass(frozen=True)
class InventoryItem:
    family: str
    legacy_id: str
    source_path: str
    pointer: str
    source_hash: str
    disposition: str
    target_id: str = ""
    reason: str = ""
    followup_phase: str = ""


@dataclass(frozen=True)
class CandidateDocument:
    relative_path: str
    object_id: str
    semantic_hash: str
    content: bytes = b""


@dataclass(frozen=True)
class MigrationInput:
    root: Path
    model_name: str
    source_paths: tuple[Path, ...]


@dataclass(frozen=True)
class MigrationCandidate:
    model_name: str
    documents: tuple[CandidateDocument, ...]
    inventory: tuple[InventoryItem, ...]
    findings: tuple[MigrationFinding, ...]


@dataclass(frozen=True)
class MigrationReport:
    schema_version: int
    transaction_id: str
    model_name: str
    adapter_version: int
    inventory: tuple[InventoryItem, ...]
    candidates: tuple[CandidateDocument, ...]
    findings: tuple[MigrationFinding, ...]


@dataclass(frozen=True)
class TransactionPaths:
    transaction_id: str
    migration_dir: Path
    candidate_dir: Path
    journal_path: Path
    report_json_path: Path
    report_markdown_path: Path
    snapshot_dir: Path
    snapshot_manifest_path: Path
