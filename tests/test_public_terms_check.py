from __future__ import annotations

import tempfile
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-public-terms.py"


class PublicTermsCheckTest(unittest.TestCase):
    def test_default_guard_rejects_internal_analysis_labels_in_public_manuscript(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "en" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nThe target-snapshot sample and saved batch define the exposure diagnostic.\n"
                + "This table is not used for ranking and is not evidence.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("target-snapshot sample", result.stdout)
        self.assertIn("exposure diagnostic", result.stdout)
        self.assertIn("not evidence", result.stdout)
        self.assertIn("replacement", result.stdout)


if __name__ == "__main__":
    unittest.main()
