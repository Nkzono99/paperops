#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


PLACEHOLDER_RE = re.compile(r"(未記入|記入|public scientific term|internal_run_label|local_directory_name|TBD|TODO)")
TERM_STATUS_RE = re.compile(r"^(public|needs_definition|internal_only|forbidden)$")


@dataclass
class Finding:
    severity: str
    message: str


def clean_scalar(value: str) -> str:
    value = value.strip()
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value.strip()


def is_placeholder(value: str | None) -> bool:
    return value is None or not str(value).strip() or PLACEHOLDER_RE.search(str(value)) is not None


def normalize_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def parse_minimal_yaml(text: str) -> dict:
    data: dict[str, object] = {}
    terms: list[dict[str, object]] = []
    current_term: dict[str, object] | None = None
    current_list_key: str | None = None
    in_terms = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "terms:":
            in_terms = True
            data["terms"] = terms
            continue
        if not in_terms:
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                data[key.strip()] = clean_scalar(value)
            continue

        if stripped.startswith("- "):
            remainder = stripped[2:].strip()
            if ":" in remainder and not remainder.startswith('"'):
                current_term = {}
                terms.append(current_term)
                key, value = remainder.split(":", 1)
                current_term[key.strip()] = clean_scalar(value)
                current_list_key = None
            elif current_term is not None and current_list_key is not None:
                current_term.setdefault(current_list_key, [])
                list_value = current_term[current_list_key]
                if isinstance(list_value, list):
                    list_value.append(clean_scalar(remainder))
            continue

        if current_term is None or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = clean_scalar(value)
        if value == "":
            current_term[key] = []
            current_list_key = key
        else:
            current_term[key] = value
            current_list_key = None

    return data


def load_terminology(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text) or {}
    else:
        loaded = parse_minimal_yaml(text)
    terms = loaded.get("terms", [])
    if isinstance(terms, dict):
        return [{"ja": key, "en_public": value, "status": "public"} for key, value in terms.items()]
    if not isinstance(terms, list):
        return []
    return [term for term in terms if isinstance(term, dict)]


def iter_manuscript_files(root: Path):
    manuscript = root / "manuscript"
    if not manuscript.exists():
        return
    for path in sorted(manuscript.glob("**/*.tex")):
        if "shared/style" in path.as_posix():
            continue
        yield path


def term_values(term: dict) -> list[str]:
    values: list[str] = []
    for key in ["ja", "en_public"]:
        value = term.get(key)
        if isinstance(value, str) and not is_placeholder(value):
            values.append(value)
    avoid = term.get("avoid", [])
    if isinstance(avoid, list):
        values.extend(str(item) for item in avoid if not is_placeholder(str(item)))
    return values


def find_occurrences(root: Path, needles: list[str]) -> list[str]:
    occurrences: list[str] = []
    if not needles:
        return occurrences
    for path in iter_manuscript_files(root):
        rel_path = path.relative_to(root).as_posix()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for number, line in enumerate(lines, start=1):
            for needle in needles:
                if needle and needle in line:
                    occurrences.append(f"`{rel_path}:{number}` に `{needle}`")
    return occurrences


def check_terms(root: Path, terms: list[dict]) -> list[Finding]:
    findings: list[Finding] = []
    for term in terms:
        term_id = str(term.get("id", "unknown"))
        status = str(term.get("status", "public")).strip()
        if not TERM_STATUS_RE.match(status):
            findings.append(Finding("warning", f"`{term_id}` の status `{status}` は未知です"))
            continue

        values = term_values(term)
        occurrences = find_occurrences(root, values)

        if status in {"internal_only", "forbidden"} and occurrences:
            for occurrence in occurrences:
                findings.append(Finding("error", f"`{term_id}` は `{status}` ですが、{occurrence} が出現しています"))
            continue

        avoid_values = [str(item) for item in term.get("avoid", []) if not is_placeholder(str(item))]
        avoid_occurrences = find_occurrences(root, avoid_values)
        for occurrence in avoid_occurrences:
            findings.append(Finding("error", f"`{term_id}` の avoid 語が公開原稿に残っています: {occurrence}"))

        if status == "needs_definition" and occurrences:
            if normalize_bool(term.get("first_definition_required", False)) and is_placeholder(
                term.get("first_definition_location")
            ):
                findings.append(
                    Finding(
                        "warning",
                        f"`{term_id}` は定義が必要ですが、first_definition_location が未記入です",
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="公開原稿に内部語・禁止語・未定義用語が残っていないか確認する。")
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()

    root = args.root.resolve()
    terminology_path = root / "manuscript/mirror/terminology.yml"
    if not terminology_path.exists():
        print("public-terms-check に失敗しました")
        print("- `manuscript/mirror/terminology.yml` が見つかりません")
        return 1

    findings = check_terms(root, load_terminology(terminology_path))
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# public-terms-check")
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
        print("公開原稿に内部語・禁止語の混入は見つかりませんでした。")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
