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
    r"(paper-my-topic|YOUR_ORG/paperops|置き換えてください|未定|未記入|TBD|TODO|Untitled|著者名|所属|Title Goes Here|日本語論文タイトルの仮置き|Placeholder English Paper Title|Author A|Author B)"
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
            if "YOUR_ORG/paperops" in line:
                add(findings, severity, f"`{rel_path}:{number}` の reusable workflow 参照が未設定です")


def check_issue_templates(root: Path, findings: list[Finding]) -> None:
    required = [
        ".github/ISSUE_TEMPLATE/manuscript-feedback.yml",
        ".github/ISSUE_TEMPLATE/evidence-request.yml",
        ".github/ISSUE_TEMPLATE/harness-friction.yml",
    ]
    for rel_path in required:
        require_file(root, rel_path, findings)


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def has_filled_section(text: str, heading: str) -> bool:
    body = section_body(text, heading)
    return bool(body) and PLACEHOLDER_RE.search(body) is None


def check_paper_quality_notes(root: Path, findings: list[Finding], allow_placeholders: bool) -> None:
    severity = "warning" if allow_placeholders else "error"

    claim_path = require_file(root, "notes/claim-evidence-map.md", findings)
    if claim_path is not None and not has_filled_section(read_text(claim_path), "Core claim"):
        add(findings, severity, "`notes/claim-evidence-map.md` の Core claim が未記入です")

    ai_use_path = require_file(root, "notes/ai-use.md", findings)
    if ai_use_path is not None:
        text = read_text(ai_use_path)
        if "## Submission disclosure draft" not in text:
            add(findings, "error", "`notes/ai-use.md` に Submission disclosure draft セクションがありません")
        if not has_filled_section(text, "Submission disclosure draft"):
            add(findings, severity, "`notes/ai-use.md` の Submission disclosure draft が未記入です")

    venue_path = require_file(root, "manuscript/venue.md", findings)
    if venue_path is not None:
        text = read_text(venue_path)
        for label in ["投稿タイプ", "ページ制限", "必須セクション"]:
            pattern = re.compile(rf"^\s*-\s*{re.escape(label)}\s*[:：]\s*(?P<value>.+?)\s*$", re.MULTILINE)
            match = pattern.search(text)
            if match is None or is_blank(match.group("value")):
                add(findings, severity, f"`manuscript/venue.md` の `{label}` が未記入です")

    reproducibility_path = require_file(root, "notes/reproducibility.md", findings)
    if reproducibility_path is not None:
        text = read_text(reproducibility_path)
        required_sections = {
            "公開データと入力": "Data availability",
            "解析エントリポイント": "Code availability",
            "図表 provenance": "Figure provenance",
        }
        for heading, label in required_sections.items():
            if f"## {heading}" not in text:
                add(findings, "error", f"`notes/reproducibility.md` に {label} セクションがありません")


def check_submission_slot(root: Path, findings: list[Finding], require_submission: bool) -> None:
    submission_dir = root / "submission"
    if not submission_dir.exists():
        if require_submission:
            add(findings, "error", "`submission/<venue>/` が見つかりません")
        return

    venue_dirs = sorted(path for path in submission_dir.iterdir() if path.is_dir())
    if require_submission and not venue_dirs:
        add(findings, "error", "`submission/<venue>/README.md` または `submission/<venue>/main.tex` が必要です")
        return

    for venue_dir in venue_dirs:
        rel_path = venue_dir.relative_to(root).as_posix()
        if not (venue_dir / "README.md").exists() and not (venue_dir / "main.tex").exists():
            severity = "error" if require_submission else "warning"
            add(findings, severity, f"`{rel_path}` に `README.md` または `main.tex` がありません")


def main() -> int:
    parser = argparse.ArgumentParser(description="共有・投稿前の論文ハーネス readiness を確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--allow-placeholders",
        action="store_true",
        help="テンプレート自身を検証するため、スターター用プレースホルダーを warning に留める。",
    )
    parser.add_argument(
        "--require-submission",
        action="store_true",
        help="投稿前ゲートとして `submission/<venue>/README.md` または `main.tex` を必須にする。",
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
            "notes/claim-evidence-map.md",
            "notes/reviewer-model.md",
            "notes/ai-use.md",
            "notes/reproducibility.md",
            "manuscript/venue.md",
            "manuscript/shared/style/macros.tex",
        ],
        findings,
        args.allow_placeholders,
    )
    check_metadata(root, findings, args.allow_placeholders)
    check_workflows(root, findings, args.allow_placeholders)
    check_issue_templates(root, findings)
    check_paper_quality_notes(root, findings, args.allow_placeholders)
    check_submission_slot(root, findings, args.require_submission)

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
