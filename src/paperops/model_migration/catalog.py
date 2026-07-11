"""Conservation rules connecting legacy inventory to migration candidates."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .types import InventoryItem, MigrationCandidate, MigrationFinding


_DISPOSITIONS = {"mapped", "deferred", "local-only", "unsupported"}


def _identity(item: InventoryItem) -> tuple[str, str, str, str]:
    return item.family, item.legacy_id, item.source_path, item.pointer


def validate_conservation(
    source: Iterable[InventoryItem],
    candidate: MigrationCandidate,
) -> tuple[MigrationFinding, ...]:
    """Require one explicit, lossless disposition for every current source item."""
    current = tuple(source)
    stored: dict[tuple[str, str, str, str], list[InventoryItem]] = defaultdict(list)
    for item in candidate.inventory:
        stored[_identity(item)].append(item)
    target_ids = {document.object_id for document in candidate.documents}
    findings: list[MigrationFinding] = []
    current_identities = {_identity(item) for item in current}
    for item in current:
        identity = _identity(item)
        dispositions = stored.get(identity, [])
        if len(dispositions) != 1:
            findings.append(
                MigrationFinding(
                    "migration.disposition",
                    item.pointer,
                    "legacy field family must have exactly one disposition",
                    source_path=item.source_path,
                )
            )
            if not dispositions:
                continue
        stored_item = dispositions[0]
        if stored_item.source_hash != item.source_hash:
            findings.append(
                MigrationFinding(
                    "migration.source_changed",
                    item.pointer,
                    "legacy source changed after the candidate inventory was captured",
                    source_path=item.source_path,
                )
            )
        disposition = stored_item.disposition
        if disposition not in _DISPOSITIONS:
            findings.append(
                MigrationFinding(
                    "migration.disposition",
                    item.pointer,
                    f"unknown disposition `{disposition}`",
                    source_path=item.source_path,
                )
            )
        elif disposition == "mapped":
            if not stored_item.target_id or stored_item.target_id not in target_ids:
                findings.append(
                    MigrationFinding(
                        "migration.unmapped",
                        item.pointer,
                        "mapped legacy field does not name an emitted candidate object",
                        source_path=item.source_path,
                    )
                )
        elif disposition == "unsupported":
            findings.append(
                MigrationFinding(
                    "migration.unsupported",
                    item.pointer,
                    "legacy field is not supported by the deterministic adapter",
                    source_path=item.source_path,
                )
            )
        elif disposition == "deferred":
            if not stored_item.reason or not stored_item.followup_phase:
                findings.append(
                    MigrationFinding(
                        "migration.disposition",
                        item.pointer,
                        "deferred disposition requires a reason and follow-up phase",
                        source_path=item.source_path,
                    )
                )
        elif disposition == "local-only":
            if not stored_item.family.startswith("confidential.") or not stored_item.reason:
                findings.append(
                    MigrationFinding(
                        "migration.disposition",
                        item.pointer,
                        "local-only is restricted to confidential families and requires a reason",
                        source_path=item.source_path,
                    )
                )
    for identity, items in stored.items():
        if identity not in current_identities:
            item = items[0]
            findings.append(
                MigrationFinding(
                    "migration.source_changed",
                    item.pointer,
                    "legacy field recorded by the candidate no longer exists",
                    source_path=item.source_path,
                )
            )
    unique: dict[tuple[str, str, str, str, str], MigrationFinding] = {}
    for finding in findings:
        key = (
            finding.code,
            finding.source_path,
            finding.pointer,
            finding.message,
            finding.severity,
        )
        unique.setdefault(key, finding)
    return tuple(unique.values())
