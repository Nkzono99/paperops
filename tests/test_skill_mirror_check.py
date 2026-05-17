from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paperops.cli.main import main  # noqa: E402


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


class SkillMirrorCheckTest(unittest.TestCase):
    def test_claude_wrapper_imports_agents_source_without_cwd_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            script = target / "scripts" / "check-skill-mirror.py"
            ok = subprocess.run(
                [sys.executable, str(script), "--root", str(target)],
                check=False,
                capture_output=True,
                text=True,
            )
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

            failed = subprocess.run(
                [sys.executable, str(script), "--root", str(target)],
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(failed.returncode, 1)
        self.assertIn("cwd 依存の参照", failed.stdout)


if __name__ == "__main__":
    unittest.main()
