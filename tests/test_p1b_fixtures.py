from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script
from tests.p1b_fixture_support import materialize_p1b_fixture, reindex_model

import sys

sys.path.insert(0, str(ROOT / "template/scripts"))

from paperops_schema import load_document  # noqa: E402


FIXTURE_ROOT = ROOT / "tests/fixtures/editorial"
INVALID_ROOT = ROOT / "tests/fixtures/models/invalid"
CATEGORIES = ("mechanism-led", "boundary-led", "negative-result-led")
CHECKER = ROOT / "template/scripts/check-paperops-models.py"
RECORD_FAMILIES = {
    "research": {"claim", "result", "figure", "source", "scientific_gate"},
    "manuscript": {"section", "block"},
    "issue": {"feedback", "analysis_request", "writing_request", "response", "review_round"},
}


def finding_codes(output: str) -> set[str]:
    return set(re.findall(r"\[([a-z_]+\.[a-z_]+)\]", output))


def set_pointer(document: object, pointer: str, value: object) -> None:
    current = document
    parts = pointer.removeprefix("/").split("/")
    for part in parts[:-1]:
        current = current[int(part)] if isinstance(current, list) else current[part]
    final = parts[-1]
    if isinstance(current, list):
        current[int(final)] = value
    else:
        current[final] = value


class P1BValidFixtureTest(unittest.TestCase):
    def test_every_story_materializes_all_six_models_and_record_families(self) -> None:
        for category in CATEGORIES:
            with self.subTest(category=category), tempfile.TemporaryDirectory() as tmp:
                project = copy_template(tmp)
                materialize_p1b_fixture(project, FIXTURE_ROOT / category)
                for model_name, families in RECORD_FAMILIES.items():
                    index = load_document(
                        project / "_paperops/model" / (
                            "issues" if model_name == "issue" else model_name
                        ) / "index.yml"
                    )
                    self.assertEqual(
                        {row["record_type"] for row in index["records"]}, families
                    )
                self.assertTrue(
                    (project / "_paperops/model/publication/publication-model.yml").is_file()
                )

    def test_every_story_passes_strict_all_with_stable_hashes(self) -> None:
        for category in CATEGORIES:
            with self.subTest(category=category), tempfile.TemporaryDirectory() as tmp:
                project = copy_template(tmp)
                manifest = load_document(FIXTURE_ROOT / category / "fixture.yml")
                materialize_p1b_fixture(project, FIXTURE_ROOT / category)
                result = run_python_script(
                    CHECKER, "--root", project, "--strict", "--phase", "all"
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                research_hash = run_python_script(
                    CHECKER, "--root", project, "--model", "research", "--print-hash"
                )
                dependency_hash = run_python_script(
                    CHECKER, "--root", project, "--print-dependency-hash", "BLK-0001"
                )
                self.assertEqual(research_hash.returncode, 0, research_hash.stdout)
                self.assertEqual(dependency_hash.returncode, 0, dependency_hash.stdout)
                self.assertEqual(research_hash.stdout.strip(), manifest["expected_research_hash"])
                self.assertEqual(
                    dependency_hash.stdout.strip(), manifest["expected_dependency_hash"]
                )

    def test_materialized_documents_are_synthetic_and_public_safe(self) -> None:
        forbidden = re.compile(
            r"(?:/home/|/Users/|/LARGE|BEGIN .* PRIVATE KEY|\bsk-[A-Za-z0-9]|raw reviewer)",
            re.IGNORECASE,
        )
        for category in CATEGORIES:
            with self.subTest(category=category), tempfile.TemporaryDirectory() as tmp:
                project = copy_template(tmp)
                materialize_p1b_fixture(project, FIXTURE_ROOT / category)
                for path in (project / "_paperops/model").rglob("*"):
                    if path.is_file():
                        self.assertIsNone(forbidden.search(path.read_text(encoding="utf-8")))


class P1BInvalidFixtureTest(unittest.TestCase):
    def test_each_invalid_case_is_one_documented_mutation_with_exact_codes(self) -> None:
        cases = sorted(INVALID_ROOT.glob("*.yml"))
        self.assertGreaterEqual(len(cases), 4)
        for case_path in cases:
            with self.subTest(case=case_path.name), tempfile.TemporaryDirectory() as tmp:
                case = load_document(case_path)
                self.assertEqual(case["fixture_version"], 1)
                self.assertTrue(case["single_mutation"])
                project = copy_template(tmp)
                materialize_p1b_fixture(project, FIXTURE_ROOT / "mechanism-led")
                document_path = project / case["document"]
                document = load_document(document_path)
                set_pointer(document, case["pointer"], case["value"])
                document_path.write_text(
                    json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                if case.get("reindex_model"):
                    reindex_model(project, case["reindex_model"])
                result = run_python_script(
                    CHECKER,
                    "--root", project,
                    "--model", case.get("model", "all"),
                    "--phase", case["phase"],
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(
                    finding_codes(result.stdout + result.stderr),
                    set(case["expected_codes"]),
                )


if __name__ == "__main__":
    unittest.main()
