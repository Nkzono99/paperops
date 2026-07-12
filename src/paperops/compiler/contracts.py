"""Deterministic section-contract layering for P3 compile inputs."""

from __future__ import annotations

import copy
import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .privacy import (
    PRIVATE_MATERIAL_MESSAGE,
    contains_private_material,
    sensitive_document_key,
)
from .safe_fs import SafeCaptureError, SafeProjectReader
from .storage import semantic_hash
from .types import CompileFinding, _freeze_json, _json_compatible


_SECTION_KIND_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_LAYER_NAMES = ("managed_default", "project_overlay", "writing_profile")
_PROFILE_KEYS = frozenset(
    {
        "schema_version",
        "paper_type",
        "overlays",
        "venue_overlay",
        "author_preferences",
        "section_depth",
    }
)
_PAPER_OVERLAY_KEYS = frozenset(
    {
        "method_requirements",
        "result_requirements",
        "figure_requirements",
        "discussion_requirements",
        "figure_defaults",
        "contract_overrides",
    }
)
_SECTION_REQUIREMENT_KEY = {
    "methods": "method_requirements",
    "results": "result_requirements",
    "discussion": "discussion_requirements",
}


class _DuplicateKeyError(yaml.YAMLError):
    pass


class _YamlAliasError(yaml.YAMLError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    def compose_node(
        self,
        parent: yaml.Node | None,
        index: int | None,
    ) -> yaml.Node:
        if self.check_event(yaml.events.AliasEvent):
            raise _YamlAliasError("YAML aliases are unsupported")
        return super().compose_node(parent, index)


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as error:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from error
        if duplicate:
            raise _DuplicateKeyError("duplicate YAML mapping key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _content_hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _missing_hash(identity: str, kind: str) -> str:
    return semantic_hash({"identity": identity, "kind": kind, "present": False})


def _pointer(parent: str, key: str) -> str:
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}" if parent else f"/{escaped}"


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


def _document_findings(
    value: Any,
    identity: str,
    pointer: str = "",
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    if value is None or isinstance(value, (bool, int)):
        return findings
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError:
            findings.append(
                _finding(
                    "compile.contract_document_value",
                    pointer,
                    "contract layer contains a non-UTF-8 Unicode scalar",
                    identity,
                )
            )
        return findings
    if isinstance(value, float):
        if not math.isfinite(value):
            findings.append(
                _finding(
                    "compile.contract_document_value",
                    pointer,
                    "contract layer contains a non-finite number",
                    identity,
                )
            )
        return findings
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                findings.append(
                    _finding(
                        "compile.contract_document_key",
                        pointer,
                        "contract layer mapping keys must be strings",
                        identity,
                    )
                )
                continue
            try:
                key.encode("utf-8")
            except UnicodeEncodeError:
                findings.append(
                    _finding(
                        "compile.contract_document_key",
                        pointer,
                        "contract layer mapping key is not a UTF-8 Unicode scalar",
                        identity,
                    )
                )
                continue
            findings.extend(
                _document_findings(item, identity, _pointer(pointer, key))
            )
        return findings
    if isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{pointer}/{index}" if pointer else f"/{index}"
            findings.extend(_document_findings(item, identity, child))
        return findings
    findings.append(
        _finding(
            "compile.contract_document_value",
            pointer,
            "contract layer contains a non-JSON scalar",
            identity,
        )
    )
    return findings


def _privacy_findings(
    value: Any,
    identity: str,
    pointer: str = "",
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    if isinstance(value, str):
        if contains_private_material(value):
            findings.append(
                _finding(
                    "compile.contract_privacy",
                    pointer,
                    PRIVATE_MATERIAL_MESSAGE,
                    identity,
                )
            )
    elif isinstance(value, dict):
        for key, item in value.items():
            is_project_metadata = (
                key == "_overlay"
                and pointer == ""
                and identity.startswith("_paperops/contracts/")
            )
            profile_parts = pointer.split("/")
            is_profile_metadata = (
                key == "_overlay"
                and identity == "manuscript/writing-profile.yml"
                and len(profile_parts) == 4
                and profile_parts[1] == "overlays"
                and profile_parts[3] == "contract_overrides"
            )
            if is_project_metadata or is_profile_metadata:
                continue
            if sensitive_document_key(key) or contains_private_material(key):
                findings.append(
                    _finding(
                        "compile.contract_privacy",
                        pointer,
                        PRIVATE_MATERIAL_MESSAGE,
                        identity,
                    )
                )
                continue
            findings.extend(
                _privacy_findings(item, identity, _pointer(pointer, key))
            )
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{pointer}/{index}" if pointer else f"/{index}"
            findings.extend(_privacy_findings(item, identity, child))
    return findings


@dataclass(frozen=True)
class ContractLayerSnapshot:
    name: str
    identity: str
    present: bool
    content_hash: str
    semantic_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "identity": self.identity,
            "present": self.present,
            "content_hash": self.content_hash,
            "semantic_hash": self.semantic_hash,
        }


@dataclass(frozen=True)
class ResolvedContract:
    section_kind: str
    effective: Mapping[str, Any]
    layers: tuple[ContractLayerSnapshot, ...]
    trace: Mapping[str, str]
    findings: tuple[CompileFinding, ...]
    snapshot_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "effective", _freeze_json(self.effective))
        object.__setattr__(self, "trace", _freeze_json(self.trace))
        object.__setattr__(self, "layers", tuple(self.layers))
        object.__setattr__(self, "findings", tuple(self.findings))

    def to_dict(self) -> dict[str, object]:
        return {
            "section_kind": self.section_kind,
            "effective": _json_compatible(self.effective),
            "layers": [layer.to_dict() for layer in self.layers],
            "trace": _json_compatible(self.trace),
            "findings": [finding.to_dict() for finding in self.findings],
            "snapshot_hash": self.snapshot_hash,
        }


def _finding(
    code: str,
    pointer: str,
    message: str,
    identity: str,
) -> CompileFinding:
    return CompileFinding(
        code=code,
        pointer=pointer,
        message=message,
        severity="error",
        identity=identity,
    )


def _load_yaml_layer(
    reader: SafeProjectReader,
    name: str,
    identity: str,
    *,
    required: bool,
) -> tuple[dict[str, Any] | None, ContractLayerSnapshot, list[CompileFinding]]:
    try:
        optional_capture = reader.read_optional_file(identity)
    except SafeCaptureError:
        layer = ContractLayerSnapshot(
            name=name,
            identity=identity,
            present=True,
            content_hash=_missing_hash(identity, "unsafe-content"),
            semantic_hash=_missing_hash(identity, "unsafe-semantic"),
        )
        return (
            None,
            layer,
            [
                _finding(
                    "compile.contract_unsafe_input",
                    "",
                    "contract input is not a safe regular project file",
                    identity,
                )
            ],
        )
    if optional_capture is None:
        layer = ContractLayerSnapshot(
            name=name,
            identity=identity,
            present=False,
            content_hash=_missing_hash(identity, "content"),
            semantic_hash=_missing_hash(identity, "semantic"),
        )
        findings = (
            [
                _finding(
                    "compile.contract_default_missing",
                    "",
                    "managed section contract is missing",
                    identity,
                )
            ]
            if required
            else []
        )
        return None, layer, findings
    content, captured = optional_capture

    findings: list[CompileFinding] = []
    document: dict[str, Any] | None = None
    try:
        text = content.decode("utf-8")
        loaded = yaml.load(text, Loader=_UniqueKeyLoader)
        if not isinstance(loaded, dict) or not all(
            isinstance(key, str) for key in loaded
        ):
            findings.append(
                _finding(
                    "compile.contract_document_type",
                    "",
                    "contract layer must be a YAML mapping with string keys",
                    identity,
                )
            )
        else:
            document_findings = _document_findings(loaded, identity)
            findings.extend(document_findings)
            operation_findings: list[CompileFinding] = []
            if name == "managed_default" and "_overlay" in loaded:
                operation_findings.append(
                    _finding(
                        "compile.contract_unknown_operation",
                        "/_overlay",
                        "managed defaults cannot declare overlay metadata",
                        identity,
                    )
                )
                findings.extend(operation_findings)
            if not document_findings and not operation_findings:
                privacy_findings = _privacy_findings(loaded, identity)
                findings.extend(privacy_findings)
                if not privacy_findings:
                    document = loaded
    except UnicodeDecodeError:
        findings.append(
            _finding(
                "compile.contract_utf8",
                "",
                "contract layer must be UTF-8",
                identity,
            )
        )
    except _DuplicateKeyError:
        findings.append(
            _finding(
                "compile.contract_duplicate_key",
                "",
                "contract layer contains a duplicate YAML key",
                identity,
            )
        )
    except _YamlAliasError:
        findings.append(
            _finding(
                "compile.contract_yaml_alias",
                "",
                "contract layer cannot contain YAML aliases",
                identity,
            )
        )
    except (yaml.YAMLError, RecursionError, ValueError, OverflowError):
        findings.append(
            _finding(
                "compile.contract_yaml_invalid",
                "",
                "contract layer is not valid YAML",
                identity,
            )
        )

    layer = ContractLayerSnapshot(
        name=name,
        identity=identity,
        present=True,
        content_hash=captured.content_hash,
        semantic_hash=(
            semantic_hash(document)
            if document is not None
            else semantic_hash(
                {
                    "identity": identity,
                    "content_hash": captured.content_hash,
                    "valid": False,
                }
            )
        ),
    )
    return document, layer, findings


def _null_findings(
    value: Any,
    identity: str,
    pointer: str = "",
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    if value is None:
        findings.append(
            _finding(
                "compile.contract_null",
                pointer,
                "null values and null deletion are unsupported",
                identity,
            )
        )
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                findings.extend(_null_findings(item, identity, _pointer(pointer, key)))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            child = f"{pointer}/{index}" if pointer else f"/{index}"
            findings.extend(_null_findings(item, identity, child))
    return findings


def _seed_trace(value: Any, layer: str, trace: dict[str, str], pointer: str = "") -> None:
    if pointer:
        trace[pointer] = layer
    if isinstance(value, dict):
        for key, item in value.items():
            _seed_trace(item, layer, trace, _pointer(pointer, key))


def _metadata(
    overlay: dict[str, Any],
    identity: str,
) -> tuple[set[str], list[CompileFinding]]:
    raw = overlay.get("_overlay")
    if raw is None:
        return set(), []
    if not isinstance(raw, dict):
        return set(), [
            _finding(
                "compile.contract_unknown_operation",
                "/_overlay",
                "overlay metadata must contain only complete_lists",
                identity,
            )
        ]
    findings: list[CompileFinding] = []
    unknown = sorted(key for key in raw if key != "complete_lists")
    for _key in unknown:
        findings.append(
            _finding(
                "compile.contract_unknown_operation",
                "/_overlay",
                "unknown or destructive overlay operation is forbidden",
                identity,
            )
        )
    declared = raw.get("complete_lists", [])
    def canonical_pointer(value: object) -> bool:
        if not isinstance(value, str) or not value.startswith("/"):
            return False
        segments = value[1:].split("/")
        if not segments or any(not segment for segment in segments):
            return False
        for segment in segments:
            index = 0
            while index < len(segment):
                if segment[index] == "~":
                    if index + 1 >= len(segment) or segment[index + 1] not in "01":
                        return False
                    index += 2
                else:
                    index += 1
        return True

    if not isinstance(declared, list) or not all(
        canonical_pointer(item) for item in declared
    ):
        findings.append(
            _finding(
                "compile.contract_complete_list_invalid",
                "/_overlay/complete_lists",
                "complete_lists must be a list of JSON Pointers",
                identity,
            )
        )
        return set(), findings
    if len(set(declared)) != len(declared):
        findings.append(
            _finding(
                "compile.contract_complete_list_invalid",
                "/_overlay/complete_lists",
                "complete_lists must not contain duplicates",
                identity,
            )
        )
    return set(declared), findings


def _same_type(base: Any, override: Any) -> bool:
    return type(base) is type(override)


def _merge_overlay(
    base: dict[str, Any],
    overlay: dict[str, Any],
    identity: str,
    complete_lists: set[str],
    trace: dict[str, str],
    layer_name: str,
    used_complete_lists: set[str],
    pointer: str = "",
) -> list[CompileFinding]:
    findings: list[CompileFinding] = []
    for key, override in overlay.items():
        if key == "_overlay" and not pointer:
            continue
        child = _pointer(pointer, key)
        if override is None:
            continue
        if key not in base:
            findings.append(
                _finding(
                    "compile.contract_unknown",
                    child,
                    "overlay key is not declared by the managed contract",
                    identity,
                )
            )
            continue
        current = base[key]
        if not pointer and key == "section":
            if override != current:
                findings.append(
                    _finding(
                        "compile.contract_section_override",
                        child,
                        "higher contract layers cannot change the section discriminator",
                        identity,
                    )
                )
            continue
        if not _same_type(current, override):
            findings.append(
                _finding(
                    "compile.contract_type_change",
                    child,
                    "overlay cannot change the managed contract value type",
                    identity,
                )
            )
            continue
        if isinstance(current, dict):
            findings.extend(
                _merge_overlay(
                    current,
                    override,
                    identity,
                    complete_lists,
                    trace,
                    layer_name,
                    used_complete_lists,
                    child,
                )
            )
        elif isinstance(current, list):
            if child not in complete_lists:
                findings.append(
                    _finding(
                        "compile.contract_list_replacement_undeclared",
                        child,
                        "ordered list replacement requires a complete_lists declaration",
                        identity,
                    )
                )
                continue
            base[key] = _clone(override)
            used_complete_lists.add(child)
            _seed_trace(base[key], layer_name, trace, child)
        else:
            base[key] = _clone(override)
            trace[child] = layer_name
    return findings


def _profile_projection(
    profile: dict[str, Any],
    section_kind: str,
    identity: str,
) -> tuple[dict[str, Any], dict[str, Any], list[CompileFinding]]:
    findings: list[CompileFinding] = []
    for key in sorted(set(profile) - _PROFILE_KEYS):
        findings.append(
            _finding(
                "compile.contract_profile_unknown",
                _pointer("", key),
                "writing profile contains an unknown top-level key",
                identity,
            )
        )

    schema_version = profile.get("schema_version")
    paper_type = profile.get("paper_type")
    overlays = profile.get("overlays")
    for pointer, valid, message in (
        ("/schema_version", type(schema_version) is int and schema_version == 1, "schema_version must be 1"),
        ("/paper_type", isinstance(paper_type, str) and bool(paper_type), "paper_type must be a non-empty string"),
        ("/overlays", isinstance(overlays, dict), "overlays must be a mapping"),
    ):
        if not valid:
            findings.append(
                _finding(
                    "compile.contract_profile_type",
                    pointer,
                    message,
                    identity,
                )
            )

    selected: dict[str, Any] = {}
    if isinstance(overlays, dict):
        for overlay_name, candidate in overlays.items():
            overlay_pointer = _pointer("/overlays", overlay_name)
            if not isinstance(candidate, dict):
                findings.append(
                    _finding(
                        "compile.contract_profile_type",
                        overlay_pointer,
                        "each paper-type overlay must be a mapping",
                        identity,
                    )
                )
                continue
            for key in sorted(set(candidate) - _PAPER_OVERLAY_KEYS):
                findings.append(
                    _finding(
                        "compile.contract_profile_unknown",
                        _pointer(overlay_pointer, key),
                        "paper-type overlay contains an unknown key",
                        identity,
                    )
                )
            for key in (
                "method_requirements",
                "result_requirements",
                "figure_requirements",
                "discussion_requirements",
            ):
                value = candidate.get(key, [])
                if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value
                ):
                    findings.append(
                        _finding(
                            "compile.contract_profile_type",
                            _pointer(overlay_pointer, key),
                            "profile requirements must be a list of strings",
                            identity,
                        )
                    )
            for key in ("figure_defaults", "contract_overrides"):
                value = candidate.get(key, {})
                if not isinstance(value, dict):
                    findings.append(
                        _finding(
                            "compile.contract_profile_type",
                            _pointer(overlay_pointer, key),
                            f"{key} must be a mapping",
                            identity,
                        )
                    )
            inactive_overrides = candidate.get("contract_overrides", {})
            if overlay_name != paper_type and isinstance(inactive_overrides, dict):
                _declared, inactive_metadata_findings = _metadata(
                    inactive_overrides,
                    identity,
                )
                findings.extend(inactive_metadata_findings)

    if isinstance(overlays, dict) and isinstance(paper_type, str):
        candidate = overlays.get(paper_type)
        if not isinstance(candidate, dict):
            findings.append(
                _finding(
                    "compile.contract_profile_overlay_missing",
                    f"/overlays/{paper_type}",
                    "paper_type has no mapping overlay",
                    identity,
                )
            )
        else:
            selected = candidate
    for key in ("venue_overlay", "author_preferences", "section_depth"):
        value = profile.get(key, {})
        if not isinstance(value, dict):
            findings.append(
                _finding(
                    "compile.contract_profile_type",
                    f"/{key}",
                    f"{key} must be a mapping",
                    identity,
                )
            )

    requirement_key = _SECTION_REQUIREMENT_KEY.get(section_kind, "")
    requirements = selected.get(requirement_key, []) if requirement_key else []
    projection = {
        "schema_version": schema_version,
        "paper_type": paper_type,
        "section_requirements": _clone(requirements) if isinstance(requirements, list) else [],
        "figure_requirements": _clone(selected.get("figure_requirements", []))
        if isinstance(selected.get("figure_requirements", []), list)
        else [],
        "figure_defaults": _clone(selected.get("figure_defaults", {}))
        if isinstance(selected.get("figure_defaults", {}), dict)
        else {},
        "venue_overlay": _clone(profile.get("venue_overlay", {}))
        if isinstance(profile.get("venue_overlay", {}), dict)
        else {},
        "author_preferences": _clone(profile.get("author_preferences", {}))
        if isinstance(profile.get("author_preferences", {}), dict)
        else {},
        "section_depth": _clone(profile.get("section_depth", {}))
        if isinstance(profile.get("section_depth", {}), dict)
        else {},
    }
    overrides = selected.get("contract_overrides", {})
    if not isinstance(overrides, dict):
        findings.append(
            _finding(
                "compile.contract_profile_type",
                f"/overlays/{paper_type}/contract_overrides",
                "contract_overrides must be a mapping",
                identity,
            )
        )
        overrides = {}
    return projection, overrides, findings


def resolve_section_contract(
    root: str | Path,
    section_kind: str,
    *,
    _capture_hook: Any | None = None,
) -> ResolvedContract:
    """Resolve one section contract without changing project state."""
    if (
        not isinstance(section_kind, str)
        or _SECTION_KIND_RE.fullmatch(section_kind) is None
        or contains_private_material(section_kind)
        or sensitive_document_key(section_kind)
    ):
        raise ValueError("section_kind must be a path-safe section name")
    project = Path(root).expanduser().absolute()
    identities = (
        f"_paperops/defaults/contracts/{section_kind}.yml",
        f"_paperops/contracts/{section_kind}.yml",
        "manuscript/writing-profile.yml",
    )
    documents: list[dict[str, Any] | None] = []
    layers: list[ContractLayerSnapshot] = []
    findings: list[CompileFinding] = []
    try:
        with SafeProjectReader(project, hook=_capture_hook) as reader:
            for index, (name, identity) in enumerate(zip(_LAYER_NAMES, identities)):
                document, layer, layer_findings = _load_yaml_layer(
                    reader,
                    name,
                    identity,
                    required=index == 0,
                )
                documents.append(document)
                layers.append(layer)
                findings.extend(layer_findings)
    except SafeCaptureError:
        documents = [None, None, None]
        layers = [
            ContractLayerSnapshot(
                name=name,
                identity=identity,
                present=False,
                content_hash=_missing_hash(identity, "unreadable-content"),
                semantic_hash=_missing_hash(identity, "unreadable-semantic"),
            )
            for name, identity in zip(_LAYER_NAMES, identities)
        ]
        findings.append(
            _finding(
                "compile.contract_root_unsafe",
                "",
                "project root is missing or unsafe",
                identities[0],
            )
        )

    for index, (document, layer) in enumerate(zip(documents, layers)):
        if document is not None:
            null_findings = _null_findings(document, layer.identity)
            findings.extend(null_findings)
            if null_findings:
                documents[index] = None

    managed = documents[0]
    effective: dict[str, Any] = _clone(managed) if managed is not None else {}
    trace: dict[str, str] = {}
    _seed_trace(effective, "managed_default", trace)
    if managed is not None and managed.get("section") not in {None, section_kind}:
        findings.append(
            _finding(
                "compile.contract_section_mismatch",
                "/section",
                "managed contract section does not match the requested section",
                identities[0],
            )
        )

    overlay = documents[1]
    if overlay is not None:
        complete_lists, metadata_findings = _metadata(overlay, identities[1])
        candidate = _clone(effective)
        candidate_trace = dict(trace)
        used_complete_lists: set[str] = set()
        merge_findings = _merge_overlay(
            candidate,
            overlay,
            identities[1],
            complete_lists,
            candidate_trace,
            "project_overlay",
            used_complete_lists,
        )
        unused_findings = [
            _finding(
                "compile.contract_complete_list_unused",
                "/_overlay/complete_lists",
                "complete_lists declaration does not replace an ordered list",
                identities[1],
            )
            for _pointer_value in sorted(complete_lists - used_complete_lists)
        ]
        layer_findings = [*metadata_findings, *merge_findings, *unused_findings]
        findings.extend(layer_findings)
        if not layer_findings:
            effective = candidate
            trace = candidate_trace

    profile = documents[2]
    if profile is not None:
        projection, overrides, profile_findings = _profile_projection(
            profile,
            section_kind,
            identities[2],
        )
        complete_lists, metadata_findings = _metadata(overrides, identities[2])
        candidate = _clone(effective)
        candidate_trace = dict(trace)
        used_complete_lists = set()
        merge_findings = _merge_overlay(
            candidate,
            overrides,
            identities[2],
            complete_lists,
            candidate_trace,
            "writing_profile",
            used_complete_lists,
        )
        unused_findings = [
            _finding(
                "compile.contract_complete_list_unused",
                "/overlays/contract_overrides/_overlay/complete_lists",
                "complete_lists declaration does not replace an ordered list",
                identities[2],
            )
            for _pointer_value in sorted(complete_lists - used_complete_lists)
        ]
        layer_findings = [
            *profile_findings,
            *metadata_findings,
            *merge_findings,
            *unused_findings,
        ]
        findings.extend(layer_findings)
        if not layer_findings:
            candidate["writing_profile"] = projection
            _seed_trace(
                projection,
                "writing_profile",
                candidate_trace,
                "/writing_profile",
            )
            effective = candidate
            trace = candidate_trace

    if effective.get("section") != section_kind:
        findings.append(
            _finding(
                "compile.contract_section_invariant",
                "/section",
                "resolved contract section must equal the requested section",
                identities[0],
            )
        )

    material = {
        "section_kind": section_kind,
        "effective": effective,
        "layers": [layer.to_dict() for layer in layers],
        "trace": trace,
        "findings": [finding.to_dict() for finding in findings],
    }
    return ResolvedContract(
        section_kind=section_kind,
        effective=effective,
        layers=tuple(layers),
        trace=trace,
        findings=tuple(findings),
        snapshot_hash=semantic_hash(material),
    )


__all__ = [
    "ContractLayerSnapshot",
    "ResolvedContract",
    "resolve_section_contract",
]
