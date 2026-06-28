#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from paperops_paths import display_path, internal_path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


LINKS_REL_PATH = "refs/links.toml"
LOCAL_LOCATIONS_REL_PATH = "refs/local/locations.toml"
LINKS_DISPLAY_PATH = "_paperops/refs/links.toml"
REQUEST_VIEW_PATHS = [
    "notes/views/research-requests.md",
    "notes/research-requests.md",
]
INACTIVE_STATUSES = {
    "closed",
    "resolved",
    "done",
    "complete",
    "completed",
    "cancelled",
    "canceled",
    "rejected",
    "defer",
    "deferred",
}
PLACEHOLDER_VALUES = {
    "",
    "blank",
    "queued id",
    "draft:*",
    "未記入",
    "tbd",
    "todo",
    "refs/links.toml",
    "_paperops/refs/links.toml",
}


@dataclass
class Finding:
    severity: str
    message: str


@dataclass
class PaperRequest:
    request_id: str
    source: str
    status: str
    target_link: str
    runops_id: str


@dataclass
class QueueState:
    path: Path
    request_ids: set[str]
    statuses: dict[str, str]
    duplicate_ids: set[str]


def read_toml(path: Path) -> dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("TOML parsing requires Python 3.11 or newer.")
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return data if isinstance(data, dict) else {}


def normalize(value: object) -> str:
    return str(value or "").strip()


def clean_cell(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1].strip()
    return value


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        value = raw_value.strip().strip('"').strip("'")
        fields[key.strip()] = value
    return fields


def is_placeholder(value: str) -> bool:
    return clean_cell(value).strip().lower() in PLACEHOLDER_VALUES


def is_active(status: str) -> bool:
    return status.strip().lower() not in INACTIVE_STATUSES


def is_placeholder_request(request: PaperRequest) -> bool:
    text = " ".join(
        [
            request.request_id,
            request.status,
            request.target_link,
            request.runops_id,
            request.source,
        ]
    )
    lower_text = text.lower()
    return request.request_id in {"AREQ-0001", "RR-0001"} and (
        "未記入" in text
        or "blank / draft:* / queued id" in lower_text
        or "blank / draft:* / queued ID" in text
    )


def load_links(root: Path, findings: list[Finding]) -> list[dict[str, Any]]:
    path = internal_path(root, LINKS_REL_PATH)
    if not path.exists():
        return []
    try:
        raw = read_toml(path)
    except Exception as exc:
        findings.append(Finding("error", f"`{display_path(root, path)}` を TOML として読めません: {exc}"))
        return []
    links = raw.get("links", [])
    if not isinstance(links, list):
        findings.append(Finding("error", f"`{display_path(root, path)}` の `links` は配列にしてください"))
        return []
    return [link for link in links if isinstance(link, dict)]


def load_local_locations(root: Path) -> dict[str, dict[str, Any]]:
    path = internal_path(root, LOCAL_LOCATIONS_REL_PATH)
    if not path.exists():
        return {}
    raw = read_toml(path)
    paths = raw.get("paths", {})
    if not isinstance(paths, dict):
        return {}
    return {key: value for key, value in paths.items() if isinstance(value, dict)}


def resolve_local_path(root: Path, link: dict[str, Any], local_locations: dict[str, dict[str, Any]]) -> Path | None:
    location_ref = normalize(link.get("location_ref"))
    if not location_ref or location_ref not in local_locations:
        return None
    raw_path = normalize(local_locations[location_ref].get("path"))
    if not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = root / path
    return path


def request_cards(root: Path) -> list[PaperRequest]:
    base = internal_path(root, "requests", "analysis")
    if not base.exists():
        return []
    requests: list[PaperRequest] = []
    for path in sorted(base.glob("*.md")):
        if path.name == "analysis-request-template.md":
            continue
        fields = frontmatter(path.read_text(encoding="utf-8", errors="replace"))
        request_id = normalize(fields.get("id")) or path.stem
        status = normalize(fields.get("status")) or "open"
        request = PaperRequest(
            request_id=request_id,
            source=display_path(root, path),
            status=status,
            target_link=normalize(fields.get("target_project_link")),
            runops_id=normalize(fields.get("runops_id")),
        )
        if request.request_id and is_active(request.status) and not is_placeholder_request(request):
            requests.append(request)
    return requests


def table_requests(root: Path) -> list[PaperRequest]:
    requests: list[PaperRequest] = []
    for rel_path in REQUEST_VIEW_PATHS:
        path = internal_path(root, rel_path)
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        headers: list[str] = []
        in_analysis = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("## "):
                in_analysis = "analysis requests" in stripped.lower()
                headers = []
                continue
            if not in_analysis or not stripped.startswith("|"):
                continue
            cells = [clean_cell(cell) for cell in stripped.strip("|").split("|")]
            if not headers:
                headers = [cell.lower() for cell in cells]
                continue
            if set(cell.strip() for cell in cells) <= {"", "---"}:
                continue
            row = {headers[index]: cells[index] for index in range(min(len(headers), len(cells)))}
            request_id = normalize(row.get("request id"))
            status = normalize(row.get("status")) or "open"
            request = PaperRequest(
                request_id=request_id,
                source=display_path(root, path),
                status=status,
                target_link=normalize(row.get("target link")),
                runops_id=normalize(row.get("runops_id")),
            )
            if request.request_id and is_active(request.status) and not is_placeholder_request(request):
                requests.append(request)
    return requests


def collect_requests(root: Path) -> list[PaperRequest]:
    seen: set[str] = set()
    collected: list[PaperRequest] = []
    for request in [*request_cards(root), *table_requests(root)]:
        key = request.request_id
        if key in seen:
            continue
        seen.add(key)
        collected.append(request)
    return collected


def request_targets_link(request: PaperRequest, link: dict[str, Any]) -> bool:
    link_id = normalize(link.get("id"))
    location_ref = normalize(link.get("location_ref"))
    target = clean_cell(request.target_link)
    if target in {link_id, location_ref}:
        return True
    if is_placeholder(target):
        return not is_placeholder(request.runops_id)
    return False


def queue_id_from_runops_id(runops_id: str) -> tuple[str, bool]:
    value = clean_cell(runops_id)
    if value.lower().startswith("draft:"):
        return value.split(":", 1)[1].strip(), True
    return value, False


def queue_state(path: Path, findings: list[Finding]) -> QueueState | None:
    if not path.exists():
        findings.append(Finding("warning", f"`{path}` が見つかりません"))
        return None
    try:
        raw = read_toml(path)
    except Exception as exc:
        findings.append(Finding("warning", f"`{path}` を TOML として読めません: {exc}"))
        return None
    rows = raw.get("requests", [])
    if not isinstance(rows, list):
        rows = []
    request_ids: set[str] = set()
    statuses: dict[str, str] = {}
    duplicate_ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        request_id = ""
        for key in ["id", "request_id", "paper_request_id", "runops_id"]:
            request_id = normalize(row.get(key))
            if request_id:
                break
        if not request_id:
            continue
        if request_id in request_ids:
            duplicate_ids.add(request_id)
        request_ids.add(request_id)
        statuses[request_id] = normalize(row.get("status"))
    return QueueState(path=path, request_ids=request_ids, statuses=statuses, duplicate_ids=duplicate_ids)


def status_group(status: str) -> str:
    value = status.strip().lower()
    if value in INACTIVE_STATUSES:
        return "closed"
    return "active"


def check_request_against_queue(
    request: PaperRequest,
    queue: QueueState | None,
    findings: list[Finding],
) -> None:
    if is_placeholder(request.runops_id):
        findings.append(
            Finding(
                "warning",
                f"`{request.request_id}` は runops_id 未記入です。linked queue に渡す draft ID または queued ID を記録してください",
            )
        )
        return
    expected_id, is_draft = queue_id_from_runops_id(request.runops_id)
    if not expected_id:
        findings.append(Finding("warning", f"`{request.request_id}` は runops_id 未記入です"))
        return
    if queue is None:
        return
    if expected_id not in queue.request_ids:
        label = "draft staged but not queued" if is_draft else "queued id not found"
        findings.append(
            Finding(
                "warning",
                f"`{request.request_id}` は {label}: `{expected_id}` が `{queue.path}` にありません",
            )
        )
        return
    if expected_id in queue.duplicate_ids:
        findings.append(
            Finding(
                "warning",
                f"`{queue.path}` で request id `{expected_id}` が重複しています",
            )
        )
    queue_status = queue.statuses.get(expected_id, "")
    if queue_status and status_group(queue_status) != status_group(request.status):
        findings.append(
            Finding(
                "warning",
                f"`{request.request_id}` の paper status `{request.status}` と queue status `{queue_status}` がずれています",
            )
        )


def check_handoff(root: Path, *, live: bool) -> list[Finding]:
    findings: list[Finding] = []
    links = load_links(root, findings)
    runops_links = [
        link
        for link in links
        if normalize(link.get("kind")) == "runops_project"
        and normalize(link.get("paper_request_queue"))
    ]
    if not runops_links:
        return findings

    requests = collect_requests(root)
    local_locations = load_local_locations(root) if live else {}
    for link in runops_links:
        link_id = normalize(link.get("id"))
        linked_requests = [request for request in requests if request_targets_link(request, link)]
        if not linked_requests:
            continue
        if not live:
            for request in linked_requests:
                check_request_against_queue(request, None, findings)
            continue
        local_path = resolve_local_path(root, link, local_locations)
        if local_path is None or not local_path.exists():
            findings.append(
                Finding(
                    "warning",
                    f"`{link_id}` の local path を解決できません。request handoff not checked: "
                    + ", ".join(request.request_id for request in linked_requests),
                )
            )
            continue
        queue_rel = normalize(link.get("paper_request_queue"))
        queue = queue_state(local_path / queue_rel, findings)
        for request in linked_requests:
            check_request_against_queue(request, queue, findings)
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="paper 側の追加解析 request と linked runops queue の handoff drift を確認する。"
    )
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--strict", action="store_true", help="warning がある場合も non-zero exit を返す。")
    parser.add_argument(
        "--live",
        action="store_true",
        help="linked runops queue を実際に読み、queued ID / status drift を確認する。",
    )
    args = parser.parse_args()

    findings = check_handoff(args.root.resolve(), live=args.live)
    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]

    print("# research-request-handoff-check")
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
        print("research request handoff に問題は見つかりませんでした。")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
