#!/usr/bin/env python3
"""Validate registered PaperOps models by phase."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops_editorial import validate_editorial_references, validate_editorial_semantics
from paperops_schema import (
    ModelFinding,
    RegistryEntry,
    SchemaRegistry,
    load_document,
    load_registry,
    semantic_hash,
    validate_document_version,
    validate_schema,
)


MODEL_CHOICES = ("all", "editorial", "results_hierarchy")
PHASE_CHOICES = ("all", "schema", "references", "semantics")


@dataclass
class LoadedModel:
    entry: RegistryEntry
    document: Any | None
    schema_findings: list[ModelFinding]

    @property
    def schema_clean(self) -> bool:
        return self.document is not None and not self.schema_findings


def _error_from_exception(error: Exception, pointer: str) -> ModelFinding:
    message = str(error)
    prefix, separator, detail = message.partition(":")
    if separator and "." in prefix and " " not in prefix:
        return ModelFinding(prefix, pointer, detail.strip())
    return ModelFinding("document.load", pointer, message)


def _load_model(entry: RegistryEntry, document_path: Path) -> LoadedModel:
    try:
        document = load_document(document_path)
        schema = load_document(entry.schema_path)
        validate_document_version(entry, document)
        findings = validate_schema(document, schema)
    except Exception as error:
        return LoadedModel(
            entry=entry,
            document=None,
            schema_findings=[_error_from_exception(error, "/")],
        )
    return LoadedModel(entry=entry, document=document, schema_findings=findings)


def _document_path(
    name: str,
    entry: RegistryEntry,
    *,
    requested_model: str,
    document: Path | None,
    results_document: Path | None,
) -> Path:
    if name == "editorial" and document is not None:
        return document
    if name == "results_hierarchy":
        if results_document is not None:
            return results_document
        if document is not None and requested_model == "results_hierarchy":
            return document
    return entry.default_path


def _prerequisite(model_names: list[str]) -> ModelFinding:
    names = ", ".join(model_names)
    return ModelFinding(
        "phase.prerequisite",
        "/",
        f"schema validation must pass before this phase ({names})",
    )


def _render(findings: list[ModelFinding]) -> None:
    sections = (("Errors", "error"), ("Warnings", "warning"), ("Info", "info"))
    print("# paperops-model-check")
    for heading, severity in sections:
        print(f"\n## {heading}\n")
        selected = [finding for finding in findings if finding.severity == severity]
        if not selected:
            print("- None.")
            continue
        for finding in selected:
            pointer = finding.pointer or "/"
            print(f"- `[{finding.code}] {pointer}`: {finding.message}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--model", choices=MODEL_CHOICES, default="all")
    parser.add_argument("--phase", choices=PHASE_CHOICES, default="all")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--print-hash", action="store_true")
    parser.add_argument("--document", type=Path)
    parser.add_argument("--results-document", type=Path)
    args = parser.parse_args()
    if args.print_hash and args.model == "all":
        parser.error("--print-hash requires one explicit --model")
    return args


def _registry_or_finding(root: Path) -> tuple[SchemaRegistry | None, list[ModelFinding]]:
    try:
        return load_registry(root), []
    except Exception as error:
        return None, [_error_from_exception(error, "/")]


def main() -> int:
    args = _parse_args()
    phase = "all" if args.print_hash else args.phase
    root = args.root.resolve()
    registry, findings = _registry_or_finding(root)
    if registry is None:
        _render(findings)
        return 1

    selected_names = (
        list(registry.entries) if args.model == "all" else [args.model]
    )
    names_to_load = list(selected_names)
    if (
        "editorial" in selected_names
        and phase in ("all", "references")
        and "results_hierarchy" not in names_to_load
    ):
        names_to_load.append("results_hierarchy")

    loaded = {
        name: _load_model(
            registry.entries[name],
            _document_path(
                name,
                registry.entries[name],
                requested_model=args.model,
                document=args.document,
                results_document=args.results_document,
            ),
        )
        for name in names_to_load
    }

    if phase in ("all", "schema"):
        for name in selected_names:
            findings.extend(loaded[name].schema_findings)
    elif phase in ("references", "semantics"):
        prerequisites = list(selected_names)
        if phase == "references" and "editorial" in selected_names:
            prerequisites = list(dict.fromkeys([*prerequisites, "results_hierarchy"]))
        failed = [name for name in prerequisites if not loaded[name].schema_clean]
        if failed:
            findings.append(_prerequisite(failed))

    editorial = loaded.get("editorial")
    results = loaded.get("results_hierarchy")
    if (
        phase in ("all", "references")
        and "editorial" in selected_names
        and editorial is not None
        and results is not None
        and editorial.schema_clean
        and results.schema_clean
    ):
        findings.extend(
            validate_editorial_references(editorial.document, results.document)
        )
    if (
        phase in ("all", "semantics")
        and "editorial" in selected_names
        and editorial is not None
        and editorial.schema_clean
    ):
        findings.extend(
            validate_editorial_semantics(editorial.document, strict=args.strict)
        )

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    failed = bool(errors or ((args.print_hash or args.strict) and warnings))
    if args.print_hash and not failed:
        model = loaded[selected_names[0]]
        if model.schema_clean:
            print(
                semantic_hash(
                    model.document,
                    excluded_paths=model.entry.hash_excluded_paths,
                )
            )
            return 0
        failed = True

    _render(findings)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
