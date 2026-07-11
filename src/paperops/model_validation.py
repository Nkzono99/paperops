"""Safe invocation and typed results for the project-managed model checker."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_MAX_CHECKER_OUTPUT_BYTES = 1024 * 1024


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
    hashes: dict[str, str]
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
        hashes={},
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


def run_model_validation(
    root: Path,
    model: str,
    *,
    phase: str = "all",
    strict: bool = False,
    timeout: float = 120.0,
) -> ValidationResult:
    """Run the target project's checker without a shell and validate JSON v1."""
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
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        return _failure(
            model,
            phase,
            "validation.version",
            "/schema_version",
            "unsupported model checker JSON schema version",
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
        isinstance(key, str) and isinstance(value, str)
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
        model=str(payload.get("model", model)),
        phase=str(payload.get("phase", phase)),
        findings=findings,
        hashes=dict(hashes),
        returncode=completed.returncode,
    )
