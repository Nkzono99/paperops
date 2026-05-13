from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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

            code, _out, err = run_cli(["init", str(target), "--skip-venv"])

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "manuscript").is_dir())
            self.assertTrue((target / ".pops" / "manifest.toml").is_file())
            self.assertFalse((target / "refs" / "local" / "locations.toml").exists())

    def test_init_bootstraps_project_local_cli_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            def fake_make_venv(root: Path) -> bool:
                scripts = "Scripts" if sys.platform.startswith("win") else "bin"
                (root / ".venv" / scripts).mkdir(parents=True)
                return True

            with (
                mock.patch("paperops.cli.main.run_make_venv", side_effect=fake_make_venv)
                as make_venv,
                mock.patch("paperops.cli.main.install_project_cli", return_value=True)
                as install,
            ):
                code, _out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 0, err)
            make_venv.assert_called_once()
            install.assert_called_once()
            self.assertTrue((target / ".venv").is_dir())

    def test_doctor_accepts_initialized_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target), "--skip-venv"])

            code, out, err = run_cli(["doctor", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("doctor: ok", out)

    def test_update_paperops_can_plan_single_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "AGENTS.md", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("Paperops update plan", out)
            self.assertIn("unchanged managed files: 1", out)

    def test_update_harness_alias_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

            code, out, err = run_cli(
                ["update-harness", "--dry-run", "--only", "AGENTS.md", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("Paperops update plan", out)

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

    def test_write_manifest_records_project_local_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            write_manifest(target, cli_install_spec="paper-harness-cli==0.1.0")
            text = (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")

            self.assertIn("[cli]", text)
            self.assertIn('package = "paper-harness-cli"', text)
            self.assertIn('install_spec = "paper-harness-cli==0.1.0"', text)
            self.assertIn('venv = ".venv"', text)

    def test_update_harness_adopt_can_record_template_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target), "--template-ref", "old"])

            code, _out, err = run_cli(
                ["update-paperops", "--adopt", "--template-ref", "new", str(target)]
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

    def test_update_notice_points_to_update_paperops_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "POPS_FORCE_VERSION_CHECK": "1",
                "POPS_UPDATE_CHECK_CACHE": str(Path(tmp) / "cache.json"),
            }
            with (
                mock.patch.dict("os.environ", env, clear=False),
                mock.patch(
                    "paperops.cli.main.fetch_latest_package_version",
                    return_value="9.9.9",
                ),
            ):
                code, _out, err = run_cli(["feedback", "--title", "notice"])

        self.assertEqual(code, 0, err)
        self.assertIn("paperops の更新があります", err)
        self.assertIn("uvx --from paper-harness-cli pops setup", err)
        self.assertIn("/update-paperops", err)

    def test_update_notice_can_be_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "POPS_DISABLE_VERSION_CHECK": "1",
                "POPS_FORCE_VERSION_CHECK": "1",
                "POPS_UPDATE_CHECK_CACHE": str(Path(tmp) / "cache.json"),
            }
            with (
                mock.patch.dict("os.environ", env, clear=False),
                mock.patch(
                    "paperops.cli.main.fetch_latest_package_version",
                    return_value="9.9.9",
                ) as fetch,
            ):
                code, _out, err = run_cli(["feedback", "--title", "notice"])

        self.assertEqual(code, 0, err)
        self.assertEqual("", err)
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
