from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-storyline.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


class StorylineCheckTest(unittest.TestCase):
    def test_strict_fails_when_storyline_required_functions_are_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Story spine

                - reader_promise: 未記入
                - central_claim: TBD

                ## Section depth map

                | function | manuscript block | status |
                | --- | --- | --- |
                | results_hierarchy | 未記入 | draft |
                | discussion_functions | 未記入 | draft |
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("storyline", result.stdout)
        self.assertIn("reader_promise", result.stdout)
        self.assertIn("results_hierarchy", result.stdout)

    def test_strict_passes_when_storyline_functions_map_to_existing_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_text(
                root / "notes" / "views" / "storyline.md",
                """
                # Storyline

                ## Story spine

                - reader_promise: Readers learn why the local work budget changes the detachment question.
                - central_claim: Local retained charge can supply static detachment work under the stated boundary.
                - evidence_ladder: baseline anchor -> relaxation boundary -> sensitivity scope.
                - scope_boundary: fixed-charge estimator, not coupled flight.

                ## Section depth map

                | function | manuscript block | status |
                | --- | --- | --- |
                | results_hierarchy | results.baseline.01 | locked |
                | mechanism_warrant | discussion.mechanism.01 | locked |
                | prior_work_delta | discussion.prior-work.01 | locked |
                | decisive_next_test | discussion.next-test.01 | locked |
                """,
            )
            write_text(
                root / "manuscript" / "en" / "sections" / "30_results.tex",
                """
                % block: results.baseline.01
                The baseline result anchors the comparison.
                """,
            )
            write_text(
                root / "manuscript" / "en" / "sections" / "40_discussion.tex",
                """
                % block: discussion.mechanism.01
                The mechanism follows from local charge retention.

                % block: discussion.prior-work.01
                This changes the prior surface-field comparison.

                % block: discussion.next-test.01
                The decisive next test is coupled dynamic lifting.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("storyline", result.stdout)


if __name__ == "__main__":
    unittest.main()
