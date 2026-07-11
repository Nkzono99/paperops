from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_python_script


sys.path.insert(0, str(ROOT / "template" / "scripts"))

from paperops_schema import load_document, validate_schema  # noqa: E402


FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "editorial"
CATEGORIES = ("mechanism-led", "boundary-led", "negative-result-led")
CHECKER = ROOT / "template" / "scripts" / "check-paperops-models.py"
INVALID_CASES = {
    "duplicate-key.yml": "document.duplicate_key",
    "duplicate-id.yml": "reference.duplicate",
    "invalid-stance.yml": "schema.enum",
    "dangling-story.yml": "reference.dangling",
    "dangling-result.yml": "reference.dangling",
    "move-cycle.yml": "reference.cycle",
    "move-order-gap.yml": "reference.order",
    "empty-role-reason.yml": "semantic.claim_role",
    "single-story-no-reason.yml": "semantic.story_count",
    "absolute-results-path.yml": "reference.path",
    "traversal-results-path.yml": "reference.path",
    "unknown-field.yml": "schema.additional",
    "non-finite.yml": "document.non_finite",
    "unsupported-schema-keyword.yml": "schema.unsupported_keyword",
}


def run_checker(case_dir, *extra):
    return run_python_script(
        CHECKER,
        "--root",
        ROOT / "template",
        "--model",
        "editorial",
        "--document",
        case_dir / "editorial-model.yml",
        "--results-document",
        case_dir / "results-hierarchy.yml",
        *extra,
    )


def unsupported_schema_override_code(case_path):
    """Run an invalid schema fixture through the validator kernel, not the CLI."""
    with tempfile.TemporaryDirectory() as tmp:
        override_path = Path(tmp) / "schema-override.yml"
        override_path.write_text(case_path.read_text(encoding="utf-8"), encoding="utf-8")
        try:
            validate_schema({}, load_document(override_path))
        except Exception as error:
            return str(error).partition(":")[0]
    return ""


class EditorialFixtureContractTest(unittest.TestCase):
    def test_valid_fixture_manifests_and_documents_satisfy_contract(self) -> None:
        for category in CATEGORIES:
            with self.subTest(category=category):
                case_dir = FIXTURE_ROOT / category
                self.assertTrue(case_dir.is_dir(), f"missing fixture directory: {case_dir}")

                manifest = load_document(case_dir / "fixture.yml")
                self.assertEqual(manifest["fixture_version"], 1)
                self.assertEqual(manifest["category"], category)
                self.assertEqual(manifest["editorial_document"], "editorial-model.yml")
                self.assertEqual(manifest["results_document"], "results-hierarchy.yml")
                self.assertRegex(manifest["expected_hash"], r"^sha256:[0-9a-f]{64}$")
                self.assertIsInstance(manifest["expected_diagnostics"], list)
                self.assertIs(manifest["synthetic"], True)

                editorial = load_document(case_dir / manifest["editorial_document"])
                self.assertGreaterEqual(len(editorial["story_candidates"]), 2)
                selected = [
                    story
                    for story in editorial["story_candidates"]
                    if story["status"] == "selected"
                ]
                rejected = [
                    story
                    for story in editorial["story_candidates"]
                    if story["status"] == "rejected"
                ]
                self.assertTrue(all(story["selection_reason"].strip() for story in selected))
                self.assertTrue(all(story["rejection_reason"].strip() for story in rejected))
                self.assertEqual(
                    set(editorial["claim_roles"]),
                    {"foreground", "supporting", "supplement", "cut"},
                )
                self.assertEqual(len(editorial["argument_moves"]), 3)
                self.assertGreaterEqual(len(editorial["visual_obligations"]), 1)
                self.assertEqual(len(editorial["results_hierarchy"]["item_ids"]), 3)

    def test_valid_fixtures_pass_strict_with_stable_hash_and_diagnostics(self) -> None:
        for category in CATEGORIES:
            with self.subTest(category=category):
                case_dir = FIXTURE_ROOT / category
                manifest = load_document(case_dir / "fixture.yml")

                strict = run_checker(case_dir, "--strict")
                self.assertEqual(strict.returncode, 0, strict.stdout + strict.stderr)
                diagnostic_codes = sorted(
                    set(re.findall(r"\[([a-z_]+\.[a-z_]+)\]", strict.stdout))
                )
                self.assertEqual(diagnostic_codes, manifest["expected_diagnostics"])

                hashed = run_checker(case_dir, "--print-hash")
                self.assertEqual(hashed.returncode, 0, hashed.stdout + hashed.stderr)
                self.assertEqual(hashed.stdout.strip(), manifest["expected_hash"])


class EditorialInvalidCorpusTest(unittest.TestCase):
    def test_invalid_corpus_reports_expected_finding_codes(self) -> None:
        invalid_dir = FIXTURE_ROOT / "invalid"
        results_path = FIXTURE_ROOT / "mechanism-led" / "results-hierarchy.yml"
        for filename, expected_code in INVALID_CASES.items():
            with self.subTest(filename=filename):
                case_path = invalid_dir / filename
                if filename == "unsupported-schema-keyword.yml":
                    self.assertEqual(
                        unsupported_schema_override_code(case_path), expected_code
                    )
                    continue
                result = run_python_script(
                    CHECKER,
                    "--root",
                    ROOT / "template",
                    "--model",
                    "editorial",
                    "--document",
                    case_path,
                    "--results-document",
                    results_path,
                    "--strict",
                )
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(f"[{expected_code}]", result.stdout + result.stderr)


class EditorialFixturePrivacyTest(unittest.TestCase):
    def test_fixture_text_contains_no_private_paths_credentials_or_raw_review(self) -> None:
        forbidden = (
            re.compile(r"/home/"),
            re.compile(r"/Users/"),
            re.compile(r"/LARGE"),
            re.compile(r"BEGIN .* PRIVATE KEY"),
            re.compile(r"sk-"),
            re.compile(r"raw reviewer", re.IGNORECASE),
        )
        fixture_files = sorted(path for path in FIXTURE_ROOT.rglob("*") if path.is_file())
        self.assertTrue(fixture_files)
        for path in fixture_files:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                with self.subTest(path=path, pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text))

        for category in CATEGORIES:
            manifest = load_document(FIXTURE_ROOT / category / "fixture.yml")
            self.assertIs(manifest["synthetic"], True)


if __name__ == "__main__":
    unittest.main()
