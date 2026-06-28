from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, run_cli, run_python_script


class SkillMirrorCheckTest(unittest.TestCase):
    def test_agents_readme_names_agents_skills_as_source_of_truth(self) -> None:
        readme = (ROOT / "template" / ".agents" / "README.md").read_text(encoding="utf-8")

        self.assertIn("`.agents/skills/` を共通手順の source of truth", readme)
        self.assertIn("`.claude/skills/` は Claude Code 用 wrapper", readme)
        self.assertNotIn("`template/.claude/skills/` をハーネス方針の source of truth", readme)

    def test_claude_wrapper_imports_agents_source_without_cwd_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            script = target / "scripts" / "check-skill-mirror.py"
            ok = run_python_script(script, "--root", target)
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertIn(".agents source と .claude 互換入口", ok.stdout)

            skill_path = target / ".claude" / "skills" / "sync-ja-en" / "SKILL.md"
            skill_path.write_text(
                skill_path.read_text(encoding="utf-8").replace(
                    "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/sync-ja-en/SKILL.md",
                    "@.agents/skills/sync-ja-en/SKILL.md",
                ),
                encoding="utf-8",
            )

            failed = run_python_script(script, "--root", target)

        self.assertEqual(failed.returncode, 1)
        self.assertIn("cwd 依存の参照", failed.stdout)


if __name__ == "__main__":
    unittest.main()
