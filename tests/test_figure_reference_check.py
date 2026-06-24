from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "scripts" / "check-figure-references.py"


class FigureReferenceCheckTest(unittest.TestCase):
    def test_strict_fails_when_main_text_figure_is_unreferenced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            section_dir = root / "manuscript" / "ja" / "sections"
            section_dir.mkdir(parents=True)
            (section_dir / "results.tex").write_text(
                textwrap.dedent(
                    r"""
                    \section{Results}
                    本文では図をまだ参照していない。
                    \begin{figure}
                    \includegraphics{../shared/figures/phase}
                    \caption{判定境界。}
                    \label{fig:phase-boundary}
                    \end{figure}
                    """
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--strict"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("fig:phase-boundary", result.stdout)
        self.assertIn("main-text figure", result.stdout)
        self.assertIn("\\ref{...}", result.stdout)

    def test_passes_when_label_is_referenced_outside_figure_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            section_dir = root / "manuscript" / "ja" / "sections"
            section_dir.mkdir(parents=True)
            (section_dir / "results.tex").write_text(
                textwrap.dedent(
                    r"""
                    \section{Results}
                    図~\ref{fig:phase-boundary} に判定境界を示す。
                    \begin{figure}
                    \includegraphics{../shared/figures/phase}
                    \caption{判定境界。}
                    \label{fig:phase-boundary}
                    \end{figure}
                    """
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--strict"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
