"""Safe on-disk staging, public reports, and byte-exact snapshots."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .types import MigrationFinding, MigrationReport, TransactionPaths


_TRANSACTION_ID = re.compile(
    r"^model-[0-9]{8}T[0-9]{6}(?:[0-9]{6})?Z-[0-9a-f]{12}$"
)
_WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[\\/]")
_URL_CREDENTIAL = re.compile(r"(https?://)[^\s/@:]+:[^\s/@]+@", re.IGNORECASE)
_SECRET_QUERY = re.compile(
    r"(?i)(token|api[_-]?key|password|secret)=([^&\s]+)"
)
_ABSOLUTE_LOCATION = re.compile(r"(?<![:/])/(?:[^\s/]+/)+[^\s,;:)]+")


class StagingError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def new_transaction_id(now: datetime, entropy: bytes | str) -> str:
    if now.tzinfo is None:
        raise StagingError("transaction.time", "transaction time must be timezone-aware")
    utc = now.astimezone(timezone.utc)
    raw_entropy = entropy.encode("utf-8") if isinstance(entropy, str) else entropy
    suffix = hashlib.sha256(raw_entropy).hexdigest()[:12]
    timestamp = utc.strftime("%Y%m%dT%H%M%S%fZ")
    return f"model-{timestamp}-{suffix}"


def _validate_transaction_id(transaction_id: str) -> None:
    if not _TRANSACTION_ID.fullmatch(transaction_id):
        raise StagingError("transaction.path", "unsafe transaction id")


def _relative_path(value: str | Path) -> Path:
    text = str(value)
    candidate = Path(text)
    if (
        not text
        or text == "."
        or "\x00" in text
        or "\\" in text
        or candidate.is_absolute()
        or _WINDOWS_ABSOLUTE.match(text)
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise StagingError("transaction.path", f"unsafe project-relative path: {text!r}")
    return candidate


def transaction_paths(root: Path, transaction_id: str) -> TransactionPaths:
    _validate_transaction_id(transaction_id)
    project = root.expanduser().absolute()
    migration_dir = project / ".paperops" / "migrations" / transaction_id
    snapshot_dir = project / ".paperops" / "snapshots" / transaction_id
    return TransactionPaths(
        transaction_id=transaction_id,
        migration_dir=migration_dir,
        candidate_dir=migration_dir / "candidate",
        journal_path=migration_dir / "journal.json",
        report_json_path=migration_dir / "report.json",
        report_markdown_path=migration_dir / "report.md",
        snapshot_dir=snapshot_dir,
        snapshot_manifest_path=snapshot_dir / "manifest.json",
    )


def _reject_symlink_components(root: Path, relative: Path) -> None:
    if root.is_symlink():
        raise StagingError("transaction.symlink", "project root must not be a symlink")
    current = root
    for part in relative.parts:
        current = current / part
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise StagingError(
                "transaction.symlink",
                f"path contains a symlink component: {relative}",
            )


def _public_text(value: str, *, confidential: bool = False) -> str:
    if confidential:
        return "[redacted]"
    rendered = _URL_CREDENTIAL.sub(r"\1[redacted]@", value)
    rendered = _SECRET_QUERY.sub(r"\1=[redacted]", rendered)
    return _ABSOLUTE_LOCATION.sub("[redacted]", rendered)


def _report_payload(report: MigrationReport) -> dict[str, Any]:
    if report.schema_version != 1:
        raise StagingError("transaction.report_version", "unsupported report schema")
    _validate_transaction_id(report.transaction_id)
    inventory: list[dict[str, Any]] = []
    for item in report.inventory:
        _relative_path(item.source_path)
        value = asdict(item)
        value["reason"] = _public_text(item.reason)
        inventory.append(value)
    candidates: list[dict[str, Any]] = []
    for candidate in report.candidates:
        _relative_path(candidate.relative_path)
        candidates.append(
            {
                "relative_path": candidate.relative_path,
                "object_id": candidate.object_id,
                "semantic_hash": candidate.semantic_hash,
            }
        )
    findings: list[dict[str, Any]] = []
    for finding in report.findings:
        if finding.source_path:
            _relative_path(finding.source_path)
        value = asdict(finding)
        value["message"] = _public_text(
            finding.message,
            confidential=finding.code == "migration.confidential",
        )
        findings.append(value)
    return {
        "schema_version": report.schema_version,
        "transaction_id": report.transaction_id,
        "model_name": report.model_name,
        "adapter_version": report.adapter_version,
        "inventory": inventory,
        "candidates": candidates,
        "findings": findings,
    }


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        with temporary.open("wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_report(paths: TransactionPaths, report: MigrationReport) -> None:
    if paths.transaction_id != report.transaction_id:
        raise StagingError("transaction.report", "report transaction does not match paths")
    project = paths.migration_dir.parents[2]
    _reject_symlink_components(
        project, Path(".paperops/migrations") / paths.transaction_id
    )
    payload = _report_payload(report)
    json_bytes = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    blocking = sum(
        finding["severity"] == "error" for finding in payload["findings"]
    )
    markdown = (
        "# Model migration report\n\n"
        f"- Transaction: `{report.transaction_id}`\n"
        f"- Model: `{report.model_name}`\n"
        f"- Inventory items: {len(report.inventory)}\n"
        f"- Candidate documents: {len(report.candidates)}\n"
        f"- Blocking findings: {blocking}\n"
    ).encode("utf-8")
    _write_bytes(paths.report_json_path, json_bytes)
    _write_bytes(paths.report_markdown_path, markdown)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _inventory_path(root: Path, relative: Path) -> list[tuple[Path, Path, os.stat_result]]:
    _reject_symlink_components(root, relative)
    source = root / relative
    try:
        metadata = source.lstat()
    except FileNotFoundError as error:
        raise StagingError("transaction.missing", f"snapshot source is missing: {relative}") from error
    if stat.S_ISLNK(metadata.st_mode):
        raise StagingError("transaction.symlink", f"snapshot source is a symlink: {relative}")
    if stat.S_ISREG(metadata.st_mode):
        return [(relative, source, metadata)]
    if not stat.S_ISDIR(metadata.st_mode):
        raise StagingError(
            "transaction.special_file", f"snapshot source is not a regular file: {relative}"
        )
    collected: list[tuple[Path, Path, os.stat_result]] = []
    for child in sorted(source.iterdir(), key=lambda item: item.name):
        child_relative = relative / child.name
        collected.extend(_inventory_path(root, child_relative))
    return collected


def snapshot_paths(
    root: Path,
    transaction_id: str,
    relative_paths: Iterable[Path],
) -> Path:
    paths = transaction_paths(root, transaction_id)
    project = root.expanduser().absolute()
    files: dict[str, tuple[Path, Path, os.stat_result]] = {}
    for value in relative_paths:
        relative = _relative_path(value)
        for item in _inventory_path(project, relative):
            files[item[0].as_posix()] = item
    _reject_symlink_components(
        project, Path(".paperops/snapshots") / transaction_id
    )
    if paths.snapshot_dir.exists() or paths.snapshot_dir.is_symlink():
        raise StagingError("transaction.snapshot_exists", "snapshot already exists")
    paths.snapshot_dir.mkdir(parents=True)
    manifest_files: list[dict[str, Any]] = []
    try:
        for relative_text in sorted(files):
            relative, source, metadata = files[relative_text]
            destination = paths.snapshot_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination, follow_symlinks=False)
            os.chmod(destination, stat.S_IMODE(metadata.st_mode))
            manifest_files.append(
                {
                    "path": relative.as_posix(),
                    "mode": f"{stat.S_IMODE(metadata.st_mode):04o}",
                    "size": metadata.st_size,
                    "sha256": _sha256(destination),
                }
            )
        payload = {
            "schema_version": 1,
            "transaction_id": transaction_id,
            "files": manifest_files,
        }
        _write_bytes(
            paths.snapshot_manifest_path,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
    except Exception:
        shutil.rmtree(paths.snapshot_dir, ignore_errors=True)
        raise
    return paths.snapshot_manifest_path


def verify_snapshot(root: Path, transaction_id: str) -> tuple[MigrationFinding, ...]:
    paths = transaction_paths(root, transaction_id)
    try:
        _reject_symlink_components(
            root.expanduser().absolute(),
            Path(".paperops/snapshots") / transaction_id,
        )
        if paths.snapshot_manifest_path.is_symlink():
            raise ValueError("manifest is a symlink")
        payload = json.loads(paths.snapshot_manifest_path.read_text(encoding="utf-8"))
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != 1
            or payload.get("transaction_id") != transaction_id
            or not isinstance(payload.get("files"), list)
        ):
            raise ValueError("invalid manifest envelope")
        entries: list[tuple[Path, dict[str, Any]]] = []
        seen: set[str] = set()
        for raw in payload["files"]:
            if not isinstance(raw, dict):
                raise ValueError("invalid file entry")
            relative = _relative_path(raw.get("path", ""))
            if relative.as_posix() in seen:
                raise ValueError("duplicate file entry")
            seen.add(relative.as_posix())
            if not isinstance(raw.get("mode"), str) or not re.fullmatch(r"0[0-7]{3}", raw["mode"]):
                raise ValueError("invalid mode")
            if not isinstance(raw.get("size"), int) or raw["size"] < 0:
                raise ValueError("invalid size")
            if not isinstance(raw.get("sha256"), str) or not re.fullmatch(
                r"sha256:[0-9a-f]{64}", raw["sha256"]
            ):
                raise ValueError("invalid hash")
            entries.append((relative, raw))
    except (OSError, ValueError, json.JSONDecodeError, StagingError) as error:
        return (
            MigrationFinding(
                "transaction.snapshot_manifest",
                "/manifest.json",
                f"snapshot manifest is invalid: {error}",
            ),
        )
    findings: list[MigrationFinding] = []
    for relative, entry in entries:
        target = paths.snapshot_dir / relative
        try:
            metadata = target.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise OSError("not a regular file")
            actual_hash = _sha256(target)
        except OSError:
            findings.append(
                MigrationFinding(
                    "transaction.snapshot_missing",
                    f"/{relative.as_posix()}",
                    "snapshot file is missing or unsafe",
                )
            )
            continue
        if actual_hash != entry["sha256"]:
            findings.append(
                MigrationFinding(
                    "transaction.snapshot_hash",
                    f"/{relative.as_posix()}",
                    "snapshot file hash does not match its manifest",
                )
            )
        elif metadata.st_size != entry["size"] or f"{stat.S_IMODE(metadata.st_mode):04o}" != entry["mode"]:
            findings.append(
                MigrationFinding(
                    "transaction.snapshot_metadata",
                    f"/{relative.as_posix()}",
                    "snapshot file size or mode does not match its manifest",
                )
            )
    return tuple(findings)
