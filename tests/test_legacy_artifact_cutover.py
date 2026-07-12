from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_cli


LEGACY_PATHS = (
    "_paperops/claims",
    "_paperops/evidence",
    "_paperops/review",
    "_paperops/requests",
    "_paperops/workflow/current-state.yml",
    "_paperops/workflow/decisions.yml",
    "_paperops/workflow/round-summary.yml",
    "_paperops/workflow/submission-ledger.yml",
)


class LegacyArtifactCutoverTest(unittest.TestCase):
    def test_source_and_initialized_scaffold_have_no_legacy_authority_artifacts(self) -> None:
        for relative in LEGACY_PATHS:
            self.assertFalse((ROOT / "template" / relative).exists(), relative)
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper"
            code, _out, err = run_cli(["init", str(project)])
            self.assertEqual(code, 0, err)
            for relative in LEGACY_PATHS:
                self.assertFalse((project / relative).exists(), relative)

    def test_init_parser_no_longer_exposes_authority_selector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(SystemExit) as raised:
            run_cli(["init", str(Path(tmp) / "paper"), "--authority", "legacy"])
        self.assertEqual(raised.exception.code, 2)

    def test_storyline_keeps_controlled_view_without_legacy_results_fallback(self) -> None:
        text = (ROOT / "template/_paperops/notes/views/storyline.md").read_text()
        self.assertIn("Methods definition registry", text)
        self.assertIn("Discussion functions", text)
        self.assertNotIn("legacy Markdown", text)
        self.assertNotIn("_paperops/claims/", text)
        self.assertNotIn("_paperops/evidence/", text)

    def test_managed_update_does_not_delete_existing_project_legacy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper"
            code, _out, err = run_cli(["init", str(project)])
            self.assertEqual(code, 0, err)
            legacy = project / "_paperops/claims/claims/existing.md"
            legacy.parent.mkdir(parents=True, exist_ok=True); legacy.write_text("project-owned\n")
            code, _out, err = run_cli(["update-paperops", str(project), "--apply"])
            self.assertEqual(code, 0, err)
            self.assertEqual(legacy.read_text(), "project-owned\n")


if __name__ == "__main__":
    unittest.main()
