"""Immutable public types for typed model changes."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class Operation:
    action: str
    model: str
    record_type: str
    object_id: str
    expected_revision: int | None
    expected_hash: str
    document: Mapping[str, Any] | None
    candidate_revision: int | None = None


@dataclass(frozen=True)
class ChangeRequest:
    schema_version: int
    reason: str
    operations: tuple[Operation, ...]


@dataclass(frozen=True)
class Replacement:
    identity: str
    before_hash: str
    after_hash: str
    content: bytes | None


@dataclass(frozen=True)
class ChangePlan:
    schema_version: int
    change_id: str
    reason: str
    affected_models: tuple[str, ...]
    operations: tuple[Operation, ...]
    replacements: tuple[Replacement, ...]
    base_model_hashes: Mapping[str, str]
    candidate_model_hashes: Mapping[str, str]


def frozen_mapping(value: dict[str, Any]) -> Mapping[str, Any]:
    """Detach the top-level document from the YAML parser's mutable mapping."""
    return MappingProxyType(dict(value))
