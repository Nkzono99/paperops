from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, make_var_tokens, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-block-flow-review.py"


def set_section_state(root: Path, section: str, state: str) -> None:
    state_path = root / "_paperops" / "workflow" / "current-state.yml"
    current = json.loads(state_path.read_text(encoding="utf-8"))
    current["sections"][section]["state"] = state
    state_path.write_text(json.dumps(current, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_block_flow_review(root: Path, section: str, table_rows: str) -> Path:
    reviews = root / "_paperops" / "review" / "block-flow"
    reviews.mkdir(parents=True, exist_ok=True)
    path = reviews / f"{section}-review.md"
    header = f"""\
---
id: BFR-9001
type: block_flow_review
section: {section}
status: reviewed
---

# {section} block-flow review

| block_id | reader_question | author_move | why_here | next_block_expectation | operation |
| --- | --- | --- | --- | --- | --- |
"""
    path.write_text(header + table_rows + "\n", encoding="utf-8")
    return path


class BlockFlowReviewCheckTest(unittest.TestCase):
    def test_strict_requires_review_artifact_for_audited_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            set_section_state(root, "results", "AUDITED")

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("results", result.stdout)
        self.assertIn("_paperops/review/block-flow", result.stdout)

    def test_strict_flags_placeholder_block_operation_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            set_section_state(root, "results", "AUDITED")
            write_block_flow_review(
                root,
                "results",
                "| results.traceability.01 | 未記入 | keep | 未記入 | 未記入 | keep |\n"
                "| results.refs.01 | 未記入 | keep | 未記入 | 未記入 | keep |\n"
                "| results.mirror.01 | 未記入 | keep | 未記入 | 未記入 | keep |",
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("reader_question", result.stdout)
        self.assertIn("why_here", result.stdout)
        self.assertIn("next_block_expectation", result.stdout)

    def test_passes_when_all_audited_section_blocks_have_review_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            set_section_state(root, "results", "AUDITED")
            write_block_flow_review(
                root,
                "results",
                "| results.traceability.01 | What state must persist across sessions? | assert traceability as the first result | it frames why workflow state matters before refs | asks how references reuse the same state | keep |\n"
                "| results.refs.01 | How are references reused? | connect refs summaries to reusable citation work | it extends state persistence to knowledge assets | asks how bilingual drift is controlled | keep |\n"
                "| results.mirror.01 | How is bilingual drift detected? | close with the mechanical mirror check | it turns the previous claims into a verifiable check | section can hand off to discussion tradeoffs | keep |",
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("block-flow review に問題は見つかりませんでした", result.stdout)

    def test_makefiles_wire_block_flow_check_to_audit_and_finish(self) -> None:
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        template_makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        for makefile in [root_makefile, template_makefile]:
            with self.subTest(makefile=makefile[:20]):
                self.assertIn("block-flow-review-check:", makefile)
                self.assertIn("check-block-flow-review.py --root", makefile)
                self.assertIn("--strict", makefile)

        self.assertIn("block-flow-review-check", make_var_tokens(root_makefile, "SMOKE_CHECKS"))
        self.assertIn("block-flow-review-check", make_var_tokens(root_makefile, "FINISH_MANUSCRIPT_CHECKS"))
        self.assertIn("block-flow-review-check", make_var_tokens(template_makefile, "AUDIT_CHECKS"))
        self.assertIn("block-flow-review-check", make_var_tokens(template_makefile, "FINISH_MANUSCRIPT_CHECKS"))


if __name__ == "__main__":
    unittest.main()
