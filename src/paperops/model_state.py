"""CLI-owned authority state for the six PaperOps models."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from paperops.cli.manifest import (
    as_table,
    read_manifest,
    write_manifest_data_atomic,
)


MODEL_NAMES = (
    "research",
    "editorial",
    "results_hierarchy",
    "manuscript",
    "issue",
    "publication",
)
AUTHORITY_MODES = (
    "legacy-authoritative",
    "shadow-compare",
    "v2-authoritative",
)
HASH_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
TRANSACTION_PATTERN = re.compile(r"^model-[A-Za-z0-9][A-Za-z0-9._-]*$")


class ModelStateError(ValueError):
    """The manifest's model authority state is not safe to use."""


@dataclass(frozen=True)
class ModelAuthorityState:
    model_name: str
    mode: str = "legacy-authoritative"
    current_hash: str = ""
    last_shadow_transaction: str = ""
    last_adopt_transaction: str = ""
    origin: str = ""


def _validate_state(name: str, state: ModelAuthorityState) -> None:
    if name not in MODEL_NAMES or state.model_name != name:
        raise ModelStateError(f"state.model: unknown or mismatched model `{name}`")
    if state.mode not in AUTHORITY_MODES:
        raise ModelStateError(f"state.mode: unsupported mode `{state.mode}`")
    if state.current_hash and HASH_PATTERN.fullmatch(state.current_hash) is None:
        raise ModelStateError("state.hash: current_hash must be sha256:<64 lowercase hex>")
    for field_name, value in (
        ("last_shadow_transaction", state.last_shadow_transaction),
        ("last_adopt_transaction", state.last_adopt_transaction),
    ):
        if value and TRANSACTION_PATTERN.fullmatch(value) is None:
            raise ModelStateError(
                f"state.transaction: {field_name} is not a safe transaction ID"
            )
    if state.origin not in {"", "init-v2"}:
        raise ModelStateError(f"state.origin: unsupported origin `{state.origin}`")
    if state.origin == "init-v2" and (
        state.mode != "v2-authoritative"
        or not state.current_hash
        or state.last_shadow_transaction
        or state.last_adopt_transaction
    ):
        raise ModelStateError(
            "state.origin: init-v2 requires v2 mode, a hash, and no migration transaction"
        )


def _state_from_table(name: str, value: object) -> ModelAuthorityState:
    table = as_table(value)
    known = {
        "mode",
        "current_hash",
        "last_shadow_transaction",
        "last_adopt_transaction",
        "origin",
    }
    unknown = sorted(set(table) - known)
    if unknown:
        raise ModelStateError(
            f"state.field: models.{name} has unknown fields: {', '.join(unknown)}"
        )
    state = ModelAuthorityState(
        model_name=name,
        mode=table.get("mode", "legacy-authoritative"),
        current_hash=table.get("current_hash", ""),
        last_shadow_transaction=table.get("last_shadow_transaction", ""),
        last_adopt_transaction=table.get("last_adopt_transaction", ""),
        origin=table.get("origin", ""),
    )
    if not all(
        isinstance(value, str)
        for value in (
            state.mode,
            state.current_hash,
            state.last_shadow_transaction,
            state.last_adopt_transaction,
            state.origin,
        )
    ):
        raise ModelStateError(f"state.type: models.{name} values must be strings")
    _validate_state(name, state)
    return state


def read_model_states(root: Path) -> dict[str, ModelAuthorityState]:
    manifest = read_manifest(root / ".pops" / "manifest.toml")
    raw_models = as_table(manifest.get("models"))
    unknown = sorted(set(raw_models) - set(MODEL_NAMES))
    if unknown:
        raise ModelStateError(
            f"state.model: unknown models in manifest: {', '.join(unknown)}"
        )
    return {
        name: _state_from_table(name, raw_models.get(name))
        for name in MODEL_NAMES
    }


def write_model_states(
    root: Path,
    states: Mapping[str, ModelAuthorityState],
) -> None:
    if set(states) != set(MODEL_NAMES):
        missing = sorted(set(MODEL_NAMES) - set(states))
        unknown = sorted(set(states) - set(MODEL_NAMES))
        raise ModelStateError(
            f"state.model: exact model set required; missing={missing}, unknown={unknown}"
        )
    models: dict[str, dict[str, str]] = {}
    for name in MODEL_NAMES:
        state = states[name]
        _validate_state(name, state)
        models[name] = {
            "mode": state.mode,
            "current_hash": state.current_hash,
            "last_shadow_transaction": state.last_shadow_transaction,
            "last_adopt_transaction": state.last_adopt_transaction,
            "origin": state.origin,
        }
    path = root / ".pops" / "manifest.toml"
    manifest = read_manifest(path)
    merged = dict(manifest)
    merged["models"] = models
    write_manifest_data_atomic(path, merged)


def manifest_bytes(root: Path) -> bytes | None:
    path = root / ".pops" / "manifest.toml"
    return path.read_bytes() if path.exists() else None
