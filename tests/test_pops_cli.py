from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paperops.cli.main import main, write_manifest


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

    def test_write_manifest_preserves_existing_scaffold_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            manifest = target / ".pops" / "manifest.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                "\n".join(
                    [
                        "[project]",
                        'tool = "pops"',
                        'local_note = "keep"',
                        "",
                        "[scaffold]",
                        'package = "paper-harness-cli"',
                        'template_ref = "abc123"',
                        'local_key = "keep-too"',
                        "",
                        "[audit]",
                        'owner = "downstream"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            write_manifest(target)
            text = manifest.read_text(encoding="utf-8")

            self.assertIn('template_ref = "abc123"', text)
            self.assertIn('local_key = "keep-too"', text)
            self.assertIn("[audit]", text)
            self.assertIn('owner = "downstream"', text)

    def test_update_harness_adopt_can_record_template_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target), "--template-ref", "old"])

            code, _out, err = run_cli(
                ["update-harness", "--adopt", "--template-ref", "new", str(target)]
            )

            self.assertEqual(code, 0, err)
            text = (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            self.assertIn('template_ref = "new"', text)

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
