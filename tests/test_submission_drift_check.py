from __future__ import annotations

import tempfile
import unittest

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-submission-drift.py"


class SubmissionDriftCheckTest(unittest.TestCase):
    def test_non_strict_warns_when_submission_blocks_drift_from_manuscript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            submission = project / "submission" / "demo"
            submission.mkdir(parents=True, exist_ok=True)
            (submission / "main.tex").write_text(
                "\n".join(
                    [
                        r"\section{Results}",
                        "% block: extra.submission.only",
                        "Submission-only text.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("manuscript/en の block を含んでいません", result.stdout)
        self.assertIn("manuscript/en にない block", result.stdout)

    def test_strict_fails_when_submission_blocks_drift_from_manuscript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            submission = project / "submission" / "demo"
            submission.mkdir(parents=True, exist_ok=True)
            (submission / "main.tex").write_text(
                "\n".join(
                    [
                        r"\section{Results}",
                        "% block: extra.submission.only",
                        "Submission-only text.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Errors", result.stdout)
        self.assertIn("manuscript/en の block を含んでいません", result.stdout)
        self.assertIn("manuscript/en にない block", result.stdout)

    def test_strict_allows_missing_submission_candidate_to_remain_non_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)

            result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("スキップします", result.stdout)

    def test_makefile_uses_strict_submission_drift_in_submission_profiles(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("check-submission-drift.py --root . --strict", makefile)


if __name__ == "__main__":
    unittest.main()
