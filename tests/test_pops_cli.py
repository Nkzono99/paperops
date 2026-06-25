from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import ROOT, run_cli

from paperops import __version__  # noqa: E402
from paperops.cli.main import write_manifest  # noqa: E402
from paperops.cli.scaffold import copy_scaffold  # noqa: E402


def set_scaffold_version(root: Path, version: str) -> None:
    manifest = root / ".pops" / "manifest.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            f'version = "{__version__}"', f'version = "{version}"', 1
        ),
        encoding="utf-8",
    )


def future_minor_version(offset: int = 1) -> str:
    major, minor, *_rest = [int(part) for part in __version__.split(".")]
    return f"{major}.{minor + offset}.0"


class PopsCliTest(unittest.TestCase):
    def test_init_creates_project_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            code, _out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "_handoff").is_dir())
            self.assertTrue((target / "_handoff" / "README.md").is_file())
            self.assertTrue((target / "_archives" / "AGENTS.md").is_file())
            self.assertTrue((target / "_archives" / "README.md").is_file())
            self.assertTrue((target / "contracts" / "results.yml").is_file())
            self.assertTrue((target / "contracts" / "methods.yml").is_file())
            self.assertTrue((target / "workflow" / "machine.yml").is_file())
            self.assertTrue((target / "workflow" / "current-state.yml").is_file())
            self.assertTrue((target / "workflow" / "decisions.yml").is_file())
            self.assertTrue((target / "workflow" / "round-summary.yml").is_file())
            self.assertTrue((target / "manuscript" / "writing-profile.yml").is_file())
            troubleshooting = (target / "TROUBLESHOOTING.md").read_text(encoding="utf-8")
            self.assertIn("Skill descriptions were shortened", troubleshooting)
            self.assertIn("通常執筆", troubleshooting)
            self.assertTrue((target / "evidence" / "results" / "result-card-template.md").is_file())
            self.assertTrue((target / "evidence" / "figures" / "figure-card-template.md").is_file())
            self.assertTrue((target / "evidence" / "sources" / "source-card-template.md").is_file())
            self.assertTrue((target / "claims" / "claims" / "claim-card-template.md").is_file())
            self.assertTrue((target / "claims" / "gates" / "scientific-gate-card-template.md").is_file())
            self.assertTrue((target / "claims" / "arguments" / "argument-card-template.md").is_file())
            self.assertTrue((target / "review" / "feedback" / "feedback-card-template.md").is_file())
            self.assertTrue((target / "review" / "rounds" / "review-round-template.md").is_file())
            self.assertTrue((target / "review" / "responses" / "response-card-template.md").is_file())
            self.assertTrue((target / "requests" / "analysis" / "analysis-request-template.md").is_file())
            self.assertTrue((target / "requests" / "writing" / "writing-request-template.md").is_file())
            self.assertTrue((target / "notes" / "views" / "claim-evidence-map.md").is_file())
            self.assertTrue((target / "manuscript").is_dir())
            self.assertTrue((target / "refs" / "links.toml").is_file())
            self.assertTrue((target / "refs" / "imports" / "README.md").is_file())
            self.assertTrue((target / "refs" / "imports" / "import-state-template.toml").is_file())
            self.assertTrue((target / "refs" / "source-reach" / "README.md").is_file())
            self.assertTrue((target / "notes" / "source-reach.md").is_file())
            self.assertTrue((target / "notes" / "scientific-gate.md").is_file())
            self.assertTrue((target / "notes" / "ai-draft-polish.md").is_file())
            self.assertTrue((target / ".pops" / "manifest.toml").is_file())
            self.assertFalse((target / "refs" / "local" / "locations.toml").exists())
            for workflow in (target / ".github" / "workflows").glob("*.yml"):
                workflow_text = workflow.read_text(encoding="utf-8")
                self.assertNotIn("YOUR_ORG/paperops", workflow_text)
                self.assertIn("Nkzono99/paperops/.github/workflows/reusable-", workflow_text)
            gitignore = (target / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("_handoff/*", gitignore)
            self.assertIn(".paperops/cache/", gitignore)
            self.assertIn("refs/source-reach/**/raw/**", gitignore)

    def test_copy_scaffold_excludes_ignored_source_reach_and_handoff_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            target = Path(tmp) / "target"
            (source / "_handoff").mkdir(parents=True)
            (source / "_handoff" / ".gitkeep").write_text("\n", encoding="utf-8")
            (source / "_handoff" / "README.md").write_text("ok\n", encoding="utf-8")
            (source / "_handoff" / "secret.txt").write_text("no\n", encoding="utf-8")
            source_reach = source / "refs" / "source-reach" / "topic"
            (source_reach / "raw").mkdir(parents=True)
            (source_reach / "raw" / "cookie.txt").write_text("no\n", encoding="utf-8")
            (source_reach / "doctor.generated.json").write_text("no\n", encoding="utf-8")
            (source_reach / "capture.generated.json").write_text("no\n", encoding="utf-8")
            (source / "harness-feedback" / "records").mkdir(parents=True)
            (source / "harness-feedback" / "records" / "feedback.md").write_text(
                "no\n",
                encoding="utf-8",
            )
            (source / "harness-lab" / "records").mkdir(parents=True)
            (source / "harness-lab" / "records" / "lab.md").write_text(
                "no\n",
                encoding="utf-8",
            )
            (source / ".harness").mkdir()
            (source / ".harness" / "state.json").write_text("no\n", encoding="utf-8")
            (source / ".harnessops").mkdir()
            (source / ".harnessops" / "lock.json").write_text("no\n", encoding="utf-8")
            (source / "_archives" / "old" / "manuscript").mkdir(parents=True)
            (source / "_archives" / "old" / "manuscript" / "main.tex").write_text(
                "no\n",
                encoding="utf-8",
            )
            (source / "_archives" / "AGENTS.md").write_text("ok\n", encoding="utf-8")
            (source / "_archives" / "README.md").write_text("ok\n", encoding="utf-8")
            (source / "notes").mkdir()
            (source / "notes" / "source-reach.md").write_text("ok\n", encoding="utf-8")

            plan = copy_scaffold(source, target, overwrite=False)

            self.assertTrue((target / "_handoff" / ".gitkeep").is_file())
            self.assertTrue((target / "_handoff" / "README.md").is_file())
            self.assertTrue((target / "notes" / "source-reach.md").is_file())
            self.assertFalse((target / "_handoff" / "secret.txt").exists())
            self.assertFalse((target / "refs" / "source-reach" / "topic" / "raw").exists())
            self.assertFalse(
                (target / "refs" / "source-reach" / "topic" / "doctor.generated.json").exists()
            )
            self.assertFalse(
                (target / "refs" / "source-reach" / "topic" / "capture.generated.json").exists()
            )
            self.assertFalse((target / "harness-feedback").exists())
            self.assertFalse((target / "harness-lab").exists())
            self.assertFalse((target / ".harness").exists())
            self.assertFalse((target / ".harnessops" / "lock.json").exists())
            self.assertTrue((target / "_archives" / "AGENTS.md").is_file())
            self.assertTrue((target / "_archives" / "README.md").is_file())
            self.assertFalse((target / "_archives" / "old").exists())
            self.assertIn("_handoff/secret.txt", plan.excluded)
            self.assertIn("refs/source-reach/topic/raw", plan.excluded)
            self.assertIn("refs/source-reach/topic/raw/cookie.txt", plan.excluded)
            self.assertIn("harness-feedback", plan.excluded)
            self.assertIn("harness-feedback/records/feedback.md", plan.excluded)
            self.assertIn("harness-lab", plan.excluded)
            self.assertIn(".harness/state.json", plan.excluded)
            self.assertIn(".harnessops/lock.json", plan.excluded)
            self.assertIn("_archives/old", plan.excluded)

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
            self.assertIn("doctor scope: structure and local setup only", out)
            self.assertIn("make readiness-check", out)
            self.assertIn("Skill context budget warning", out)
            self.assertIn("TROUBLESHOOTING.md", out)

    def test_doctor_rejects_invalid_link_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "refs" / "links.toml").write_text("not = [valid", encoding="utf-8")

            code, out, _err = run_cli(["doctor", str(target)])

            self.assertEqual(code, 1)
            self.assertIn("refs/links.toml", out)
            self.assertIn("TOML", out)
            self.assertIn("doctor: failed", out)

    def test_doctor_warns_when_link_alias_is_not_in_local_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "refs" / "local" / "locations.toml").write_text(
                "\n".join(
                    [
                        "[paths.runops_main]",
                        'kind = "runops_project"',
                        'host = "local"',
                        'path = "/tmp/runops"',
                    ]
                ),
                encoding="utf-8",
            )

            code, out, err = run_cli(["doctor", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("figure_sources", out)
            self.assertIn("external_notes", out)
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

    def test_update_paperops_can_add_missing_section_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "contracts" / "results.yml").unlink()

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "contracts/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("+ contracts/results.yml [section contract]", out)

            code, _out, err = run_cli(
                ["update-paperops", "--apply", "--only", "contracts/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "contracts" / "results.yml").is_file())

    def test_update_paperops_can_add_missing_workflow_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "workflow" / "machine.yml").unlink()

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "workflow/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("+ workflow/machine.yml [workflow state machine]", out)

            code, _out, err = run_cli(
                ["update-paperops", "--apply", "--only", "workflow/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "workflow" / "machine.yml").is_file())

    def test_update_paperops_explains_changed_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            agents = target / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8") + "\nlocal operator note\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "AGENTS.md", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("changed managed files: 1", out)
            self.assertIn("meaning: target file differs from the scaffold source", out)
            self.assertIn("! AGENTS.md [agent guidance]", out)
            self.assertIn("--apply --force only when local edits may be replaced", out)

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
            self.assertIn("runops.paper.request.draft", out)

            code, out, err = run_cli(["links", "check", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("links: ok", out)

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
            applied_version = future_minor_version()
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    f'version = "{__version__}"', f'version = "{applied_version}"', 1
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
            latest_version = future_minor_version()
            applied_version = future_minor_version(2)
            manifest = target / ".pops" / "manifest.toml"
            manifest.write_text(
                manifest.read_text(encoding="utf-8").replace(
                    f'version = "{__version__}"', f'version = "{applied_version}"', 1
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
                    return_value=latest_version,
                ),
            ):
                code, _out, err = run_cli(["doctor", str(target)])

        self.assertEqual(code, 0, err)
        self.assertIn(f"実行中の pops が古いです: {__version__} -> {latest_version}", err)
        self.assertIn("実行中の pops がこのプロジェクトの適用済み scaffold より古い", err)
        self.assertNotIn(
            f"paperops ハーネス更新候補: {applied_version} -> {latest_version}",
            err,
        )

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
