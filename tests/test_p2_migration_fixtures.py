from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import ROOT, copy_template, run_cli
from tests.test_issue_migration_adapter import IssueMigrationAdapterTest
from tests.test_paperops_model_check import valid_documents
from tests.test_publication_model import publication
from tests.test_research_migration_adapter import ResearchMigrationAdapterTest

from paperops.model_migration.adapters.issue import IssueAdapter
from paperops.model_migration.adapters.publication import PublicationAdapter
from paperops.model_migration.adapters.research import ResearchAdapter
from paperops.model_migration.types import MigrationInput


class P2MigrationFixtureTest(unittest.TestCase):
    def test_fixture_matrix_names_every_required_transition_case(self) -> None:
        payload = yaml.safe_load((ROOT / "tests/fixtures/migration/mixed/cases.yml").read_text())
        self.assertEqual(
            set(payload["cases"]),
            {
                "legacy-only",
                "typed-only",
                "mixed",
                "modified-managed-checker",
                "existing-project-owned-state",
                "partial-missing",
                "unknown-field",
                "private-raw-data",
                "submitted-round",
            },
        )

    def test_legacy_only_research_and_typed_only_editorial_diff_without_tracked_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            research = ResearchMigrationAdapterTest().project(Path(tmp))
            tracked = (research / "_paperops/model/research/index.yml").read_bytes()
            code, _raw, err = run_cli(["model", "diff", "research", str(research), "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual((research / "_paperops/model/research/index.yml").read_bytes(), tracked)

        with tempfile.TemporaryDirectory() as tmp:
            editorial = copy_template(tmp)
            document, results = valid_documents()
            directory = editorial / "_paperops/model/editorial"
            (directory / "editorial-model.yml").write_text(yaml.safe_dump(document, sort_keys=False))
            (directory / "results-hierarchy.yml").write_text(yaml.safe_dump(results, sort_keys=False))
            (editorial / "_paperops/notes/views/storyline.md").unlink()
            tracked = (directory / "editorial-model.yml").read_bytes()
            code, _raw, err = run_cli(["model", "diff", "editorial", str(editorial), "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual((directory / "editorial-model.yml").read_bytes(), tracked)

    def test_mixed_project_checker_drift_and_partial_missing_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            publication_path = project / "_paperops/model/publication/publication-model.yml"
            ledger = project / "_paperops/workflow/submission-ledger.yml"
            ledger.write_text(yaml.safe_dump({"schema_version": 1, "migration_publication": yaml.safe_load(publication_path.read_text())}, sort_keys=False))
            before = publication_path.read_bytes()
            code, _raw, err = run_cli(["model", "diff", "publication", str(project), "--json"])
            self.assertEqual(code, 0, err)
            self.assertEqual(publication_path.read_bytes(), before)

            checker = project / "scripts/check-paperops-models.py"
            checker.write_text("print('managed checker drift')\n")
            code, raw, _ = run_cli(["model", "validate", "publication", str(project), "--json"])
            self.assertEqual(code, 1)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "validation.output")

        with tempfile.TemporaryDirectory() as tmp:
            project = ResearchMigrationAdapterTest().project(Path(tmp))
            shutil.rmtree(project / "_paperops/evidence/sources", ignore_errors=True)
            candidate = ResearchAdapter().materialize(MigrationInput(project, "research", ()))
            self.assertIn("migration.missing", [item.code for item in candidate.findings])

    def test_unknown_private_issue_and_submitted_round_stay_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            helper = IssueMigrationAdapterTest()
            documents = helper.documents()
            documents[0]["unknown_field"] = "unmapped"
            documents[0]["raw_reviewer_text"] = "confidential local reviewer material"
            project = helper.project(Path(tmp), documents)
            candidate = IssueAdapter().materialize(MigrationInput(project, "issue", ()))
            codes = [item.code for item in candidate.findings]
            self.assertIn("migration.unknown_field", codes)
            self.assertIn("migration.confidential", codes)
            self.assertNotIn(b"confidential local reviewer material", b"".join(item.content for item in candidate.documents))

        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            ledger = project / "_paperops/workflow/submission-ledger.yml"
            ledger.write_text(yaml.safe_dump({"schema_version": 1, "migration_publication": publication()}, sort_keys=False))
            candidate = PublicationAdapter().materialize(MigrationInput(project, "publication", ()))
            self.assertEqual(candidate.findings, ())
            emitted = json.loads(candidate.documents[0].content)
            self.assertTrue(emitted["rounds"][0]["immutable"])

    def test_wheel_installed_cli_operates_on_copied_scaffold(self) -> None:
        uv = shutil.which("uv")
        if uv is None:
            self.skipTest("uv is required for the wheel distribution check")
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dist = base / "dist"
            subprocess.run(
                [uv, "build", "--wheel", "--out-dir", str(dist)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            wheel = next(dist.glob("*.whl"))
            venv = base / "venv"
            subprocess.run([sys.executable, "-m", "venv", "--system-site-packages", str(venv)], check=True)
            python = venv / "bin/python"
            subprocess.run([python, "-m", "pip", "install", "--no-deps", str(wheel)], check=True, capture_output=True, text=True)
            pops = venv / "bin/pops"
            project = base / "paper-wheel"
            subprocess.run([pops, "init", str(project)], check=True, capture_output=True, text=True)
            status = subprocess.run([pops, "model", "status", "all", str(project), "--json"], check=True, capture_output=True, text=True)
            self.assertEqual(set(json.loads(status.stdout)["models"]), {"research", "editorial", "results_hierarchy", "manuscript", "issue", "publication"})
            validation = subprocess.run([pops, "model", "validate", "publication", str(project), "--json"], check=False, capture_output=True, text=True)
            self.assertIn(validation.returncode, {0, 1})
            self.assertEqual(json.loads(validation.stdout)["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
