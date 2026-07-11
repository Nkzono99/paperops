from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template

from paperops.model_validation import run_model_validation


class ModelValidationRunnerTest(unittest.TestCase):
    def test_runs_project_checker_with_space_safe_argv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp, "paper project with spaces")
            result = run_model_validation(project, "research", strict=True)

        self.assertTrue(result.ok, result.findings)
        self.assertEqual(result.schema_version, 1)
        self.assertEqual(result.model, "research")
        self.assertEqual(result.phase, "all")

    def test_missing_checker_is_a_stable_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_model_validation(Path(tmp), "research")

        self.assertFalse(result.ok)
        self.assertEqual(result.findings[0].code, "validation.checker_missing")
        self.assertEqual(result.findings[0].pointer, "/scripts/check-paperops-models.py")

    def test_malformed_and_unknown_json_versions_are_stable_findings(self) -> None:
        payloads = (
            ("not json\n", "validation.output"),
            (json.dumps({"schema_version": 2, "ok": True}) + "\n", "validation.version"),
        )
        for payload, expected_code in payloads:
            with self.subTest(expected_code=expected_code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                checker = root / "scripts/check-paperops-models.py"
                checker.parent.mkdir(parents=True)
                checker.write_text(
                    "import sys\nsys.stdout.write(" + repr(payload) + ")\n",
                    encoding="utf-8",
                )
                result = run_model_validation(root, "research")

            self.assertFalse(result.ok)
            self.assertEqual(result.findings[0].code, expected_code)

    def test_oversized_checker_output_is_a_stable_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            checker = root / "scripts/check-paperops-models.py"
            checker.parent.mkdir(parents=True)
            checker.write_text(
                "import sys\nsys.stdout.write('x' * (1024 * 1024 + 1))\n",
                encoding="utf-8",
            )
            result = run_model_validation(root, "research")

        self.assertFalse(result.ok)
        self.assertEqual(result.findings[0].code, "validation.output")
        self.assertEqual(result.findings[0].pointer, "/")

    def test_error_findings_preserve_code_pointer_message_and_severity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            index = project / "_paperops/model/research/index.yml"
            document = json.loads(json.dumps({
                "model_name": "research",
                "schema_version": 1,
                "index_revision": 1,
                "records": [],
                "extensions": {},
                "metadata": {"updated_at": ""},
                "unknown": True,
            }))
            index.write_text(json.dumps(document), encoding="utf-8")
            result = run_model_validation(project, "research", phase="schema")

        finding = next(item for item in result.findings if item.code == "schema.additional")
        self.assertEqual(finding.pointer, "/unknown")
        self.assertTrue(finding.message)
        self.assertEqual(finding.severity, "error")


if __name__ == "__main__":
    unittest.main()
