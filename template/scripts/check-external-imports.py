#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops_paths import display_path, internal_path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None  # type: ignore[assignment]


LINKS_REL_PATH = "refs/links.toml"
LOCAL_LOCATIONS_REL_PATH = "refs/local/locations.toml"
IMPORTS_REL_PATH = "refs/imports"
LINKS_DISPLAY_PATH = "_paperops/refs/links.toml"
IMPORTS_DISPLAY_PATH = "_paperops/refs/imports/"

ALLOWED_STATES = {
    "script_only_candidate",
    "import_hook_candidate",
    "dirty_integrated_candidate",
    "dirty_indexed_candidate",
    "tracked_indexed_export",
    "paper_imported_state",
    "rejected_or_discarded",
}
INDEXED_STATES = {
    "dirty_indexed_candidate",
    "tracked_indexed_export",
    "paper_imported_state",
}
CLEAN_PROVENANCE_STATES = {
    "tracked_indexed_export",
    "paper_imported_state",
}
ALLOWED_CLAIM_POLICIES = {
    "supported-evidence",
    "supplement-only",
    "authoring-guard",
    "provenance-only",
    "notes-only",
    "needs-triage",
    "do-not-use",
}
FALSE_VALUES = {"false", "0", "no", "n"}


@dataclass(frozen=True)
class Finding:
    severity: str
    message: str


def read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("TOML parsing requires Python 3.11 or newer.")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data if isinstance(data, dict) else {}


def add(findings: list[Finding], severity: str, message: str) -> None:
    findings.append(Finding(severity=severity, message=message))


def load_links(root: Path, findings: list[Finding]) -> dict[str, dict[str, Any]]:
    path = internal_path(root, LINKS_REL_PATH)
    if not path.exists():
        return {}
    try:
        raw = read_toml(path)
    except Exception as exc:
        add(findings, "error", f"`{display_path(root, path)}` を TOML として読めません: {exc}")
        return {}
    links = raw.get("links", [])
    if not isinstance(links, list):
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for item in links:
        if isinstance(item, dict):
            link_id = str(item.get("id", "")).strip()
            if link_id:
                rows[link_id] = item
    return rows


def load_local_locations(root: Path) -> dict[str, dict[str, Any]]:
    path = internal_path(root, LOCAL_LOCATIONS_REL_PATH)
    if not path.exists():
        return {}
    raw = read_toml(path)
    paths = raw.get("paths", {})
    if not isinstance(paths, dict):
        return {}
    return {key: value for key, value in paths.items() if isinstance(value, dict)}


def import_record_paths(root: Path) -> list[Path]:
    imports_dir = internal_path(root, IMPORTS_REL_PATH)
    if not imports_dir.exists():
        return []
    paths: list[Path] = []
    for path in sorted(imports_dir.glob("*.toml")):
        if path.name == "import-state-template.toml" or path.name.endswith(".example.toml"):
            continue
        paths.append(path)
    return paths


def table(raw: dict[str, Any], key: str) -> dict[str, Any]:
    value = raw.get(key, {})
    return value if isinstance(value, dict) else {}


def string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def relative_path(value: Any, label: str, record_label: str, findings: list[Finding]) -> Path | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        add(
            findings,
            "warning",
            f"`{record_label}` の `{label}` は絶対パスです。tracked import state には portable な相対パスを置いてください",
        )
        return None
    return path


def count_csv_rows(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            rows = [row for row in csv.reader(f) if any(cell.strip() for cell in row)]
    except OSError:
        return None
    if not rows:
        return 0
    return max(len(rows) - 1, 0)


def count_false_column(path: Path, column: str) -> int | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or column not in reader.fieldnames:
                return None
            return sum(
                1
                for row in reader
                if str(row.get(column, "")).strip().lower() in FALSE_VALUES
            )
    except OSError:
        return None


def git_current_state(repo: Path) -> tuple[str | None, bool | None]:
    if not repo.exists():
        return None, None
    try:
        inside = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if inside.returncode != 0 or inside.stdout.strip() != "true":
            return None, None
        head = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    commit = head.stdout.strip() if head.returncode == 0 else None
    dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
    return commit, dirty


def resolved_export_base(
    record: dict[str, Any],
    link: dict[str, Any],
    local_locations: dict[str, dict[str, Any]],
    record_label: str,
    findings: list[Finding],
) -> tuple[Path | None, Path | None]:
    location_ref = str(link.get("location_ref", "")).strip()
    local = local_locations.get(location_ref)
    if not local:
        return None, None
    local_path_raw = str(local.get("path", "")).strip()
    if not local_path_raw:
        add(findings, "warning", f"`{record_label}` の local path `{location_ref}` が空のため live freshness を確認できません")
        return None, None
    local_path = Path(local_path_raw)
    if not local_path.exists():
        add(findings, "warning", f"`{record_label}` の local path `{location_ref}` が存在しないため live freshness を確認できません")
        return None, local_path
    export_rel = relative_path(table(record, "export").get("path"), "export.path", record_label, findings)
    export_base = local_path / export_rel if export_rel else local_path
    return export_base, local_path


def compare_live_csv(
    *,
    record_label: str,
    table_name: str,
    display_name: str,
    record_table: dict[str, Any],
    export_base: Path | None,
    findings: list[Finding],
) -> None:
    if not record_table:
        return
    rel_path = relative_path(record_table.get("path"), f"{table_name}.path", record_label, findings)
    if export_base is None or rel_path is None:
        return
    live_path = export_base / rel_path
    if not live_path.exists():
        add(findings, "warning", f"`{record_label}` の live {display_name} が見つかりません: `{rel_path.as_posix()}`")
        return
    recorded_rows = int_value(record_table.get("rows"))
    live_rows = count_csv_rows(live_path)
    if recorded_rows is not None and live_rows is not None and recorded_rows != live_rows:
        add(
            findings,
            "warning",
            f"`{record_label}` の {display_name} rows drift: recorded {recorded_rows}, live {live_rows}",
        )
    if table_name == "source_index":
        recorded_false = int_value(record_table.get("source_exists_false"))
        live_false = count_false_column(live_path, "source_exists")
        if recorded_false is not None and live_false is not None and recorded_false != live_false:
            add(
                findings,
                "warning",
                f"`{record_label}` の source_exists=false count drift: recorded {recorded_false}, live {live_false}",
            )
        if live_false:
            add(
                findings,
                "warning",
                f"`{record_label}` の live source index に source_exists=false が {live_false} 行あります",
            )


def check_record(
    path: Path,
    record: dict[str, Any],
    links: dict[str, dict[str, Any]],
    local_locations: dict[str, dict[str, Any]],
    findings: list[Finding],
) -> None:
    rel_label = path.as_posix()
    record_id = str(record.get("id", "")).strip()
    record_label = record_id or rel_label

    if record.get("schema_version") != 1:
        add(findings, "error", f"`{rel_label}` の `schema_version` は 1 である必要があります")

    link_id = str(record.get("link_id", "")).strip()
    state = str(record.get("state", "")).strip()
    claim_policy = str(record.get("claim_evidence_policy", "")).strip()

    if not record_id:
        add(findings, "error", f"`{rel_label}` に `id` がありません")
    if not link_id:
        add(findings, "error", f"`{record_label}` に `link_id` がありません")
    elif link_id not in links:
        add(
            findings,
            "error",
            f"`{record_label}` の link_id `{link_id}` は `{LINKS_DISPLAY_PATH}` にありません",
        )

    if state not in ALLOWED_STATES:
        add(findings, "error", f"`{record_label}` の state `{state}` は未知です")

    if not str(record.get("artifact_category_summary", "")).strip():
        add(findings, "warning", f"`{record_label}` に `artifact_category_summary` がありません")
    if claim_policy not in ALLOWED_CLAIM_POLICIES:
        add(
            findings,
            "warning",
            f"`{record_label}` の `claim_evidence_policy` は {', '.join(sorted(ALLOWED_CLAIM_POLICIES))} のいずれかにしてください",
        )
    if not string_list(record.get("must_not_claim")):
        add(findings, "warning", f"`{record_label}` の `must_not_claim` が空です")

    source = table(record, "source")
    if state in CLEAN_PROVENANCE_STATES:
        if not str(source.get("commit", "")).strip():
            add(findings, "warning", f"`{record_label}` は clean provenance state ですが `source.commit` がありません")
        if source.get("dirty") is True:
            add(findings, "warning", f"`{record_label}` は clean provenance state ですが `source.dirty = true` です")

    source_index = table(record, "source_index")
    integrity = table(record, "integrity_manifest")
    if state in INDEXED_STATES:
        for table_name, record_table in [
            ("source_index", source_index),
            ("integrity_manifest", integrity),
        ]:
            if not str(record_table.get("path", "")).strip():
                add(findings, "warning", f"`{record_label}` は indexed state ですが `{table_name}.path` がありません")
            if int_value(record_table.get("rows")) is None:
                add(findings, "warning", f"`{record_label}` は indexed state ですが `{table_name}.rows` がありません")

    artifacts = record.get("artifacts", [])
    if artifacts and isinstance(artifacts, list):
        for index, artifact in enumerate(artifacts, start=1):
            if not isinstance(artifact, dict):
                add(findings, "warning", f"`{record_label}` の artifacts[{index}] は table にしてください")
                continue
            name = str(artifact.get("name", f"artifacts[{index}]")).strip()
            if not str(artifact.get("category", "")).strip():
                add(findings, "warning", f"`{record_label}` の artifact `{name}` に category がありません")
            if not str(artifact.get("claim_role", "")).strip():
                add(findings, "warning", f"`{record_label}` の artifact `{name}` に claim_role がありません")
            artifact_state = str(artifact.get("state", "")).strip()
            if artifact_state and artifact_state not in ALLOWED_STATES:
                add(findings, "warning", f"`{record_label}` の artifact `{name}` の state `{artifact_state}` は未知です")

    link = links.get(link_id, {})
    export_base, local_path = resolved_export_base(record, link, local_locations, record_label, findings)
    compare_live_csv(
        record_label=record_label,
        table_name="source_index",
        display_name="source index",
        record_table=source_index,
        export_base=export_base,
        findings=findings,
    )
    compare_live_csv(
        record_label=record_label,
        table_name="integrity_manifest",
        display_name="integrity manifest",
        record_table=integrity,
        export_base=export_base,
        findings=findings,
    )

    if local_path is not None:
        current_commit, current_dirty = git_current_state(local_path)
        recorded_commit = str(source.get("commit", "")).strip()
        if recorded_commit and current_commit and recorded_commit != current_commit:
            add(
                findings,
                "warning",
                f"`{record_label}` の source commit drift: recorded {recorded_commit}, live {current_commit}",
            )
        recorded_dirty = source.get("dirty")
        if isinstance(recorded_dirty, bool) and current_dirty is not None and recorded_dirty != current_dirty:
            add(
                findings,
                "warning",
                f"`{record_label}` の source dirty state drift: recorded {recorded_dirty}, live {current_dirty}",
            )


def check_external_imports(root: Path) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    links = load_links(root, findings)
    local_locations = load_local_locations(root)
    paths = import_record_paths(root)
    for path in paths:
        try:
            record = read_toml(path)
        except Exception as exc:
            add(findings, "error", f"`{path.relative_to(root).as_posix()}` を TOML として読めません: {exc}")
            continue
        check_record(path.relative_to(root), record, links, local_locations, findings)
    return findings, len(paths)


def print_findings(findings: list[Finding], record_count: int) -> None:
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# external-import-check")
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
    if record_count == 0:
        print(f"記録済み import state はありません。外部 bundle を使う前に `{IMPORTS_DISPLAY_PATH}` へ state record を作成してください。")
    elif not findings:
        print("external import state に問題は見つかりませんでした。")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="外部 export bundle の source index / integrity / provenance state を advisory に確認する。",
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--strict",
        action="store_true",
        help="warning も失敗扱いにする。",
    )
    args = parser.parse_args()

    findings, record_count = check_external_imports(args.root.resolve())
    print_findings(findings, record_count)
    has_errors = any(finding.severity == "error" for finding in findings)
    has_warnings = any(finding.severity == "warning" for finding in findings)
    return 1 if has_errors or (args.strict and has_warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
