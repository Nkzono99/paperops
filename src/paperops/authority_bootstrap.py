"""Authority initialization for a newly staged PaperOps project."""

from __future__ import annotations

from pathlib import Path

from paperops.cli.manifest import as_table, read_manifest, write_manifest_data_atomic
from paperops.model_state import HASH_PATTERN, MODEL_NAMES
from paperops.model_validation import run_model_validation


def _write_authority_manifest(
    root: Path,
    *,
    model_mode: str,
    workflow_mode: str,
    hashes: dict[str, str],
) -> None:
    manifest_path = root / ".pops" / "manifest.toml"
    manifest = read_manifest(manifest_path)
    merged = dict(manifest)
    merged["models"] = {
        name: {
            "mode": model_mode,
            "current_hash": hashes.get(name, ""),
            "last_shadow_transaction": "",
            "last_adopt_transaction": "",
        }
        for name in MODEL_NAMES
    }
    workflow = as_table(manifest.get("workflow"))
    workflow["mode"] = workflow_mode
    workflow.setdefault("last_shadow_migration", "")
    workflow.setdefault("last_adopt_transaction", "")
    merged["workflow"] = workflow
    write_manifest_data_atomic(manifest_path, merged)


def bootstrap_v2_authority(root: Path) -> dict[str, str]:
    """Validate starter models and atomically make typed state authoritative."""
    result = run_model_validation(root, "all", phase="all", strict=False)
    if not result.ok:
        codes = ", ".join(finding.code for finding in result.findings)
        raise ValueError(f"starter model validation failed: {codes}")
    hashes: dict[str, str] = {}
    for name in MODEL_NAMES:
        digest = result.hashes.get(name, "")
        if HASH_PATTERN.fullmatch(digest) is None:
            raise ValueError(f"starter model `{name}` has no canonical hash")
        hashes[name] = digest

    _write_authority_manifest(
        root,
        model_mode="v2-authoritative",
        workflow_mode="v2-authoritative",
        hashes=hashes,
    )
    return hashes


def bootstrap_legacy_authority(root: Path) -> None:
    """Record an explicit legacy authority choice for a new project."""
    _write_authority_manifest(
        root,
        model_mode="legacy-authoritative",
        workflow_mode="legacy",
        hashes={},
    )
