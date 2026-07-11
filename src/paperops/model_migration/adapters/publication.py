"""Publication ledger migration that references but never copies artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from ..types import CandidateDocument, InventoryItem, MigrationCandidate, MigrationFinding, MigrationInput


_LEDGER = Path("_paperops/workflow/submission-ledger.yml")


def _hash(value: Any) -> str:
    normalized = copy.deepcopy(value)
    if isinstance(normalized.get("metadata"), dict):
        normalized["metadata"].pop("updated_at", None)
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(payload).hexdigest()


class PublicationAdapter:
    adapter_version = 1

    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]:
        return self.materialize(migration_input).inventory

    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate:
        root = migration_input.root.absolute()
        path = root / _LEDGER
        findings: list[MigrationFinding] = []
        try:
            raw = path.read_bytes()
            ledger = yaml.safe_load(raw)
        except (OSError, yaml.YAMLError) as error:
            return MigrationCandidate("publication", (), (), (MigrationFinding("migration.missing", "/ledger", f"submission ledger cannot be read: {error}", source_path=_LEDGER.as_posix()),))
        document = ledger.get("migration_publication") if isinstance(ledger, dict) else None
        if not isinstance(document, dict):
            return MigrationCandidate("publication", (), (), (MigrationFinding("migration.unresolved", "/migration_publication", "submission ledger requires an explicit structured publication payload", source_path=_LEDGER.as_posix()),))
        for index, round_state in enumerate(document.get("rounds", [])):
            if not isinstance(round_state, dict) or round_state.get("status") not in {"submitted", "under-review", "resubmitted"}:
                continue
            if round_state.get("immutable") is not True:
                findings.append(MigrationFinding("immutability.submitted_round", f"/rounds/{index}/immutable", "submitted round must be explicitly immutable"))
            for field in ("candidate_hash", "source_commit", "gate_report_ref", "artifact_refs", "snapshot_path", "snapshot_manifest_ref", "snapshot_dependencies", "response_package_refs"):
                if round_state.get(field) in (None, "", []):
                    findings.append(MigrationFinding("migration.unresolved", f"/rounds/{index}/{field}", f"submitted round requires `{field}`"))
        candidate = document.get("current_candidate")
        if isinstance(candidate, dict):
            for request_id in candidate.get("analysis_request_refs", []):
                matches = tuple((root / "_paperops/model/issues/analysis").glob(f"{request_id}.yml"))
                for match in matches:
                    try:
                        request = yaml.safe_load(match.read_text())
                    except (OSError, yaml.YAMLError):
                        continue
                    if isinstance(request, dict) and request.get("status") in {"planned", "predicted", "running", "executed"}:
                        findings.append(MigrationFinding("migration.unresolved", "/current_candidate/analysis_request_refs", f"analysis request `{request_id}` is not reconciled"))
        identity = str(document.get("model_id", "publication"))
        content = (json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
        semantic_hash = _hash(document)
        output = CandidateDocument("_paperops/model/publication/publication-model.yml", identity, semantic_hash, content)
        source_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
        inventory = (InventoryItem("publication.ledger", identity, _LEDGER.as_posix(), "/migration_publication", source_hash, "mapped", identity),)
        return MigrationCandidate("publication", (output,), inventory, tuple(findings))
