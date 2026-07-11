#!/usr/bin/env python3
"""Validate registered PaperOps models by phase."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath

from paperops_editorial import validate_editorial_references, validate_editorial_semantics
from paperops_models import (
    ModelDocument,
    build_object_catalog,
    dependency_hash,
    load_model_document,
    validate_cross_model_references,
    validate_dependency_state,
    validate_reference_contract_definition,
    validate_issue_semantics,
    validate_manuscript_semantics,
    validate_publication_semantics,
    validate_research_semantics,
)
from paperops_schema import (
    KNOWN_MODEL_VERSIONS,
    ModelFinding,
    RegistryEntry,
    SchemaRegistry,
    load_registry,
    semantic_hash,
)


MODEL_CHOICES = ("all", *KNOWN_MODEL_VERSIONS)
PHASE_CHOICES = ("all", "schema", "references", "semantics", "approvals", "dependencies", "hash")


def _error_from_exception(error: Exception, pointer: str) -> ModelFinding:
    message = str(error)
    prefix, separator, detail = message.partition(":")
    if separator and "." in prefix and " " not in prefix:
        detail = detail.strip()
        if detail.startswith("/") and ":" in detail:
            error_pointer, _, error_detail = detail.partition(":")
            return ModelFinding(prefix, error_pointer, error_detail.strip())
        return ModelFinding(prefix, pointer, detail)
    return ModelFinding("document.load", pointer, message)


def _load_model(
    root: Path,
    entry: RegistryEntry,
    document_path: Path,
    *,
    strict: bool,
) -> ModelDocument:
    return load_model_document(
        root,
        entry,
        document_path=document_path,
        strict=strict,
    )


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


def _unsafe_relative_path(value: str) -> bool:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    return (
        posix.is_absolute()
        or windows.is_absolute()
        or bool(windows.drive)
        or bool(windows.root)
        or ".." in posix.parts
        or ".." in windows.parts
    )


def _embedded_results_path(
    editorial: ModelDocument,
    *,
    root: Path,
    document_override: Path | None,
) -> tuple[Path | None, ModelFinding | None]:
    if not isinstance(editorial.document, dict):
        return None, _prerequisite(["editorial"])
    connection = editorial.document.get("results_hierarchy")
    raw_path = connection.get("document") if isinstance(connection, dict) else None
    if not isinstance(raw_path, str) or not raw_path or _unsafe_relative_path(raw_path):
        return None, ModelFinding(
            "reference.path",
            "/results_hierarchy/document",
            "Results hierarchy document must be a safe relative path",
        )
    base = document_override.resolve().parent if document_override is not None else root
    candidate = (base / raw_path).resolve()
    if not candidate.is_relative_to(base.resolve()):
        return None, ModelFinding(
            "reference.path",
            "/results_hierarchy/document",
            "Results hierarchy document escapes its binding root",
        )
    if not candidate.is_file():
        return None, ModelFinding(
            "reference.document",
            "/results_hierarchy/document",
            f"Results hierarchy document is missing or unreadable: {candidate}",
        )
    return candidate, None


def _hash_model(model: ModelDocument) -> tuple[str | None, ModelFinding | None]:
    if not model.schema_clean:
        return None, None
    try:
        return (
            semantic_hash(
                model.document,
                excluded_paths=model.entry.hash_excluded_paths,
            ),
            None,
        )
    except Exception as error:
        return None, _error_from_exception(error, "/")


def _prerequisite(model_names: list[str]) -> ModelFinding:
    names = ", ".join(model_names)
    return ModelFinding(
        "phase.prerequisite",
        "/",
        f"schema validation must pass before this phase ({names})",
    )


def _is_record_schema_finding(finding: ModelFinding) -> bool:
    return finding.code.startswith(("schema.", "document.", "registry."))


def _catalog_findings_for_phase(
    catalog_findings: tuple[ModelFinding, ...],
    phase: str,
) -> list[ModelFinding]:
    if phase in ("all", "hash"):
        return list(catalog_findings)
    if phase == "schema":
        return [
            finding
            for finding in catalog_findings
            if _is_record_schema_finding(finding)
        ]
    if phase == "references":
        return [
            finding
            for finding in catalog_findings
            if not _is_record_schema_finding(finding)
            and not finding.code.startswith("hash.")
        ]
    return []


def _global_catalog_findings_for_phase(
    catalog_findings: tuple[ModelFinding, ...],
    phase: str,
) -> list[ModelFinding]:
    if phase in ("all", "references", "hash"):
        return list(catalog_findings)
    return []


def _deduplicate_findings(findings: list[ModelFinding]) -> list[ModelFinding]:
    deduplicated: list[ModelFinding] = []
    seen: set[tuple[str, str, str, str]] = set()
    for finding in findings:
        key = (finding.code, finding.pointer, finding.message, finding.severity)
        if key not in seen:
            seen.add(key)
            deduplicated.append(finding)
    return deduplicated


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


def _render_json(
    findings: list[ModelFinding],
    *,
    ok: bool,
    model: str,
    phase: str,
    hashes: dict[str, str] | None = None,
) -> None:
    print(json.dumps(
        {
            "schema_version": 1,
            "ok": ok,
            "model": model,
            "phase": phase,
            "findings": [
                {
                    "code": finding.code,
                    "pointer": finding.pointer or "/",
                    "message": finding.message,
                    "severity": finding.severity,
                }
                for finding in findings
            ],
            "hashes": dict(sorted((hashes or {}).items())),
        },
        ensure_ascii=False,
        sort_keys=True,
    ))


def _render_result(
    args: argparse.Namespace,
    findings: list[ModelFinding],
    *,
    failed: bool,
    phase: str,
    hashes: dict[str, str] | None = None,
) -> int:
    if args.json:
        _render_json(
            findings,
            ok=not failed,
            model=args.model,
            phase=phase,
            hashes=hashes,
        )
    else:
        _render(findings)
    return 1 if failed else 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--model", choices=MODEL_CHOICES, default="all")
    parser.add_argument("--phase", choices=PHASE_CHOICES, default="all")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--print-hash", action="store_true")
    parser.add_argument("--object-id")
    parser.add_argument("--print-dependency-hash")
    parser.add_argument("--document", type=Path)
    parser.add_argument("--results-document", type=Path)
    args = parser.parse_args()
    if args.object_id is not None and not args.print_hash:
        parser.error("--object-id requires --print-hash")
    if args.print_dependency_hash is not None and args.print_hash:
        parser.error("--print-hash and --print-dependency-hash are mutually exclusive")
    if args.print_hash and args.model == "all" and args.object_id is None:
        parser.error("--print-hash requires one explicit --model")
    return args


def _registry_or_finding(root: Path) -> tuple[SchemaRegistry | None, list[ModelFinding]]:
    try:
        return load_registry(root), []
    except Exception as error:
        return None, [_error_from_exception(error, "/")]


def main() -> int:
    args = _parse_args()
    phase = "all" if args.print_hash or args.print_dependency_hash else args.phase
    root = args.root.resolve()
    registry, findings = _registry_or_finding(root)
    if registry is None:
        return _render_result(args, findings, failed=True, phase=phase)
    findings.extend(validate_reference_contract_definition(registry))

    if args.model != "all" and args.model not in registry.entries:
        return _render_result(
            args,
            [
                ModelFinding(
                    "registry.model",
                    "/",
                    f"model `{args.model}` is not registered in this project",
                )
            ],
            failed=True,
            phase=phase,
        )

    selected_names = (
        list(registry.entries) if args.model == "all" else [args.model]
    )
    manuscript_requires_missing_research = (
        "manuscript" in selected_names
        and phase in ("all", "semantics")
        and "research" not in registry.entries
    )
    publication_support_names = ("research", "manuscript", "issue")
    publication_requires_missing_support = (
        "publication" in selected_names
        and phase in ("all", "semantics")
        and any(name not in registry.entries for name in publication_support_names)
    )
    names_to_load = list(selected_names)
    if phase in ("all", "references", "approvals", "dependencies"):
        for graph_name in registry.entries:
            if graph_name not in names_to_load:
                names_to_load.append(graph_name)
    if (
        "editorial" in selected_names
        and phase in ("all", "references")
        and "results_hierarchy" not in names_to_load
    ):
        names_to_load.append("results_hierarchy")
    if (
        "manuscript" in selected_names
        and phase in ("all", "semantics")
        and "research" in registry.entries
        and "research" not in names_to_load
    ):
        names_to_load.append("research")
    if "publication" in selected_names and phase in ("all", "semantics"):
        for support_name in publication_support_names:
            if support_name in registry.entries and support_name not in names_to_load:
                names_to_load.append(support_name)

    loaded: dict[str, ModelDocument] = {}
    if "editorial" in names_to_load:
        loaded["editorial"] = _load_model(
            root,
            registry.entries["editorial"],
            _document_path(
                "editorial",
                registry.entries["editorial"],
                requested_model=args.model,
                document=args.document,
                results_document=args.results_document,
            ),
            strict=args.strict,
        )

    binding_findings: list[ModelFinding] = []
    if "results_hierarchy" in names_to_load:
        results_path: Path | None
        embedded_results = False
        if args.results_document is not None:
            results_path = args.results_document
            if "editorial" in selected_names:
                binding_findings.append(
                    ModelFinding(
                        "reference.document_source",
                        "/results_hierarchy/document",
                        f"using explicit --results-document override: {results_path}",
                        severity="info",
                    )
                )
        elif "editorial" in loaded and loaded["editorial"].schema_clean:
            embedded_results = True
            results_path, binding_error = _embedded_results_path(
                loaded["editorial"],
                root=root,
                document_override=args.document,
            )
            if binding_error is not None:
                binding_findings.append(binding_error)
        else:
            results_path = _document_path(
                "results_hierarchy",
                registry.entries["results_hierarchy"],
                requested_model=args.model,
                document=args.document,
                results_document=args.results_document,
            )
        if results_path is not None:
            loaded_results = _load_model(
                root,
                registry.entries["results_hierarchy"],
                results_path,
                strict=args.strict,
            )
            if (
                embedded_results
                and loaded_results.document is None
                and any(
                    finding.code == "document.load"
                    for finding in loaded_results.schema_findings
                )
            ):
                binding_findings.append(
                    ModelFinding(
                        "reference.document",
                        "/results_hierarchy/document",
                        f"Results hierarchy document is unreadable: {results_path}",
                    )
                )
            else:
                loaded["results_hierarchy"] = loaded_results

    for name in names_to_load:
        if name not in loaded and name != "results_hierarchy":
            loaded[name] = _load_model(
                root,
                registry.entries[name],
                _document_path(
                    name,
                    registry.entries[name],
                    requested_model=args.model,
                    document=args.document,
                    results_document=args.results_document,
                ),
                strict=args.strict,
            )

    if phase in ("all", "schema"):
        for name in selected_names:
            model = loaded.get(name)
            if model is not None:
                findings.extend(model.schema_findings)
                findings.extend(
                    _catalog_findings_for_phase(model.catalog_findings, phase)
                )
        if (
            phase == "all"
            and "editorial" in selected_names
            and "results_hierarchy" not in selected_names
            and "results_hierarchy" in loaded
            and not loaded["results_hierarchy"].schema_clean
        ):
            findings.extend(loaded["results_hierarchy"].schema_findings)
        if manuscript_requires_missing_research:
            findings.append(_prerequisite(["research"]))
        if publication_requires_missing_support:
            findings.append(
                _prerequisite(
                    [name for name in publication_support_names if name not in registry.entries]
                )
            )
        if phase == "all":
            for name, model in loaded.items():
                if name in selected_names:
                    continue
                findings.extend(model.schema_findings)
                findings.extend(
                    _catalog_findings_for_phase(model.catalog_findings, phase)
                )
    elif phase == "hash":
        for name in selected_names:
            model = loaded.get(name)
            if model is None:
                findings.append(_prerequisite([name]))
            else:
                findings.extend(model.schema_findings)
                findings.extend(
                    _catalog_findings_for_phase(model.catalog_findings, phase)
                )
    elif phase in ("references", "semantics", "approvals", "dependencies"):
        prerequisites = list(selected_names)
        if phase == "references" and "editorial" in selected_names:
            prerequisites = list(dict.fromkeys([*prerequisites, "results_hierarchy"]))
        if phase == "semantics" and "manuscript" in selected_names:
            prerequisites = list(dict.fromkeys([*prerequisites, "research"]))
        if phase == "semantics" and "publication" in selected_names:
            prerequisites = list(dict.fromkeys([*prerequisites, *publication_support_names]))
        if phase in ("references", "approvals", "dependencies"):
            prerequisites = list(loaded)
        binding_blocks_results = any(
            finding.severity == "error"
            and finding.code in {"reference.document", "reference.path"}
            for finding in binding_findings
        )
        failed = [
            name
            for name in prerequisites
            if name not in loaded or not loaded[name].schema_clean
            if not (name == "results_hierarchy" and binding_blocks_results)
        ]
        if failed:
            findings.append(_prerequisite(failed))

    supporting_research = (
        "manuscript" in selected_names
        and "research" not in selected_names
        and "research" in loaded
        and phase in ("all", "semantics")
    )
    if supporting_research:
        research_support = loaded["research"]
        if phase == "all":
            findings.extend(research_support.schema_findings)
        findings.extend(research_support.catalog_findings)

    if "publication" in selected_names and phase in ("all", "semantics"):
        for support_name in publication_support_names:
            if support_name in selected_names or support_name not in loaded:
                continue
            support = loaded[support_name]
            if phase == "all":
                findings.extend(support.schema_findings)
            findings.extend(support.catalog_findings)

    if phase in ("all", "references"):
        findings.extend(binding_findings)

    catalog = build_object_catalog(loaded.values())
    research_objects_available = any(
        obj.model_name == "research" for obj in catalog.objects.values()
    )
    findings.extend(_global_catalog_findings_for_phase(catalog.findings, phase))
    if phase == "references":
        for name in selected_names:
            model = loaded.get(name)
            if model is not None:
                findings.extend(
                    _catalog_findings_for_phase(model.catalog_findings, phase)
                )

    if phase in ("all", "references") and not any(
        not model.schema_clean for model in loaded.values()
    ):
        findings.extend(
            validate_cross_model_references(
                catalog,
                defer_empty_editorial_research=not research_objects_available,
            )
        )

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
        if research_objects_available:
            findings = [finding for finding in findings if finding.code != "reference.deferred"]
    if (
        phase in ("all", "semantics")
        and "editorial" in selected_names
        and editorial is not None
        and editorial.schema_clean
    ):
        findings.extend(
            validate_editorial_semantics(editorial.document, strict=args.strict)
        )
    research = loaded.get("research")
    if (
        phase in ("all", "semantics")
        and "research" in selected_names
        and research is not None
        and research.schema_clean
    ):
        findings.extend(validate_research_semantics(catalog))
    manuscript = loaded.get("manuscript")
    if (
        phase in ("all", "semantics")
        and "manuscript" in selected_names
        and manuscript is not None
        and manuscript.schema_clean
        and research is not None
        and research.schema_clean
    ):
        findings.extend(validate_manuscript_semantics(catalog))
    issue = loaded.get("issue")
    if (
        phase in ("all", "semantics")
        and "issue" in selected_names
        and issue is not None
        and issue.schema_clean
    ):
        findings.extend(validate_issue_semantics(catalog))
    publication = loaded.get("publication")
    if (
        phase in ("all", "semantics")
        and "publication" in selected_names
        and publication is not None
        and publication.schema_clean
        and all(
            name in loaded and loaded[name].schema_clean
            for name in publication_support_names
        )
    ):
        findings.extend(validate_publication_semantics(publication.document, catalog))

    if phase in ("all", "dependencies") and not any(
        not model.schema_clean for model in loaded.values()
    ):
        findings.extend(validate_dependency_state(catalog))

    if phase == "approvals":
        approval_findings: list[ModelFinding] = []
        if research is not None and research.schema_clean:
            approval_findings.extend(validate_research_semantics(catalog))
        if manuscript is not None and manuscript.schema_clean and research is not None and research.schema_clean:
            approval_findings.extend(validate_manuscript_semantics(catalog))
        if issue is not None and issue.schema_clean:
            approval_findings.extend(validate_issue_semantics(catalog))
        if publication is not None and publication.schema_clean:
            approval_findings.extend(validate_publication_semantics(publication.document, catalog))
        findings.extend(finding for finding in approval_findings if finding.code.startswith("approval."))

    computed_hashes: dict[str, str] = {}
    if phase in ("all", "hash"):
        for name in selected_names:
            model = loaded.get(name)
            if model is None:
                continue
            digest, hash_finding = _hash_model(model)
            if hash_finding is not None:
                findings.append(hash_finding)
            elif digest is not None:
                computed_hashes[name] = digest

    findings = _deduplicate_findings(findings)
    if any(finding.severity == "error" for finding in findings):
        findings = [
            finding
            for finding in findings
            if finding.code != "reference.document_source"
        ]
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    failed = bool(errors or ((args.print_hash or args.strict) and warnings))
    if args.print_dependency_hash is not None and not failed:
        try:
            digest = dependency_hash(args.print_dependency_hash, catalog)
            computed_hashes[f"dependency:{args.print_dependency_hash}"] = digest
            if not args.json:
                print(digest)
                return 0
        except Exception as error:
            findings.append(_error_from_exception(error, "/object-id"))
            failed = True
    if args.print_hash and not failed:
        digest: str | None
        if args.object_id is not None:
            selected_object = catalog.objects.get(args.object_id)
            digest = selected_object.object_hash if selected_object is not None else None
            if selected_object is None:
                findings.append(
                    ModelFinding(
                        "reference.dangling",
                        "/object-id",
                        f"object `{args.object_id}` is not present in the validated catalog",
                    )
                )
                failed = True
        else:
            digest = computed_hashes.get(selected_names[0])
        if digest is not None:
            computed_hashes[
                args.object_id if args.object_id is not None else selected_names[0]
            ] = digest
            if not args.json:
                print(digest)
                return 0
        else:
            failed = True

    return _render_result(
        args,
        findings,
        failed=failed,
        phase=phase,
        hashes=computed_hashes,
    )


if __name__ == "__main__":
    raise SystemExit(main())
