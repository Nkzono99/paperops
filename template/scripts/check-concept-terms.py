#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path

from paperops_paths import display_path, internal_path


VIEW_REL_PATH = "notes/views/concept-terms.md"
ALLOWED_STATUSES = {"accepted", "needs-review", "plain-language", "avoid"}
PLACEHOLDER_RE = re.compile(r"(未記入|TBD|TODO|canonical term|plain-language expansion)", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-/][A-Za-z0-9]+)*")
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "before",
    "by",
    "define",
    "defined",
    "defines",
    "for",
    "from",
    "in",
    "include",
    "includes",
    "is",
    "it",
    "of",
    "on",
    "only",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}


@dataclass
class Finding:
    severity: str
    message: str


@dataclass
class ConceptTerm:
    term_id: str
    canonical: str
    status: str
    variants: set[str] = field(default_factory=set)


@dataclass
class Occurrence:
    term: str
    normalized: str
    rel_path: str
    line_number: int
    line: str

    @property
    def location(self) -> str:
        return f"{self.rel_path}:{self.line_number}"


def is_placeholder(value: str) -> bool:
    return not value.strip() or PLACEHOLDER_RE.search(value) is not None


def normalize_term(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[`*_{}\\]", " ", value)
    value = re.sub(r"[-/]+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def strip_tex_commands(line: str) -> str:
    line = re.sub(r"%.*$", "", line)
    line = re.sub(r"`[^`]+`", " ", line)
    line = re.sub(r"\\(?:cite|ref|label|url|path|input|includegraphics)(?:\[[^\]]*\])?\{[^}]*\}", " ", line)
    line = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", line)
    line = line.replace("{", " ").replace("}", " ")
    return line


def split_variant_cell(value: str) -> list[str]:
    if is_placeholder(value):
        return []
    return [part.strip() for part in re.split(r"\s*;\s*", value) if part.strip()]


def parse_table_rows(text: str, heading: str) -> tuple[list[str], list[dict[str, str]]]:
    lines = text.splitlines()
    in_section = False
    headers: list[str] = []
    rows: list[dict[str, str]] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == f"## {heading}"
            headers = []
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = [cell.strip().strip("`") for cell in stripped.strip("|").split("|")]
        if not headers:
            headers = [cell.lower() for cell in cells]
            continue
        if set(cell.replace("-", "").strip() for cell in cells) <= {""}:
            continue
        row = {headers[index]: cells[index] for index in range(min(len(headers), len(cells)))}
        rows.append(row)
    return headers, rows


def load_concept_terms(root: Path, findings: list[Finding]) -> dict[str, ConceptTerm]:
    path = internal_path(root, VIEW_REL_PATH)
    if not path.exists():
        findings.append(Finding("error", f"`{display_path(root, path)}` が見つかりません"))
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    required_sections = ["Concept term map", "Usage audit", "Plain-language expansion log"]
    for section in required_sections:
        if f"## {section}" not in text:
            findings.append(Finding("error", f"`{display_path(root, path)}` に `{section}` セクションがありません"))

    _, rows = parse_table_rows(text, "Concept term map")
    terms: dict[str, ConceptTerm] = {}
    for row in rows:
        canonical = row.get("canonical term", "").strip()
        if is_placeholder(canonical):
            continue
        status = row.get("status", "needs-review").strip()
        term_id = row.get("term id", canonical).strip() or canonical
        if status not in ALLOWED_STATUSES:
            findings.append(Finding("warning", f"`{term_id}` の status `{status}` は未知です"))
        term = ConceptTerm(term_id=term_id, canonical=canonical, status=status)
        for variant in split_variant_cell(row.get("variants / avoid", "")):
            term.variants.add(variant)
        terms[normalize_term(canonical)] = term
        for variant in term.variants:
            terms[normalize_term(variant)] = term
    return terms


def manuscript_files(root: Path) -> list[Path]:
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return []
    return [
        path
        for path in sorted(manuscript.glob("**/*.tex"))
        if "shared/style" not in path.as_posix() and "mirror/reports" not in path.as_posix()
    ]


def token_is_termish(token: str) -> bool:
    return "-" in token or "/" in token


def is_stop_token(token: str) -> bool:
    return token.lower().strip("-/") in STOPWORDS


def extract_candidates_from_line(line: str) -> list[str]:
    cleaned = strip_tex_commands(line)
    tokens = [(match.group(0), match.start(), match.end()) for match in TOKEN_RE.finditer(cleaned)]
    candidates: list[tuple[int, int, str]] = []
    for index, (token, start_pos, end_pos) in enumerate(tokens):
        if not token_is_termish(token):
            continue

        start = index
        while start > 0 and index - start < 2:
            previous = tokens[start - 1][0]
            if is_stop_token(previous) or token_is_termish(previous):
                break
            start -= 1

        end = index + 1
        while end < len(tokens) and end - index <= 3:
            next_token = tokens[end][0]
            if is_stop_token(next_token) or token_is_termish(next_token):
                break
            end += 1

        span_start = tokens[start][1]
        span_end = tokens[end - 1][2]
        candidate = cleaned[span_start:span_end].strip()
        if candidate and not is_placeholder(candidate):
            candidates.append((span_start, span_end, candidate))

    maximal: list[tuple[int, int, str]] = []
    for candidate in sorted(candidates, key=lambda item: (item[0], -(item[1] - item[0]))):
        if any(candidate[0] >= kept[0] and candidate[1] <= kept[1] for kept in maximal):
            continue
        maximal.append(candidate)
    return [candidate for _, _, candidate in maximal]


def collect_occurrences(root: Path) -> list[Occurrence]:
    occurrences: list[Occurrence] = []
    for path in manuscript_files(root):
        rel_path = path.relative_to(root).as_posix()
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not line.strip() or line.lstrip().startswith("%"):
                continue
            for candidate in extract_candidates_from_line(line):
                occurrences.append(
                    Occurrence(
                        term=candidate,
                        normalized=normalize_term(candidate),
                        rel_path=rel_path,
                        line_number=number,
                        line=line.strip(),
                    )
                )
    return occurrences


def location_summary(occurrences: list[Occurrence], limit: int = 3) -> str:
    locations = [f"`{occurrence.location}`" for occurrence in occurrences[:limit]]
    if len(occurrences) > limit:
        locations.append(f"ほか {len(occurrences) - limit} 件")
    return ", ".join(locations)


def check_terms(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    registered = load_concept_terms(root, findings)
    occurrences = collect_occurrences(root)
    by_normalized: dict[str, list[Occurrence]] = {}
    by_line: dict[str, list[Occurrence]] = {}
    for occurrence in occurrences:
        by_normalized.setdefault(occurrence.normalized, []).append(occurrence)
        by_line.setdefault(occurrence.location, []).append(occurrence)
    dense_locations = {
        location
        for location, grouped in by_line.items()
        if len({occurrence.term for occurrence in grouped}) >= 3
    }

    for normalized, grouped in sorted(by_normalized.items()):
        if not normalized:
            continue
        registered_term = registered.get(normalized)
        spellings = sorted({occurrence.term for occurrence in grouped})
        primary = spellings[0]
        dense_unregistered = any(occurrence.location in dense_locations for occurrence in grouped)
        if registered_term is None and (dense_unregistered or len(grouped) >= 2):
            findings.append(
                Finding(
                    "warning",
                    f"未登録の概念語候補: `{primary}` ({len(grouped)} 回; {location_summary(grouped)})。"
                    f"`{display_path(root, internal_path(root, VIEW_REL_PATH))}` で accepted / plain-language / avoid を判断してください",
                )
            )
        elif registered_term is not None and registered_term.status == "avoid":
            findings.append(
                Finding(
                    "error",
                    f"`{registered_term.term_id}` は avoid ですが `{primary}` が出現しています ({location_summary(grouped)})",
                )
            )
        elif registered_term is not None and registered_term.status in {"needs-review", "plain-language"}:
            findings.append(
                Finding(
                    "warning",
                    f"`{registered_term.term_id}` は {registered_term.status} ですが `{primary}` が出現しています ({location_summary(grouped)})",
                )
            )

        if len(spellings) >= 2:
            findings.append(
                Finding(
                    "warning",
                    "表記揺れ候補: "
                    + ", ".join(f"`{spelling}`" for spelling in spellings)
                    + f" ({location_summary(grouped)})",
                )
            )

        registered_status = registered_term.status if registered_term is not None else "unregistered"
        threshold = 6 if registered_status == "accepted" else 3
        if len(grouped) >= threshold:
            findings.append(
                Finding(
                    "warning",
                    f"`{primary}` が {len(grouped)} 回出現しています。強調語として必要か、普通の文へほどくか確認してください",
                )
            )

    for location, grouped in sorted(by_line.items()):
        distinct = sorted({occurrence.term for occurrence in grouped})
        if len(distinct) >= 3:
            findings.append(
                Finding(
                    "warning",
                    f"`{location}` は一文に概念語候補が {len(distinct)} 件あります: "
                    + ", ".join(f"`{term}`" for term in distinct),
                )
            )

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="本文の概念語化、hyphen/slash compound、表記揺れを確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="warning がある場合も non-zero exit を返す。")
    args = parser.parse_args()

    findings = check_terms(args.root.resolve())
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# concept-term-check")
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
        print("概念語候補は `_paperops/notes/views/concept-terms.md` に記録し、強調して残す語、普通の文へほどく語、本文から避ける語を分けてください。")
        print("")
    if not findings:
        print("本文の概念語化と表記揺れに明らかな問題は見つかりませんでした。")

    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
