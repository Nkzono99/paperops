"""Safe invocation and typed results for the project-managed model checker."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal


_MAX_CHECKER_OUTPUT_BYTES = 1024 * 1024
_SAFE_QUERY_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SECTION_ID = re.compile(r"^SEC-[0-9]{4,}$")
_SEMANTIC_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


@dataclass(frozen=True)
class ValidationFinding:
    code: str
    pointer: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class ValidationResult:
    schema_version: int
    ok: bool
    model: str
    phase: str
    findings: tuple[ValidationFinding, ...]
    hashes: Mapping[str, str]
    returncode: int


def _failure(
    model: str,
    phase: str,
    code: str,
    pointer: str,
    message: str,
    *,
    returncode: int = 1,
) -> ValidationResult:
    return ValidationResult(
        schema_version=1,
        ok=False,
        model=model,
        phase=phase,
        findings=(ValidationFinding(code, pointer, message),),
        hashes=MappingProxyType({}),
        returncode=returncode,
    )


def _finding(value: Any) -> ValidationFinding | None:
    if not isinstance(value, dict):
        return None
    code = value.get("code")
    pointer = value.get("pointer")
    message = value.get("message")
    severity = value.get("severity")
    if not all(isinstance(item, str) for item in (code, pointer, message, severity)):
        return None
    if severity not in {"error", "warning", "info"}:
        return None
    return ValidationFinding(code, pointer, message, severity)


def _run_checker(
    root: Path,
    model: str,
    *,
    phase: str = "all",
    strict: bool = False,
    timeout: float = 120.0,
    query: Literal["validation", "hash", "compile_readiness"] = "validation",
    object_id: str | None = None,
    section_ids: tuple[str, ...] = (),
) -> ValidationResult:
    resolved = root.expanduser().resolve()
    checker = resolved / "scripts" / "check-paperops-models.py"
    if not checker.is_file():
        return _failure(
            model,
            phase,
            "validation.checker_missing",
            "/scripts/check-paperops-models.py",
            "project-managed model checker is missing; run pops update-paperops",
        )
    argv = [
        sys.executable,
        str(checker),
        "--root",
        str(resolved),
        "--model",
        model,
        "--phase",
        phase,
        "--json",
    ]
    if strict:
        argv.append("--strict")
    if query == "hash":
        argv.append("--print-hash")
        if object_id is not None:
            argv.extend(("--object-id", object_id))
    elif query == "compile_readiness":
        argv.append("--compile-readiness")
        for section_id in section_ids:
            argv.extend(("--section-id", section_id))
    try:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            completed = subprocess.run(
                argv,
                check=False,
                stdout=stdout,
                stderr=stderr,
                timeout=timeout,
            )
            stdout.seek(0)
            raw_output = stdout.read(_MAX_CHECKER_OUTPUT_BYTES + 1)
    except subprocess.TimeoutExpired:
        return _failure(
            model,
            phase,
            "validation.timeout",
            "/",
            "model checker exceeded the validation timeout",
        )
    except OSError as error:
        return _failure(
            model,
            phase,
            "validation.execution",
            "/",
            f"model checker could not be executed: {error}",
        )
    if len(raw_output) > _MAX_CHECKER_OUTPUT_BYTES:
        return _failure(
            model,
            phase,
            "validation.output",
            "/",
            "model checker output exceeded the validation limit",
            returncode=completed.returncode or 1,
        )
    try:
        payload = json.loads(raw_output.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _failure(
            model,
            phase,
            "validation.output",
            "/",
            "model checker did not return valid JSON",
            returncode=completed.returncode or 1,
        )
    if (
        not isinstance(payload, dict)
        or type(payload.get("schema_version")) is not int
        or payload["schema_version"] != 1
    ):
        return _failure(
            model,
            phase,
            "validation.version",
            "/schema_version",
            "unsupported model checker JSON schema version",
            returncode=completed.returncode or 1,
        )
    if payload.get("model") != model or payload.get("phase") != phase:
        return _failure(
            model,
            phase,
            "validation.output",
            "/model",
            "model checker JSON identity disagrees with the requested query",
            returncode=completed.returncode or 1,
        )
    raw_findings = payload.get("findings")
    if not isinstance(raw_findings, list):
        return _failure(
            model,
            phase,
            "validation.output",
            "/findings",
            "model checker JSON findings must be an array",
            returncode=completed.returncode or 1,
        )
    findings = tuple(item for value in raw_findings if (item := _finding(value)) is not None)
    if len(findings) != len(raw_findings):
        return _failure(
            model,
            phase,
            "validation.output",
            "/findings",
            "model checker JSON contains a malformed finding",
            returncode=completed.returncode or 1,
        )
    hashes = payload.get("hashes")
    if not isinstance(hashes, dict) or not all(
        isinstance(key, str)
        and isinstance(value, str)
        and _SEMANTIC_HASH.fullmatch(value) is not None
        for key, value in hashes.items()
    ):
        return _failure(
            model,
            phase,
            "validation.output",
            "/hashes",
            "model checker JSON hashes must be a string mapping",
            returncode=completed.returncode or 1,
        )
    ok = payload.get("ok")
    if not isinstance(ok, bool) or ok != (completed.returncode == 0):
        return _failure(
            model,
            phase,
            "validation.output",
            "/ok",
            "model checker JSON status disagrees with its exit code",
            returncode=completed.returncode or 1,
        )
    return ValidationResult(
        schema_version=1,
        ok=ok,
        model=model,
        phase=phase,
        findings=findings,
        hashes=MappingProxyType(dict(hashes)),
        returncode=completed.returncode,
    )


def run_model_validation(
    root: Path,
    model: str,
    *,
    phase: str = "all",
    strict: bool = False,
    timeout: float = 120.0,
) -> ValidationResult:
    """Run the target project's checker without a shell and validate JSON v1."""
    return _run_checker(
        root,
        model,
        phase=phase,
        strict=strict,
        timeout=timeout,
    )


def run_model_hash(
    root: Path,
    model: str,
    object_id: str | None = None,
    *,
    timeout: float = 120.0,
) -> ValidationResult:
    """Return a checker-validated model or catalog-object semantic hash."""
    if not isinstance(model, str) or _SAFE_QUERY_ID.fullmatch(model) is None:
        return _failure(
            model,
            "all",
            "validation.request",
            "/model",
            "model must be a safe identifier",
        )
    if object_id is not None and (
        not isinstance(object_id, str)
        or _SAFE_QUERY_ID.fullmatch(object_id) is None
    ):
        return _failure(
            model,
            "all",
            "validation.request",
            "/object-id",
            "object ID must be a safe identifier",
        )
    expected_key = model
    if object_id is not None:
        expected_key = object_id
    result = _run_checker(
        root,
        model,
        timeout=timeout,
        query="hash",
        object_id=object_id,
    )
    expected_keys = {model} if object_id is None else {model, object_id}
    if result.ok and (
        set(result.hashes) != expected_keys
        or _SEMANTIC_HASH.fullmatch(result.hashes.get(expected_key, "")) is None
    ):
        return _failure(
            model,
            result.phase,
            "validation.output",
            f"/hashes/{expected_key}",
            "model checker did not return the requested semantic hash",
            returncode=result.returncode or 1,
        )
    return result


def run_manuscript_compile_readiness(
    root: Path,
    section_ids: tuple[str, ...] | list[str],
    *,
    timeout: float = 120.0,
) -> ValidationResult:
    """Run the checker's read-only P3 readiness query for selected sections."""
    try:
        selected = tuple(section_ids)
    except TypeError:
        selected = ()
    if (
        not selected
        or len(selected) > 1000
        or any(
            not isinstance(item, str) or _SECTION_ID.fullmatch(item) is None
            for item in selected
        )
        or len(set(selected)) != len(selected)
    ):
        return _failure(
            "manuscript",
            "all",
            "validation.request",
            "/section-id",
            "compile readiness requires SEC-<digits> section IDs",
        )
    return _run_checker(
        root,
        "manuscript",
        timeout=timeout,
        query="compile_readiness",
        section_ids=selected,
    )
