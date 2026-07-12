from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_cli, run_python_script


class WorkflowKernelTest(unittest.TestCase):
    def test_template_keeps_policy_but_projects_current_state_from_models(self) -> None:
        defaults = ROOT / "template/_paperops/defaults/workflow"
        for name in ("machine.yml", "focus-policy.yml", "subagent-roster.yml"):
            self.assertTrue((defaults / name).is_file())
        for name in ("current-state.yml", "decisions.yml", "round-summary.yml", "submission-ledger.yml"):
            self.assertFalse((ROOT / "template/_paperops/workflow" / name).exists())
        checker = (ROOT / "template/scripts/check-workflow-state.py").read_text(encoding="utf-8")
        self.assertIn("workflow_projection", checker)
        self.assertNotIn('internal_path(root, "workflow", "current-state.yml")', checker)

    def test_workflow_check_accepts_fresh_typed_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            result = run_python_script(ROOT / "template/scripts/check-workflow-state.py", "--root", root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("workflow state is valid", result.stdout)

    def test_init_uses_v2_projection_and_rejects_legacy_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper"
            code, _out, err = run_cli(["init", str(root)])
            self.assertEqual(code, 0, err)
            code, out, err = run_cli(["workflow", "status", str(root), "--json"])
            self.assertEqual(code, 0, err or out)
            self.assertIn('"stage":"INGESTED"', out)
            code, _out, err = run_cli(["workflow", "advance", "STORY_SEEDED", str(root)])
            self.assertEqual(code, 2)
            self.assertIn("legacy workflow mutation is disabled", err)

    def test_makefiles_keep_workflow_check_name(self) -> None:
        for path in (ROOT / "Makefile", ROOT / "template/Makefile"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("workflow-check", text)
            self.assertIn("check-workflow-state.py", text)


if __name__ == "__main__":
    unittest.main()
