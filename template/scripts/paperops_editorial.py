"""Reference and semantic validation for the PaperOps Editorial model."""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from paperops_schema import ModelFinding


EXTENSION_KEY_PATTERN = re.compile(
    r"^x-[a-z0-9][a-z0-9._-]*-[a-z0-9][a-z0-9._-]*$"
)
MOVE_STANCES = frozenset({"assert", "reject", "boundary", "hold"})
PLACEHOLDER_VALUES = frozenset(
    {
        "",
        "未記入",
        "未設定",
        "未定",
        "todo",
        "tbd",
        "placeholder",
        "fill in",
        "xx",
    }
)


def _finding(
    code: str,
    pointer: str,
    message: str,
    *,
    severity: str = "error",
) -> ModelFinding:
    return ModelFinding(code=code, pointer=pointer, message=message, severity=severity)


def _items(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _mapping(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        return None
    return value


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _blank(value: Any) -> bool:
    return isinstance(value, str) and not value.strip()


def _placeholder(value: Any) -> bool:
    """Return whether a string is a fixed starter placeholder."""
    return isinstance(value, str) and value.strip().casefold() in PLACEHOLDER_VALUES


def _id_index(
    objects: list[Any],
    pointer: str,
    findings: list[ModelFinding],
) -> tuple[dict[str, int], set[str]]:
    first_index: dict[str, int] = {}
    duplicates: set[str] = set()
    for index, raw_item in enumerate(objects):
        item = _mapping(raw_item)
        if item is None:
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str):
            continue
        if item_id in first_index:
            duplicates.add(item_id)
            findings.append(
                _finding(
                    "reference.duplicate",
                    f"{pointer}/{index}/id",
                    f"duplicate ID `{item_id}`",
                )
            )
        else:
            first_index[item_id] = index
    for duplicate in duplicates:
        first_index.pop(duplicate, None)
    return first_index, duplicates


def _check_reference(
    value: Any,
    pointer: str,
    target_name: str,
    index: dict[str, int],
    duplicates: set[str],
    findings: list[ModelFinding],
) -> None:
    if not isinstance(value, str) or not value or value in duplicates:
        return
    if value not in index:
        findings.append(
            _finding(
                "reference.dangling",
                pointer,
                f"{target_name} `{value}` does not exist",
            )
        )


def _check_reference_array(
    value: Any,
    pointer: str,
    target_name: str,
    index: dict[str, int],
    duplicates: set[str],
    findings: list[ModelFinding],
) -> None:
    if not isinstance(value, list):
        return
    for item_index, reference in enumerate(value):
        _check_reference(
            reference,
            f"{pointer}/{item_index}",
            target_name,
            index,
            duplicates,
            findings,
        )


def _defer_reference_array(
    value: Any,
    pointer: str,
    target_name: str,
    findings: list[ModelFinding],
) -> None:
    if not isinstance(value, list):
        return
    for index, reference in enumerate(value):
        if isinstance(reference, str) and reference:
            findings.append(
                _finding(
                    "reference.deferred",
                    f"{pointer}/{index}",
                    f"{target_name} `{reference}` will be resolved when its model is available",
                    severity="info",
                )
            )


def _check_move_order(moves: list[Any], findings: list[ModelFinding]) -> None:
    for index, raw_move in enumerate(moves):
        move = _mapping(raw_move)
        if move is None:
            continue
        position = move.get("position")
        expected_position = index + 1
        if (
            isinstance(position, int)
            and not isinstance(position, bool)
            and position != expected_position
        ):
            findings.append(
                _finding(
                    "reference.order",
                    f"/argument_moves/{index}/position",
                    f"move position must be {expected_position} in array order",
                )
            )

        next_move_id = move.get("next_move_id")
        if not isinstance(next_move_id, str):
            continue
        expected_next = ""
        if index + 1 < len(moves):
            next_move = _mapping(moves[index + 1])
            if next_move is None or not isinstance(next_move.get("id"), str):
                continue
            expected_next = next_move["id"]
        if next_move_id != expected_next:
            findings.append(
                _finding(
                    "reference.order",
                    f"/argument_moves/{index}/next_move_id",
                    f"next_move_id must follow array order and be `{expected_next}`",
                )
            )


def _check_move_cycles(
    moves: list[Any],
    move_index: dict[str, int],
    duplicate_moves: set[str],
    findings: list[ModelFinding],
) -> None:
    colors: dict[str, int] = {move_id: 0 for move_id in move_index}
    for start_move_id in move_index:
        if colors[start_move_id] != 0:
            continue
        trail: list[str] = []
        move_id = start_move_id
        while move_id in move_index and colors[move_id] == 0:
            colors[move_id] = 1
            trail.append(move_id)
            index = move_index[move_id]
            move = _mapping(moves[index])
            next_move_id = move.get("next_move_id") if move is not None else None
            if (
                not isinstance(next_move_id, str)
                or not next_move_id
                or next_move_id in duplicate_moves
                or next_move_id not in move_index
            ):
                break
            if colors[next_move_id] == 1:
                findings.append(
                    _finding(
                        "reference.cycle",
                        f"/argument_moves/{index}/next_move_id",
                        f"move edge to `{next_move_id}` closes a cycle",
                    )
                )
                break
            if colors[next_move_id] == 2:
                break
            move_id = next_move_id
        for visited_move_id in trail:
            colors[visited_move_id] = 2


def _unsafe_document_path(value: str) -> bool:
    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    return (
        posix.is_absolute()
        or windows.is_absolute()
        or ".." in posix.parts
        or ".." in windows.parts
    )


def validate_editorial_references(
    editorial: dict[str, Any],
    results: dict[str, Any],
) -> list[ModelFinding]:
    """Validate local Editorial references and report deferred external ones."""
    findings: list[ModelFinding] = []
    if not isinstance(editorial, dict) or not isinstance(results, dict):
        return findings

    stories = _items(editorial.get("story_candidates"))
    moves = _items(editorial.get("argument_moves"))
    visuals = _items(editorial.get("visual_obligations"))
    result_items = _items(results.get("items"))

    story_index, duplicate_stories = _id_index(stories, "/story_candidates", findings)
    move_index, duplicate_moves = _id_index(moves, "/argument_moves", findings)
    _id_index(visuals, "/visual_obligations", findings)
    result_index, duplicate_results = _id_index(result_items, "/items", findings)

    _check_reference(
        editorial.get("selected_story_id"),
        "/selected_story_id",
        "story",
        story_index,
        duplicate_stories,
        findings,
    )

    for story_number, raw_story in enumerate(stories):
        story = _mapping(raw_story)
        if story is None:
            continue
        _check_reference_array(
            story.get("argument_move_ids"),
            f"/story_candidates/{story_number}/argument_move_ids",
            "argument move",
            move_index,
            duplicate_moves,
            findings,
        )
        _check_reference_array(
            story.get("result_order"),
            f"/story_candidates/{story_number}/result_order",
            "Results hierarchy item",
            result_index,
            duplicate_results,
            findings,
        )

    for move_number, raw_move in enumerate(moves):
        move = _mapping(raw_move)
        if move is None:
            continue
        _check_reference(
            move.get("next_move_id"),
            f"/argument_moves/{move_number}/next_move_id",
            "argument move",
            move_index,
            duplicate_moves,
            findings,
        )
        _check_reference_array(
            move.get("result_item_ids"),
            f"/argument_moves/{move_number}/result_item_ids",
            "Results hierarchy item",
            result_index,
            duplicate_results,
            findings,
        )
        _defer_reference_array(
            move.get("claim_ids"),
            f"/argument_moves/{move_number}/claim_ids",
            "claim",
            findings,
        )

    results_connection = _mapping(editorial.get("results_hierarchy"))
    if results_connection is not None:
        document = results_connection.get("document")
        if isinstance(document, str) and _unsafe_document_path(document):
            findings.append(
                _finding(
                    "reference.path",
                    "/results_hierarchy/document",
                    "Results hierarchy document must be a project-relative path without traversal",
                )
            )
        _check_reference_array(
            results_connection.get("item_ids"),
            "/results_hierarchy/item_ids",
            "Results hierarchy item",
            result_index,
            duplicate_results,
            findings,
        )

    claim_roles = _mapping(editorial.get("claim_roles"))
    if claim_roles is not None:
        for role, raw_entry in claim_roles.items():
            entry = _mapping(raw_entry)
            if entry is not None:
                _defer_reference_array(
                    entry.get("claim_ids"),
                    f"/claim_roles/{_pointer_token(role)}/claim_ids",
                    "claim",
                    findings,
                )

    for visual_number, raw_visual in enumerate(visuals):
        visual = _mapping(raw_visual)
        if visual is None:
            continue
        _defer_reference_array(
            visual.get("claim_ids"),
            f"/visual_obligations/{visual_number}/claim_ids",
            "claim",
            findings,
        )
        _defer_reference_array(
            visual.get("figure_ids"),
            f"/visual_obligations/{visual_number}/figure_ids",
            "figure",
            findings,
        )

    _check_move_order(moves, findings)
    _check_move_cycles(moves, move_index, duplicate_moves, findings)
    return findings


def validate_extension_keys(extensions: dict[str, Any]) -> list[ModelFinding]:
    """Validate extension names without interpreting extension values."""
    if not isinstance(extensions, dict):
        return []
    findings: list[ModelFinding] = []
    for key in extensions:
        if isinstance(key, str) and not EXTENSION_KEY_PATTERN.fullmatch(key):
            findings.append(
                _finding(
                    "semantic.extension",
                    f"/{_pointer_token(key)}",
                    f"extension key `{key}` must use x-<owner>-<name> format",
                )
            )
    return findings


def _add_placeholder(
    value: Any,
    pointer: str,
    strict: bool,
    findings: list[ModelFinding],
) -> None:
    if _placeholder(value):
        findings.append(
            _finding(
                "semantic.placeholder",
                pointer,
                "starter placeholder must be replaced with an editorial decision",
                severity="error" if strict else "warning",
            )
        )


def _add_empty_collection_placeholder(
    value: Any,
    pointer: str,
    strict: bool,
    findings: list[ModelFinding],
) -> None:
    if isinstance(value, list) and not value:
        findings.append(
            _finding(
                "semantic.placeholder",
                pointer,
                "starter collection must be replaced with editorial decisions",
                severity="error" if strict else "warning",
            )
        )


def _validate_story_semantics(
    editorial: dict[str, Any],
    strict: bool,
    findings: list[ModelFinding],
) -> None:
    raw_stories = editorial.get("story_candidates")
    if not isinstance(raw_stories, list):
        return
    stories = [(index, item) for index, raw in enumerate(raw_stories) if (item := _mapping(raw))]
    selected = [(index, story) for index, story in stories if story.get("status") == "selected"]
    if raw_stories:
        if len(selected) != 1:
            findings.append(
                _finding(
                    "semantic.story_selection",
                    "/story_candidates",
                    "exactly one story candidate must have selected status",
                )
            )
        elif isinstance(editorial.get("selected_story_id"), str):
            selected_id = selected[0][1].get("id")
            if isinstance(selected_id, str) and editorial["selected_story_id"] != selected_id:
                findings.append(
                    _finding(
                        "semantic.story_selection",
                        "/selected_story_id",
                        "selected_story_id must match the selected candidate",
                    )
                )

    _add_empty_collection_placeholder(raw_stories, "/story_candidates", strict, findings)
    for index, story in stories:
        status = story.get("status")
        if status == "selected" and _blank(story.get("selection_reason")):
            findings.append(
                _finding(
                    "semantic.story_selection",
                    f"/story_candidates/{index}/selection_reason",
                    "selected story requires a selection reason",
                )
            )
        if status == "rejected" and _blank(story.get("rejection_reason")):
            findings.append(
                _finding(
                    "semantic.story_selection",
                    f"/story_candidates/{index}/rejection_reason",
                    "rejected story requires a rejection reason",
                )
            )
        _add_placeholder(story.get("label"), f"/story_candidates/{index}/label", strict, findings)
        _add_placeholder(story.get("thesis"), f"/story_candidates/{index}/thesis", strict, findings)
        if status == "selected":
            _add_placeholder(
                story.get("selection_reason"),
                f"/story_candidates/{index}/selection_reason",
                strict,
                findings,
            )
        if status == "rejected":
            _add_placeholder(
                story.get("rejection_reason"),
                f"/story_candidates/{index}/rejection_reason",
                strict,
                findings,
            )

    if len(raw_stories) == 1:
        reason = editorial.get("single_candidate_reason")
        if _blank(reason):
            findings.append(
                _finding(
                    "semantic.story_count",
                    "/single_candidate_reason",
                    "a single story candidate requires an explanation",
                )
            )
        _add_placeholder(reason, "/single_candidate_reason", strict, findings)


def _validate_claim_roles(
    editorial: dict[str, Any],
    strict: bool,
    findings: list[ModelFinding],
) -> None:
    claim_roles = _mapping(editorial.get("claim_roles"))
    if claim_roles is None:
        return
    assigned: dict[str, str] = {}
    for role, raw_entry in claim_roles.items():
        entry = _mapping(raw_entry)
        if entry is None:
            continue
        claim_ids = entry.get("claim_ids")
        none_reason = entry.get("none_reason")
        if not isinstance(claim_ids, list) or not isinstance(none_reason, str):
            continue
        role_pointer = f"/claim_roles/{_pointer_token(role)}"
        if not claim_ids:
            if _blank(none_reason):
                findings.append(
                    _finding(
                        "semantic.claim_role",
                        f"{role_pointer}/none_reason",
                        "an empty claim role requires a reason",
                    )
                )
            _add_placeholder(none_reason, f"{role_pointer}/none_reason", strict, findings)
        elif not _blank(none_reason):
            findings.append(
                _finding(
                    "semantic.claim_role",
                    f"{role_pointer}/none_reason",
                    "none_reason must be empty when claims are assigned",
                )
            )
        for index, claim_id in enumerate(claim_ids):
            if not isinstance(claim_id, str):
                continue
            if claim_id in assigned and assigned[claim_id] != role:
                findings.append(
                    _finding(
                        "semantic.claim_role",
                        f"{role_pointer}/claim_ids/{index}",
                        f"claim `{claim_id}` is already assigned to role `{assigned[claim_id]}`",
                    )
                )
            else:
                assigned[claim_id] = role


def _validate_moves(
    editorial: dict[str, Any],
    strict: bool,
    findings: list[ModelFinding],
) -> None:
    moves = editorial.get("argument_moves")
    if not isinstance(moves, list):
        return
    _add_empty_collection_placeholder(moves, "/argument_moves", strict, findings)
    for index, raw_move in enumerate(moves):
        move = _mapping(raw_move)
        if move is None:
            continue
        stance = move.get("stance")
        if isinstance(stance, str) and stance not in MOVE_STANCES:
            findings.append(
                _finding(
                    "semantic.move",
                    f"/argument_moves/{index}/stance",
                    f"unsupported argument stance `{stance}`",
                )
            )
        for field in ("reader_question", "assertion"):
            value = move.get(field)
            pointer = f"/argument_moves/{index}/{field}"
            if strict and _blank(value):
                findings.append(
                    _finding(
                        "semantic.move",
                        pointer,
                        f"argument move {field} must not be blank in strict mode",
                    )
                )
            _add_placeholder(value, pointer, strict, findings)


def _validate_visuals(
    editorial: dict[str, Any],
    strict: bool,
    findings: list[ModelFinding],
) -> None:
    visuals = editorial.get("visual_obligations")
    if not isinstance(visuals, list):
        return
    _add_empty_collection_placeholder(visuals, "/visual_obligations", strict, findings)
    for index, raw_visual in enumerate(visuals):
        visual = _mapping(raw_visual)
        if visual is None:
            continue
        pointer = f"/visual_obligations/{index}"
        status = visual.get("status")
        waiver_reason = visual.get("waiver_reason")
        if status == "waived" and _blank(waiver_reason):
            findings.append(
                _finding(
                    "semantic.visual",
                    f"{pointer}/waiver_reason",
                    "a waived visual obligation requires a reason",
                )
            )
        figure_ids = visual.get("figure_ids")
        if status == "satisfied" and isinstance(figure_ids, list) and not figure_ids:
            findings.append(
                _finding(
                    "semantic.visual",
                    f"{pointer}/figure_ids",
                    "a satisfied visual obligation requires a figure reference",
                )
            )
        for field in ("reader_task", "takeaway", "preferred_form"):
            _add_placeholder(visual.get(field), f"{pointer}/{field}", strict, findings)
        if status == "waived":
            _add_placeholder(waiver_reason, f"{pointer}/waiver_reason", strict, findings)


def validate_editorial_semantics(
    editorial: dict[str, Any],
    *,
    strict: bool,
) -> list[ModelFinding]:
    """Validate Editorial decisions after schema and reference validation."""
    findings: list[ModelFinding] = []
    if not isinstance(editorial, dict):
        return findings

    transformation = _mapping(editorial.get("reader_transformation"))
    if transformation is not None:
        for field in ("reader_before", "reader_after", "why_it_matters"):
            _add_placeholder(
                transformation.get(field),
                f"/reader_transformation/{field}",
                strict,
                findings,
            )

    _validate_story_semantics(editorial, strict, findings)
    _add_placeholder(editorial.get("selected_story_id"), "/selected_story_id", strict, findings)
    _validate_claim_roles(editorial, strict, findings)
    _validate_moves(editorial, strict, findings)
    _validate_visuals(editorial, strict, findings)

    metadata = _mapping(editorial.get("metadata"))
    if metadata is not None:
        _add_placeholder(metadata.get("updated_at"), "/metadata/updated_at", strict, findings)

    results_connection = _mapping(editorial.get("results_hierarchy"))
    if results_connection is not None:
        _add_empty_collection_placeholder(
            results_connection.get("item_ids"),
            "/results_hierarchy/item_ids",
            strict,
            findings,
        )

    extensions = editorial.get("extensions")
    if isinstance(extensions, dict):
        for extension_finding in validate_extension_keys(extensions):
            findings.append(
                _finding(
                    extension_finding.code,
                    f"/extensions{extension_finding.pointer}",
                    extension_finding.message,
                    severity=extension_finding.severity,
                )
            )
    return findings
