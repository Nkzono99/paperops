from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_cli, run_python_script


class WorkflowKernelTest(unittest.TestCase):
    def test_template_defines_workflow_kernel_and_make_target(self) -> None:
        workflow_root = ROOT / "template" / "workflow"
        for name in ["README.md", "machine.yml", "current-state.yml", "decisions.yml", "round-summary.yml"]:
            with self.subTest(name=name):
                self.assertTrue((workflow_root / name).is_file())

        machine = (workflow_root / "machine.yml").read_text(encoding="utf-8")
        state = (workflow_root / "current-state.yml").read_text(encoding="utf-8")
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        for required in [
            "EVIDENCE_READY",
            "STORY_LOCKED",
            "SECTION_PLANNED",
            "UNDER_REVIEW",
            "evidence_loop",
            "story_loop",
            "section_loop",
            "prose_loop",
            "submission_loop",
            "max_autonomous_rounds_per_issue",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, machine)

        self.assertIn('"state": "SCOPED"', state)
        self.assertIn('"depends_on"', state)
        self.assertIn('"results.core_relaxation"', state)
        self.assertIn("workflow-check:", makefile)
        self.assertIn("check-workflow-state.py --root .", makefile)

    def test_workflow_check_accepts_template_state(self) -> None:
        result = run_python_script(
            ROOT / "template" / "scripts" / "check-workflow-state.py",
            "--root",
            ROOT / "template",
            encoding="utf-8",
            errors="replace",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("workflow-check", result.stdout)
        self.assertIn("workflow state is valid", result.stdout)

    def test_pops_workflow_status_next_and_advance_with_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            code, out, err = run_cli(["workflow", "status", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("workflow state: SCOPED", out)

            code, out, err = run_cli(["workflow", "next", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("next overall state: EVIDENCE_READY", out)
            self.assertIn("guard blocked", out)

            state_path = target / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["guards"]["EVIDENCE_READY"] = {
                key: True for key in state["guards"]["EVIDENCE_READY"]
            }
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(["workflow", "advance", "evidence-ready", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("advanced: SCOPED -> EVIDENCE_READY", out)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["overall"]["state"],
                "EVIDENCE_READY",
            )

    def test_pops_workflow_invalidate_marks_dependent_sections_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            code, out, err = run_cli(["workflow", "invalidate", "CLM-0003", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("stale: results.core_relaxation", out)
            self.assertIn("stale: discussion.mechanism", out)

            state = json.loads((target / "workflow" / "current-state.yml").read_text(encoding="utf-8"))
            self.assertEqual(state["sections"]["results.core_relaxation"]["state"], "STALE")
            self.assertEqual(state["sections"]["results.core_relaxation"]["route"], "story_loop")
            self.assertEqual(state["sections"]["discussion.mechanism"]["state"], "STALE")

    def test_pops_workflow_route_review_can_apply_issue_class_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            code, out, err = run_cli(
                ["workflow", "route-review", "--issue-class", "section-loop", "--apply", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("issue class: section_loop", out)
            self.assertIn("route to: SECTION_PLANNED", out)
            state = json.loads((target / "workflow" / "current-state.yml").read_text(encoding="utf-8"))
            self.assertEqual(state["overall"]["state"], "SECTION_PLANNED")
            self.assertEqual(state["loop_counters"]["section_loop"], 1)

    def test_workflow_kernel_is_documented_and_connected_to_finish_manuscript(self) -> None:
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        cli_docs = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
        skill = (
            ROOT / "template" / ".agents" / "skills" / "finish-manuscript" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for required in [
            "workflow/",
            "階層型状態機械",
            "stale",
            "pops workflow",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, architecture)

        self.assertIn("pops workflow status", cli_docs)
        self.assertIn("pops workflow invalidate", cli_docs)
        self.assertIn("Issue Router", skill)
        self.assertIn("route-review", skill)
        self.assertIn("UNDER_REVIEW", skill)


if __name__ == "__main__":
    unittest.main()
