#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None


PLACEHOLDER_RE = re.compile(
    r"(paper-my-topic|YOUR_ORG/paper-harness-template|置き換えてください|未定|未記入|TBD|TODO|Untitled|著者名|所属|Title Goes Here)"
)


@dataclass
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def add(finding_list: list[Finding], severity: str, message: str) -> None:
    finding_list.append(Finding(severity=severity, message=message))


def require_file(root: Path, rel_path: str, findings: list[Finding]) -> Path | None:
    path = root / rel_path
    if not path.exists():
        add(findings, "error", f"`{rel_path}` が見つかりません")
        return None
    return path


def check_placeholders(
    root: Path,
    rel_paths: Iterable[str],
    findings: list[Finding],
    allow_placeholders: bool,
) -> None:
    severity = "warning" if allow_placeholders else "error"
    for rel_path in rel_paths:
        path = require_file(root, rel_path, findings)
        if path is None:
            continue
        for number, line in enumerate(read_text(path).splitlines(), start=1):
            if PLACEHOLDER_RE.search(line):
                add(findings, severity, f"`{rel_path}:{number}` にスターター用プレースホルダーが残っています")


def get_nested(data: dict, dotted_key: str):
    current = data
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def is_blank(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or PLACEHOLDER_RE.search(value) is not None
    if isinstance(value, list):
        return len(value) == 0
    return False


def check_metadata(root: Path, findings: list[Finding], allow_placeholders: bool) -> None:
    rel_path = "manuscript/publication-metadata.toml"
    path = require_file(root, rel_path, findings)
    if path is None:
        return
    if tomllib is None:
        add(findings, "error", "`manuscript/publication-metadata.toml` の検証には Python 3.11 以降が必要です")
        return

    try:
        metadata = tomllib.loads(read_text(path))
    except tomllib.TOMLDecodeError as exc:
        add(findings, "error", f"`{rel_path}` を TOML として読めません: {exc}")
        return

    required_scalars = [
        "manuscript.title_ja",
        "manuscript.title_en",
        "manuscript.source_language",
        "manuscript.status",
        "repository.primary_branch",
        "licenses.manuscript",
    ]
    severity = "warning" if allow_placeholders else "error"
    for key in required_scalars:
        value = get_nested(metadata, key)
        if is_blank(value):
            add(findings, severity, f"`{rel_path}` の `{key}` が未記入です")

    authors = metadata.get("authors")
    if not isinstance(authors, list) or not authors:
        add(findings, severity, f"`{rel_path}` に `[[authors]]` がありません")
    else:
        for index, author in enumerate(authors, start=1):
            if not isinstance(author, dict) or is_blank(author.get("name")):
                add(findings, severity, f"`{rel_path}` の author {index} に名前がありません")
            if not isinstance(author, dict) or is_blank(author.get("affiliation")):
                add(findings, "warning", f"`{rel_path}` の author {index} に affiliation がありません")

    for key in ["repository.url", "licenses.code", "licenses.data", "provenance.last_public_build_commit"]:
        value = get_nested(metadata, key)
        if is_blank(value):
            add(findings, "warning", f"`{rel_path}` の `{key}` が未記入です")


def check_workflows(root: Path, findings: list[Finding], allow_placeholders: bool) -> None:
    workflow_dir = root / ".github" / "workflows"
    if not workflow_dir.exists():
        add(findings, "warning", "`.github/workflows/` が見つかりません")
        return

    severity = "warning" if allow_placeholders else "error"
    for workflow in sorted(workflow_dir.glob("*.yml")):
        rel_path = workflow.relative_to(root).as_posix()
        for number, line in enumerate(read_text(workflow).splitlines(), start=1):
            if "YOUR_ORG/paper-harness-template" in line:
                add(findings, severity, f"`{rel_path}:{number}` の reusable workflow 参照が未設定です")


def check_issue_templates(root: Path, findings: list[Finding]) -> None:
    required = [
        ".github/ISSUE_TEMPLATE/manuscript-feedback.yml",
        ".github/ISSUE_TEMPLATE/evidence-request.yml",
        ".github/ISSUE_TEMPLATE/harness-friction.yml",
    ]
    for rel_path in required:
        require_file(root, rel_path, findings)


def main() -> int:
    parser = argparse.ArgumentParser(description="共有・投稿前の論文ハーネス readiness を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="テンプレート自身を検証するため、スターター用プレースホルダーを warning に留める。",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[Finding] = []

    check_placeholders(
        root,
        [
            "README.md",
            "notes/project-brief.md",
            "notes/contribution-claims.md",
            "notes/reproducibility.md",
            "manuscript/venue.md",
        ],
        findings,
        args.allow_placeholders,
    )
    check_metadata(root, findings, args.allow_placeholders)
    check_workflows(root, findings, args.allow_placeholders)
    check_issue_templates(root, findings)

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# readiness-check")
    print("")
    if errors:
        print("## Errors")
        for finding in errors:
            print(f"- {finding.message}")
        print("")
    if warnings:
        print("## Warnings")
        for finding in warnings:
            print(f"- {finding.message}")
        print("")
    if not findings:
        print("共有・投稿前の必須項目に未対応のものは見つかりませんでした。")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
