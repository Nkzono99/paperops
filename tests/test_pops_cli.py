from __future__ import annotations

import json
import os
import stat
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import ROOT, copy_template, run_cli

from paperops import __version__  # noqa: E402
from paperops.authority_bootstrap import bootstrap_v2_authority  # noqa: E402
from paperops.cli.main import write_manifest  # noqa: E402
from paperops.cli.manifest import applied_migrations  # noqa: E402
from paperops.cli.migrations import get_migration  # noqa: E402
from paperops.cli.scaffold import copy_scaffold, is_managed_update  # noqa: E402
from paperops.model_state import MODEL_NAMES  # noqa: E402


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


def create_legacy_internal_layout(root: Path) -> None:
    (root / "manuscript").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "Makefile").write_text("ci:\n\t@echo ok\n", encoding="utf-8")
    for directory in ["notes", "refs", "claims", "evidence", "workflow", "contracts", "review", "requests"]:
        (root / directory).mkdir()
        (root / directory / "legacy.md").write_text(f"# {directory}\n", encoding="utf-8")


class PopsCliTest(unittest.TestCase):
    def test_init_defaults_to_v2_authority_for_all_models_and_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            code, out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 0, err)
            manifest = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["workflow"]["mode"], "v2-authoritative")
            self.assertEqual(tuple(manifest["models"]), MODEL_NAMES)
            for name in MODEL_NAMES:
                with self.subTest(model=name):
                    state = manifest["models"][name]
                    self.assertEqual(state["mode"], "v2-authoritative")
                    self.assertRegex(state["current_hash"], r"^sha256:[0-9a-f]{64}$")
                    self.assertEqual(state["last_shadow_transaction"], "")
                    self.assertEqual(state["last_adopt_transaction"], "")
                    self.assertIn(f"  {name}: {state['current_hash']}", out)
            self.assertIn("Authority: v2-authoritative", out)
            self.assertIn("Workflow: v2-authoritative", out)

    def test_init_v2_is_immediately_valid_for_model_and_compile_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            code, raw, err = run_cli(["model", "status", "all", str(target), "--json"])
            self.assertEqual(code, 0, err or raw)
            self.assertTrue(json.loads(raw)["ok"])

            code, raw, err = run_cli(["compile", "status", "all", str(target), "--json"])
            self.assertIn(code, {0, 1}, err or raw)
            self.assertNotIn("compile.authority_journal", raw)
            self.assertNotIn("compile.authority_state", raw)

    def test_init_v2_model_status_detects_live_model_hash_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)
            publication = target / "_paperops" / "model" / "publication" / "publication-model.yml"
            publication.write_text(
                publication.read_text(encoding="utf-8").replace('  name: ""', '  name: "Journal"'),
                encoding="utf-8",
            )

            code, raw, err = run_cli(["model", "status", "all", str(target), "--json"])

            self.assertEqual(code, 1, err or raw)
            self.assertIn("state.hash_mismatch", raw)

    def test_init_legacy_records_explicit_legacy_authority_and_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            code, out, err = run_cli(["init", str(target), "--authority", "legacy"])

            self.assertEqual(code, 0, err)
            manifest = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["workflow"]["mode"], "legacy")
            self.assertTrue(
                all(manifest["models"][name]["mode"] == "legacy-authoritative" for name in MODEL_NAMES)
            )
            self.assertIn("Authority: legacy-authoritative", out)
            self.assertIn("deprecated", err)
            self.assertIn("removal is not scheduled", err)

    def test_init_rejects_v2_force_copy_into_nonempty_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            target.mkdir()
            marker = target / "project-owned.txt"
            marker.write_text("keep\n", encoding="utf-8")

            code, _out, err = run_cli(["init", str(target), "--force"])

            self.assertEqual(code, 2)
            self.assertIn("--authority legacy", err)
            self.assertEqual(marker.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse((target / ".pops").exists())

    def test_init_bootstrap_failure_leaves_no_partial_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            with mock.patch(
                "paperops.cli.main.bootstrap_v2_authority",
                side_effect=ValueError("starter model validation failed: schema.invalid"),
            ):
                code, _out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 1)
            self.assertIn("schema.invalid", err)
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(tmp).glob(".paper-demo.pops-init-*")), [])

    def test_init_preserves_empty_target_mode_and_restores_it_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            target.mkdir(mode=0o750)
            target.chmod(0o750)

            with mock.patch(
                "paperops.cli.main.bootstrap_v2_authority",
                side_effect=ValueError("starter model validation failed: schema.invalid"),
            ):
                code, _out, _err = run_cli(["init", str(target)])
            self.assertEqual(code, 1)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o750)

            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o750)

    def test_init_new_target_uses_normal_directory_umask(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            previous = os.umask(0o027)
            try:
                code, _out, err = run_cli(["init", str(target)])
            finally:
                os.umask(previous)

            self.assertEqual(code, 0, err)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o750)

    def test_init_does_not_replace_target_created_during_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            def create_contending_target(staging: Path) -> dict[str, str]:
                hashes = bootstrap_v2_authority(staging)
                target.mkdir()
                return hashes

            with mock.patch(
                "paperops.cli.main.bootstrap_v2_authority",
                side_effect=create_contending_target,
            ):
                code, _out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 1)
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.iterdir()), [])
            self.assertNotIn(".pops-init-", err)

    def test_legacy_force_copy_preserves_existing_v2_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)
            before = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            (target / "project-owned.txt").write_text("keep\n", encoding="utf-8")

            code, _out, err = run_cli(
                ["init", str(target), "--force", "--authority", "legacy"]
            )

            self.assertEqual(code, 0, err)
            after = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            self.assertEqual(after["models"], before["models"])
            self.assertEqual(after["workflow"], before["workflow"])
            self.assertEqual((target / "project-owned.txt").read_text(encoding="utf-8"), "keep\n")

    def test_setup_of_existing_legacy_scaffold_does_not_invent_authority_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)

            code, _out, err = run_cli(["setup", "--path", str(target)])

            self.assertEqual(code, 0, err)
            manifest = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            self.assertNotIn("models", manifest)
            self.assertNotIn("workflow", manifest)

    def test_managed_update_preserves_explicit_authority_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for authority in ("v2", "legacy"):
                with self.subTest(authority=authority):
                    target = Path(tmp) / f"paper-{authority}"
                    args = ["init", str(target)]
                    if authority == "legacy":
                        args.extend(["--authority", "legacy"])
                    code, _out, err = run_cli(args)
                    self.assertEqual(code, 0, err)
                    manifest_path = target / ".pops" / "manifest.toml"
                    before = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
                    managed = target / "_paperops" / "defaults" / "contracts" / "results.yml"
                    managed.unlink()

                    code, _out, err = run_cli(
                        [
                            "update-paperops",
                            "--apply",
                            "--only",
                            "_paperops/defaults/contracts/results.yml",
                            str(target),
                        ]
                    )

                    self.assertEqual(code, 0, err)
                    after = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
                    self.assertEqual(after["models"], before["models"])
                    self.assertEqual(after["workflow"], before["workflow"])

    def test_init_contains_editorial_starter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"

            code, _out, err = run_cli(["init", str(target)])

            self.assertEqual(code, 0, err)
            self.assertTrue(
                (target / "_paperops" / "model" / "editorial" / "editorial-model.yml").is_file()
            )

    def test_init_contains_empty_model_indexes_but_update_does_not_manage_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)
            for model_name, relative in (
                ("research", "_paperops/model/research/index.yml"),
                ("manuscript", "_paperops/model/manuscript/index.yml"),
                ("issue", "_paperops/model/issues/index.yml"),
            ):
                with self.subTest(model=model_name):
                    index = target / relative
                    self.assertIn("records: []", index.read_text(encoding="utf-8"))

                    project_owned = index.read_text(encoding="utf-8") + "\n# project-owned\n"
                    index.write_text(project_owned, encoding="utf-8")
                    code, out, err = run_cli(["update-paperops", "--apply", str(target)])
                    self.assertEqual(code, 0, err)
                    self.assertEqual(index.read_text(encoding="utf-8"), project_owned)
                    self.assertNotIn(relative, out)

                    index.unlink()
                    code, out, err = run_cli(["update-paperops", "--apply", str(target)])
                    self.assertEqual(code, 0, err)
                    self.assertFalse(index.exists())
                    self.assertNotIn(relative, out)

            publication = target / "_paperops/model/publication/publication-model.yml"
            self.assertTrue(publication.is_file())
            project_owned = publication.read_text(encoding="utf-8") + "\n# project-owned\n"
            publication.write_text(project_owned, encoding="utf-8")
            code, out, err = run_cli(["update-paperops", "--apply", str(target)])
            self.assertEqual(code, 0, err)
            self.assertEqual(publication.read_text(encoding="utf-8"), project_owned)
            self.assertNotIn("_paperops/model/publication/publication-model.yml", out)

            publication.unlink()
            code, out, err = run_cli(["update-paperops", "--apply", str(target)])
            self.assertEqual(code, 0, err)
            self.assertFalse(publication.exists())
            self.assertNotIn("_paperops/model/publication/publication-model.yml", out)

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
            self.assertTrue((target / "_paperops" / "defaults" / "contracts" / "results.yml").is_file())
            self.assertTrue((target / "_paperops" / "defaults" / "contracts" / "methods.yml").is_file())
            self.assertTrue((target / "_paperops" / "defaults" / "contracts" / "figures.yml").is_file())
            self.assertTrue((target / "_paperops" / "defaults" / "workflow" / "machine.yml").is_file())
            self.assertTrue((target / "_paperops" / "defaults" / "workflow" / "focus-policy.yml").is_file())
            self.assertTrue((target / "_paperops" / "defaults" / "workflow" / "subagent-roster.yml").is_file())
            self.assertFalse((target / "_paperops" / "workflow" / "machine.yml").exists())
            self.assertTrue((target / "_paperops" / "workflow" / "current-state.yml").is_file())
            self.assertTrue((target / "_paperops" / "workflow" / "decisions.yml").is_file())
            self.assertTrue((target / "_paperops" / "workflow" / "round-summary.yml").is_file())
            self.assertTrue((target / "manuscript" / "writing-profile.yml").is_file())
            troubleshooting = (target / "TROUBLESHOOTING.md").read_text(encoding="utf-8")
            self.assertIn("Skill descriptions were shortened", troubleshooting)
            self.assertIn("通常執筆", troubleshooting)
            self.assertTrue((target / "_paperops" / "evidence" / "results" / "result-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "evidence" / "figures" / "figure-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "evidence" / "sources" / "source-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "claims" / "claims" / "claim-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "claims" / "gates" / "scientific-gate-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "claims" / "arguments" / "argument-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "review" / "feedback" / "feedback-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "review" / "rounds" / "review-round-template.md").is_file())
            self.assertTrue((target / "_paperops" / "review" / "responses" / "response-card-template.md").is_file())
            self.assertTrue((target / "_paperops" / "requests" / "analysis" / "analysis-request-template.md").is_file())
            self.assertTrue((target / "_paperops" / "requests" / "writing" / "writing-request-template.md").is_file())
            self.assertTrue((target / "scripts" / "check-figure-obligations.py").is_file())
            self.assertTrue(
                (target / ".agents" / "skills" / "plan-figure-story" / "SKILL.md").is_file()
            )
            self.assertTrue(
                (target / ".claude" / "skills" / "plan-figure-story" / "SKILL.md").is_file()
            )
            self.assertTrue((target / "AGENTS.project.md").is_file())
            self.assertTrue((target / "CLAUDE.project.md").is_file())
            self.assertTrue((target / "Makefile.project").is_file())
            agents_guidance = (target / "AGENTS.md").read_text(encoding="utf-8")
            claude_guidance = (target / "CLAUDE.md").read_text(encoding="utf-8")
            makefile = (target / "Makefile").read_text(encoding="utf-8")
            self.assertIn("AGENTS.project.md", agents_guidance)
            self.assertIn("CLAUDE.project.md", claude_guidance)
            self.assertIn("-include Makefile.project", makefile)
            self.assertIn("-include Makefile.local", makefile)
            self.assertTrue((target / "_paperops" / "notes" / "views" / "claim-evidence-map.md").is_file())
            self.assertTrue((target / "story" / "story-seed.md").is_file())
            self.assertTrue((target / "manuscript").is_dir())
            self.assertTrue((target / "_paperops" / "refs" / "links.toml").is_file())
            self.assertTrue((target / "_paperops" / "refs" / "imports" / "README.md").is_file())
            self.assertTrue((target / "_paperops" / "refs" / "imports" / "import-state-template.toml").is_file())
            self.assertTrue((target / "_paperops" / "refs" / "source-reach" / "README.md").is_file())
            self.assertTrue((target / "_paperops" / "notes" / "source-reach.md").is_file())
            self.assertTrue((target / "_paperops" / "notes" / "scientific-gate.md").is_file())
            self.assertTrue((target / "_paperops" / "notes" / "ai-draft-polish.md").is_file())
            self.assertTrue((target / ".pops" / "manifest.toml").is_file())
            self.assertFalse((target / "_paperops" / "refs" / "local" / "locations.toml").exists())
            for workflow in (target / ".github" / "workflows").glob("*.yml"):
                workflow_text = workflow.read_text(encoding="utf-8")
                self.assertNotIn("YOUR_ORG/paperops", workflow_text)
                self.assertIn("Nkzono99/paperops/.github/workflows/reusable-", workflow_text)
            gitignore = (target / ".gitignore").read_text(encoding="utf-8")
            self.assertIn("_handoff/*", gitignore)
            self.assertIn(".paperops/cache/", gitignore)
            self.assertIn("Makefile.local", gitignore)
            self.assertIn("_paperops/refs/source-reach/**/raw/**", gitignore)

    def test_copy_scaffold_excludes_ignored_source_reach_and_handoff_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            target = Path(tmp) / "target"
            (source / "_handoff").mkdir(parents=True)
            (source / "_handoff" / ".gitkeep").write_text("\n", encoding="utf-8")
            (source / "_handoff" / "README.md").write_text("ok\n", encoding="utf-8")
            (source / "_handoff" / "secret.txt").write_text("no\n", encoding="utf-8")
            source_reach = source / "_paperops" / "refs" / "source-reach" / "topic"
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
            (source / "_paperops" / "notes").mkdir(parents=True)
            (source / "_paperops" / "notes" / "source-reach.md").write_text("ok\n", encoding="utf-8")
            (source / ".paperops" / "cache").mkdir(parents=True)
            (source / ".paperops" / "cache" / "context.generated.md").write_text("no\n", encoding="utf-8")
            (source / ".tools" / "tex").mkdir(parents=True)
            (source / ".tools" / "tex" / "bin").write_text("no\n", encoding="utf-8")
            (source / "scripts" / "__pycache__").mkdir(parents=True)
            (source / "scripts" / "__pycache__" / "check.cpython-311.pyc").write_bytes(b"no")
            (source / "scripts" / "check.pyc").write_bytes(b"no")
            (source / "submission" / "agu" / "build").mkdir(parents=True)
            (source / "submission" / "agu" / "build" / "main.pdf").write_text("no\n", encoding="utf-8")
            (source / "submission" / "agu" / ".tools").mkdir(parents=True)
            (source / "submission" / "agu" / ".tools" / "local.txt").write_text("no\n", encoding="utf-8")
            (source / "tex-env.toml").write_text("no\n", encoding="utf-8")
            (source / "_paperops" / "refs" / "papers" / "paper.pdf").parent.mkdir(parents=True)
            (source / "_paperops" / "refs" / "papers" / "paper.pdf").write_text("no\n", encoding="utf-8")
            (source / "_paperops" / "refs" / "research" / "scan" / "results").mkdir(parents=True)
            (source / "_paperops" / "refs" / "research" / "scan" / "results" / "raw.json").write_text(
                "no\n",
                encoding="utf-8",
            )
            (source / "_paperops" / "refs" / "research" / "scan" / "report.generated.md").write_text(
                "no\n",
                encoding="utf-8",
            )
            (source / "_paperops" / "refs" / "research" / "scan" / "raw-findings.json").write_text(
                "no\n",
                encoding="utf-8",
            )

            plan = copy_scaffold(source, target, overwrite=False)

            self.assertTrue((target / "_handoff" / ".gitkeep").is_file())
            self.assertTrue((target / "_handoff" / "README.md").is_file())
            self.assertTrue((target / "_paperops" / "notes" / "source-reach.md").is_file())
            self.assertFalse((target / ".paperops").exists())
            self.assertFalse((target / ".tools").exists())
            self.assertFalse((target / "scripts" / "__pycache__").exists())
            self.assertFalse((target / "scripts" / "check.pyc").exists())
            self.assertFalse((target / "submission" / "agu" / "build").exists())
            self.assertFalse((target / "submission" / "agu" / ".tools").exists())
            self.assertFalse((target / "tex-env.toml").exists())
            self.assertFalse((target / "_paperops" / "refs" / "papers").exists())
            self.assertFalse((target / "_paperops" / "refs" / "research" / "scan" / "results").exists())
            self.assertFalse((target / "_paperops" / "refs" / "research" / "scan" / "report.generated.md").exists())
            self.assertFalse((target / "_paperops" / "refs" / "research" / "scan" / "raw-findings.json").exists())
            self.assertFalse((target / "_handoff" / "secret.txt").exists())
            self.assertFalse((target / "_paperops" / "refs" / "source-reach" / "topic" / "raw").exists())
            self.assertFalse(
                (target / "_paperops" / "refs" / "source-reach" / "topic" / "doctor.generated.json").exists()
            )
            self.assertFalse(
                (target / "_paperops" / "refs" / "source-reach" / "topic" / "capture.generated.json").exists()
            )
            self.assertFalse((target / "harness-feedback").exists())
            self.assertFalse((target / "harness-lab").exists())
            self.assertFalse((target / ".harness").exists())
            self.assertFalse((target / ".harnessops" / "lock.json").exists())
            self.assertTrue((target / "_archives" / "AGENTS.md").is_file())
            self.assertTrue((target / "_archives" / "README.md").is_file())
            self.assertFalse((target / "_archives" / "old").exists())
            self.assertIn("_handoff/secret.txt", plan.excluded)
            self.assertIn("_paperops/refs/source-reach/topic/raw", plan.excluded)
            self.assertIn("_paperops/refs/source-reach/topic/raw/cookie.txt", plan.excluded)
            self.assertIn("harness-feedback", plan.excluded)
            self.assertIn("harness-feedback/records/feedback.md", plan.excluded)
            self.assertIn("harness-lab", plan.excluded)
            self.assertIn(".harness/state.json", plan.excluded)
            self.assertIn(".harnessops/lock.json", plan.excluded)
            self.assertIn("_archives/old", plan.excluded)
            self.assertIn(".paperops/cache/context.generated.md", plan.excluded)
            self.assertIn(".tools/tex/bin", plan.excluded)
            self.assertIn("scripts/__pycache__/check.cpython-311.pyc", plan.excluded)
            self.assertIn("scripts/check.pyc", plan.excluded)
            self.assertIn("submission/agu/build/main.pdf", plan.excluded)
            self.assertIn("submission/agu/.tools/local.txt", plan.excluded)
            self.assertIn("tex-env.toml", plan.excluded)
            self.assertIn("_paperops/refs/papers/paper.pdf", plan.excluded)
            self.assertIn("_paperops/refs/research/scan/results/raw.json", plan.excluded)
            self.assertIn("_paperops/refs/research/scan/report.generated.md", plan.excluded)
            self.assertIn("_paperops/refs/research/scan/raw-findings.json", plan.excluded)

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

    def test_migrate_list_and_show_registered_internal_layout_migration(self) -> None:
        code, out, err = run_cli(["migrate", "list"])

        self.assertEqual(code, 0, err)
        self.assertIn("M0-0001", out)
        self.assertIn("M0-0002", out)
        self.assertIn("_paperops", out)

        code, out, err = run_cli(["migrate", "show", "M0-0001"])

        self.assertEqual(code, 0, err)
        self.assertIn("Move legacy top-level paperops state into _paperops", out)
        self.assertIn("v0 checkpoint", out)
        self.assertIn("notes/ -> _paperops/notes/", out)

        code, out, err = run_cli(["migrate", "show", "M0-0002"])

        self.assertEqual(code, 0, err)
        self.assertIn("Split managed defaults from project overlays", out)
        self.assertIn("_paperops/defaults", out)
        self.assertIn("No files are deleted or moved", out)

    def test_migrate_defaults_split_is_guided_and_does_not_move_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper-demo"
            run_cli(["init", str(project)])
            overlay = project / "_paperops" / "contracts" / "results.yml"
            overlay.parent.mkdir(parents=True, exist_ok=True)
            overlay.write_text("project: overlay\n", encoding="utf-8")

            code, out, err = run_cli(["migrate", "apply", "M0-0002", str(project)])

            self.assertEqual(code, 0, err)
            self.assertIn("No file moves are planned.", out)
            self.assertIn("Applied migration M0-0002", out)
            self.assertTrue(overlay.is_file())
            self.assertEqual("project: overlay\n", overlay.read_text(encoding="utf-8"))

    def test_migrate_lists_typed_results_hierarchy_guide(self) -> None:
        code, out, err = run_cli(["migrate", "list"])

        self.assertEqual(code, 0, err)
        self.assertIn("M0-0003", out)

        code, out, err = run_cli(["migrate", "show", "M0-0003"])

        self.assertEqual(code, 0, err)
        self.assertIn("results-hierarchy.yml", out)
        self.assertIn("legacy", out.lower())

    def test_typed_results_hierarchy_guide_requires_strict_check_before_legacy_delete(self) -> None:
        guide = (ROOT / "docs" / "migrations" / "v0.md").read_text(encoding="utf-8")
        m0_0003_guide = guide.split("## M0-0003:", 1)[1]
        strict_command = "python scripts/check-section-contracts.py --root . --strict"
        delete_step = "strict checker 成功後にだけ、旧 Markdown の Results hierarchy を削除する。"

        self.assertIn(strict_command, m0_0003_guide)
        self.assertIn(delete_step, m0_0003_guide)
        self.assertLess(m0_0003_guide.index(strict_command), m0_0003_guide.index(delete_step))
        self.assertNotIn(
            "`make section-contract-check` を実行し、strict checker",
            m0_0003_guide,
        )

    def test_migrate_lists_editorial_model_schema_kernel_guide(self) -> None:
        code, out, err = run_cli(["migrate", "list"])

        self.assertEqual(code, 0, err)
        self.assertIn("M0-0004", out)
        self.assertIn("Editorial Model", out)

        code, out, err = run_cli(["migrate", "show", "M0-0004"])

        self.assertEqual(code, 0, err)
        self.assertIn("Editorial Model", out)
        self.assertIn("schema-check", out)
        self.assertIn("project-owned", out)

        strict = "strict schema/reference/semantics"
        canonical_hash = "canonical semantic-v1 hash"
        human_approval = "human approval"
        authority_switch = "authority switch"
        legacy_retention = "legacy controlled view"
        for required in [strict, canonical_hash, human_approval, authority_switch, legacy_retention]:
            self.assertIn(required, out)
        self.assertLess(out.index(strict), out.index(canonical_hash))
        self.assertLess(out.index(canonical_hash), out.index(human_approval))
        self.assertLess(out.index(human_approval), out.index(authority_switch))
        self.assertLess(out.index(authority_switch), out.index(legacy_retention))

    def test_editorial_model_schema_kernel_migration_is_guide_only(self) -> None:
        migration = get_migration("M0-0004")

        self.assertIsNotNone(migration)
        assert migration is not None
        self.assertEqual(migration.moves, ())

        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper-demo"
            run_cli(["init", str(project)])
            editorial_model = project / "_paperops" / "model" / "editorial" / "editorial-model.yml"
            editorial_model.unlink()

            code, out, err = run_cli(["migrate", "apply", "M0-0004", str(project)])

            self.assertEqual(code, 0, err)
            self.assertIn("No file moves are planned.", out)
            self.assertIn("Applied migration M0-0004", out)
            self.assertFalse(editorial_model.exists())
            manifest_path = project / ".pops" / "manifest.toml"
            self.assertTrue(manifest_path.is_file())
            manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
            migrations = manifest.get("migrations", {})
            self.assertIn("M0-0004", migrations.get("applied", []))
            self.assertEqual(applied_migrations(project), ("M0-0004",))

    def test_migration_dry_run_does_not_change_or_record_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper-demo"
            run_cli(["init", str(project)])
            manifest_path = project / ".pops" / "manifest.toml"
            before = manifest_path.read_bytes()

            code, _out, err = run_cli(
                ["migrate", "apply", "M0-0004", "--dry-run", str(project)]
            )

            self.assertEqual(code, 0, err)
            self.assertEqual(manifest_path.read_bytes(), before)
            self.assertNotIn("M0-0004", applied_migrations(project))

    def test_migration_repeat_apply_is_byte_identical_noop(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper-demo"
            run_cli(["init", str(project)])
            manifest_path = project / ".pops" / "manifest.toml"

            code, _out, err = run_cli(["migrate", "apply", "M0-0004", str(project)])
            self.assertEqual(code, 0, err)
            after_first = manifest_path.read_bytes()

            code, out, err = run_cli(["migrate", "apply", "M0-0004", str(project)])

            self.assertEqual(code, 0, err)
            self.assertIn("already applied", out.lower())
            self.assertEqual(manifest_path.read_bytes(), after_first)
            self.assertEqual(applied_migrations(project), ("M0-0004",))

    def test_migration_record_preserves_existing_manifest_sections_and_sorts_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "paper-demo"
            run_cli(["init", str(project)])
            manifest_path = project / ".pops" / "manifest.toml"
            with manifest_path.open("a", encoding="utf-8") as handle:
                handle.write('\n[project_extension]\nowner = "authors"\n')

            for migration_id in ["M0-0004", "M0-0002", "M0-0003"]:
                code, _out, err = run_cli(
                    ["migrate", "apply", migration_id, str(project)]
                )
                self.assertEqual(code, 0, err)

            parsed = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(
                parsed.get("migrations", {}).get("applied"),
                ["M0-0002", "M0-0003", "M0-0004"],
            )
            self.assertEqual(parsed["project_extension"]["owner"], "authors")

    def test_editorial_model_migration_checks_strictly_before_authority_switch(self) -> None:
        guide = (ROOT / "docs" / "migrations" / "v0.md").read_text(encoding="utf-8")
        m0_0004_guide = guide.split("## M0-0004:", 1)[1]
        strict_command = "python scripts/check-paperops-models.py --root . --model editorial --strict"
        authority_switch = "Editorial Model へ authority を切り替える"
        legacy_retention = "legacy controlled view を維持する"

        self.assertIn(strict_command, m0_0004_guide)
        self.assertIn(authority_switch, m0_0004_guide)
        self.assertIn(legacy_retention, m0_0004_guide)
        self.assertLess(m0_0004_guide.index(strict_command), m0_0004_guide.index(authority_switch))
        self.assertLess(m0_0004_guide.index(strict_command), m0_0004_guide.index(legacy_retention))

    def test_migrate_legacy_apply_still_writes_manifest_without_moving_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            before_path_project = Path(tmp) / "before-path"
            before_path_project.mkdir()
            create_legacy_internal_layout(before_path_project)

            code, out, err = run_cli(["migrate", "--apply", str(before_path_project)])

            self.assertEqual(code, 0, err)
            self.assertIn("Created .pops/manifest.toml", out)
            self.assertTrue((before_path_project / ".pops" / "manifest.toml").is_file())
            self.assertTrue((before_path_project / "notes" / "legacy.md").is_file())

            after_path_project = Path(tmp) / "after-path"
            after_path_project.mkdir()
            create_legacy_internal_layout(after_path_project)

            code, out, err = run_cli(["migrate", str(after_path_project), "--apply"])

            self.assertEqual(code, 0, err)
            self.assertIn("Created .pops/manifest.toml", out)
            self.assertTrue((after_path_project / ".pops" / "manifest.toml").is_file())
            self.assertTrue((after_path_project / "notes" / "legacy.md").is_file())

    def test_migrate_internal_layout_dry_run_reports_moves_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "legacy-paper"
            project.mkdir()
            create_legacy_internal_layout(project)

            code, out, err = run_cli(["migrate", "apply", "M0-0001", "--dry-run", str(project)])

            self.assertEqual(code, 0, err)
            self.assertIn("DRY-RUN", out)
            self.assertIn("notes/ -> _paperops/notes/", out)
            self.assertTrue((project / "notes" / "legacy.md").is_file())
            self.assertFalse((project / "_paperops").exists())

    def test_migrate_internal_layout_apply_moves_legacy_dirs_and_writes_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "legacy-paper"
            project.mkdir()
            create_legacy_internal_layout(project)

            code, out, err = run_cli(["migrate", "apply", "M0-0001", str(project)])

            self.assertEqual(code, 0, err)
            self.assertIn("Applied migration M0-0001", out)
            self.assertTrue((project / "_paperops" / "notes" / "legacy.md").is_file())
            self.assertTrue((project / "_paperops" / "refs" / "legacy.md").is_file())
            self.assertFalse((project / "notes").exists())
            self.assertFalse((project / "refs").exists())
            self.assertTrue((project / ".pops" / "manifest.toml").is_file())
            self.assertEqual(applied_migrations(project), ("M0-0001",))

    def test_migrate_internal_layout_stops_on_conflict_without_deleting_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "legacy-paper"
            project.mkdir()
            create_legacy_internal_layout(project)
            (project / "_paperops" / "notes").mkdir(parents=True)
            (project / "_paperops" / "notes" / "modern.md").write_text("# modern\n", encoding="utf-8")

            code, out, err = run_cli(["migrate", "apply", "M0-0001", str(project)])

            self.assertEqual(code, 1)
            self.assertIn("conflict", out + err)
            self.assertTrue((project / "notes" / "legacy.md").is_file())
            self.assertTrue((project / "_paperops" / "notes" / "modern.md").is_file())
            self.assertNotIn("M0-0001", applied_migrations(project))

    def test_doctor_rejects_invalid_link_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "_paperops" / "refs" / "links.toml").write_text("not = [valid", encoding="utf-8")

            code, out, _err = run_cli(["doctor", str(target)])

            self.assertEqual(code, 1)
            self.assertIn("refs/links.toml", out)
            self.assertIn("TOML", out)
            self.assertIn("doctor: failed", out)

    def test_doctor_warns_when_link_alias_is_not_in_local_locations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "_paperops" / "refs" / "local" / "locations.toml").write_text(
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
            (target / "_paperops" / "defaults" / "contracts" / "results.yml").unlink()

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "_paperops/defaults/contracts/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("+ _paperops/defaults/contracts/results.yml [section contract]", out)

            code, _out, err = run_cli(
                ["update-paperops", "--apply", "--only", "_paperops/defaults/contracts/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "_paperops" / "defaults" / "contracts" / "results.yml").is_file())

    def test_update_paperops_can_add_missing_workflow_kernel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            (target / "_paperops" / "defaults" / "workflow" / "machine.yml").unlink()

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "_paperops/defaults/workflow/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("+ _paperops/defaults/workflow/machine.yml [workflow state machine]", out)

            code, _out, err = run_cli(
                ["update-paperops", "--apply", "--only", "_paperops/defaults/workflow/", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertTrue((target / "_paperops" / "defaults" / "workflow" / "machine.yml").is_file())

    def test_update_paperops_can_add_managed_schema_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            schema = target / "_paperops" / "defaults" / "schemas" / "results-hierarchy.schema.json"
            schema.unlink()

            code, out, err = run_cli(
                [
                    "update-paperops",
                    "--dry-run",
                    "--only",
                    "_paperops/defaults/schemas/",
                    str(target),
                ]
            )

            self.assertEqual(code, 0, err)
            self.assertIn(
                "+ _paperops/defaults/schemas/results-hierarchy.schema.json [schema]",
                out,
            )

            code, _out, err = run_cli(
                [
                    "update-paperops",
                    "--apply",
                    "--only",
                    "_paperops/defaults/schemas/",
                    str(target),
                ]
            )

            self.assertEqual(code, 0, err)
            self.assertTrue(schema.is_file())

    def test_update_manages_schema_registry_and_checker_but_not_editorial_state(self) -> None:
        managed = [
            "_paperops/defaults/schemas/registry.yml",
            "_paperops/defaults/schemas/editorial-model.schema.json",
            "scripts/paperops_schema.py",
            "scripts/paperops_editorial.py",
            "scripts/paperops_models.py",
            "scripts/check-paperops-models.py",
        ]
        project_owned = "_paperops/model/editorial/editorial-model.yml"
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)
            for rel in [*managed, project_owned]:
                (target / rel).unlink()

            code, out, err = run_cli(["update-paperops", "--dry-run", str(target)])

            self.assertEqual(code, 0, err)
            for rel in managed:
                self.assertIn(f"+ {rel}", out)
            self.assertNotIn(project_owned, out)

            code, _out, err = run_cli(["update-paperops", "--apply", str(target)])

            self.assertEqual(code, 0, err)
            for rel in managed:
                self.assertTrue((target / rel).is_file(), rel)
            self.assertFalse((target / project_owned).exists())

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

    def test_update_paperops_apply_stops_before_manifest_advance_when_changed_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            set_scaffold_version(target, "0.1.0")
            missing_contract = target / "_paperops" / "defaults" / "contracts" / "results.yml"
            missing_contract.unlink()
            agents = target / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8") + "\nlocal fork without detach\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(
                [
                    "update-paperops",
                    "--apply",
                    "--only",
                    "AGENTS.md,_paperops/defaults/contracts/",
                    str(target),
                ]
            )

            self.assertEqual(code, 1)
            self.assertIn("changed managed files block this update", out + err)
            self.assertIn("--force", out + err)
            self.assertFalse(missing_contract.exists())
            manifest = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["scaffold"]["version"], "0.1.0")

    def test_detach_marks_managed_file_and_update_skips_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            agents = target / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8") + "\nproject-specific fork\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(
                ["detach", "AGENTS.md", str(target), "--reason", "project voice"]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("Detached managed file: AGENTS.md", out)
            manifest = (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            self.assertIn("[detached]", manifest)
            self.assertIn('paths = ["AGENTS.md"]', manifest)
            self.assertIn("[detached.reasons]", manifest)
            self.assertIn('"AGENTS.md" = "project voice"', manifest)

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "AGENTS.md", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("detached managed files: 1", out)
            self.assertIn("~ AGENTS.md [detached fork]", out)
            self.assertIn("changed managed files: 0", out)

    def test_detach_list_reports_registered_forks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            run_cli(["detach", "AGENTS.md", str(target), "--reason", "project voice"])

            code, out, err = run_cli(["detach", "list", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("Detached managed files:", out)
            self.assertIn("AGENTS.md", out)
            self.assertIn("project voice", out)

    def test_detach_rejects_project_owned_extension_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])

            code, out, err = run_cli(
                ["detach", "AGENTS.project.md", str(target), "--reason", "not managed"]
            )

            self.assertEqual(code, 2)
            self.assertIn("not a managed paperops file", err)
            self.assertEqual("", out)

    def test_reattach_removes_detached_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            agents = target / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8") + "\nproject-specific fork\n",
                encoding="utf-8",
            )
            run_cli(["detach", "AGENTS.md", str(target), "--reason", "project voice"])

            code, out, err = run_cli(["reattach", "AGENTS.md", str(target)])

            self.assertEqual(code, 0, err)
            self.assertIn("Reattached managed file: AGENTS.md", out)
            manifest = (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            self.assertNotIn('paths = ["AGENTS.md"]', manifest)
            self.assertNotIn('"AGENTS.md" = "project voice"', manifest)

            code, out, err = run_cli(
                ["update-paperops", "--dry-run", "--only", "AGENTS.md", str(target)]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("detached managed files: 0", out)
            self.assertIn("changed managed files: 1", out)
            self.assertIn("! AGENTS.md [agent guidance]", out)

    def test_project_extension_skills_are_not_managed_update_paths(self) -> None:
        self.assertFalse(is_managed_update("AGENTS.project.md"))
        self.assertFalse(is_managed_update("CLAUDE.project.md"))
        self.assertFalse(is_managed_update("Makefile.project"))
        self.assertFalse(is_managed_update("Makefile.local"))
        self.assertFalse(is_managed_update(".agents/skills/project-custom/SKILL.md"))
        self.assertFalse(is_managed_update(".claude/skills/project-custom/SKILL.md"))
        self.assertTrue(is_managed_update(".agents/skills/update-paperops/SKILL.md"))
        self.assertTrue(is_managed_update(".claude/skills/update-paperops/SKILL.md"))

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

    def test_upgrade_step_does_not_advance_manifest_when_changed_files_block_apply(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            run_cli(["init", str(target)])
            set_scaffold_version(target, "0.1.0")
            agents = target / "AGENTS.md"
            agents.write_text(
                agents.read_text(encoding="utf-8") + "\nlocal fork without detach\n",
                encoding="utf-8",
            )

            code, out, err = run_cli(
                [
                    "update-paperops",
                    "--upgrade-step",
                    "--from-version",
                    "0.1.0",
                    "--to-version",
                    __version__,
                    "--apply",
                    str(target),
                ]
            )

            self.assertEqual(code, 1)
            self.assertIn("changed managed files", out + err)
            self.assertIn("--force", out + err)
            manifest = tomllib.loads(
                (target / ".pops" / "manifest.toml").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["scaffold"]["version"], "0.1.0")

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
