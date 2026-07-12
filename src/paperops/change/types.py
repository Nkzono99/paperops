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


@dataclass(frozen=True)
class ChangeRequest:
    schema_version: int
    reason: str
    operations: tuple[Operation, ...]


def frozen_mapping(value: dict[str, Any]) -> Mapping[str, Any]:
    """Detach the top-level document from the YAML parser's mutable mapping."""
    return MappingProxyType(dict(value))
