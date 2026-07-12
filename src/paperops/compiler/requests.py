"""Resolve intuitive compile targets into exact typed write scopes."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .inputs import CompileInputError, _authoritative_snapshots, _load_model_inputs
from .tex import bind_typed_tex_blocks, scan_manuscript
from .types import CompileFinding, CompileRequest, WriteScope


_OPERATION_ORDER = ("keep", "compress", "move", "merge", "split", "cut", "rewrite", "add")


class CompileRequestError(ValueError):
    """A public target/scope combination cannot be resolved safely."""


def _state_error(pointer: str, message: str) -> CompileInputError:
    return CompileInputError(
        CompileFinding("compile.scope_unavailable", pointer, message)
    )


def resolve_compile_request(
    root: str | Path,
    target: str = "all",
    *,
    scope: str | None = None,
    block_ids: tuple[str, ...] = (),
    shadow_transaction_id: str = "",
) -> CompileRequest:
    """Resolve model topology, bindings, files, languages, and operations."""
    if target == "all":
        level = scope or "manuscript"
        if level != "manuscript":
            raise CompileRequestError("all target requires manuscript scope")
    else:
        level = scope or "section"
        if level == "manuscript":
            raise CompileRequestError("an explicit section cannot use manuscript scope")
    if level == "block" and not block_ids:
        raise CompileRequestError("block scope requires at least one --block")
    if level != "block" and block_ids:
        raise CompileRequestError("--block is valid only with block scope")
    if len(block_ids) != len(set(block_ids)):
        raise CompileRequestError("block IDs must be unique")

    project = Path(root).expanduser().absolute()
    authority = _authoritative_snapshots(project)
    documents, objects = _load_model_inputs(project, authority)
    manuscript_index = next(
        (
            item.document
            for item in documents
            if item.model_name == "manuscript" and item.document_type == "index"
        ),
        None,
    )
    if manuscript_index is None:
        raise _state_error("/manuscript", "current Manuscript index is missing")
    catalog = {item.object_id: item for item in objects}
    rows = manuscript_index.get("records")
    if not isinstance(rows, tuple):
        raise _state_error("/manuscript/records", "current Manuscript index is invalid")
    ordered_sections = tuple(
        row.get("id")
        for row in rows
        if isinstance(row, Mapping) and row.get("record_type") == "section"
    )
    if not ordered_sections or any(not isinstance(item, str) for item in ordered_sections):
        raise _state_error("/manuscript/records", "current Manuscript has no compilable sections")
    targets = ordered_sections if target == "all" else (target,)
    if any(
        section_id not in catalog or catalog[section_id].object_type != "section"
        for section_id in targets
    ):
        raise CompileRequestError("target is not a current Manuscript section")

    topology = tuple(
        block_id
        for section_id in targets
        for block_id in catalog[section_id].document.get("ordered_block_ids", ())
        if isinstance(block_id, str)
    )
    if not topology or any(
        block_id not in catalog or catalog[block_id].object_type != "block"
        for block_id in topology
    ):
        raise _state_error("/manuscript/blocks", "target section block topology is invalid")
    selected = (
        tuple(block_id for block_id in topology if block_id in set(block_ids))
        if level == "block"
        else topology
    )
    if level == "block" and set(selected) != set(block_ids):
        raise CompileRequestError("a requested block does not belong to the target section")

    manuscript = scan_manuscript(project)
    bindings = bind_typed_tex_blocks(
        manuscript,
        tuple(
            item.document
            for item in objects
            if item.object_type == "block"
        ),
    )
    if any(item.severity == "error" for item in bindings.findings):
        raise _state_error("/manuscript/bindings", "typed TeX bindings are invalid")
    selected_bindings = tuple(
        item for item in bindings.bindings if item.typed_block_id in set(selected)
    )
    files = tuple(sorted({item.file_identity for item in selected_bindings}))
    language_set = {item.language for item in selected_bindings}
    languages = tuple(
        language
        for language in ("ja", "en", *sorted(language_set - {"ja", "en"}))
        if language in language_set
    )
    operations = {
        operation
        for block_id in selected
        for operation in catalog[block_id].document.get("allowed_operations", ())
        if isinstance(operation, str)
    }
    planned = {
        catalog[block_id].document.get("operation") for block_id in selected
    }
    operations.update(item for item in planned if isinstance(item, str))
    allowed_operations = tuple(
        operation for operation in _OPERATION_ORDER if operation in operations
    )
    if not files or not languages or not allowed_operations:
        raise _state_error(
            "/write_scope",
            "target bindings or allowed operations are incomplete",
        )
    return CompileRequest(
        targets=tuple(targets),
        write_scope=WriteScope(
            level=level,
            languages=languages,
            files=files,
            section_ids=tuple(targets),
            block_ids=selected,
            allowed_operations=allowed_operations,
        ),
        source_mode="shadow" if shadow_transaction_id else "authoritative",
        shadow_transaction_id=shadow_transaction_id,
    )


__all__ = ["CompileRequestError", "resolve_compile_request"]
