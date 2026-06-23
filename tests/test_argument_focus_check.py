from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "scripts" / "check-argument-focus.py"


class ArgumentFocusCheckTest(unittest.TestCase):
    def test_strict_fails_on_local_condition_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            shutil.copytree(ROOT / "template", target)
            section = target / "manuscript" / "ja" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\n12 条件中 2 条件で正の work が残ったが、これは直接証明ではない。\n"
                + "8 条件中 0 条件であり、screening に限定する。\n"
                + "この結果は bracket であり、robust ranking は主張しない。\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(target),
                    "--strict",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("ローカル条件数の列挙", result.stdout)
        self.assertIn("防御的・限定的な表現", result.stdout)
        self.assertIn("/contextualize-conditions", result.stdout)

    def test_missing_condition_context_map_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            shutil.copytree(ROOT / "template", target)
            (target / "notes" / "condition-context-map.md").unlink()

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
        self.assertIn("`notes/condition-context-map.md` が見つかりません", result.stdout)


if __name__ == "__main__":
    unittest.main()
