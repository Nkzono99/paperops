from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "scripts" / "readiness-check.py"


class ReadinessCheckTest(unittest.TestCase):
    def test_requires_decision_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            shutil.copytree(ROOT / "template", target)
            (target / "notes" / "decision-log.md").unlink()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(target),
                    "--allow-placeholders",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("`notes/decision-log.md` が見つかりません", result.stdout)


if __name__ == "__main__":
    unittest.main()
