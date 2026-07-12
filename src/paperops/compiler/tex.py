"""Pure TeX block parsing and protected-reference inventories for P3."""

from __future__ import annotations

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence

import yaml

from .privacy import contains_private_material, sensitive_document_key
from .safe_fs import SafeCaptureError, SafeProjectReader
from .storage import semantic_hash
from .types import CompileFinding


_BLOCK_RE = re.compile(
    r"^\s*%\s*block:\s*(?P<block_id>[A-Za-z0-9:._-]+)\s*$"
)
_BLOCK_PREFIX_RE = re.compile(r"^\s*%\s*block\s*:")
_COUNT_OF_RE = re.compile(r"\b(?P<value>[0-9]+)\s+of\s+(?P<denominator>[0-9]+)\b")
# Stay below CPython's minimum configurable int-string guard (640 digits).
_MAX_QUANTITY_DIGITS = 512
_CITE_COMMANDS = frozenset(
    {
        "autocite",
        "cite",
        "citealp",
        "citeauthor",
        "citep",
        "citet",
        "cites",
        "citeyear",
        "citeyearpar",
        "footcite",
        "nocite",
        "parencite",
        "parencites",
        "smartcite",
        "supercite",
        "textcite",
        "textcites",
    }
)
_CITE_COMMAND_RE = re.compile(r"\\(?P<command>[A-Za-z]+)\*?")
_FIGURE_LABEL_RE = re.compile(r"\\label\{(?P<label>fig:[^}]+)\}")
_FIGURE_REF_RE = re.compile(
    r"\\(?:ref|autoref|cref|Cref|figref|Figref)\{(?P<labels>[^}]+)\}"
)
_FIGURE_ID_RE = re.compile(r"^fig:[A-Za-z0-9][A-Za-z0-9:._/+~-]*$")
_PREDICTED_RE = re.compile(
    r"(?<!\\)%\s*(?P<name>PREDICTED-RESULT|SIM-REQUEST|EXPECTATION-BASIS|REPLACE-XX)\s*:?\s*(?P<body>.*)$"
)
_AREQ_RE = re.compile(r"\bAREQ-[A-Za-z0-9_.-]+\b")
_PLACEHOLDER_RE = re.compile(r"(?i)(?<![A-Za-z0-9])(?:xx|TODO|TBD)(?![A-Za-z0-9])")
_SUPPRESSION_RE = re.compile(r"paperops:\s*allow-authoring-intent", re.IGNORECASE)
_AUTHORING_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "claim strengthening work plan",
        re.compile(
            r"claim\s*を\s*強め|claim\s*を\s*補強|主張\s*を\s*強め|主張\s*を\s*補強",
            re.IGNORECASE,
        ),
    ),
    (
        "additional work needed for claim",
        re.compile(
            r"必要な追加作業|追加作業.{0,30}(claim|主張)|(claim|主張).{0,30}追加作業",
            re.IGNORECASE,
        ),
    ),
    (
        "drafting meta note",
        re.compile(r"執筆上|執筆意図|執筆メモ|著者メモ|作業メモ|原稿メモ"),
    ),
    (
        "unresolved draft placeholder",
        re.compile(
            r"\b(?:TODO|TBD)\b|後で(?:埋める|書く|追記|整理)|後ほど(?:埋める|書く|追記|整理)",
            re.IGNORECASE,
        ),
    ),
    (
        "planned later fill",
        re.compile(r"(ここ|本節|この段落).{0,24}(?:予定|後で|後ほど).{0,24}(?:示す|説明|追記|整理|埋める)"),
    ),
    (
        "english authoring note",
        re.compile(r"\b(?:authoring|drafting|writing)\s+note\b", re.IGNORECASE),
    ),
    (
        "english claim strengthening plan",
        re.compile(
            r"\b(?:strengthen(?:ing)?\s+the\s+claim|claim.{0,40}strengthen|additional\s+work\s+(?:needed\s+to\s+)?strengthen)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "english unresolved placeholder",
        re.compile(
            r"\b(?:TODO|TBD|placeholder|fill\s+in\s+later|add\s+later|to\s+be\s+added)\b",
            re.IGNORECASE,
        ),
    ),
)
_MAP_KEYS = frozenset({"version", "source_language", "target_language", "file_pair"})
_TERM_ROOT_KEYS = frozenset({"source_language", "target_language", "terms"})
_TERM_KEYS = frozenset(
    {
        "id",
        "ja",
        "en_public",
        "status",
        "first_definition_required",
        "first_definition_location",
        "avoid",
        "allowed_context",
        "replacement_rule",
        "figure_label_rule",
        "owner",
        "last_reviewed",
    }
)
_TERM_STATUSES = frozenset({"public", "needs_definition", "internal_only", "forbidden"})
_TERM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_CONCEPT_STATUSES = frozenset({"accepted", "needs-review", "plain-language", "avoid"})
_ANALYSIS_REQUEST_STATUSES = frozenset(
    {
        "planned",
        "predicted",
        "analysis-needed",
        "open",
        "running",
        "executed",
        "reconciled",
        "abandoned",
        "closed",
        "resolved",
        "cancelled",
        "canceled",
        "rejected",
    }
)
_ANALYSIS_REQUEST_ID_RE = re.compile(r"^AREQ-[A-Za-z0-9_.-]+$")
_TYPED_BLOCK_ID_RE = re.compile(r"^BLK-[0-9]{4,}$")


class _DuplicateYamlKey(yaml.YAMLError):
    pass


class _YamlAlias(yaml.YAMLError):
    pass


class _UniqueYamlLoader(yaml.SafeLoader):
    def compose_node(
        self,
        parent: yaml.Node | None,
        index: int | None,
    ) -> yaml.Node:
        if self.check_event(yaml.events.AliasEvent):
            raise _YamlAlias("YAML aliases are unsupported")
        return super().compose_node(parent, index)


def _construct_unique_yaml_mapping(
    loader: _UniqueYamlLoader,
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
            raise _DuplicateYamlKey("duplicate YAML mapping key")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_yaml_mapping,
)


def _generic_finding(
    code: str,
    message: str,
    identity: str,
    pointer: str = "",
    severity: str = "error",
) -> CompileFinding:
    return CompileFinding(
        code=code,
        pointer=pointer,
        message=message,
        severity=severity,
        identity=identity,
    )


def _safe_relative(value: str) -> bool:
    try:
        _validate_identity(value)
    except (TypeError, ValueError):
        return False
    return True


def _public_identity(value: str) -> bool:
    if not _safe_relative(value) or contains_private_material(value):
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return not any(ord(character) < 32 or ord(character) == 127 for character in value)


def _public_key_pointer(parent: str, key: object) -> str:
    if not isinstance(key, str):
        return parent
    if sensitive_document_key(key) or contains_private_material(key):
        return parent
    try:
        key.encode("utf-8")
    except UnicodeEncodeError:
        return parent
    if any(ord(character) < 32 or ord(character) == 127 for character in key):
        return parent
    escaped = key.replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}" if parent else f"/{escaped}"


def _decode_utf8(
    content: bytes,
    identity: str,
    code: str,
) -> tuple[str | None, list[CompileFinding]]:
    try:
        return content.decode("utf-8"), []
    except UnicodeDecodeError:
        return None, [_generic_finding(code, "input must be UTF-8", identity)]


def _load_unique_yaml(
    content: bytes,
    identity: str,
    code_prefix: str,
) -> tuple[Any | None, list[CompileFinding]]:
    text, findings = _decode_utf8(content, identity, f"{code_prefix}_utf8")
    if text is None:
        return None, findings
    try:
        return yaml.load(text, Loader=_UniqueYamlLoader), findings
    except _DuplicateYamlKey:
        findings.append(
            _generic_finding(
                f"{code_prefix}_duplicate_key",
                "YAML input contains a duplicate mapping key",
                identity,
            )
        )
    except _YamlAlias:
        findings.append(
            _generic_finding(
                f"{code_prefix}_alias",
                "YAML aliases are unsupported",
                identity,
            )
        )
    except (yaml.YAMLError, RecursionError, ValueError, OverflowError):
        findings.append(
            _generic_finding(
                f"{code_prefix}_invalid",
                "YAML input is invalid",
                identity,
            )
        )
    return None, findings


def _frontmatter(
    content: bytes,
    identity: str,
) -> tuple[dict[str, Any] | None, list[CompileFinding]]:
    text, findings = _decode_utf8(
        content,
        identity,
        "compile.analysis_request_utf8",
    )
    if text is None:
        return None, findings
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, [
            _generic_finding(
                "compile.analysis_request_frontmatter",
                "analysis request must start with YAML frontmatter",
                identity,
            )
        ]
    try:
        end = next(index for index, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None, [
            _generic_finding(
                "compile.analysis_request_frontmatter",
                "analysis request frontmatter is not closed",
                identity,
            )
        ]
    front = ("\n".join(lines[1:end]) + "\n").encode("utf-8")
    loaded, parse_findings = _load_unique_yaml(
        front,
        identity,
        "compile.analysis_request",
    )
    findings.extend(parse_findings)
    if loaded is not None and not isinstance(loaded, dict):
        findings.append(
            _generic_finding(
                "compile.analysis_request_frontmatter",
                "analysis request frontmatter must be a mapping",
                identity,
            )
        )
        return None, findings
    if isinstance(loaded, dict) and not all(
        isinstance(key, str) for key in loaded
    ):
        findings.append(
            _generic_finding(
                "compile.analysis_request_frontmatter",
                "analysis request frontmatter keys must be strings",
                identity,
            )
        )
        return None, findings
    return loaded, findings


def _private_public_text(value: str) -> bool:
    return contains_private_material(value)


def _legacy_hash(body: str) -> str:
    normalized = "\n".join(line.rstrip() for line in body.splitlines()).strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _raw_block_bodies(content: bytes) -> dict[str, str]:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return {}
    lines = text.splitlines(keepends=True)
    markers: list[tuple[str, int]] = []
    for index, line in enumerate(lines):
        match = _BLOCK_RE.fullmatch(line.rstrip("\r\n"))
        if match:
            markers.append((match.group("block_id"), index))
    result: dict[str, str] = {}
    duplicates: set[str] = set()
    for marker_index, (marker_id, line_index) in enumerate(markers):
        end = markers[marker_index + 1][1] if marker_index + 1 < len(markers) else len(lines)
        body = "".join(lines[line_index + 1 : end])
        if marker_id in result:
            duplicates.add(marker_id)
        else:
            result[marker_id] = body
    for marker_id in duplicates:
        result.pop(marker_id, None)
    return result


def _parse_mirror_map(
    content: bytes,
    identity: str,
) -> tuple[list[tuple[str, str]], list[CompileFinding]]:
    text, findings = _decode_utf8(content, identity, "compile.mirror_map_utf8")
    if text is None:
        return [], findings
    try:
        document = tomllib.loads(text)
    except (tomllib.TOMLDecodeError, RecursionError, ValueError):
        return [], [
            *findings,
            _generic_finding(
                "compile.mirror_map_invalid",
                "mirror map is not valid TOML",
                identity,
            ),
        ]
    for key in sorted(set(document) - _MAP_KEYS):
        findings.append(
            _generic_finding(
                "compile.mirror_map_unknown",
                "mirror map contains an unknown key",
                identity,
                _public_key_pointer("", key),
            )
        )
    if type(document.get("version")) is not int or document.get("version") != 1:
        findings.append(
            _generic_finding(
                "compile.mirror_map_type",
                "mirror map version must be 1",
                identity,
                "/version",
            )
        )
    for key, expected in (("source_language", "ja"), ("target_language", "en")):
        if document.get(key) != expected:
            findings.append(
                _generic_finding(
                    "compile.mirror_map_language",
                    f"mirror map {key} must be {expected}",
                    identity,
                    f"/{key}",
                )
            )
    raw_pairs = document.get("file_pair")
    if not isinstance(raw_pairs, list):
        findings.append(
            _generic_finding(
                "compile.mirror_map_type",
                "file_pair must be an array of tables",
                identity,
                "/file_pair",
            )
        )
        return [], findings
    pairs: list[tuple[str, str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    seen_paths: dict[str, set[str]] = {"ja": set(), "en": set()}
    for index, item in enumerate(raw_pairs):
        pointer = f"/file_pair/{index}"
        if not isinstance(item, dict) or set(item) != {"ja", "en"}:
            findings.append(
                _generic_finding(
                    "compile.mirror_map_pair",
                    "file pair must contain exactly ja and en",
                    identity,
                    pointer,
                )
            )
            continue
        ja = item.get("ja")
        en = item.get("en")
        if not isinstance(ja, str) or not isinstance(en, str):
            findings.append(
                _generic_finding(
                    "compile.mirror_map_pair",
                    "file pair paths must be strings",
                    identity,
                    pointer,
                )
            )
            continue
        if (
            not _safe_relative(ja)
            or not _safe_relative(en)
            or not _public_identity(ja)
            or not _public_identity(en)
            or not ja.startswith("ja/")
            or not en.startswith("en/")
            or not ja.endswith(".tex")
            or not en.endswith(".tex")
        ):
            findings.append(
                _generic_finding(
                    "compile.mirror_map_path",
                    "file pair paths must be safe manuscript-relative language paths",
                    identity,
                    pointer,
                )
            )
            continue
        pair = (ja, en)
        if pair in seen_pairs or ja in seen_paths["ja"] or en in seen_paths["en"]:
            findings.append(
                _generic_finding(
                    "compile.mirror_map_duplicate",
                    "mirror map repeats a pair or language path",
                    identity,
                    pointer,
                )
            )
            continue
        seen_pairs.add(pair)
        seen_paths["ja"].add(ja)
        seen_paths["en"].add(en)
        pairs.append(pair)
    return pairs, findings


def _parse_terminology(
    content: bytes,
    identity: str,
) -> tuple[list[TerminologyRule], list[CompileFinding]]:
    document, findings = _load_unique_yaml(content, identity, "compile.terminology")
    if not isinstance(document, dict):
        if document is not None:
            findings.append(
                _generic_finding(
                    "compile.terminology_type",
                    "terminology root must be a mapping",
                    identity,
                )
            )
        return [], findings
    for key in document:
        if isinstance(key, str) and key in _TERM_ROOT_KEYS:
            continue
        findings.append(
            _generic_finding(
                "compile.terminology_key",
                "terminology root contains a non-string or unknown key",
                identity,
                _public_key_pointer("", key),
            )
        )
    for key, expected in (("source_language", "ja"), ("target_language", "en")):
        if document.get(key) != expected:
            findings.append(
                _generic_finding(
                    "compile.terminology_language",
                    f"terminology {key} must be {expected}",
                    identity,
                    f"/{key}",
                )
            )
    terms = document.get("terms")
    if not isinstance(terms, list):
        findings.append(
            _generic_finding(
                "compile.terminology_type",
                "terms must be a list",
                identity,
                "/terms",
            )
        )
        return [], findings
    rules: list[TerminologyRule] = []
    seen: set[str] = set()
    for index, raw in enumerate(terms):
        pointer = f"/terms/{index}"
        if not isinstance(raw, dict):
            findings.append(
                _generic_finding(
                    "compile.terminology_type",
                    "terminology rule must be a mapping",
                    identity,
                    pointer,
                )
            )
            continue
        invalid = False
        for key in raw:
            if isinstance(key, str) and key in _TERM_KEYS:
                continue
            findings.append(
                _generic_finding(
                    "compile.terminology_key",
                    "terminology rule contains a non-string or unknown key",
                    identity,
                    _public_key_pointer(pointer, key),
                )
            )
            invalid = True
        term_id = raw.get("id")
        scalar_fields = {
            "id": term_id,
            "ja": raw.get("ja"),
            "en_public": raw.get("en_public"),
            "status": raw.get("status"),
            "first_definition_location": raw.get("first_definition_location", ""),
            "replacement_rule": raw.get("replacement_rule", ""),
            "figure_label_rule": raw.get("figure_label_rule", ""),
            "owner": raw.get("owner", ""),
            "last_reviewed": raw.get("last_reviewed", ""),
        }
        if not all(isinstance(value, str) for value in scalar_fields.values()):
            findings.append(
                _generic_finding(
                    "compile.terminology_type",
                    "terminology scalar fields must be strings",
                    identity,
                    pointer,
                )
            )
            invalid = True
        avoid = raw.get("avoid", [])
        allowed = raw.get("allowed_context", [])
        if not isinstance(avoid, list) or not all(isinstance(item, str) for item in avoid):
            findings.append(
                _generic_finding(
                    "compile.terminology_type",
                    "avoid must be a list of strings",
                    identity,
                    f"{pointer}/avoid",
                )
            )
            invalid = True
            avoid = []
        if not isinstance(allowed, list) or not all(isinstance(item, str) for item in allowed):
            findings.append(
                _generic_finding(
                    "compile.terminology_type",
                    "allowed_context must be a list of strings",
                    identity,
                    f"{pointer}/allowed_context",
                )
            )
            invalid = True
            allowed = []
        required = raw.get("first_definition_required")
        if type(required) is not bool:
            findings.append(
                _generic_finding(
                    "compile.terminology_type",
                    "first_definition_required must be boolean",
                    identity,
                    f"{pointer}/first_definition_required",
                )
            )
            invalid = True
        status = raw.get("status")
        if not isinstance(status, str) or status not in _TERM_STATUSES:
            findings.append(
                _generic_finding(
                    "compile.terminology_status",
                    "terminology status is unsupported",
                    identity,
                    f"{pointer}/status",
                )
            )
            invalid = True
        if isinstance(term_id, str):
            if _TERM_ID_RE.fullmatch(term_id) is None:
                findings.append(
                    _generic_finding(
                        "compile.terminology_id",
                        "terminology rule ID is invalid",
                        identity,
                        f"{pointer}/id",
                    )
                )
                invalid = True
            if term_id in seen:
                findings.append(
                    _generic_finding(
                        "compile.terminology_duplicate_id",
                        "terminology rule ID is duplicated",
                        identity,
                        f"{pointer}/id",
                    )
                )
                invalid = True
            seen.add(term_id)
        location = raw.get("first_definition_location", "")
        if isinstance(location, str) and location and not _safe_relative(location):
            findings.append(
                _generic_finding(
                    "compile.terminology_identity",
                    "first definition location must be project-relative",
                    identity,
                    f"{pointer}/first_definition_location",
                )
            )
            invalid = True
        public_values = [
            str(term_id) if isinstance(term_id, str) else "",
            raw.get("ja", ""),
            raw.get("en_public", ""),
            *avoid,
            *allowed,
            location if isinstance(location, str) else "",
            raw.get("replacement_rule", ""),
            raw.get("figure_label_rule", ""),
        ]
        if any(isinstance(value, str) and _private_public_text(value) for value in public_values):
            findings.append(
                _generic_finding(
                    "compile.privacy_private_public_text",
                    "Writer-facing terminology contains private material",
                    identity,
                    pointer,
                )
            )
            invalid = True
        if invalid:
            continue
        rules.append(
            TerminologyRule(
                term_id=str(term_id),
                ja=str(raw["ja"]),
                en_public=str(raw["en_public"]),
                status=str(status),
                first_definition_required=bool(required),
                first_definition_location=str(location),
                avoid=tuple(avoid),
                allowed_context=tuple(allowed),
                replacement_rule=str(raw.get("replacement_rule", "")),
                figure_label_rule=str(raw.get("figure_label_rule", "")),
            )
        )
    return rules, findings


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _parse_concept_terms(
    content: bytes,
    identity: str,
) -> tuple[list[ConceptTermRule], list[CompileFinding]]:
    text, findings = _decode_utf8(content, identity, "compile.concept_terms_utf8")
    if text is None:
        return [], findings
    lines = text.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if _table_cells(line)[:2] == ["term ID", "canonical term"]
        ),
        -1,
    )
    if header_index < 0 or header_index + 1 >= len(lines):
        return [], [
            *findings,
            _generic_finding(
                "compile.concept_terms_table_missing",
                "concept term map table is missing",
                identity,
            ),
        ]
    rules: list[ConceptTermRule] = []
    seen: set[str] = set()
    for line_number, line in enumerate(lines[header_index + 2 :], start=header_index + 3):
        if not line.strip() or line.lstrip().startswith("#"):
            break
        if not line.lstrip().startswith("|"):
            continue
        cells = _table_cells(line)
        if len(cells) != 8:
            findings.append(
                _generic_finding(
                    "compile.concept_terms_row",
                    "concept term row must contain exactly eight columns",
                    identity,
                    f"/lines/{line_number}",
                )
            )
            continue
        term_id, canonical, status, role, expansion, variants_raw, first_use, notes = cells
        invalid = False
        if not re.fullmatch(r"CT-[0-9]{4,}", term_id):
            findings.append(
                _generic_finding(
                    "compile.concept_terms_id",
                    "concept term ID is invalid",
                    identity,
                    f"/lines/{line_number}/id",
                )
            )
            invalid = True
        if term_id in seen:
            findings.append(
                _generic_finding(
                    "compile.concept_terms_duplicate_id",
                    "concept term ID is duplicated",
                    identity,
                    f"/lines/{line_number}/id",
                )
            )
            invalid = True
        seen.add(term_id)
        if status not in _CONCEPT_STATUSES:
            findings.append(
                _generic_finding(
                    "compile.concept_terms_status",
                    "concept term status is unsupported",
                    identity,
                    f"/lines/{line_number}/status",
                )
            )
            invalid = True
        variants = tuple(
            item.strip()
            for item in re.split(r"\s*[,;]\s*", variants_raw)
            if item.strip()
        )
        public_values = [
            term_id,
            canonical,
            status,
            role,
            expansion,
            *variants,
            first_use.strip("`"),
            notes,
        ]
        if any(_private_public_text(value) for value in public_values):
            findings.append(
                _generic_finding(
                    "compile.privacy_private_public_text",
                    "Writer-facing concept terminology contains private material",
                    identity,
                    f"/lines/{line_number}",
                )
            )
            invalid = True
        if invalid:
            continue
        rules.append(
            ConceptTermRule(
                term_id=term_id,
                canonical_term=canonical,
                status=status,
                manuscript_role=role,
                plain_language_expansion=expansion,
                variants=variants,
                first_use=first_use.strip("`"),
                notes=notes,
            )
        )
    return rules, findings


def _parse_ledger(
    content: bytes,
    identity: str,
) -> tuple[list[dict[str, str]], list[CompileFinding]]:
    document, findings = _load_unique_yaml(content, identity, "compile.mirror_ledger")
    if not isinstance(document, dict):
        if document is not None:
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_type",
                    "mirror ledger root must be a mapping",
                    identity,
                )
            )
        return [], findings
    if set(document) - {"version", "blocks"}:
        findings.append(
            _generic_finding(
                "compile.mirror_ledger_unknown",
                "mirror ledger contains unknown root keys",
                identity,
            )
        )
    if type(document.get("version")) is not int or document.get("version") != 1:
        findings.append(
            _generic_finding(
                "compile.mirror_ledger_type",
                "mirror ledger version must be 1",
                identity,
                "/version",
            )
        )
    blocks = document.get("blocks")
    if not isinstance(blocks, list):
        findings.append(
            _generic_finding(
                "compile.mirror_ledger_type",
                "mirror ledger blocks must be a list",
                identity,
                "/blocks",
            )
        )
        return [], findings
    required = {
        "id",
        "source_file",
        "target_file",
        "source_hash_at_last_sync",
        "target_hash_at_last_sync",
        "status",
        "last_sync",
    }
    entries: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for index, raw in enumerate(blocks):
        pointer = f"/blocks/{index}"
        if not isinstance(raw, dict) or set(raw) != required:
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_entry",
                    "mirror ledger entry has an invalid field set",
                    identity,
                    pointer,
                )
            )
            continue
        string_fields = (
            "id",
            "source_file",
            "target_file",
            "source_hash_at_last_sync",
            "target_hash_at_last_sync",
            "status",
        )
        if not all(isinstance(raw.get(key), str) for key in string_fields):
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_entry",
                    "mirror ledger identity and hash fields must be strings",
                    identity,
                    pointer,
                )
            )
            continue
        source = str(raw["source_file"])
        target = str(raw["target_file"])
        block_id = str(raw["id"])
        ledger_status = str(raw["status"])
        if (
            _BLOCK_RE.fullmatch(f"% block: {block_id}") is None
            or not _safe_relative(source)
            or not _safe_relative(target)
            or not source.startswith("ja/")
            or not target.startswith("en/")
        ):
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_identity",
                    "mirror ledger identities are invalid",
                    identity,
                    pointer,
                )
            )
            continue
        if (
            re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ledger_status) is None
            or _private_public_text(ledger_status)
        ):
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_status",
                    "mirror ledger status is invalid or private",
                    identity,
                    f"{pointer}/status",
                )
            )
            continue
        if not re.fullmatch(r"[0-9a-f]{16}", str(raw["source_hash_at_last_sync"])) or not re.fullmatch(
            r"[0-9a-f]{16}", str(raw["target_hash_at_last_sync"])
        ):
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_legacy_hash",
                    "legacy sync hashes must be exactly 16 lowercase hex characters",
                    identity,
                    pointer,
                )
            )
            continue
        key = (source, target, block_id)
        if key in seen:
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_duplicate",
                    "mirror ledger entry is duplicated",
                    identity,
                    pointer,
                )
            )
            continue
        seen.add(key)
        entries.append({field: str(raw[field]) for field in string_fields})
    return entries, findings


def _parse_analysis_requests(
    files: Sequence[tuple[str, bytes, str]],
) -> tuple[list[AnalysisRequestSnapshot], list[CompileFinding]]:
    requests: list[AnalysisRequestSnapshot] = []
    findings: list[CompileFinding] = []
    seen: set[str] = set()
    for identity, content, content_hash in files:
        if identity.startswith("_paperops/model/issues/analysis/"):
            loaded, parse_findings = _load_unique_yaml(
                content, identity, "compile.analysis_request"
            )
            document = loaded if isinstance(loaded, dict) else None
            if loaded is not None and document is None:
                parse_findings.append(
                    _generic_finding(
                        "compile.analysis_request_document",
                        "typed analysis request must be a mapping",
                        identity,
                    )
                )
        else:
            document, parse_findings = _frontmatter(content, identity)
        findings.extend(parse_findings)
        if document is None:
            continue
        request_id = document.get("id")
        request_type = document.get("record_type", document.get("type"))
        status = document.get("status")
        invalid = False
        if not isinstance(request_id, str) or _ANALYSIS_REQUEST_ID_RE.fullmatch(request_id) is None:
            findings.append(
                _generic_finding(
                    "compile.analysis_request_id",
                    "analysis request ID is invalid",
                    identity,
                    "/id",
                )
            )
            invalid = True
        elif _private_public_text(request_id):
            findings.append(
                _generic_finding(
                    "compile.analysis_request_privacy",
                    "analysis request ID contains private material",
                    identity,
                    "/id",
                )
            )
            invalid = True
        if request_type != "analysis_request":
            findings.append(
                _generic_finding(
                    "compile.analysis_request_type",
                    "analysis request type must be analysis_request",
                    identity,
                    "/type",
                )
            )
            invalid = True
        if not isinstance(status, str) or status not in _ANALYSIS_REQUEST_STATUSES:
            findings.append(
                _generic_finding(
                    "compile.analysis_request_status",
                    "analysis request status is unsupported",
                    identity,
                    "/status",
                )
            )
            invalid = True
        if isinstance(request_id, str) and not _private_public_text(request_id):
            if request_id in seen:
                findings.append(
                    _generic_finding(
                        "compile.analysis_request_duplicate_id",
                        "analysis request ID is duplicated",
                        identity,
                        "/id",
                    )
                )
                invalid = True
            seen.add(request_id)
        if invalid:
            continue
        requests.append(
            AnalysisRequestSnapshot(
                request_id=str(request_id),
                status=str(status),
                identity=identity,
                content_hash=content_hash,
            )
        )
    return requests, findings


def _bib_entries(text: str) -> tuple[list[tuple[str, str]], bool]:
    active = "\n".join(_split_tex_comment(line)[0] for line in text.splitlines())
    entries: list[tuple[str, str]] = []
    invalid = False
    index = 0
    while index < len(active):
        marker = active.find("@", index)
        if marker < 0:
            break
        cursor = marker + 1
        while cursor < len(active) and active[cursor].isalpha():
            cursor += 1
        entry_type = active[marker + 1 : cursor].lower()
        if not entry_type:
            index = marker + 1
            continue
        while cursor < len(active) and active[cursor].isspace():
            cursor += 1
        if cursor >= len(active) or active[cursor] not in "{(":
            index = marker + 1
            continue
        opener = active[cursor]
        body_start = cursor + 1
        cursor = body_start
        stack = ["}" if opener == "{" else ")"]
        quoted = False
        escaped = False
        while cursor < len(active) and stack:
            character = active[cursor]
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif quoted:
                if character == '"':
                    quoted = False
            elif character == '"':
                quoted = True
            elif character == "{":
                stack.append("}")
            elif character == "}" and stack[-1] == "}":
                stack.pop()
            elif character == "(" and stack[-1] == ")":
                stack.append(")")
            elif character == ")" and stack[-1] == ")":
                stack.pop()
            cursor += 1
        if stack or quoted:
            invalid = True
            break
        body = active[body_start : cursor - 1]
        index = cursor
        if entry_type in {"comment", "preamble", "string"}:
            continue
        if "," not in body:
            continue
        key = body.split(",", 1)[0].strip()
        if key and not any(character.isspace() for character in key):
            entries.append((key, entry_type))
    return entries, invalid


def _parse_bibliography_files(
    files: Sequence[tuple[str, bytes, str]],
) -> tuple[list[BibliographyFileSnapshot], list[CompileFinding]]:
    snapshots: list[BibliographyFileSnapshot] = []
    findings: list[CompileFinding] = []
    key_owner: dict[str, str] = {}
    for identity, content, content_hash in files:
        text, decode_findings = _decode_utf8(
            content,
            identity,
            "compile.bibliography_utf8",
        )
        findings.extend(decode_findings)
        if text is None:
            continue
        entries, invalid = _bib_entries(text)
        if invalid:
            findings.append(
                _generic_finding(
                    "compile.bibliography_invalid",
                    "bibliography contains an unclosed top-level entry",
                    identity,
                )
            )
        entries = sorted(entries)
        local_seen: set[str] = set()
        for key, _entry_type in entries:
            if _private_public_text(key):
                findings.append(
                    _generic_finding(
                        "compile.bibliography_key",
                        "bibliography key contains private material",
                        identity,
                    )
                )
                continue
            if key in local_seen or key in key_owner:
                findings.append(
                    _generic_finding(
                        "compile.bibliography_duplicate_key",
                        "bibliography key is duplicated",
                        identity,
                    )
                )
            local_seen.add(key)
            key_owner.setdefault(key, identity)
        snapshots.append(
            BibliographyFileSnapshot(
                identity=identity,
                content_hash=content_hash,
                entry_keys=tuple(sorted(local_seen)),
            )
        )
    return snapshots, findings


def scan_manuscript(
    root: str | Path,
    *,
    _capture_hook: Any | None = None,
) -> ManuscriptSnapshot:
    """Capture manuscript context without mutating TeX, mirror ledger, or cards."""
    project = Path(root).expanduser().absolute()
    map_identity = "manuscript/mirror/map.toml"
    ledger_identity = "manuscript/mirror/block-ledger.yml"
    terminology_identity = "manuscript/mirror/terminology.yml"
    concept_identity = "_paperops/notes/views/concept-terms.md"
    contents: dict[str, bytes] = {}
    read_files: dict[str, ReadFileSnapshot] = {}
    findings: list[CompileFinding] = []
    attempted: set[str] = set()

    def missing_hash(identity: str) -> str:
        return semantic_hash({"identity": identity, "present": False})

    pairs: list[tuple[str, str]] = []
    try:
        with SafeProjectReader(project, hook=_capture_hook) as reader:
            def capture(identity: str, missing_code: str = "") -> bytes | None:
                if identity in contents:
                    return contents[identity]
                if identity in attempted:
                    return None
                attempted.add(identity)
                try:
                    optional_capture = reader.read_optional_file(identity)
                except SafeCaptureError:
                    findings.append(
                        _generic_finding(
                            "compile.manuscript_unsafe_file",
                            "manuscript input is not a safe regular project file",
                            identity,
                        )
                    )
                    return None
                if optional_capture is None:
                    if missing_code:
                        findings.append(
                            _generic_finding(
                                missing_code,
                                "required manuscript input is missing",
                                identity,
                            )
                        )
                    return None
                content, captured = optional_capture
                contents[identity] = content
                read_files[identity] = ReadFileSnapshot(
                    identity=identity,
                    content_hash=captured.content_hash,
                    size=captured.size,
                )
                return content

            def capture_tree(
                identity: str,
                suffixes: tuple[str, ...],
                *,
                excluded: frozenset[str] = frozenset(),
                include: Callable[[str], bool] | None = None,
            ) -> list[str]:
                try:
                    optional_tree = reader.read_optional_tree_files(
                        identity,
                        suffixes=suffixes,
                        include=include,
                    )
                except SafeCaptureError:
                    findings.append(
                        _generic_finding(
                            "compile.manuscript_unsafe_tree",
                            "manuscript discovery tree contains an unsafe entry",
                            identity,
                        )
                    )
                    return []
                if optional_tree is None:
                    return []
                captured_tree = optional_tree
                identities: list[str] = []
                for content, captured in captured_tree:
                    if captured.identity in excluded:
                        continue
                    if not _public_identity(captured.identity):
                        findings.append(
                            _generic_finding(
                                "compile.manuscript_private_identity",
                                "discovered manuscript identity contains private material",
                                identity,
                            )
                        )
                        continue
                    previous = contents.get(captured.identity)
                    if previous is not None and previous != content:
                        findings.append(
                            _generic_finding(
                                "compile.manuscript_capture_changed",
                                "manuscript input changed during capture",
                                captured.identity,
                            )
                        )
                        continue
                    contents[captured.identity] = content
                    read_files[captured.identity] = ReadFileSnapshot(
                        identity=captured.identity,
                        content_hash=captured.content_hash,
                        size=captured.size,
                    )
                    attempted.add(captured.identity)
                    identities.append(captured.identity)
                return identities

            manuscript_identities = capture_tree(
                "manuscript",
                (".tex", ".bib", ".toml", ".yml"),
                include=lambda identity: (
                    not identity.endswith(".bib")
                    or PurePosixPath(identity).parent.as_posix()
                    == "manuscript/shared/bib"
                ),
            )
            for required_identity, missing_code in (
                (map_identity, "compile.mirror_map_missing"),
                (ledger_identity, "compile.mirror_ledger_missing"),
                (terminology_identity, "compile.terminology_missing"),
            ):
                if required_identity not in contents:
                    findings.append(
                        _generic_finding(
                            missing_code,
                            "required manuscript input is missing from the held tree",
                            required_identity,
                        )
                    )
            map_content = contents.get(map_identity)
            if map_content is not None:
                pairs, map_findings = _parse_mirror_map(map_content, map_identity)
                findings.extend(map_findings)

            capture(concept_identity, "compile.concept_terms_missing")
            for ja_relative, en_relative in pairs:
                for relative in (ja_relative, en_relative):
                    identity = f"manuscript/{relative}"
                    if identity not in contents:
                        findings.append(
                            _generic_finding(
                                "compile.mirror_file_missing",
                                "mapped TeX file is missing from the held manuscript tree",
                                identity,
                            )
                        )

            analysis_identities = capture_tree(
                "_paperops/model/issues/analysis",
                (".yml", ".yaml"),
                excluded=frozenset(),
                include=lambda identity: (
                    PurePosixPath(identity).parent.as_posix()
                    == "_paperops/model/issues/analysis"
                ),
            )
            bibliography_identities = [
                identity
                for identity in manuscript_identities
                if identity.endswith(".bib")
            ]
            for bibliography_root in (
                "_paperops/refs/bib/imported",
                "_paperops/refs/bib/curated",
            ):
                bibliography_identities.extend(
                    capture_tree(
                        bibliography_root,
                        (".bib",),
                        include=lambda identity, expected=bibliography_root: (
                            PurePosixPath(identity).parent.as_posix() == expected
                        ),
                    )
                )
            bibliography_identities = sorted(set(bibliography_identities))
    except SafeCaptureError:
        findings.append(
            _generic_finding(
                "compile.manuscript_root_unsafe",
                "project root is missing or unsafe",
                map_identity,
            )
        )
        analysis_identities = []
        bibliography_identities = []

    tex_files: list[TexFileSnapshot] = []
    tex_by_identity: dict[str, TexFileSnapshot] = {}
    for identity in sorted(key for key in contents if key.endswith(".tex")):
        snapshot = parse_tex_bytes(identity, contents[identity])
        tex_files.append(snapshot)
        tex_by_identity[identity] = snapshot
        findings.extend(snapshot.findings)

    file_pairs: list[MirrorFilePairSnapshot] = []
    for index, (ja_relative, en_relative) in enumerate(pairs):
        ja_identity = f"manuscript/{ja_relative}"
        en_identity = f"manuscript/{en_relative}"
        ja = tex_by_identity.get(ja_identity)
        en = tex_by_identity.get(en_identity)
        if ja is None or en is None:
            status = "missing_file"
        elif ja.marker_order == en.marker_order:
            status = "exact"
        elif sorted(ja.marker_order) == sorted(en.marker_order):
            status = "reordered"
            findings.append(
                _generic_finding(
                    "compile.mirror_block_reordered",
                    "JA and EN raw block markers have different order",
                    map_identity,
                    f"/file_pair/{index}",
                )
            )
        else:
            status = "missing_blocks"
            findings.append(
                _generic_finding(
                    "compile.mirror_block_missing",
                    "JA and EN raw block marker sets differ",
                    map_identity,
                    f"/file_pair/{index}",
                )
            )
        file_pairs.append(
            MirrorFilePairSnapshot(
                pair_index=index,
                ja_identity=ja_identity,
                en_identity=en_identity,
                ja_content_hash=ja.content_hash if ja is not None else missing_hash(ja_identity),
                en_content_hash=en.content_hash if en is not None else missing_hash(en_identity),
                ja_marker_order=ja.marker_order if ja is not None else (),
                en_marker_order=en.marker_order if en is not None else (),
                status=status,
            )
        )

    ledger_entries: list[dict[str, str]] = []
    if ledger_identity in contents:
        ledger_entries, ledger_findings = _parse_ledger(
            contents[ledger_identity],
            ledger_identity,
        )
        findings.extend(ledger_findings)
    declared_pair_paths = set(pairs)
    valid_ledger_entries: list[dict[str, str]] = []
    for entry in ledger_entries:
        if (entry["source_file"], entry["target_file"]) not in declared_pair_paths:
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_pair",
                    "mirror ledger row does not belong to a declared map pair",
                    ledger_identity,
                )
            )
            continue
        valid_ledger_entries.append(entry)
    ledger_entries = valid_ledger_entries
    ledger_keys = {
        (entry["source_file"], entry["target_file"], entry["id"])
        for entry in ledger_entries
    }
    bodies_by_identity = {
        identity: _raw_block_bodies(content)
        for identity, content in contents.items()
        if identity.endswith(".tex")
    }
    blocks_by_identity = {
        identity: {block.marker_id: block for block in snapshot.blocks}
        for identity, snapshot in tex_by_identity.items()
        if len(snapshot.marker_order) == len(set(snapshot.marker_order))
    }
    freshness: list[MirrorFreshnessFact] = []
    for entry in ledger_entries:
        source_identity = f"manuscript/{entry['source_file']}"
        target_identity = f"manuscript/{entry['target_file']}"
        block_id = entry["id"]
        source_body = bodies_by_identity.get(source_identity, {}).get(block_id)
        target_body = bodies_by_identity.get(target_identity, {}).get(block_id)
        source_block = blocks_by_identity.get(source_identity, {}).get(block_id)
        target_block = blocks_by_identity.get(target_identity, {}).get(block_id)
        if source_body is None or target_body is None or source_block is None or target_block is None:
            findings.append(
                _generic_finding(
                    "compile.mirror_ledger_missing_block",
                    "mirror ledger refers to a missing or ambiguous raw block",
                    ledger_identity,
                    severity="warning",
                )
            )
            continue
        current_source = _legacy_hash(source_body)
        current_target = _legacy_hash(target_body)
        source_changed = current_source != entry["source_hash_at_last_sync"]
        target_changed = current_target != entry["target_hash_at_last_sync"]
        if source_changed and target_changed:
            status = "both_changed"
            findings.append(
                _generic_finding(
                    "compile.mirror_both_languages_drift",
                    "both language blocks changed since the reviewed legacy ledger entry",
                    ledger_identity,
                    severity="warning",
                )
            )
        elif source_changed:
            status = "source_changed"
            findings.append(
                _generic_finding(
                    "compile.mirror_single_language_drift",
                    "source language block changed without a reviewed ledger update",
                    ledger_identity,
                    severity="warning",
                )
            )
        elif target_changed:
            status = "target_changed"
            findings.append(
                _generic_finding(
                    "compile.mirror_single_language_drift",
                    "target language block changed without a reviewed ledger update",
                    ledger_identity,
                    severity="warning",
                )
            )
        else:
            status = "current"
        freshness.append(
            MirrorFreshnessFact(
                raw_block_id=block_id,
                source_identity=source_identity,
                target_identity=target_identity,
                source_hash_at_last_sync=entry["source_hash_at_last_sync"],
                target_hash_at_last_sync=entry["target_hash_at_last_sync"],
                current_source_legacy_hash=current_source,
                current_target_legacy_hash=current_target,
                source_body_hash=source_block.body_hash,
                target_body_hash=target_block.body_hash,
                source_changed=source_changed,
                target_changed=target_changed,
                status=status,
                ledger_status=entry["status"],
            )
        )

    for ja_relative, en_relative in pairs:
        ja = tex_by_identity.get(f"manuscript/{ja_relative}")
        en = tex_by_identity.get(f"manuscript/{en_relative}")
        if ja is None or en is None:
            continue
        for block_id in sorted(set(ja.marker_order) & set(en.marker_order)):
            if (ja_relative, en_relative, block_id) not in ledger_keys:
                findings.append(
                    _generic_finding(
                        "compile.mirror_ledger_entry_missing",
                        "current mirror block has no reviewed legacy ledger entry",
                        ledger_identity,
                        severity="warning",
                    )
                )

    terminology_rules: list[TerminologyRule] = []
    if terminology_identity in contents:
        terminology_rules, terminology_findings = _parse_terminology(
            contents[terminology_identity],
            terminology_identity,
        )
        findings.extend(terminology_findings)
    concept_terms: list[ConceptTermRule] = []
    if concept_identity in contents:
        concept_terms, concept_findings = _parse_concept_terms(
            contents[concept_identity],
            concept_identity,
        )
        findings.extend(concept_findings)

    analysis_files = [
        (identity, contents[identity], read_files[identity].content_hash)
        for identity in analysis_identities
        if identity in contents
    ]
    analysis_requests, analysis_findings = _parse_analysis_requests(analysis_files)
    findings.extend(analysis_findings)
    bibliography_inputs = [
        (identity, contents[identity], read_files[identity].content_hash)
        for identity in bibliography_identities
        if identity in contents
    ]
    bibliography_files, bibliography_findings = _parse_bibliography_files(
        bibliography_inputs
    )
    findings.extend(bibliography_findings)
    bibliography_keys = {
        key for bibliography in bibliography_files for key in bibliography.entry_keys
    }
    missing_citations: set[tuple[str, str]] = set()
    for identity, snapshot in tex_by_identity.items():
        if identity.startswith("manuscript/shared/style/"):
            continue
        text, _ = _decode_utf8(contents[identity], identity, "compile.tex_utf8")
        if text is None:
            continue
        for key in _citations(_uncomment(text)):
            if key not in bibliography_keys and (identity, key) not in missing_citations:
                missing_citations.add((identity, key))
                findings.append(
                    _generic_finding(
                        "compile.citation_missing",
                        "TeX citation key is absent from the captured bibliography registry",
                        identity,
                    )
                )

    ordered_read_files = tuple(read_files[key] for key in sorted(read_files))
    material = {
        "read_files": [item.to_dict() for item in ordered_read_files],
        "tex_files": [item.to_dict() for item in tex_files],
        "file_pairs": [item.to_dict() for item in file_pairs],
        "freshness": [item.to_dict() for item in freshness],
        "terminology_rules": [item.to_dict() for item in terminology_rules],
        "concept_terms": [item.to_dict() for item in concept_terms],
        "analysis_requests": [item.to_dict() for item in analysis_requests],
        "bibliography_files": [item.to_dict() for item in bibliography_files],
        "findings": [finding.to_dict() for finding in findings],
    }
    return ManuscriptSnapshot(
        read_files=ordered_read_files,
        tex_files=tuple(tex_files),
        file_pairs=tuple(file_pairs),
        freshness=tuple(freshness),
        terminology_rules=tuple(terminology_rules),
        concept_terms=tuple(concept_terms),
        analysis_requests=tuple(analysis_requests),
        bibliography_files=tuple(bibliography_files),
        findings=tuple(findings),
        snapshot_hash=semantic_hash(material),
    )


def bind_typed_tex_blocks(
    snapshot: ManuscriptSnapshot,
    typed_blocks: Sequence[Mapping[str, object]],
) -> TexBindingResult:
    """Bind typed BLK identities only through explicit ja/en raw marker fields."""
    if not isinstance(snapshot, ManuscriptSnapshot):
        raise TypeError("snapshot must be a ManuscriptSnapshot")
    if isinstance(typed_blocks, (str, bytes, bytearray)) or not isinstance(
        typed_blocks,
        Sequence,
    ):
        raise TypeError("typed_blocks must be a sequence of mappings")
    lookup: dict[tuple[str, str], list[tuple[TexFileSnapshot, TexBlockSnapshot]]] = {}
    for tex_file in snapshot.tex_files:
        language = ""
        if tex_file.identity.startswith("manuscript/ja/"):
            language = "ja"
        elif tex_file.identity.startswith("manuscript/en/"):
            language = "en"
        if not language:
            continue
        for block in tex_file.blocks:
            lookup.setdefault((language, block.marker_id), []).append((tex_file, block))

    bindings: list[TexBlockBinding] = []
    findings: list[CompileFinding] = []
    seen_typed: set[str] = set()
    used_raw: dict[tuple[str, str], str] = {}
    declared_pairs = {
        (pair.ja_identity, pair.en_identity)
        for pair in snapshot.file_pairs
    }
    for index, document in enumerate(typed_blocks):
        pointer = f"/blocks/{index}"
        if not isinstance(document, Mapping):
            findings.append(
                _generic_finding(
                    "compile.tex_binding_type",
                    "typed block binding input must be a mapping",
                    "",
                    pointer,
                )
            )
            continue
        typed_id = document.get("id")
        if not isinstance(typed_id, str) or _TYPED_BLOCK_ID_RE.fullmatch(typed_id) is None:
            findings.append(
                _generic_finding(
                    "compile.tex_binding_typed_id",
                    "typed block ID must match BLK-[0-9]{4,}",
                    "",
                    f"{pointer}/id",
                )
            )
            continue
        if typed_id in seen_typed:
            findings.append(
                _generic_finding(
                    "compile.tex_binding_duplicate_typed_id",
                    "typed block ID is duplicated in binding input",
                    "",
                    f"{pointer}/id",
                )
            )
            continue
        seen_typed.add(typed_id)
        pending: list[
            tuple[str, str, TexFileSnapshot, TexBlockSnapshot]
        ] = []
        block_findings: list[CompileFinding] = []
        for language in ("ja", "en"):
            field = f"{language}_tex_block_id"
            raw_id = document.get(field)
            if not isinstance(raw_id, str) or _BLOCK_RE.fullmatch(f"% block: {raw_id}") is None:
                block_findings.append(
                    _generic_finding(
                        "compile.tex_binding_raw_id",
                        "explicit raw TeX block ID is missing or invalid",
                        "",
                        f"{pointer}/{field}",
                    )
                )
                continue
            raw_key = (language, raw_id)
            if raw_key in used_raw:
                block_findings.append(
                    _generic_finding(
                        "compile.tex_binding_reused_raw",
                        "one explicit raw TeX marker cannot bind multiple typed blocks",
                        "",
                        f"{pointer}/{field}",
                    )
                )
                continue
            matches = lookup.get((language, raw_id), [])
            if not matches:
                block_findings.append(
                    _generic_finding(
                        "compile.tex_binding_missing",
                        "explicit raw TeX block marker was not captured",
                        "",
                        f"{pointer}/{field}",
                    )
                )
                continue
            if len(matches) != 1:
                block_findings.append(
                    _generic_finding(
                        "compile.tex_binding_ambiguous",
                        "explicit raw TeX block marker is ambiguous",
                        "",
                        f"{pointer}/{field}",
                    )
                )
                continue
            tex_file, block = matches[0]
            pending.append((language, raw_id, tex_file, block))
        if block_findings:
            findings.extend(block_findings)
            continue
        if len(pending) != 2:
            continue
        by_language = {item[0]: item for item in pending}
        ja_file = by_language["ja"][2]
        en_file = by_language["en"][2]
        if (ja_file.identity, en_file.identity) not in declared_pairs:
            findings.append(
                _generic_finding(
                    "compile.tex_binding_pair",
                    "explicit JA and EN markers must belong to one declared map pair",
                    "",
                    pointer,
                )
            )
            continue
        for language, raw_id, tex_file, block in pending:
            used_raw[(language, raw_id)] = typed_id
            bindings.append(
                TexBlockBinding(
                    typed_block_id=typed_id,
                    language=language,
                    raw_block_id=raw_id,
                    file_identity=tex_file.identity,
                    marker_index=block.marker_index,
                    body_hash=block.body_hash,
                    region_hash=block.region_hash,
                )
            )
    return TexBindingResult(tuple(bindings), tuple(findings))


def _hash(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def _validate_identity(identity: str) -> None:
    if not isinstance(identity, str) or not identity or "\x00" in identity or "\\" in identity:
        raise ValueError("identity must be a safe project-relative identity")
    posix = PurePosixPath(identity)
    windows = PureWindowsPath(identity)
    if (
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or windows.root
        or identity != posix.as_posix()
        or any(part in {"", ".", ".."} for part in posix.parts)
    ):
        raise ValueError("identity must be a safe project-relative identity")


def _split_tex_comment(line: str) -> tuple[str, str]:
    escaped = False
    for index, character in enumerate(line):
        if character == "%" and not escaped:
            return line[:index], line[index + 1 :]
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    return line, ""


def _uncomment(text: str) -> str:
    return "\n".join(_split_tex_comment(line)[0] for line in text.splitlines())


def _consume_optional_groups(text: str, index: int) -> int:
    while index < len(text) and text[index].isspace():
        index += 1
    while index < len(text) and text[index] == "[":
        depth = 1
        index += 1
        while index < len(text) and depth:
            if text[index] == "[":
                depth += 1
            elif text[index] == "]":
                depth -= 1
            index += 1
        while index < len(text) and text[index].isspace():
            index += 1
    return index


def _consume_brace_group(text: str, index: int) -> tuple[str | None, int]:
    if index >= len(text) or text[index] != "{":
        return None, index
    depth = 1
    index += 1
    start = index
    while index < len(text) and depth:
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index], index + 1
        index += 1
    return None, index


def _citations(text: str) -> tuple[str, ...]:
    keys: list[str] = []
    for match in _CITE_COMMAND_RE.finditer(text):
        command = match.group("command")
        if command not in _CITE_COMMANDS:
            continue
        index = match.end()
        while True:
            index = _consume_optional_groups(text, index)
            group, index = _consume_brace_group(text, index)
            if group is None:
                break
            keys.extend(key.strip() for key in group.split(",") if key.strip())
            if not command.endswith("s"):
                break
    return tuple(keys)


def _detach_tuple_fields(instance: object, *names: str) -> None:
    for name in names:
        object.__setattr__(instance, name, tuple(getattr(instance, name)))


@dataclass(frozen=True)
class QuantityHit:
    value: int
    denominator: int
    literal: str
    line_number: int

    def to_dict(self) -> dict[str, object]:
        return {
            "value": self.value,
            "denominator": self.denominator,
            "literal": self.literal,
            "line_number": self.line_number,
        }


@dataclass(frozen=True)
class PredictedMarkerHit:
    name: str
    body_hash: str
    line_number: int
    analysis_request_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "analysis_request_ids")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "body_hash": self.body_hash,
            "line_number": self.line_number,
            "analysis_request_ids": list(self.analysis_request_ids),
        }


@dataclass(frozen=True)
class PlaceholderHit:
    literal: str
    line_number: int

    def to_dict(self) -> dict[str, object]:
        return {"literal": self.literal, "line_number": self.line_number}


@dataclass(frozen=True)
class AuthoringIntentHit:
    kind: str
    line_number: int

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "line_number": self.line_number}


@dataclass(frozen=True)
class BlockInventory:
    citation_keys: tuple[str, ...]
    quantities: tuple[QuantityHit, ...]
    figure_labels: tuple[str, ...]
    figure_references: tuple[str, ...]
    predicted_markers: tuple[PredictedMarkerHit, ...]
    analysis_request_ids: tuple[str, ...]
    placeholders: tuple[PlaceholderHit, ...]
    authoring_intents: tuple[AuthoringIntentHit, ...]

    def __post_init__(self) -> None:
        _detach_tuple_fields(
            self,
            "citation_keys",
            "quantities",
            "figure_labels",
            "figure_references",
            "predicted_markers",
            "analysis_request_ids",
            "placeholders",
            "authoring_intents",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "citation_keys": list(self.citation_keys),
            "quantities": [item.to_dict() for item in self.quantities],
            "figure_labels": list(self.figure_labels),
            "figure_references": list(self.figure_references),
            "predicted_markers": [item.to_dict() for item in self.predicted_markers],
            "analysis_request_ids": list(self.analysis_request_ids),
            "placeholders": [item.to_dict() for item in self.placeholders],
            "authoring_intents": [item.to_dict() for item in self.authoring_intents],
        }


@dataclass(frozen=True)
class TexBlockSnapshot:
    marker_id: str
    marker_index: int
    marker_line: int
    marker_hash: str
    body_hash: str
    region_hash: str
    inventory: BlockInventory
    protected_hashes: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "protected_hashes",
            MappingProxyType(dict(self.protected_hashes)),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "marker_id": self.marker_id,
            "marker_index": self.marker_index,
            "marker_line": self.marker_line,
            "marker_hash": self.marker_hash,
            "body_hash": self.body_hash,
            "region_hash": self.region_hash,
            "inventory": self.inventory.to_dict(),
            "protected_hashes": dict(self.protected_hashes),
        }


@dataclass(frozen=True)
class TexFileSnapshot:
    identity: str
    content_hash: str
    marker_order: tuple[str, ...]
    blocks: tuple[TexBlockSnapshot, ...]
    findings: tuple[CompileFinding, ...]

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "marker_order", "blocks", "findings")

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "content_hash": self.content_hash,
            "marker_order": list(self.marker_order),
            "blocks": [block.to_dict() for block in self.blocks],
            "findings": [finding.to_dict() for finding in self.findings],
        }


@dataclass(frozen=True)
class ReadFileSnapshot:
    identity: str
    content_hash: str
    size: int

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "content_hash": self.content_hash,
            "size": self.size,
        }


@dataclass(frozen=True)
class MirrorFilePairSnapshot:
    pair_index: int
    ja_identity: str
    en_identity: str
    ja_content_hash: str
    en_content_hash: str
    ja_marker_order: tuple[str, ...]
    en_marker_order: tuple[str, ...]
    status: str

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "ja_marker_order", "en_marker_order")

    def to_dict(self) -> dict[str, object]:
        return {
            "pair_index": self.pair_index,
            "ja_identity": self.ja_identity,
            "en_identity": self.en_identity,
            "ja_content_hash": self.ja_content_hash,
            "en_content_hash": self.en_content_hash,
            "ja_marker_order": list(self.ja_marker_order),
            "en_marker_order": list(self.en_marker_order),
            "status": self.status,
        }


@dataclass(frozen=True)
class MirrorFreshnessFact:
    raw_block_id: str
    source_identity: str
    target_identity: str
    source_hash_at_last_sync: str
    target_hash_at_last_sync: str
    current_source_legacy_hash: str
    current_target_legacy_hash: str
    source_body_hash: str
    target_body_hash: str
    source_changed: bool
    target_changed: bool
    status: str
    ledger_status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "raw_block_id": self.raw_block_id,
            "source_identity": self.source_identity,
            "target_identity": self.target_identity,
            "source_hash_at_last_sync": self.source_hash_at_last_sync,
            "target_hash_at_last_sync": self.target_hash_at_last_sync,
            "current_source_legacy_hash": self.current_source_legacy_hash,
            "current_target_legacy_hash": self.current_target_legacy_hash,
            "source_body_hash": self.source_body_hash,
            "target_body_hash": self.target_body_hash,
            "source_changed": self.source_changed,
            "target_changed": self.target_changed,
            "status": self.status,
            "ledger_status": self.ledger_status,
        }


@dataclass(frozen=True)
class TerminologyRule:
    term_id: str
    ja: str
    en_public: str
    status: str
    first_definition_required: bool
    first_definition_location: str
    avoid: tuple[str, ...]
    allowed_context: tuple[str, ...]
    replacement_rule: str
    figure_label_rule: str

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "avoid", "allowed_context")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.term_id,
            "ja": self.ja,
            "en_public": self.en_public,
            "status": self.status,
            "first_definition_required": self.first_definition_required,
            "first_definition_location": self.first_definition_location,
            "avoid": list(self.avoid),
            "allowed_context": list(self.allowed_context),
            "replacement_rule": self.replacement_rule,
            "figure_label_rule": self.figure_label_rule,
        }


@dataclass(frozen=True)
class ConceptTermRule:
    term_id: str
    canonical_term: str
    status: str
    manuscript_role: str
    plain_language_expansion: str
    variants: tuple[str, ...]
    first_use: str
    notes: str

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "variants")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.term_id,
            "canonical_term": self.canonical_term,
            "status": self.status,
            "manuscript_role": self.manuscript_role,
            "plain_language_expansion": self.plain_language_expansion,
            "variants": list(self.variants),
            "first_use": self.first_use,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class AnalysisRequestSnapshot:
    request_id: str
    status: str
    identity: str
    content_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.request_id,
            "status": self.status,
            "identity": self.identity,
            "content_hash": self.content_hash,
        }


@dataclass(frozen=True)
class BibliographyFileSnapshot:
    identity: str
    content_hash: str
    entry_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "entry_keys")

    def to_dict(self) -> dict[str, object]:
        return {
            "identity": self.identity,
            "content_hash": self.content_hash,
            "entry_keys": list(self.entry_keys),
        }


@dataclass(frozen=True)
class ManuscriptSnapshot:
    read_files: tuple[ReadFileSnapshot, ...]
    tex_files: tuple[TexFileSnapshot, ...]
    file_pairs: tuple[MirrorFilePairSnapshot, ...]
    freshness: tuple[MirrorFreshnessFact, ...]
    terminology_rules: tuple[TerminologyRule, ...]
    concept_terms: tuple[ConceptTermRule, ...]
    analysis_requests: tuple[AnalysisRequestSnapshot, ...]
    bibliography_files: tuple[BibliographyFileSnapshot, ...]
    findings: tuple[CompileFinding, ...]
    snapshot_hash: str

    def __post_init__(self) -> None:
        _detach_tuple_fields(
            self,
            "read_files",
            "tex_files",
            "file_pairs",
            "freshness",
            "terminology_rules",
            "concept_terms",
            "analysis_requests",
            "bibliography_files",
            "findings",
        )

    @property
    def read_paths(self) -> tuple[str, ...]:
        return tuple(item.identity for item in self.read_files)

    def to_dict(self) -> dict[str, object]:
        return {
            "read_files": [item.to_dict() for item in self.read_files],
            "tex_files": [item.to_dict() for item in self.tex_files],
            "file_pairs": [item.to_dict() for item in self.file_pairs],
            "freshness": [item.to_dict() for item in self.freshness],
            "terminology_rules": [item.to_dict() for item in self.terminology_rules],
            "concept_terms": [item.to_dict() for item in self.concept_terms],
            "analysis_requests": [item.to_dict() for item in self.analysis_requests],
            "bibliography_files": [item.to_dict() for item in self.bibliography_files],
            "findings": [finding.to_dict() for finding in self.findings],
            "snapshot_hash": self.snapshot_hash,
        }


@dataclass(frozen=True)
class TexBlockBinding:
    typed_block_id: str
    language: str
    raw_block_id: str
    file_identity: str
    marker_index: int
    body_hash: str
    region_hash: str

    def to_dict(self) -> dict[str, object]:
        return {
            "typed_block_id": self.typed_block_id,
            "language": self.language,
            "raw_block_id": self.raw_block_id,
            "file_identity": self.file_identity,
            "marker_index": self.marker_index,
            "body_hash": self.body_hash,
            "region_hash": self.region_hash,
        }


@dataclass(frozen=True)
class TexBindingResult:
    bindings: tuple[TexBlockBinding, ...]
    findings: tuple[CompileFinding, ...]

    def __post_init__(self) -> None:
        _detach_tuple_fields(self, "bindings", "findings")

    def to_dict(self) -> dict[str, object]:
        return {
            "bindings": [binding.to_dict() for binding in self.bindings],
            "findings": [finding.to_dict() for finding in self.findings],
        }


def _ordered_unique(values: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _inventory(
    body: str,
    first_line: int,
) -> tuple[BlockInventory, tuple[str, ...], tuple[int, ...]]:
    prose = _uncomment(body)
    quantities: list[QuantityHit] = []
    invalid_quantity_lines: list[int] = []
    quantity_line = first_line
    quantity_cursor = 0
    for match in _COUNT_OF_RE.finditer(prose):
        quantity_line += prose.count("\n", quantity_cursor, match.start())
        quantity_cursor = match.end()
        line_number = quantity_line
        quantity_line += prose.count("\n", match.start(), match.end())
        if (
            len(match.group("value")) > _MAX_QUANTITY_DIGITS
            or len(match.group("denominator")) > _MAX_QUANTITY_DIGITS
        ):
            invalid_quantity_lines.append(line_number)
            continue
        try:
            value = int(match.group("value"))
            denominator = int(match.group("denominator"))
        except ValueError:
            invalid_quantity_lines.append(line_number)
            continue
        quantities.append(
            QuantityHit(
                value=value,
                denominator=denominator,
                literal=match.group(0),
                line_number=line_number,
            )
        )
    private_categories: list[str] = []
    citation_keys: list[str] = []
    for key in _citations(prose):
        if _private_public_text(key):
            private_categories.append("citations")
        else:
            citation_keys.append(key)
    labels: list[str] = []
    for match in _FIGURE_LABEL_RE.finditer(prose):
        label = match.group("label").strip()
        if _FIGURE_ID_RE.fullmatch(label) is None or _private_public_text(label):
            private_categories.append("figure_labels")
        else:
            labels.append(label)
    references: list[str] = []
    for match in _FIGURE_REF_RE.finditer(prose):
        for raw_label in match.group("labels").split(","):
            label = raw_label.strip()
            if not label.startswith("fig:"):
                continue
            if _FIGURE_ID_RE.fullmatch(label) is None or _private_public_text(label):
                private_categories.append("figure_references")
            else:
                references.append(label)

    predicted: list[PredictedMarkerHit] = []
    request_ids: list[str] = []
    placeholders: list[PlaceholderHit] = []
    authoring: list[AuthoringIntentHit] = []
    allow_next_content_line = False
    for offset, raw_line in enumerate(body.splitlines(), start=first_line):
        marker = _PREDICTED_RE.search(raw_line)
        if marker:
            marker_request_ids: list[str] = []
            for request_id in _AREQ_RE.findall(marker.group("body")):
                if _private_public_text(request_id):
                    private_categories.append("analysis_requests")
                else:
                    marker_request_ids.append(request_id)
            predicted.append(
                PredictedMarkerHit(
                    name=marker.group("name"),
                    body_hash=_hash(marker.group("body").strip().encode("utf-8")),
                    line_number=offset,
                    analysis_request_ids=_ordered_unique(marker_request_ids),
                )
            )
        for request_id in _AREQ_RE.findall(raw_line):
            if _private_public_text(request_id):
                private_categories.append("analysis_requests")
            else:
                request_ids.append(request_id)
        prose_line, comment = _split_tex_comment(raw_line)
        for hit in _PLACEHOLDER_RE.finditer(prose_line):
            placeholders.append(PlaceholderHit(hit.group(0), offset))
        if _SUPPRESSION_RE.search(comment):
            if not prose_line.strip():
                allow_next_content_line = True
            continue
        if not prose_line.strip():
            continue
        if allow_next_content_line:
            allow_next_content_line = False
            continue
        for kind, pattern in _AUTHORING_PATTERNS:
            if pattern.search(prose_line):
                authoring.append(AuthoringIntentHit(kind, offset))
                break

    inventory = BlockInventory(
        citation_keys=tuple(citation_keys),
        quantities=tuple(quantities),
        figure_labels=tuple(labels),
        figure_references=tuple(references),
        predicted_markers=tuple(predicted),
        analysis_request_ids=_ordered_unique(request_ids),
        placeholders=tuple(placeholders),
        authoring_intents=tuple(authoring),
    )
    return (
        inventory,
        _ordered_unique(private_categories),
        tuple(invalid_quantity_lines),
    )


def _protected_hashes(inventory: BlockInventory) -> dict[str, str]:
    quantities = [
        {
            "value": item.value,
            "denominator": item.denominator,
            "literal": item.literal,
        }
        for item in inventory.quantities
    ]
    predicted_markers = [
        {
            "name": item.name,
            "body_hash": item.body_hash,
            "analysis_request_ids": list(item.analysis_request_ids),
        }
        for item in inventory.predicted_markers
    ]
    return {
        "citations": semantic_hash(list(inventory.citation_keys)),
        "quantities": semantic_hash(quantities),
        "figure_labels": semantic_hash(list(inventory.figure_labels)),
        "figure_references": semantic_hash(list(inventory.figure_references)),
        "predicted_markers": semantic_hash(predicted_markers),
        "analysis_requests": semantic_hash(list(inventory.analysis_request_ids)),
        "placeholders": semantic_hash([item.literal for item in inventory.placeholders]),
        "authoring_intents": semantic_hash([item.kind for item in inventory.authoring_intents]),
    }


def parse_tex_bytes(identity: str, content: bytes) -> TexFileSnapshot:
    """Parse one UTF-8 TeX file from bytes without filesystem access."""
    _validate_identity(identity)
    if not _public_identity(identity):
        raise ValueError("identity must be a public project-relative identity")
    if not isinstance(content, bytes):
        raise TypeError("content must be bytes")
    content_hash = _hash(content)
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        finding = CompileFinding(
            code="compile.tex_utf8",
            pointer="",
            message="TeX source must be UTF-8",
            severity="error",
            identity=identity,
        )
        return TexFileSnapshot(identity, content_hash, (), (), (finding,))

    lines = text.splitlines(keepends=True)
    markers: list[tuple[str, int, str]] = []
    findings: list[CompileFinding] = []
    for line_index, line in enumerate(lines):
        without_newline = line.rstrip("\r\n")
        match = _BLOCK_RE.fullmatch(without_newline)
        if match:
            if _private_public_text(match.group("block_id")):
                findings.append(
                    _generic_finding(
                        "compile.privacy_private_public_text",
                        "raw TeX block ID contains private material",
                        identity,
                        f"/lines/{line_index + 1}",
                    )
                )
                continue
            markers.append((match.group("block_id"), line_index, line))
            continue
        if _BLOCK_PREFIX_RE.match(without_newline):
            findings.append(
                CompileFinding(
                    code="compile.tex_invalid_block_id",
                    pointer=f"/lines/{line_index + 1}",
                    message="raw TeX block ID must match [A-Za-z0-9:._-]+",
                    severity="error",
                    identity=identity,
                )
            )

    seen: dict[str, int] = {}
    blocks: list[TexBlockSnapshot] = []
    for marker_index, (marker_id, line_index, marker_line) in enumerate(markers):
        if marker_id in seen:
            findings.append(
                CompileFinding(
                    code="compile.tex_duplicate_block",
                    pointer=f"/blocks/{marker_index}/marker_id",
                    message="raw TeX block marker is duplicated in one file",
                    severity="error",
                    identity=identity,
                )
            )
        else:
            seen[marker_id] = marker_index
        next_line_index = (
            markers[marker_index + 1][1]
            if marker_index + 1 < len(markers)
            else len(lines)
        )
        body = "".join(lines[line_index + 1 : next_line_index])
        region = marker_line + body
        inventory, private_categories, invalid_quantity_lines = _inventory(
            body,
            line_index + 2,
        )
        for invalid_line in invalid_quantity_lines:
            findings.append(
                _generic_finding(
                    "compile.tex_quantity_invalid",
                    "quantity literal exceeds the supported numeric bound",
                    identity,
                    f"/lines/{invalid_line}",
                )
            )
        for category in private_categories:
            findings.append(
                _generic_finding(
                    "compile.privacy_private_public_text",
                    "TeX public reference inventory contains private material",
                    identity,
                    f"/blocks/{marker_index}/inventory/{category}",
                )
            )
        blocks.append(
            TexBlockSnapshot(
                marker_id=marker_id,
                marker_index=marker_index,
                marker_line=line_index + 1,
                marker_hash=_hash(marker_line.encode("utf-8")),
                body_hash=_hash(body.encode("utf-8")),
                region_hash=_hash(region.encode("utf-8")),
                inventory=inventory,
                protected_hashes=_protected_hashes(inventory),
            )
        )

    return TexFileSnapshot(
        identity=identity,
        content_hash=content_hash,
        marker_order=tuple(marker_id for marker_id, _line, _raw in markers),
        blocks=tuple(blocks),
        findings=tuple(findings),
    )


__all__ = [
    "AnalysisRequestSnapshot",
    "AuthoringIntentHit",
    "BibliographyFileSnapshot",
    "BlockInventory",
    "ConceptTermRule",
    "ManuscriptSnapshot",
    "MirrorFilePairSnapshot",
    "MirrorFreshnessFact",
    "PlaceholderHit",
    "PredictedMarkerHit",
    "QuantityHit",
    "ReadFileSnapshot",
    "TerminologyRule",
    "TexBindingResult",
    "TexBlockBinding",
    "TexBlockSnapshot",
    "TexFileSnapshot",
    "bind_typed_tex_blocks",
    "parse_tex_bytes",
    "scan_manuscript",
]
