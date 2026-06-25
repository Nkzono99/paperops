from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-quantity-integrity.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


class QuantityIntegrityCheckTest(unittest.TestCase):
    def test_strict_fails_on_unregistered_public_count_fraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "manuscript" / "en" / "sections" / "00_abstract.tex",
                r"""
                We found release-compatible behavior in 128 of 140 selected candidates.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("未登録の数量表現", result.stdout)
        self.assertIn("128 of 140", result.stdout)

    def test_passes_when_public_count_fraction_is_declared_by_result_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "evidence" / "results" / "RES-0001.md",
                """
                ---
                id: RES-0001
                type: result
                status: accepted
                quantity_contracts:
                  - id: QTY-0001
                    value: 128
                    denominator: 140
                    unit_of_analysis: selected candidate
                    estimand: endpoint positive work
                    aggregation: none
                    independence: temporally correlated snapshots
                    source_artifact: data/processed/work-summary.csv
                    manuscript_blocks:
                      - abstract
                      - results
                ---

                # Result
                """,
            )
            write_text(
                root / "manuscript" / "en" / "sections" / "00_abstract.tex",
                r"""
                We found release-compatible behavior in 128 of 140 selected candidates.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("quantity integrity", result.stdout)


if __name__ == "__main__":
    unittest.main()
