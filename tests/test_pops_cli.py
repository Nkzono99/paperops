from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from paperops.cli.main import main


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


class PopsCliTest(unittest.TestCase):
    def test_init_creates_project_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            code, _out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "manuscript").is_dir())
            self.assertTrue((target / ".pops" / "manifest.toml").is_file())
            self.assertFalse((target / "refs" / "local" / "locations.toml").exists())

    def test_doctor_accepts_initialized_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

            code, out, err = run_cli(["doctor", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("doctor: ok", out)

    def test_update_harness_can_plan_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

            code, out, err = run_cli(
                ["update-harness", "--dry-run", "--only", "AGENTS.md", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("Harness update plan", out)
            self.assertIn("unchanged managed files: 1", out)

    def test_feedback_can_write_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "feedback.md"

            code, _out, err = run_cli(
                [
                    "feedback",
                    "--title",
                    "CLI feedback",
                    "--body",
                    "改善内容",
                    "--output",
                    str(output),
                ]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("CLI feedback", output.read_text(encoding="utf-8"))

    def test_top_level_version_flag(self) -> None:
        code, out, err = run_cli(["--version"])

        self.assertEqual(code, 0, err)
        self.assertIn("pops 0.1.0", out)


if __name__ == "__main__":
    unittest.main()
