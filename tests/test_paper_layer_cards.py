from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "scripts" / "check-paper-layer-cards.py"


class PaperLayerCardsTest(unittest.TestCase):
    def test_template_layer_cards_are_valid(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(ROOT / "template"),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("paper layer cards", result.stdout)
        self.assertIn("カード層と互換ビューの外形に問題は見つかりませんでした", result.stdout)

    def test_missing_feedback_template_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            shutil.copytree(ROOT / "template", target)
            feedback_template = target / "review" / "feedback" / "feedback-card-template.md"
            if feedback_template.exists():
                feedback_template.unlink()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(target),
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("`review/feedback/feedback-card-template.md` が見つかりません", result.stdout)


if __name__ == "__main__":
    unittest.main()
