#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_paths import internal_path


TEX_EXTENSIONS = ["", ".tex"]
GRAPHIC_EXTENSIONS = ["", ".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg"]
BUILTIN_BST_STYLES = {
    "abbrv",
    "alpha",
    "apalike",
    "ieeetr",
    "jplain",
    "junsrt",
    "plain",
    "unsrt",
}

INPUT_RE = re.compile(r"\\(?P<command>input|include)\s*\{(?P<target>[^}]+)\}")
GRAPHICS_RE = re.compile(r"\\includegraphics\s*(?:\[[^\]]*\]\s*)?\{(?P<target>[^}]+)\}")
BIBLIOGRAPHY_RE = re.compile(r"\\bibliography\s*\{(?P<targets>[^}]+)\}")
BIBSTYLE_RE = re.compile(r"\\bibliographystyle\s*\{(?P<target>[^}]+)\}")
GRAPHICSPATH_RE = re.compile(r"\\graphicspath\s*\{(?P<body>(?:\{[^}]+\}\s*)+)\}")
GRAPHICSPATH_ITEM_RE = re.compile(r"\{(?P<path>[^}]+)\}")


@dataclass
class Finding:
    severity: str
    message: str


def strip_comments(text: str) -> str:
    lines = []
    for line in text.splitlines():
        escaped = False
        kept = []
        for char in line:
            if char == "%" and not escaped:
                break
            kept.append(char)
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        lines.append("".join(kept))
    return "\n".join(lines)


def with_suffix_candidates(target: str, extensions: list[str]) -> list[str]:
    path = Path(target)
    if path.suffix:
        return [target]
    return [f"{target}{extension}" for extension in extensions]


def resolve_existing(base: Path, target: str, extensions: list[str]) -> Path | None:
    for candidate in with_suffix_candidates(target, extensions):
        path = (base / candidate).resolve()
        if path.exists():
            return path
    return None


def resolve_tex_include(current_file: Path, target: str) -> Path | None:
    return resolve_existing(current_file.parent, target, TEX_EXTENSIONS)


def read_tex(path: Path) -> str:
    return strip_comments(path.read_text(encoding="utf-8"))


def rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def discover_graphics_paths(path: Path, text: str) -> list[Path]:
    paths = [path.parent]
    for match in GRAPHICSPATH_RE.finditer(text):
        for item in GRAPHICSPATH_ITEM_RE.finditer(match.group("body")):
            paths.append((path.parent / item.group("path")).resolve())
    return paths


def resolve_graphic(
    root: Path,
    current_file: Path,
    main_dir: Path,
    graphics_paths: list[Path],
    target: str,
) -> Path | None:
    search_dirs = [
        *graphics_paths,
        current_file.parent,
        main_dir,
        root / "manuscript" / "shared" / "figures",
        root / "manuscript" / "shared" / "figures" / "generated",
    ]
    for directory in search_dirs:
        found = resolve_existing(directory, target, GRAPHIC_EXTENSIONS)
        if found is not None:
            return found
    return None


def resolve_bib(root: Path, current_file: Path, target: str) -> Path | None:
    search_dirs = [
        current_file.parent,
        root / "manuscript" / "shared" / "bib",
        internal_path(root, "refs", "bib", "curated"),
        internal_path(root, "refs", "bib", "imported"),
    ]
    for directory in search_dirs:
        found = resolve_existing(directory, target, ["", ".bib"])
        if found is not None:
            return found
    return None


def resolve_bst(root: Path, current_file: Path, main_dir: Path, target: str) -> Path | None:
    search_dirs = [
        current_file.parent,
        main_dir,
        root / "manuscript" / "shared" / "style",
    ]
    for directory in search_dirs:
        found = resolve_existing(directory, target, ["", ".bst"])
        if found is not None:
            return found
    style_root = root / "manuscript" / "shared" / "style"
    if style_root.is_dir() and "/" not in target and "\\" not in target:
        for candidate in with_suffix_candidates(target, ["", ".bst"]):
            for path in style_root.rglob(candidate):
                if path.is_file():
                    return path.resolve()
    return None


def scan_file(
    root: Path,
    path: Path,
    findings: list[Finding],
    visited: set[Path],
    stack: list[Path],
    main_dir: Path,
    inherited_graphics_paths: list[Path],
) -> None:
    path = path.resolve()
    if path in stack:
        cycle = " -> ".join(rel(item, root) for item in [*stack, path])
        findings.append(Finding("error", f"TeX input/include の循環を検出しました: {cycle}"))
        return
    if path in visited:
        return
    if not path.exists():
        findings.append(Finding("error", f"`{rel(path, root)}` が見つかりません"))
        return

    visited.add(path)
    stack.append(path)
    text = read_tex(path)
    graphics_paths = [*inherited_graphics_paths, *discover_graphics_paths(path, text)]

    for match in INPUT_RE.finditer(text):
        target = match.group("target").strip()
        found = resolve_tex_include(path, target)
        if found is None:
            findings.append(
                Finding(
                    "error",
                    f"`{rel(path, root)}` の `\\{match.group('command')}{{{target}}}` が見つかりません",
                )
            )
            continue
        scan_file(root, found, findings, visited, stack, main_dir, graphics_paths)

    for match in GRAPHICS_RE.finditer(text):
        target = match.group("target").strip()
        if resolve_graphic(root, path, main_dir, graphics_paths, target) is None:
            findings.append(
                Finding("error", f"`{rel(path, root)}` の `\\includegraphics{{{target}}}` が見つかりません")
            )

    for match in BIBLIOGRAPHY_RE.finditer(text):
        for target in [item.strip() for item in match.group("targets").split(",") if item.strip()]:
            if resolve_bib(root, path, target) is None:
                findings.append(
                    Finding("error", f"`{rel(path, root)}` の `\\bibliography` 参照 `{target}` が見つかりません")
                )

    for match in BIBSTYLE_RE.finditer(text):
        target = match.group("target").strip()
        if "/" not in target and "\\" not in target and target in BUILTIN_BST_STYLES:
            continue
        if resolve_bst(root, path, main_dir, target) is None:
            severity = "error" if "/" in target or "\\" in target else "warning"
            findings.append(
                Finding(
                    severity,
                    f"`{rel(path, root)}` の `\\bibliographystyle{{{target}}}` がローカルに見つかりません",
                )
            )

    stack.pop()


def main() -> int:
    parser = argparse.ArgumentParser(description="LaTeX 原稿の構造参照を軽量検証する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--main", type=Path, required=True)
    parser.add_argument("--label", default="TeX 原稿")
    args = parser.parse_args()

    root = args.root.resolve()
    main_tex = args.main.resolve()
    findings: list[Finding] = []

    scan_file(root, main_tex, findings, set(), [], main_tex.parent, [])

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print(f"# {args.label} 構造検証")
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
        print(f"{rel(main_tex, root)} の input/include、図、bibliography 参照に問題は見つかりませんでした。")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
