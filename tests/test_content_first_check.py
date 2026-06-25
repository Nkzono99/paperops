from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-content-first.py"


class ContentFirstCheckTest(unittest.TestCase):
    def test_strict_blocks_submission_only_work_before_structure_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)

            result = run_python_script(
                SCRIPT,
                "--root",
                root,
                "--phase",
                "progress",
                "--intent",
                "submission",
                "--changed-file",
                "manuscript/publication-metadata.toml",
                "--changed-file",
                "submission/cover-letter.md",
                "--strict",
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("content-first", result.stdout)
            self.assertIn("Submission hygiene", result.stdout)
            self.assertIn("STRUCTURE_ACCEPTED", result.stdout)
            self.assertIn("manuscript content blocker", result.stdout)

    def test_strict_blocks_harness_only_work_before_structure_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)

            result = run_python_script(
                SCRIPT,
                "--root",
                root,
                "--phase",
                "progress",
                "--intent",
                "harness",
                "--changed-file",
                "scripts/readiness-check.py",
                "--changed-file",
                "Makefile",
                "--strict",
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("downstream harness", result.stdout)
            self.assertIn("feedback-paper-harness", result.stdout)

    def test_allows_content_work_when_structure_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)

            result = run_python_script(
                SCRIPT,
                "--root",
                root,
                "--phase",
                "progress",
                "--intent",
                "content",
                "--changed-file",
                "notes/views/storyline.md",
                "--changed-file",
                "manuscript/ja/sections/30_results.tex",
                "--strict",
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("content-first", result.stdout)
            self.assertIn("content intent is aligned", result.stdout)

    def test_strict_blocks_subagent_report_only_work_as_content_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)

            result = run_python_script(
                SCRIPT,
                "--root",
                root,
                "--phase",
                "progress",
                "--intent",
                "content",
                "--changed-file",
                "review/rounds/subagent-report-story-001.md",
                "--strict",
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("content-first", result.stdout)
            self.assertIn("subagent reports are not manuscript edits", result.stdout)
            self.assertIn("manuscript content blocker", result.stdout)

    def test_finish_phase_requires_structure_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)

            result = run_python_script(
                SCRIPT,
                "--root",
                root,
                "--phase",
                "finish",
                "--intent",
                "content",
                "--strict",
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("finish-manuscript", result.stdout)
            self.assertIn("STRUCTURE_ACCEPTED", result.stdout)

    def test_finish_phase_requires_story_and_section_guards_even_if_structure_guard_is_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            state_path = root / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["guards"]["STRUCTURE_ACCEPTED"] = {
                key: True for key in state["guards"]["STRUCTURE_ACCEPTED"]
            }
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_python_script(
                SCRIPT,
                "--root",
                root,
                "--phase",
                "finish",
                "--intent",
                "content",
                "--strict",
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("STORY_LOCKED", result.stdout)
            self.assertIn("SECTION_PLANNED", result.stdout)

    def test_makefiles_and_template_define_content_first_gate(self) -> None:
        expected_paths = [
            ROOT / "template" / "workflow" / "focus-policy.yml",
            SCRIPT,
        ]
        for path in expected_paths:
            with self.subTest(path=path):
                self.assertTrue(path.exists(), f"{path} is missing")

        template_makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        state = json.loads((ROOT / "template" / "workflow" / "current-state.yml").read_text(encoding="utf-8"))

        for required in [
            "content-first-check",
            "finish-manuscript-check",
            "check-content-first.py",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, template_makefile)
                self.assertIn(required, root_makefile)

        self.assertIn("CONTENT_FIRST", state["guards"])

    def test_feedback_and_review_round_templates_preserve_high_level_routes(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                ROOT / "template" / "review" / "feedback" / "feedback-card-template.md",
                ROOT / "template" / "review" / "rounds" / "review-round-template.md",
                ROOT / "template" / "notes" / "views" / "peer-review.md",
                ROOT / "template" / ".agents" / "skills" / "integrate-writing-feedback" / "SKILL.md",
            ]
        )

        for required in [
            "storyline_change",
            "section_depth_blocker",
            "results_hierarchy_gap",
            "discussion_function_gap",
            "submission_hygiene_only",
            "Editorial architecture audit",
            "highest-priority route",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)

    def test_downstream_instructions_mention_content_first_checkpoint(self) -> None:
        combined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in [
                ROOT / "template" / "AGENTS.md",
                ROOT / "template" / "CLAUDE.md",
                ROOT / "template" / "README.md",
            ]
        )

        for required in [
            "content-first-check",
            "finish-manuscript-check",
            "design-paper-storyline",
            "Submission hygiene",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, combined)


if __name__ == "__main__":
    unittest.main()
