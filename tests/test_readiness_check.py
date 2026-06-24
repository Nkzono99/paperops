from __future__ import annotations

import tempfile
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "readiness-check.py"
MIRROR_FRESHNESS_SCRIPT = ROOT / "template" / "scripts" / "mirror-freshness-check.py"


class ReadinessCheckTest(unittest.TestCase):
    def test_requires_decision_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            (target / "notes" / "decision-log.md").unlink()

            result = run_python_script(SCRIPT, "--root", target, "--allow-placeholders")

        self.assertEqual(result.returncode, 1)
        self.assertIn("`notes/decision-log.md` が見つかりません", result.stdout)

    def test_warns_when_public_bibliography_includes_mypapers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            main_tex = target / "manuscript" / "ja" / "main.tex"
            main_tex.write_text(
                main_tex.read_text(encoding="utf-8").replace(
                    r"\bibliography{references}",
                    r"\bibliography{references,mypapers}",
                ),
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--allow-placeholders")

        self.assertEqual(result.returncode, 0)
        self.assertIn("bibliography に `mypapers` が含まれています", result.stdout)

    def test_mirror_freshness_strict_fails_on_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            ledger = target / "manuscript" / "mirror" / "block-ledger.yml"
            ledger.unlink()

            non_strict = run_python_script(
                MIRROR_FRESHNESS_SCRIPT,
                "--root",
                target / "manuscript",
            )
            strict = run_python_script(
                MIRROR_FRESHNESS_SCRIPT,
                "--root",
                target / "manuscript",
                "--strict",
            )

        self.assertEqual(non_strict.returncode, 0)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("--update", strict.stdout)


if __name__ == "__main__":
    unittest.main()
