from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python 3.11+ is required.
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
RELEASE_HEADING_RE = re.compile(
    r"^(?P<version>\d+\.\d+\.\d+) - (?P<date>\d{4}-\d{2}-\d{2})$"
)


class CheckFailure(Exception):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class Section:
    title: str
    line: int
    body: str


@dataclass(frozen=True)
class ReleaseSection:
    version: str
    released_on: date
    line: int
    body: str


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check paperops release version source-of-truth state."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--release-version",
        help=(
            "Target release version. When set, require pyproject/src/changelog to "
            "be prepared for this version and require the v<version> tag to be absent."
        ),
    )
    parser.add_argument(
        "--github-repo",
        help="Optional owner/repo for checking that GitHub Release v<version> is absent.",
    )
    args = parser.parse_args(argv)

    try:
        facts = check_release_version_truth(
            args.root,
            release_version=args.release_version,
            github_repo=args.github_repo,
        )
    except CheckFailure as exc:
        print("release version truth: failed", file=sys.stderr)
        for error in exc.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("release version truth: ok")
    for fact in facts:
        print(f"- {fact}")
    return 0


def check_release_version_truth(
    root: Path,
    *,
    release_version: str | None = None,
    existing_tags: Iterable[str] | None = None,
    github_repo: str | None = None,
) -> list[str]:
    root = root.resolve()
    errors: list[str] = []

    pyproject_version = read_pyproject_version(root)
    src_version = read_src_version(root)
    if pyproject_version != src_version:
        errors.append(
            "pyproject.toml version and src/paperops/__init__.py __version__ "
            f"must match: {pyproject_version!r} != {src_version!r}"
        )

    sections = parse_changelog(root / "CHANGELOG.md")
    unreleased = [section for section in sections if section.title == "Unreleased"]
    if not unreleased:
        errors.append("CHANGELOG.md must contain a top-level '## Unreleased' section.")
    elif sections[0].title != "Unreleased":
        errors.append(
            "CHANGELOG.md must keep '## Unreleased' as the first level-2 section."
        )
    if len(unreleased) > 1:
        lines = ", ".join(str(section.line) for section in unreleased)
        errors.append(f"CHANGELOG.md has duplicate Unreleased sections at lines {lines}.")

    releases = parse_release_sections(sections, errors)
    check_release_order(releases, errors)

    current_release = [release for release in releases if release.version == pyproject_version]
    if release_version is None and not current_release:
        errors.append(
            "CHANGELOG.md must contain exactly one package release section for the "
            f"current project version {pyproject_version}."
        )

    if release_version is not None:
        check_target_release(
            root,
            release_version=release_version,
            pyproject_version=pyproject_version,
            src_version=src_version,
            unreleased=unreleased[0] if unreleased else None,
            releases=releases,
            existing_tags=existing_tags,
            github_repo=github_repo,
            errors=errors,
        )

    if errors:
        raise CheckFailure(errors)

    facts = [
        f"pyproject/src version: {pyproject_version}",
        f"package release headings: {', '.join(release.version for release in releases)}",
    ]
    if release_version is not None:
        facts.append(f"target release tag v{release_version}: absent")
        if github_repo:
            facts.append(f"GitHub Release v{release_version}: absent in {github_repo}")
    return facts


def read_pyproject_version(root: Path) -> str:
    if tomllib is None:
        raise CheckFailure(["Python 3.11 or newer is required for tomllib."])
    path = root / "pyproject.toml"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    version = project.get("version")
    if not isinstance(version, str) or not version:
        raise CheckFailure(["pyproject.toml must define [project].version."])
    return version


def read_src_version(root: Path) -> str:
    path = root / "src" / "paperops" / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node.value.value
    raise CheckFailure(["src/paperops/__init__.py must assign __version__ to a string."])


def parse_changelog(path: Path) -> list[Section]:
    text = path.read_text(encoding="utf-8")
    matches = list(HEADING_RE.finditer(text))
    sections: list[Section] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        line = text.count("\n", 0, match.start()) + 1
        sections.append(Section(title=match.group("title"), line=line, body=text[start:end]))
    return sections


def parse_release_sections(sections: list[Section], errors: list[str]) -> list[ReleaseSection]:
    releases: list[ReleaseSection] = []
    seen: dict[str, int] = {}
    for section in sections:
        match = RELEASE_HEADING_RE.fullmatch(section.title)
        if not match:
            continue
        version = match.group("version")
        try:
            released_on = date.fromisoformat(match.group("date"))
        except ValueError:
            errors.append(
                f"CHANGELOG.md line {section.line}: invalid release date {match.group('date')!r}."
            )
            continue
        if version in seen:
            errors.append(
                "CHANGELOG.md has duplicate package release heading "
                f"{version!r} at lines {seen[version]} and {section.line}."
            )
        else:
            seen[version] = section.line
        releases.append(
            ReleaseSection(
                version=version,
                released_on=released_on,
                line=section.line,
                body=section.body,
            )
        )
    return releases


def check_release_order(releases: list[ReleaseSection], errors: list[str]) -> None:
    for previous, current in zip(releases, releases[1:]):
        if version_key(previous.version) <= version_key(current.version):
            errors.append(
                "CHANGELOG.md package release headings must be newest version first: "
                f"{previous.version} at line {previous.line} is not newer than "
                f"{current.version} at line {current.line}."
            )
        if previous.released_on < current.released_on:
            errors.append(
                "CHANGELOG.md package release dates must be newest first: "
                f"{previous.released_on.isoformat()} at line {previous.line} is older "
                f"than {current.released_on.isoformat()} at line {current.line}."
            )


def check_target_release(
    root: Path,
    *,
    release_version: str,
    pyproject_version: str,
    src_version: str,
    unreleased: Section | None,
    releases: list[ReleaseSection],
    existing_tags: Iterable[str] | None,
    github_repo: str | None,
    errors: list[str],
) -> None:
    if not RELEASE_HEADING_RE.match(f"{release_version} - 2000-01-01"):
        errors.append(f"--release-version must be a three-part semantic version: {release_version!r}.")
        return

    if pyproject_version != release_version:
        errors.append(
            f"pyproject.toml [project].version must be {release_version!r} for release preflight."
        )
    if src_version != release_version:
        errors.append(
            f"src/paperops/__init__.py __version__ must be {release_version!r} for release preflight."
        )
    if unreleased is not None and unreleased.body.strip():
        errors.append("CHANGELOG.md '## Unreleased' must be empty during release preflight.")

    matching_releases = [release for release in releases if release.version == release_version]
    if not matching_releases:
        errors.append(
            f"CHANGELOG.md must contain a package release section for {release_version}."
        )
    elif releases and releases[0].version != release_version:
        errors.append(
            f"CHANGELOG.md first package release section must be {release_version}; "
            f"found {releases[0].version} at line {releases[0].line}."
        )

    tag = f"v{release_version}"
    local_tags = set(existing_tags) if existing_tags is not None else read_git_tags(root)
    if tag in local_tags:
        errors.append(f"local git tag {tag} already exists; choose a new release version.")

    if github_repo:
        github_tags = read_github_release_tags(root, github_repo)
        normalized = {tag_name.lstrip("v") for tag_name in github_tags}
        if release_version in normalized:
            errors.append(
                f"GitHub Release v{release_version} already exists in {github_repo}."
            )
        latest = latest_release_version(github_tags)
        if latest is not None and version_key(release_version) <= version_key(latest):
            errors.append(
                f"target release {release_version} must be newer than latest GitHub "
                f"release {latest} in {github_repo}."
            )


def read_git_tags(root: Path) -> set[str]:
    result = subprocess.run(
        ["git", "tag", "--list", "v*"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise CheckFailure(["could not read local git tags: " + result.stderr.strip()])
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def read_github_release_tags(root: Path, repo: str) -> list[str]:
    result = subprocess.run(
        ["gh", "release", "list", "--repo", repo, "--limit", "100", "--json", "tagName"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise CheckFailure(
            ["could not read GitHub releases with gh: " + result.stderr.strip()]
        )
    data = json.loads(result.stdout or "[]")
    return [
        item["tagName"]
        for item in data
        if isinstance(item, dict) and isinstance(item.get("tagName"), str)
    ]


def latest_release_version(tags: Iterable[str]) -> str | None:
    versions = [tag.lstrip("v") for tag in tags if RELEASE_HEADING_RE.match(f"{tag.lstrip('v')} - 2000-01-01")]
    if not versions:
        return None
    return max(versions, key=version_key)


def version_key(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".", 2)
    return int(major), int(minor), int(patch)


if __name__ == "__main__":
    raise SystemExit(main())
