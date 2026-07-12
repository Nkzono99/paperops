#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from paperops_paths import display_path, internal_path


PLACEHOLDER_RE = re.compile(r"(未記入|TBD|TODO|置き換えてください)")
LOCAL_COUNT_RE = re.compile(
    r"(\d+\s*/\s*\d+|\d+\s*(?:条件|点|個|cases?|conditions?)\s*(?:中|のうち|out of|of)\s*\d+|\d+\s*(?:個|点)?の保存時刻のうち\s*\d+)"
)
DEFENSIVE_RE = re.compile(
    r"(直接証明ではない|主張しない|証拠としては使わない|限定する|限定される|条件付き|確認した条件|"
    r"bracket|screening|exploratory|caveat|not claim|not evidence|not intended)",
    re.IGNORECASE,
)
LOCAL_PROVENANCE_RE = re.compile(
    r"(run label|directory name|script name|artifact name|raw run|scheduler log|中間出力ディレクトリ|実行識別子)",
    re.IGNORECASE,
)
NOTE_LABEL_ONLY_RE = re.compile(
    r"^(?:[-*]\s*)?(?:[A-Z]{1,8}-?\d{2,5}\s+)?[A-Za-z0-9][A-Za-z0-9_./:-]*"
    r"(?:\s+[A-Za-z0-9][A-Za-z0-9_./:-]*){0,5}$"
)
NOTE_LABEL_MARKER_RE = re.compile(r"\b[A-Z]{1,8}-?\d{2,5}\b|[-_][A-Za-z0-9]")
COMPARATOR_OVERCLAIM_RE = re.compile(
    r"(lost in|not captured by|better than|stronger than|weaker than|outperform|"
    r"従来近似|従来法|近似では失われ|より強い|より弱い|"
    r"center[- ]charge|net[- ]charge|grain[- ]centered|object[- ]level|"
    r"中心電荷|粒子中心|平均化|axisym|random patch)",
    re.IGNORECASE,
)
COMPLETION_WORD_RE = re.compile(
    r"(completed|completion|final snapshot|latest|last|onset|fraction|saved snapshots?|"
    r"完了|最終|保存時刻|後半|割合)",
    re.IGNORECASE,
)
EQUILIBRIUM_WORD_RE = re.compile(
    r"(equilibrium|steady[- ]state|steady state|calibrated exposure|independent samples?|probability|"
    r"帯電平衡|物理的平衡|定常|較正済み|独立標本|確率)",
    re.IGNORECASE,
)


@dataclass
class Finding:
    severity: str
    message: str


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_blank(value: str) -> bool:
    return not value.strip() or PLACEHOLDER_RE.search(value) is not None


def section_body(text: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        return ""
    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end].strip()


def resolve_view_path(root: Path, preferred: str, legacy: str, findings: list[Finding]) -> tuple[str, Path] | None:
    preferred_path = internal_path(root, preferred)
    if preferred_path.exists():
        return display_path(root, preferred_path), preferred_path
    legacy_path = internal_path(root, legacy)
    if legacy_path.exists():
        return display_path(root, legacy_path), legacy_path
    findings.append(Finding("error", f"`{display_path(root, preferred_path)}` が見つかりません（旧互換: `{legacy}`）"))
    return None


REQUIRED_VIEW_MAPS = [
    (
        "notes/views/argument-map.md",
        "notes/argument-map.md",
        ("一文の中心主張", "証拠の階層", "ローカル条件から公開主張への抽象化", "Defense budget"),
        "一文の中心主張",
    ),
    (
        "notes/views/result-pattern-map.md",
        "notes/result-pattern-map.md",
        ("結果パターン inventory", "観察から解釈への変換", "Evidence packet 化する場合", "Claim に昇格する前の確認"),
        None,
    ),
    (
        "notes/views/condition-context-map.md",
        "notes/condition-context-map.md",
        ("条件軸の公開名", "Local condition から paper context への対応", "条件の役割", "本文で言ってよい形"),
        None,
    ),
]


def check_view_maps(root: Path, findings: list[Finding]) -> None:
    for preferred, legacy, headings, blank_warning_heading in REQUIRED_VIEW_MAPS:
        resolved = resolve_view_path(root, preferred, legacy, findings)
        if resolved is None:
            continue
        rel_path, path = resolved
        text = read_text(path)
        for heading in headings:
            if f"## {heading}" not in text:
                findings.append(Finding("error", f"`{rel_path}` に `{heading}` セクションがありません"))
        if blank_warning_heading and is_blank(section_body(text, blank_warning_heading)):
            findings.append(Finding("warning", f"`{rel_path}` の一文の中心主張が未記入です"))


def manuscript_files(root: Path) -> list[Path]:
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return []
    return [
        path
        for path in sorted(manuscript.glob("**/*.tex"))
        if "shared/style" not in path.as_posix()
    ]


def note_files(root: Path) -> list[Path]:
    notes = internal_path(root, "notes")
    if not notes.exists():
        return []
    return [
        path
        for path in sorted(notes.glob("**/*.md"))
        if not path.name.endswith(".generated.md")
    ]


def content_lines_without_frontmatter(text: str) -> list[tuple[int, str]]:
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        for index, line in enumerate(lines[1:], start=1):
            if line.strip() == "---":
                start = index + 1
                break
    return list(enumerate(lines[start:], start=start + 1))


def check_manuscript_smells(root: Path, findings: list[Finding]) -> None:
    defensive_counts: dict[str, int] = {}
    for path in manuscript_files(root):
        rel_path = path.relative_to(root).as_posix()
        for number, line in enumerate(read_text(path).splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("%"):
                continue
            if LOCAL_COUNT_RE.search(stripped):
                findings.append(
                    Finding(
                        "warning",
                        f"`{rel_path}:{number}` にローカル条件数の列挙があります。物理的意味・境界条件・証拠階層へ抽象化してください",
                    )
                )
            if LOCAL_PROVENANCE_RE.search(stripped):
                findings.append(
                    Finding(
                        "warning",
                        f"`{rel_path}:{number}` に内部 provenance 語があります。公開語へ置換するか `_paperops/notes/` / `_paperops/refs/` へ退避してください",
                    )
                )
            if COMPARATOR_OVERCLAIM_RE.search(stripped):
                findings.append(
                    Finding(
                        "warning",
                        f"`{rel_path}:{number}` に direct comparator 未確認の比較・方法新規性 claim らしい表現があります。"
                        " matched comparator が無い場合は `not collapsed to ...` のような使用範囲表現に落とし、typed Issue Model の analysis_request に比較依頼を残してください",
                    )
                )
            if COMPLETION_WORD_RE.search(stripped) and EQUILIBRIUM_WORD_RE.search(stripped):
                findings.append(
                    Finding(
                        "warning",
                        f"`{rel_path}:{number}` で run completion と physical equilibrium / calibrated exposure / independent sample が近接しています。"
                        " completed run、final snapshot、steady state、time calibration、independent samples を別 status として gate してください",
                    )
                )
            if DEFENSIVE_RE.search(stripped):
                defensive_counts[rel_path] = defensive_counts.get(rel_path, 0) + 1

    for rel_path, count in sorted(defensive_counts.items()):
        if count >= 3:
            findings.append(
                Finding(
                    "warning",
                    f"`{rel_path}` に防御的・限定的な表現が {count} 回あります。重要な caveat を一箇所へ集約してください",
                )
            )


def check_note_smells(root: Path, findings: list[Finding]) -> None:
    for path in note_files(root):
        rel_path = path.relative_to(root).as_posix()
        for number, line in content_lines_without_frontmatter(read_text(path)):
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("|"):
                continue
            if stripped.endswith(":") or "未記入" in stripped:
                continue
            if (
                NOTE_LABEL_ONLY_RE.fullmatch(stripped)
                and NOTE_LABEL_MARKER_RE.search(stripped)
                and any(ch.isalpha() for ch in stripped)
            ):
                findings.append(
                    Finding(
                        "warning",
                        f"`{rel_path}:{number}` はラベルだけの行に見えます。"
                        " route/status label は field として残してよいですが、同じ bullet か直後に"
                        " 前提・判断根拠・本文への影響を普通の文で展開してください",
                    )
                )


def main() -> int:
    parser = argparse.ArgumentParser(description="AI 初稿が列挙的・防御的・ローカル条件依存になっていないか確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="warning がある場合も non-zero exit を返す。")
    args = parser.parse_args()

    root = args.root.resolve()
    findings: list[Finding] = []
    check_view_maps(root, findings)
    check_manuscript_smells(root, findings)
    check_note_smells(root, findings)

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# argument-focus-check")
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
        print("AI 初稿を改稿する前に `/map-result-patterns`、`/audit-ai-draft`、`/contextualize-conditions`、必要なら `/scientific-gate` で typed Research Model と `_paperops/notes/views/` を更新してください。tracked model の更新は `pops change` を使い、claim lock 後の文体 polish だけなら `/polish-ai-draft` を使ってください。")
        print("")
    if not findings:
        print("論旨設計メモと本文の argument focus に明らかな問題は見つかりませんでした。")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
