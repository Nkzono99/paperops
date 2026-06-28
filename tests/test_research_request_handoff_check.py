from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-research-request-handoff.py"


def write_locations(project: Path, runops_dir: Path) -> None:
    locations = project / "_paperops" / "refs" / "local" / "locations.toml"
    locations.parent.mkdir(parents=True, exist_ok=True)
    locations.write_text(
        "\n".join(
            [
                "[paths.runops_main]",
                'kind = "runops_project"',
                'host = "local-desktop"',
                f'path = "{runops_dir.as_posix()}"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_request_card(
    project: Path,
    *,
    request_id: str = "AREQ-0008",
    status: str = "open",
    target_link: str = "runops-main",
    runops_id: str = "draft:PAPER-REQ-0008",
) -> None:
    card = project / "_paperops" / "requests" / "analysis" / f"{request_id}.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(
        "\n".join(
            [
                "---",
                f"id: {request_id}",
                "type: analysis_request",
                f"status: {status}",
                f"target_project_link: {target_link}",
                f"runops_id: {runops_id}",
                "---",
                "",
                "# Analysis Request",
                "",
                "## 依頼内容",
                "",
                "追加解析を linked runops queue に渡す。",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_queue(runops_dir: Path, body: str) -> None:
    queue = runops_dir / "research" / "paper_requests.toml"
    queue.parent.mkdir(parents=True, exist_ok=True)
    queue.write_text(body, encoding="utf-8")


class ResearchRequestHandoffCheckTest(unittest.TestCase):
    def test_warns_and_strict_fails_when_draft_is_not_queued(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            runops_dir = Path(tmp) / "runops"
            write_locations(project, runops_dir)
            write_queue(runops_dir, "schema_version = 1\n")
            write_request_card(project)

            result = run_python_script(SCRIPT, "--root", project)
            strict_result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(strict_result.returncode, 1, strict_result.stdout + strict_result.stderr)
        self.assertIn("draft staged but not queued", result.stdout)
        self.assertIn("PAPER-REQ-0008", result.stdout)

    def test_passes_when_runops_queue_contains_request_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            runops_dir = Path(tmp) / "runops"
            write_locations(project, runops_dir)
            write_queue(
                runops_dir,
                "\n".join(
                    [
                        "schema_version = 1",
                        "",
                        "[[requests]]",
                        'id = "PAPER-REQ-0008"',
                        'status = "open"',
                        "",
                    ]
                ),
            )
            write_request_card(project, runops_id="PAPER-REQ-0008")

            result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("research request handoff に問題は見つかりませんでした", result.stdout)

    def test_warns_when_active_request_cannot_resolve_local_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_request_card(project)

            result = run_python_script(SCRIPT, "--root", project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("local path を解決できません", result.stdout)
        self.assertIn("request handoff not checked", result.stdout)

    def test_notes_view_request_rows_are_checked_for_missing_runops_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            runops_dir = Path(tmp) / "runops"
            write_locations(project, runops_dir)
            write_queue(runops_dir, "schema_version = 1\n")
            view = project / "_paperops" / "notes" / "views" / "research-requests.md"
            text = view.read_text(encoding="utf-8")
            view.write_text(
                text.replace(
                    "| AREQ-0001 | `_paperops/requests/analysis/AREQ-0001.md` | FB-0001 | CLM-0001 | _paperops/refs/links.toml | 未記入 | denominator / independence / convergence / external validation / figure redesign | blank / draft:* / queued ID | planned |",
                    "| AREQ-0001 | `_paperops/requests/analysis/AREQ-0001.md` | FB-0001 | CLM-0001 | _paperops/refs/links.toml | 未記入 | denominator / independence / convergence / external validation / figure redesign | blank / draft:* / queued ID | planned |\n"
                    "| RR-0008 | `_paperops/requests/analysis/RR-0008.md` | FB-0001 | CLM-0001 | runops-main | verification table | convergence | blank | open |",
                ),
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("runops_id 未記入", result.stdout)
        self.assertIn("RR-0008", result.stdout)

    def test_makefile_exposes_research_request_handoff_check_target(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("research-request-handoff-check:", makefile)
        self.assertIn("check-research-request-handoff.py", makefile)
        self.assertIn("research-request-handoff-check", makefile.split("ci:", 1)[1])


if __name__ == "__main__":
    unittest.main()
