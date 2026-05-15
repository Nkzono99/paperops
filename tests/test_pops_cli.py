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

from paperops import __version__
from paperops.cli.main import main, write_manifest


def run_cli(args: list[str]) -> tuple[int, str, str]:
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(args)
    return code, stdout.getvalue(), stderr.getvalue()


def set_scaffold_version(root: Path, version: str) -> None:
    manifest = root / ".pops" / "manifest.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            f'version = "{__version__}"', f'version = "{version}"', 1
        ),
        encoding="utf-8",
    )


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

    def test_init_uses_uvx_flow_without_project_local_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            code, out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("uvx --from paper-harness-cli pops doctor", out)
            self.assertFalse((target / ".venv").exists())

    def test_doctor_accepts_initialized_project(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

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

    def test_update_paperops_plans_versioned_upgrade_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            set_scaffold_version(target, "0.1.0")
            with mock.patch(
                "paperops.cli.main.available_package_versions",
                return_value=["0.1.0", "0.1.2", "0.2.0", "0.2.5", "0.3.4"],
            ):
                code, out, err = run_cli(["update-paperops", "--plan", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("Paperops upgrade chain", out)
            self.assertIn("1. 0.1.0 -> 0.2.5", out)
            self.assertIn("2. 0.2.5 -> 0.3.4", out)

    def test_update_paperops_apply_chain_invokes_exact_uvx_versions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            set_scaffold_version(target, "0.1.0")
            with (
                mock.patch(
                    "paperops.cli.main.available_package_versions",
                    return_value=["0.1.0", "0.2.5", "0.3.4"],
                ),
                mock.patch("paperops.cli.upgrade.subprocess.run") as run,
            ):
                run.return_value = mock.Mock(returncode=0)
                code, out, err = run_cli(
                    ["update-paperops", "--apply-chain", str(target)]
                )

            self.assertEqual(code, 0, err)
            self.assertIn("Running: uvx --from paper-harness-cli==0.2.5", out)
            self.assertIn("Running: uvx --from paper-harness-cli==0.3.4", out)
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(commands[0][:3], ["uvx", "--from", "paper-harness-cli==0.2.5"])
            self.assertIn("--upgrade-step", commands[0])
            self.assertIn("--apply", commands[0])
            self.assertEqual(commands[1][:3], ["uvx", "--from", "paper-harness-cli==0.3.4"])

    def test_update_paperops_apply_chain_requires_allow_major(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    f'version = "{__version__}"', 'version = "0.9.0"', 1
                ),
                encoding="utf-8",
            )
            with mock.patch(
                "paperops.cli.main.available_package_versions",
                return_value=["0.9.0", "1.0.0"],
            ):
                code, _out, err = run_cli(
                    ["update-paperops", "--apply-chain", str(target)]
                )

            self.assertEqual(code, 2)
            self.assertIn("--allow-major", err)

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

    def test_write_manifest_records_uvx_cli_runner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            write_manifest(target)
            text = (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")

            self.assertIn("[cli]", text)
            self.assertIn('package = "paper-harness-cli"', text)
            self.assertIn('runner = "uvx"', text)
            self.assertIn('command = "uvx --from paper-harness-cli pops"', text)
            self.assertIn('layout_version = "0.1"', text)
            self.assertIn("[upgrade]", text)
            checkpoint = ".".join(__version__.split(".")[:2])
            self.assertIn(f'last_checkpoint = "{checkpoint}"', text)
            self.assertNotIn('venv = ".venv"', text)

    def test_setup_refreshes_cli_runner_without_changing_scaffold_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                "\n".join(
                    [
                        "[project]",
                        'tool = "pops"',
                        "",
                        "[scaffold]",
                        'package = "paper-harness-cli"',
                        'version = "0.0.5"',
                        'source = "Nkzono99/paperops"',
                        "",
                        "[cli]",
                        'package = "paper-harness-cli"',
                        'version = "0.0.5"',
                        'install_spec = "paper-harness-cli==0.0.5"',
                        'venv = ".venv"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            code, _out, err = run_cli(["setup", str(target)])

            self.assertEqual(code, 0, err)
            text = manifest.read_text(encoding="utf-8")
            self.assertIn('version = "0.0.5"', text)
            self.assertIn('runner = "uvx"', text)
            self.assertNotIn('install_spec = "paper-harness-cli==0.0.5"', text)
            self.assertNotIn('venv = ".venv"', text)

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

    def test_links_commands_list_and_check_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

            code, out, err = run_cli(["links", "list", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("runops-main", out)
            self.assertIn("figure-sources", out)
            self.assertIn("mcp: runops/runops", out)
            self.assertIn("paper requests: research/paper_requests.toml", out)

            code, out, err = run_cli(["links", "check", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("links: ok", out)

    def test_links_check_reports_invalid_kind(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            links_path = target / "refs" / "links.toml"
            links_path.write_text(
                links_path.read_text(encoding="utf-8").replace(
                    'kind = "runops_project"',
                    'kind = "mystery"',
                    1,
                ),
                encoding="utf-8",
            )

            code, out, _err = run_cli(["links", "check", str(target)])

            self.assertEqual(code, 1)
            self.assertIn("[error]", out)
            self.assertIn("mystery", out)

    def test_top_level_version_flag(self) -> None:
        code, out, err = run_cli(["--version"])

        self.assertEqual(code, 0, err)
        self.assertIn(f"pops {__version__}", out)

    def test_update_notice_points_to_update_paperops_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "POPS_FORCE_VERSION_CHECK": "1",
                "POPS_UPDATE_CHECK_CACHE": str(Path(tmp) / "cache.json"),
            }
            with (
                mock.patch.dict("os.environ", env, clear=False),
                mock.patch(
                    "paperops.cli.pypi.fetch_latest_package_version",
                    return_value="9.9.9",
                ),
            ):
                code, _out, err = run_cli(["feedback", "--title", "notice"])

        self.assertEqual(code, 0, err)
        self.assertIn("実行中の pops が古いです", err)
        self.assertIn("uvx --from paper-harness-cli pops <command>", err)
        self.assertIn("uvx --from paper-harness-cli pops update-paperops --plan", err)
        self.assertIn("/update-paperops", err)

    def test_update_notice_compares_applied_scaffold_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    f'version = "{__version__}"', 'version = "0.0.1"', 1
                ),
                encoding="utf-8",
            )
            env = {
                "POPS_FORCE_VERSION_CHECK": "1",
                "POPS_UPDATE_CHECK_CACHE": str(Path(tmp) / "cache.json"),
            }
            with (
                mock.patch.dict("os.environ", env, clear=False),
                mock.patch(
                    "paperops.cli.pypi.fetch_latest_package_version",
                    return_value=None,
                ),
            ):
                code, _out, err = run_cli(["doctor", str(target)])

        self.assertEqual(code, 0, err)
        self.assertIn(f"paperops ハーネス更新候補: 0.0.1 -> {__version__}", err)
        self.assertIn("uvx --from paper-harness-cli pops update-paperops --plan", err)

    def test_update_notice_detects_running_cli_older_than_applied_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    f'version = "{__version__}"', 'version = "0.3.0"', 1
                ),
                encoding="utf-8",
            )
            env = {
                "POPS_FORCE_VERSION_CHECK": "1",
                "POPS_UPDATE_CHECK_CACHE": str(Path(tmp) / "cache.json"),
            }
            with (
                mock.patch.dict("os.environ", env, clear=False),
                mock.patch(
                    "paperops.cli.pypi.fetch_latest_package_version",
                    return_value=None,
                ),
            ):
                code, _out, err = run_cli(["doctor", str(target)])

        self.assertEqual(code, 0, err)
        self.assertIn("実行中の pops がこのプロジェクトの適用済み scaffold より古い", err)
        self.assertIn("uvx --from paper-harness-cli pops <command>", err)

    def test_update_notice_reports_applied_scaffold_newer_than_latest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    f'version = "{__version__}"', 'version = "0.4.0"', 1
                ),
                encoding="utf-8",
            )
            env = {
                "POPS_FORCE_VERSION_CHECK": "1",
                "POPS_UPDATE_CHECK_CACHE": str(Path(tmp) / "cache.json"),
            }
            with (
                mock.patch.dict("os.environ", env, clear=False),
                mock.patch(
                    "paperops.cli.pypi.fetch_latest_package_version",
                    return_value="0.3.0",
                ),
            ):
                code, _out, err = run_cli(["doctor", str(target)])

        self.assertEqual(code, 0, err)
        self.assertIn(f"実行中の pops が古いです: {__version__} -> 0.3.0", err)
        self.assertIn("実行中の pops がこのプロジェクトの適用済み scaffold より古い", err)
        self.assertNotIn("paperops ハーネス更新候補: 0.4.0 -> 0.3.0", err)

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
                    "paperops.cli.pypi.fetch_latest_package_version",
                    return_value="9.9.9",
                ) as fetch,
            ):
                code, _out, err = run_cli(["feedback", "--title", "notice"])

        self.assertEqual(code, 0, err)
        self.assertEqual("", err)
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
