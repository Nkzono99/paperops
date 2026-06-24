from __future__ import annotations

import tempfile
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-paper-layer-cards.py"


class PaperLayerCardsTest(unittest.TestCase):
    def test_template_layer_cards_are_valid(self) -> None:
        result = run_python_script(SCRIPT, "--root", ROOT / "template")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("paper layer cards", result.stdout)
        self.assertIn("カード層と互換ビューの外形に問題は見つかりませんでした", result.stdout)

    def test_missing_feedback_template_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            feedback_template = target / "review" / "feedback" / "feedback-card-template.md"
            if feedback_template.exists():
                feedback_template.unlink()

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`review/feedback/feedback-card-template.md` が見つかりません", result.stdout)


if __name__ == "__main__":
    unittest.main()
