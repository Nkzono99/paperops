"""Dependency-free reader for explicitly structured legacy Markdown cards."""

from __future__ import annotations

import hashlib
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .types import MigrationFinding


_DEFINITION = re.compile(r"^\s*[-*]\s+([^:]+):\s*(.*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_TABLE_DELIMITER = re.compile(r"^:?-{3,}:?$")
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_ABSOLUTE_VALUE = re.compile(r"^/(?:[^/]+/)*[^/]+$")
_CREDENTIAL_URL = re.compile(r"^[a-z][a-z0-9+.-]*://[^/@\s]+:[^/@\s]+@", re.I)
_PRIVATE_NAME = re.compile(r"(?:raw|private|local).*(?:path|location)|password|secret|token", re.I)


@dataclass(frozen=True)
class LegacyValue:
    value: str | tuple[str, ...]
    pointer: str
    line: int


@dataclass(frozen=True)
class LegacyTable:
    headers: tuple[str, ...]
    rows: tuple[dict[str, str], ...]
    pointer: str
    line: int


@dataclass(frozen=True)
class LegacySection:
    title: str
    pointer: str
    line: int
    definitions: dict[str, LegacyValue]
    tables: tuple[LegacyTable, ...]


@dataclass(frozen=True)
class LegacyCard:
    source_path: str
    source_hash: str
    frontmatter: dict[str, LegacyValue]
    sections: tuple[LegacySection, ...]
    findings: tuple[MigrationFinding, ...]


@dataclass(frozen=True)
class LegacyInventory:
    cards: tuple[LegacyCard, ...]
    findings: tuple[MigrationFinding, ...]


class LegacyReadError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _parse_scalar(value: str) -> str | tuple[str, ...]:
    rendered = value.strip()
    if len(rendered) >= 2 and rendered[0] == rendered[-1] and rendered[0] in {'"', "'"}:
        return rendered[1:-1]
    if rendered.startswith("[") and rendered.endswith("]"):
        inner = rendered[1:-1].strip()
        if not inner:
            return ()
        return tuple(part.strip().strip('"\'') for part in inner.split(","))
    return rendered


def _values(value: str | tuple[str, ...]) -> Iterable[str]:
    return value if isinstance(value, tuple) else (value,)


def _confidential(name: str, value: str | tuple[str, ...]) -> bool:
    return any(
        item
        and (
            _CREDENTIAL_URL.match(item)
            or _WINDOWS_ABSOLUTE.match(item)
            or _ABSOLUTE_VALUE.match(item)
            or (_PRIVATE_NAME.search(name) and item not in {"none", "n/a"})
        )
        for item in _values(value)
    )


def _finding(
    code: str,
    source_path: str,
    pointer: str,
    message: str,
    *,
    severity: str = "error",
) -> MigrationFinding:
    return MigrationFinding(code, pointer, message, severity, source_path)


def load_legacy_card(path: Path, *, project_root: Path | None = None) -> LegacyCard:
    try:
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise LegacyReadError("migration.missing", "legacy card is missing") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise LegacyReadError("migration.path", "legacy card must be a regular file")
    content = path.read_bytes()
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise LegacyReadError("migration.encoding", "legacy card must be UTF-8") from error
    if project_root is None:
        source_path = path.name
    else:
        try:
            relative = path.absolute().relative_to(project_root.absolute())
            _safe_root(project_root.absolute(), relative)
            source_path = relative.as_posix()
        except ValueError as error:
            raise LegacyReadError("migration.path", "legacy card escapes project root") from error
    source_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
    lines = text.splitlines()
    findings: list[MigrationFinding] = []
    frontmatter: dict[str, LegacyValue] = {}
    body_start = 0
    if lines and lines[0].strip() == "---":
        try:
            end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
        except StopIteration:
            findings.append(
                _finding(
                    "migration.unknown_field",
                    source_path,
                    "/frontmatter",
                    "front matter is not terminated",
                )
            )
            end = len(lines)
        def store_frontmatter(name: str, value: str | tuple[str, ...], line: int) -> None:
            pointer = f"/frontmatter/{_pointer_token(name)}"
            if name in frontmatter:
                findings.append(
                    _finding(
                        "migration.duplicate",
                        source_path,
                        pointer,
                        f"front matter key `{name}` is duplicated",
                    )
                )
                return
            frontmatter[name] = LegacyValue(value, pointer, line)
            if _confidential(name, value):
                findings.append(
                    _finding(
                        "migration.confidential",
                        source_path,
                        pointer,
                        "confidential or local-only value requires an explicit disposition",
                        severity="warning",
                    )
                )

        index = 1
        while index < end:
            raw = lines[index]
            if not raw.strip() or raw.lstrip().startswith("#"):
                index += 1
                continue
            if ":" not in raw or raw.startswith((" ", "\t", "-")):
                findings.append(
                    _finding(
                        "migration.unknown_field",
                        source_path,
                        f"/frontmatter/line-{index + 1}",
                        "front matter line is not a supported scalar or inline list",
                    )
                )
                index += 1
                continue
            name, raw_value = raw.split(":", 1)
            name = name.strip()
            if raw_value.strip():
                store_frontmatter(name, _parse_scalar(raw_value), index + 1)
                index += 1
                continue
            child_index = index + 1
            children: list[tuple[int, str]] = []
            while child_index < end:
                child = lines[child_index]
                if not child.strip():
                    child_index += 1
                    continue
                if not child.startswith((" ", "\t")):
                    break
                children.append((child_index + 1, child.strip()))
                child_index += 1
            if children and all(child.startswith("- ") for _, child in children):
                store_frontmatter(
                    name,
                    tuple(child[2:].strip().strip('"\'') for _, child in children),
                    index + 1,
                )
            elif children and all(":" in child and not child.startswith("-") for _, child in children):
                for line, child in children:
                    child_name, child_value = child.split(":", 1)
                    store_frontmatter(
                        f"{name}.{child_name.strip()}",
                        _parse_scalar(child_value),
                        line,
                    )
            elif children:
                findings.append(
                    _finding(
                        "migration.unknown_field",
                        source_path,
                        f"/frontmatter/{_pointer_token(name)}",
                        "nested front matter must be a flat mapping or scalar list",
                    )
                )
            else:
                store_frontmatter(name, "", index + 1)
            index = child_index
        body_start = min(end + 1, len(lines))

    sections: list[LegacySection] = []
    title = "Document"
    section_line = body_start + 1
    section_pointer = "/document"
    definitions: dict[str, LegacyValue] = {}
    tables: list[LegacyTable] = []
    unknown_lines: list[int] = []

    def finish_section() -> None:
        nonlocal definitions, tables, unknown_lines
        if definitions or tables or unknown_lines or title != "Document":
            sections.append(
                LegacySection(
                    title,
                    section_pointer,
                    section_line,
                    dict(definitions),
                    tuple(tables),
                )
            )
        for line in unknown_lines:
            findings.append(
                _finding(
                    "migration.unknown_field",
                    source_path,
                    f"{section_pointer}/line-{line}",
                    "unstructured prose is not interpreted during deterministic migration",
                    severity="warning",
                )
            )
        definitions = {}
        tables = []
        unknown_lines = []

    index = body_start
    while index < len(lines):
        raw = lines[index]
        heading = _HEADING.match(raw)
        if heading:
            finish_section()
            title = heading.group(2).strip()
            section_line = index + 1
            section_pointer = f"/sections/{_pointer_token(title)}"
            index += 1
            continue
        definition = _DEFINITION.match(raw)
        if definition:
            name = definition.group(1).strip()
            pointer = f"{section_pointer}/definitions/{_pointer_token(name)}"
            if name in definitions:
                findings.append(
                    _finding(
                        "migration.duplicate",
                        source_path,
                        pointer,
                        f"definition `{name}` is duplicated in one section",
                    )
                )
            else:
                value = _parse_scalar(definition.group(2))
                definitions[name] = LegacyValue(value, pointer, index + 1)
                if _confidential(name, value):
                    findings.append(
                        _finding(
                            "migration.confidential",
                            source_path,
                            pointer,
                            "confidential or local-only value requires an explicit disposition",
                            severity="warning",
                        )
                    )
            index += 1
            continue
        if raw.strip().startswith("|") and index + 1 < len(lines):
            headers = tuple(cell.strip() for cell in raw.strip().strip("|").split("|"))
            delimiters = tuple(
                cell.strip() for cell in lines[index + 1].strip().strip("|").split("|")
            )
            if len(headers) == len(delimiters) and all(
                _TABLE_DELIMITER.fullmatch(cell) for cell in delimiters
            ):
                pointer = f"{section_pointer}/tables/{len(tables)}"
                if len(set(headers)) != len(headers):
                    findings.append(
                        _finding(
                            "migration.duplicate",
                            source_path,
                            f"{pointer}/headers",
                            "Markdown table contains duplicate headers",
                        )
                    )
                rows: list[dict[str, str]] = []
                index += 2
                while index < len(lines) and lines[index].strip().startswith("|"):
                    cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
                    cells.extend([""] * (len(headers) - len(cells)))
                    rows.append(dict(zip(headers, cells[: len(headers)])))
                    index += 1
                tables.append(LegacyTable(headers, tuple(rows), pointer, index + 1))
                continue
        stripped = raw.strip()
        if stripped and not stripped.startswith(("```", "<!--")):
            unknown_lines.append(index + 1)
        index += 1
    finish_section()
    return LegacyCard(
        source_path,
        source_hash,
        frontmatter,
        tuple(sections),
        tuple(findings),
    )


def _safe_root(root: Path, relative: Path) -> Path:
    text = str(relative)
    if (
        not text
        or "\\" in text
        or relative.is_absolute()
        or _WINDOWS_ABSOLUTE.match(text)
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise LegacyReadError("migration.path", "allowed root is not project-relative")
    project = root.absolute()
    if project.is_symlink():
        raise LegacyReadError("migration.path", "project root is a symlink")
    current = project
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise LegacyReadError("migration.path", "allowed root contains a symlink")
    return project / relative


def inventory_tree(root: Path, allowed_roots: Iterable[Path]) -> LegacyInventory:
    cards: list[LegacyCard] = []
    findings: list[MigrationFinding] = []
    project = root.absolute()
    for allowed in allowed_roots:
        try:
            target = _safe_root(project, allowed)
        except LegacyReadError as error:
            findings.append(MigrationFinding(error.code, "/sources", str(error)))
            continue
        if not target.exists():
            findings.append(
                MigrationFinding(
                    "migration.missing",
                    f"/{allowed.as_posix()}",
                    "declared legacy source is missing",
                )
            )
            continue
        if not target.is_file() and not target.is_dir():
            findings.append(
                MigrationFinding(
                    "migration.path",
                    f"/{allowed.as_posix()}",
                    "declared legacy source is not a regular file or directory",
                )
            )
            continue
        candidates = (target,) if target.is_file() else tuple(sorted(target.rglob("*.md")))
        for path in candidates:
            try:
                relative = path.relative_to(project)
                _safe_root(project, relative)
                card = load_legacy_card(path, project_root=project)
            except (LegacyReadError, ValueError) as error:
                code = error.code if isinstance(error, LegacyReadError) else "migration.path"
                findings.append(MigrationFinding(code, "/sources", str(error)))
                continue
            cards.append(card)
            findings.extend(card.findings)
    seen_ids: dict[str, str] = {}
    for card in cards:
        identity = card.frontmatter.get("id")
        if identity is None or not isinstance(identity.value, str) or not identity.value:
            continue
        previous = seen_ids.get(identity.value)
        if previous is not None:
            findings.append(
                MigrationFinding(
                    "migration.duplicate",
                    identity.pointer,
                    f"legacy ID `{identity.value}` is duplicated across cards",
                    "error",
                    card.source_path,
                )
            )
        else:
            seen_ids[identity.value] = card.source_path
    return LegacyInventory(tuple(cards), tuple(findings))
