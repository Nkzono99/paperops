from __future__ import annotations

import tempfile
import textwrap
import unittest
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "scripts" / "check-figure-obligations.py"


def write_card(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def run_python_script(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *[str(arg) for arg in args]],
        check=False,
        capture_output=True,
        text=True,
    )


class FigureObligationCheckTest(unittest.TestCase):
    def test_fails_when_declared_visual_obligation_has_no_figure_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_card(
                root / "claims" / "claims" / "CLM-0001.md",
                """
                ---
                id: CLM-0001
                type: claim
                status: supported
                visual_obligations:
                  - id: VO-STATE-0001
                    role: model_or_state_visualization
                    required: true
                ---

                # Claim
                """,
            )

            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("VO-STATE-0001", result.stdout)
        self.assertIn("figure obligation", result.stdout)

    def test_passes_when_visual_obligation_is_satisfied_by_figure_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_card(
                root / "claims" / "claims" / "CLM-0001.md",
                """
                ---
                id: CLM-0001
                type: claim
                status: supported
                visual_obligations:
                  - id: VO-CRITERION-0001
                    role: estimator_or_decision_criterion
                    required: true
                ---

                # Claim
                """,
            )
            write_card(
                root / "evidence" / "figures" / "FIG-0001.md",
                """
                ---
                id: FIG-0001
                type: figure
                status: draft
                figure_ref: "fig:criterion"
                current_manuscript_role: main
                satisfies_visual_obligations:
                  - VO-CRITERION-0001
                ---

                # Figure
                """,
            )

            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("visual obligation", result.stdout)

    def test_strict_fails_supported_claim_without_obligation_or_no_figure_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_card(
                root / "claims" / "claims" / "CLM-0001.md",
                """
                ---
                id: CLM-0001
                type: claim
                status: supported
                gate_status: ready-to-write
                visual_obligations: []
                ---

                # Claim
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("CLM-0001", result.stdout)
        self.assertIn("no_figure_reason", result.stdout)


if __name__ == "__main__":
    unittest.main()
