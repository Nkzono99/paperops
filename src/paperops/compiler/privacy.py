"""Shared detection for private material in Writer-facing semantic strings."""

from __future__ import annotations

import re
from pathlib import PurePosixPath, PureWindowsPath


_CREDENTIAL_URL = re.compile(
    r"(?i)\b[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@"
)
_EMBEDDED_POSIX_PATH = re.compile(
    r"(?<![A-Za-z0-9._:/-])/(?:[^\s/]+/)*[^\s,;:)\]}>\"']+"
)
_EMBEDDED_WINDOWS_PATH = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:[A-Z]:[\\/]|\\\\[^\\/\s]+[\\/])[^\s,;:)\]}>\"']+"
)
_PRIVATE_URI = re.compile(r"(?i)\b(?:file|ssh|sftp):(?://)?[^\s]+")
_PARENT_TRAVERSAL = re.compile(
    r"(?<![A-Za-z0-9._-])(?:\.\.[\\/])+(?:[^\s\\/]+[\\/]?)+"
)
_HOME_REFERENCE = re.compile(
    r"(?i)(?:^|[\s`\"'(])(?:~[\\/]|\$\{?(?:HOME|USERPROFILE)\}?[\\/])"
)
_AUTHORIZATION_CREDENTIAL = re.compile(
    r"(?i)\b(?:authorization|proxy-authorization)\s*[:=]\s*"
    r"(?:bearer|basic)\s+\S+"
)
_BEARER_CREDENTIAL = re.compile(
    r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?i)(?:token|api[_-]?key|password|passwd|secret|credential)\s*[:=]\s*\S+"
)
_SECRET_LITERAL = re.compile(
    r"(?:\bsk-[A-Za-z0-9_-]{12,}"
    r"|\bgh[opusr]_[A-Za-z0-9]{12,}"
    r"|\bgithub_pat_[A-Za-z0-9_]{12,}"
    r"|\bglpat-[A-Za-z0-9_-]{12,}"
    r"|\bxox[baprs]-[A-Za-z0-9-]{12,}"
    r"|\b(?:AKIA|ASIA)[0-9A-Z]{16})"
)
_PRIVATE_RAW_SENTINEL = re.compile(
    r"(?i)(?:^|[\s._-])(?:raw[\s._-]+review(?:er)?|private[\s._-]+raw)"
    r"(?:[\s:._-]|$)"
)
_PRIVATE_KEY_HEADER = re.compile(
    r"(?i)-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
)
_KEY_COMPONENT = re.compile(r"[^a-z0-9]+")
_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


PRIVATE_MATERIAL_MESSAGE = (
    "Writer-facing material contains private location or credential data"
)


def sensitive_document_key(value: str) -> bool:
    """Detect exact credential-like key components without rejecting token budgets."""
    if not isinstance(value, str):
        raise TypeError("document key must be a string")
    separated = _CAMEL_CASE_BOUNDARY.sub("_", value)
    components = tuple(
        part for part in _KEY_COMPONENT.split(separated.casefold()) if part
    )
    if any(
        part
        in {
            "password",
            "passwd",
            "secret",
            "credential",
            "apikey",
            "authorization",
        }
        for part in components
    ):
        return True
    for index, component in enumerate(components):
        if component != "token":
            continue
        following = components[index + 1] if index + 1 < len(components) else ""
        preceding = components[index - 1] if index else ""
        if following not in {"count", "budget", "limit", "usage", "length"} and preceding not in {
            "count",
            "budget",
            "limit",
            "usage",
            "length",
        }:
            return True
    sensitive_pairs = {
        ("api", "key"),
        ("access", "token"),
        ("auth", "token"),
        ("bearer", "token"),
        ("refresh", "token"),
        ("session", "token"),
        ("id", "token"),
        ("private", "key"),
        ("local", "path"),
        ("raw", "review"),
        ("raw", "reviewer"),
        ("private", "raw"),
    }
    return any(pair in sensitive_pairs for pair in zip(components, components[1:]))


def contains_private_material(
    value: str,
    *,
    allow_project_relative: bool = True,
) -> bool:
    """Return whether a public semantic string contains local/private material."""
    if not isinstance(value, str):
        raise TypeError("public semantic value must be a string")
    stripped = value.strip()
    if not stripped:
        return False
    try:
        stripped.encode("utf-8")
    except UnicodeEncodeError:
        return True
    if any(
        (ord(character) < 32 and character not in "\t\n\r")
        or ord(character) == 127
        for character in stripped
    ):
        return True
    posix = PurePosixPath(stripped)
    windows = PureWindowsPath(stripped)
    private = bool(
        posix.is_absolute()
        or windows.is_absolute()
        or windows.drive
        or _EMBEDDED_POSIX_PATH.search(stripped)
        or _EMBEDDED_WINDOWS_PATH.search(stripped)
        or _PRIVATE_URI.search(stripped)
        or _PARENT_TRAVERSAL.search(stripped)
        or _HOME_REFERENCE.search(stripped)
        or _CREDENTIAL_URL.search(stripped)
        or _AUTHORIZATION_CREDENTIAL.search(stripped)
        or _BEARER_CREDENTIAL.search(stripped)
        or _SECRET_ASSIGNMENT.search(stripped)
        or _SECRET_LITERAL.search(stripped)
        or _PRIVATE_RAW_SENTINEL.search(stripped)
        or _PRIVATE_KEY_HEADER.search(stripped)
    )
    if private or allow_project_relative:
        return private
    return bool(
        ("/" in stripped or "\\" in stripped)
        and not stripped.lower().startswith(("https://", "http://", "doi:"))
    )


def contains_private_public_text(value: str) -> bool:
    """Backward-compatible spelling for public project-relative material."""
    return contains_private_material(value, allow_project_relative=True)


__all__ = [
    "PRIVATE_MATERIAL_MESSAGE",
    "contains_private_material",
    "contains_private_public_text",
    "sensitive_document_key",
]
