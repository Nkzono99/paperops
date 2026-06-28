from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-claim-evidence.py"


def write_claim_view(project: Path, body: str) -> None:
    path = project / "_paperops" / "notes" / "views" / "claim-evidence-map.md"
    path.write_text(body, encoding="utf-8")


class ClaimEvidenceCheckTest(unittest.TestCase):
    def test_non_strict_warns_when_not_claiming_item_appears_in_public_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_claim_view(
                project,
                "\n".join(
                    [
                        "# Claim Evidence Map",
                        "",
                        "| Claim ID | Claim | Evidence | Warrant / reasoning | Scope | Limitation | Manuscript blocks | Figure/Table | Status |",
                        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                        "| CLM-0001 | main claim | RES-0001 | mechanism | stated scope | limitation | abstract.block | FIG-0001 | supported |",
                        "",
                        "## Not claiming",
                        "",
                        "- forbidden central claim",
                        "",
                    ]
                ),
            )
            abstract = project / "manuscript" / "en" / "sections" / "00_abstract.tex"
            abstract.write_text(
                abstract.read_text(encoding="utf-8") + "\nforbidden central claim\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("forbidden central claim", result.stdout)

    def test_strict_fails_when_not_claiming_item_appears_in_public_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_claim_view(
                project,
                "\n".join(
                    [
                        "# Claim Evidence Map",
                        "",
                        "| Claim ID | Claim | Evidence | Warrant / reasoning | Scope | Limitation | Manuscript blocks | Figure/Table | Status |",
                        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                        "| CLM-0001 | main claim | RES-0001 | mechanism | stated scope | limitation | abstract.block | FIG-0001 | supported |",
                        "",
                        "## Not claiming",
                        "",
                        "- forbidden central claim",
                        "",
                    ]
                ),
            )
            abstract = project / "manuscript" / "en" / "sections" / "00_abstract.tex"
            abstract.write_text(
                abstract.read_text(encoding="utf-8") + "\nforbidden central claim\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Errors", result.stdout)
        self.assertIn("forbidden central claim", result.stdout)

    def test_strict_fails_when_claim_rows_remain_draft_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_claim_view(
                project,
                "\n".join(
                    [
                        "# Claim Evidence Map",
                        "",
                        "| Claim ID | Claim | Evidence | Warrant / reasoning | Scope | Limitation | Manuscript blocks | Figure/Table | Status |",
                        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
                        "| CLM-0001 | draft claim | RES-0001 | mechanism | scope | limitation | results.block | FIG-0001 | draft |",
                        "",
                    ]
                ),
            )

            result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("draft のみ", result.stdout)

    def test_finish_makefile_runs_strict_claim_evidence_check(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("check-claim-evidence.py --root . --strict", makefile)


if __name__ == "__main__":
    unittest.main()
