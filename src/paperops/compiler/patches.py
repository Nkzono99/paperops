"""Public, raw-text-free DTOs for scoped Writer candidate patches."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .storage import semantic_hash
from .types import (
    CompileFinding,
    _freeze_json,
    _json_compatible,
    _validate_hash,
    _validate_id,
)


@dataclass(frozen=True)
class WriterPatchResult:
    session_id: str
    compile_id: str
    status: str
    applicable: bool
    source_mode: str
    base_manifest_hash: str
    candidate_snapshot_hash: str
    authority: tuple[Mapping[str, Any], ...]
    write_scope: Mapping[str, Any]
    target_files: tuple[Mapping[str, Any], ...]
    changes: tuple[Mapping[str, Any], ...]
    findings: tuple[CompileFinding, ...]
    proposed_dispositions: tuple[Mapping[str, Any], ...] = ()
    introduced_references: tuple[Mapping[str, Any], ...] = ()
    mirror_impacts: tuple[Mapping[str, Any], ...] = ()
    conservation_result: str = "pending"
    compile_bundle_hash: str = ""
    patch_hash: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        _validate_id(self.session_id, "Writer session ID")
        _validate_id(self.compile_id, "compile ID")
        if self.status not in {"ready", "blocked", "replan_required"}:
            raise ValueError("Writer patch status is invalid")
        if type(self.applicable) is not bool:
            raise TypeError("Writer patch applicable must be boolean")
        if self.source_mode not in {"authoritative", "shadow"}:
            raise ValueError("Writer patch source mode is invalid")
        _validate_hash(self.base_manifest_hash, "Writer base manifest hash")
        _validate_hash(self.candidate_snapshot_hash, "Writer candidate snapshot hash")
        if self.patch_hash:
            _validate_hash(self.patch_hash, "Writer patch hash")
        if self.compile_bundle_hash:
            _validate_hash(self.compile_bundle_hash, "Writer compile bundle hash")
        if self.conservation_result not in {"pending", "blocked", "passed"}:
            raise ValueError("Writer patch conservation result is invalid")
        if self.schema_version != 1:
            raise ValueError("unsupported Writer patch schema version")
        for field_name in (
            "authority", "target_files", "changes", "proposed_dispositions",
            "introduced_references", "mirror_impacts",
        ):
            object.__setattr__(
                self,
                field_name,
                tuple(_freeze_json(item) for item in getattr(self, field_name)),
            )
        object.__setattr__(self, "write_scope", _freeze_json(self.write_scope))
        object.__setattr__(self, "findings", tuple(self.findings))

    @property
    def ok(self) -> bool:
        return self.status == "ready" and not any(
            item.severity == "error" for item in self.findings
        )

    def _payload(self) -> dict[str, object]:
        payload = {
            "schema_version": self.schema_version,
            "session_id": self.session_id,
            "compile_id": self.compile_id,
            "status": self.status,
            "applicable": self.applicable,
            "source_mode": self.source_mode,
            "base_manifest_hash": self.base_manifest_hash,
            "candidate_snapshot_hash": self.candidate_snapshot_hash,
            "authority": [_json_compatible(item) for item in self.authority],
            "write_scope": _json_compatible(self.write_scope),
            "target_files": [_json_compatible(item) for item in self.target_files],
            "changes": [_json_compatible(item) for item in self.changes],
            "proposed_dispositions": [
                _json_compatible(item) for item in self.proposed_dispositions
            ],
            "introduced_references": [
                _json_compatible(item) for item in self.introduced_references
            ],
            "mirror_impacts": [
                _json_compatible(item) for item in self.mirror_impacts
            ],
            "conservation_result": self.conservation_result,
            "findings": [item.to_dict() for item in self.findings],
        }
        if self.compile_bundle_hash:
            payload["compile_bundle_hash"] = self.compile_bundle_hash
        return payload

    def to_dict(self) -> dict[str, object]:
        payload = self._payload()
        payload["patch_hash"] = self.patch_hash or semantic_hash(payload)
        return payload


__all__ = ["WriterPatchResult"]
