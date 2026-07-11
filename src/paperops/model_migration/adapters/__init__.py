"""Protocol and deterministic adapter lookup for the six PaperOps models."""

from __future__ import annotations

from importlib import import_module
from typing import Protocol

from ..types import InventoryItem, MigrationCandidate, MigrationInput


class ModelAdapter(Protocol):
    def inventory(self, migration_input: MigrationInput) -> tuple[InventoryItem, ...]: ...

    def materialize(self, migration_input: MigrationInput) -> MigrationCandidate: ...


_ADAPTER_CLASSES = {
    "research": ("research", "ResearchAdapter"),
    "editorial": ("editorial", "EditorialAdapter"),
    "results_hierarchy": ("editorial", "EditorialAdapter"),
    "manuscript": ("manuscript", "ManuscriptAdapter"),
    "issue": ("issue", "IssueAdapter"),
    "publication": ("publication", "PublicationAdapter"),
}


def adapter_for(model_name: str) -> ModelAdapter:
    try:
        module_name, class_name = _ADAPTER_CLASSES[model_name]
    except KeyError as error:
        raise ValueError(f"unknown model adapter: {model_name}") from error
    module = import_module(f"{__name__}.{module_name}")
    adapter_class = getattr(module, class_name)
    return adapter_class()


__all__ = ["ModelAdapter", "adapter_for"]
