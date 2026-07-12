from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import ROOT, copy_template, run_cli, run_python_script


class WorkflowKernelTest(unittest.TestCase):
    def test_template_defines_workflow_kernel_and_make_target(self) -> None:
        workflow_root = ROOT / "template" / "_paperops" / "workflow"
        defaults_root = ROOT / "template" / "_paperops" / "defaults" / "workflow"
        for name in ["README.md", "current-state.yml", "decisions.yml", "round-summary.yml"]:
            with self.subTest(name=name):
                self.assertTrue((workflow_root / name).is_file())
        for name in ["README.md", "machine.yml", "focus-policy.yml", "subagent-roster.yml"]:
            with self.subTest(name=name):
                self.assertTrue((defaults_root / name).is_file())

        machine = (defaults_root / "machine.yml").read_text(encoding="utf-8")
        state = (workflow_root / "current-state.yml").read_text(encoding="utf-8")
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        for required in [
            "STORY_SEEDED",
            "EVIDENCE_PLANNED",
            "EVIDENCE_READY",
            "STORY_RECONCILED",
            "ARCHITECTURE_LOCKED",
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
        self.assertIn("workflow-check:", makefile)
        self.assertIn("check-workflow-state.py --root .", makefile)

    def test_template_current_state_is_topic_neutral_starter(self) -> None:
        state_path = ROOT / "template" / "_paperops" / "workflow" / "current-state.yml"
        state = json.loads(state_path.read_text(encoding="utf-8"))

        self.assertEqual(
            set(state["sections"]),
            {"abstract", "introduction", "methods", "results", "discussion", "conclusion"},
        )
        for section_name, section in state["sections"].items():
            with self.subTest(section=section_name):
                self.assertEqual(section["state"], "UNPLANNED")
                for refs in section.get("depends_on", {}).values():
                    self.assertEqual([], refs)

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

    def test_workflow_loaders_accept_non_json_yaml_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target), "--authority", "legacy"])
            self.assertEqual(code, 0, err)

            state_path = target / "_paperops" / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            yaml_text = yaml.safe_dump(state, allow_unicode=True, sort_keys=False)
            self.assertNotIn('"overall"', yaml_text)
            state_path.write_text(yaml_text, encoding="utf-8")

            code, out, err = run_cli(["workflow", "status", str(target)])
            check = run_python_script(
                target / "scripts" / "check-workflow-state.py",
                "--root",
                target,
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(code, 0, err)
        self.assertIn("workflow state: SCOPED", out)
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
        self.assertIn("workflow state is valid", check.stdout)

    def test_workflow_check_validates_subagent_roster_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            roster_path = root / "_paperops" / "defaults" / "workflow" / "subagent-roster.yml"
            roster = json.loads(roster_path.read_text(encoding="utf-8"))
            del roster["roles"][0]["outputs"]
            roster_path.write_text(
                json.dumps(roster, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_python_script(
                root / "scripts" / "check-workflow-state.py",
                "--root",
                root,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("workflow-check", result.stdout)
            self.assertIn("subagent-roster.yml", result.stdout)
            self.assertIn("role `story_architect` outputs is missing", result.stdout)

    def test_workflow_check_rejects_public_reader_private_manuscript_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            roster_path = root / "_paperops" / "defaults" / "workflow" / "subagent-roster.yml"
            roster = json.loads(roster_path.read_text(encoding="utf-8"))
            public_reader = next(role for role in roster["roles"] if role["id"] == "public_reader")
            public_reader["allowed_inputs"].append("manuscript/ja/")
            roster_path.write_text(
                json.dumps(roster, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_python_script(
                root / "scripts" / "check-workflow-state.py",
                "--root",
                root,
                encoding="utf-8",
                errors="replace",
            )

            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("workflow-check", result.stdout)
            self.assertIn("public_reader", result.stdout)
            self.assertIn("public-only", result.stdout)

    def test_workflow_check_rejects_polished_overall_with_drafted_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            state_path = root / "_paperops" / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["overall"]["state"] = "POLISHED"
            state["sections"]["results"]["state"] = "DRAFTED"
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_python_script(
                root / "scripts" / "check-workflow-state.py",
                "--root",
                root,
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("overall.state `POLISHED`", result.stdout)
        self.assertIn("results", result.stdout)
        self.assertIn("DRAFTED", result.stdout)

    def test_workflow_check_rejects_structure_accepted_before_results_and_discussion_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            state_path = root / "_paperops" / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["overall"]["state"] = "STRUCTURE_ACCEPTED"
            state["sections"]["results"]["state"] = "DRAFTED"
            state["sections"]["discussion"]["state"] = "DRAFTED"
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            result = run_python_script(
                root / "scripts" / "check-workflow-state.py",
                "--root",
                root,
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("overall.state `STRUCTURE_ACCEPTED`", result.stdout)
        self.assertIn("results", result.stdout)
        self.assertIn("discussion", result.stdout)
        self.assertIn("block-flow review", result.stdout)

    def test_pops_workflow_status_next_and_advance_with_guards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target), "--authority", "legacy"])
            self.assertEqual(code, 0, err)

            code, out, err = run_cli(["workflow", "status", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("workflow state: SCOPED", out)

            code, out, err = run_cli(["workflow", "next", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("next overall state: STORY_SEEDED", out)
            self.assertIn("guard blocked", out)

            state_path = target / "_paperops" / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["guards"]["STORY_SEEDED"] = {
                key: True for key in state["guards"]["STORY_SEEDED"]
            }
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(["workflow", "advance", "story-seeded", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("advanced: SCOPED -> STORY_SEEDED", out)
            self.assertEqual(
                json.loads(state_path.read_text(encoding="utf-8"))["overall"]["state"],
                "STORY_SEEDED",
            )

    def test_pops_workflow_invalidate_marks_dependent_sections_stale(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target), "--authority", "legacy"])
            self.assertEqual(code, 0, err)

            state_path = target / "_paperops" / "workflow" / "current-state.yml"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["sections"]["results"]["depends_on"]["claims"] = ["CLM-0001@v1"]
            state["sections"]["discussion"]["depends_on"]["claims"] = ["CLM-0001@v1"]
            state_path.write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(["workflow", "invalidate", "CLM-0001", str(target)])
            self.assertEqual(code, 0, err)
            self.assertIn("stale: results", out)
            self.assertIn("stale: discussion", out)

            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertEqual(state["sections"]["results"]["state"], "STALE")
            self.assertEqual(state["sections"]["results"]["route"], "story_loop")
            self.assertEqual(state["sections"]["discussion"]["state"], "STALE")

    def test_pops_workflow_route_review_can_apply_issue_class_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target), "--authority", "legacy"])
            self.assertEqual(code, 0, err)

            code, out, err = run_cli(
                ["workflow", "route-review", "--issue-class", "section-loop", "--apply", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("issue class: section_loop", out)
            self.assertIn("route to: SECTION_PLANNED", out)
            state = json.loads((target / "_paperops" / "workflow" / "current-state.yml").read_text(encoding="utf-8"))
            self.assertEqual(state["overall"]["state"], "SECTION_PLANNED")
            self.assertEqual(state["loop_counters"]["section_loop"], 1)

    def test_pops_workflow_route_review_blocks_submission_loop_before_structure_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target), "--authority", "legacy"])
            self.assertEqual(code, 0, err)

            code, out, err = run_cli(
                ["workflow", "route-review", "--issue-class", "submission-loop", "--apply", str(target)]
            )

            self.assertEqual(code, 1)
            self.assertEqual(err, "")
            self.assertIn("submission_loop is blocked", out)
            self.assertIn("STRUCTURE_ACCEPTED", out)
            state = json.loads((target / "_paperops" / "workflow" / "current-state.yml").read_text(encoding="utf-8"))
            self.assertEqual(state["overall"]["state"], "SCOPED")
            self.assertNotIn("submission_loop", state["loop_counters"])

    def test_workflow_kernel_is_documented_and_connected_to_finish_manuscript(self) -> None:
        architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
        cli_docs = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")
        skill = (
            ROOT / "template" / ".agents" / "skills" / "finish-manuscript" / "SKILL.md"
        ).read_text(encoding="utf-8") + (
            ROOT / "template" / ".agents" / "skills" / "route-manuscript-feedback" / "SKILL.md"
        ).read_text(encoding="utf-8")

        for required in [
            "_paperops/workflow/",
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

    def test_package_declares_pyyaml_for_workflow_yaml_loading(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("PyYAML>=6.0", pyproject)


if __name__ == "__main__":
    unittest.main()
