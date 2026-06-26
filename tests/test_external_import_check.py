from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-external-imports.py"


def write_minimal_links(root: Path) -> None:
    (root / "_paperops" / "refs" / "local").mkdir(parents=True, exist_ok=True)
    (root / "_paperops" / "refs" / "imports").mkdir(parents=True, exist_ok=True)
    (root / "_paperops" / "refs" / "links.toml").write_text(
        textwrap.dedent(
            """\
            schema_version = 1

            [[links]]
            id = "runops-main"
            kind = "runops_project"
            location_ref = "runops_main"
            description = "External analysis project"
            paper_roles = ["results"]
            access = "read"
            """
        ),
        encoding="utf-8",
    )


def run_check(root: Path, *extra: str):
    return run_python_script(SCRIPT, "--root", root, *extra)


class ExternalImportCheckTest(unittest.TestCase):
    def test_template_has_no_concrete_import_records_by_default(self) -> None:
        result = run_check(ROOT / "template")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("external-import-check", result.stdout)
        self.assertIn("記録済み import state はありません", result.stdout)

    def test_tracked_export_without_index_integrity_or_claim_policy_warns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            (root / "_paperops" / "refs" / "imports").mkdir(parents=True, exist_ok=True)
            record = root / "_paperops" / "refs" / "imports" / "runops-main.toml"
            record.write_text(
                textwrap.dedent(
                    """\
                    schema_version = 1
                    id = "IMP-0001"
                    link_id = "runops-main"
                    state = "tracked_indexed_export"
                    bundle_label = "dust_release"

                    [source]
                    commit = "abc123"
                    dirty = false
                    """
                ),
                encoding="utf-8",
            )

            result = run_check(root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("source_index.path", result.stdout)
        self.assertIn("integrity_manifest.path", result.stdout)
        self.assertIn("claim_evidence_policy", result.stdout)
        self.assertIn("must_not_claim", result.stdout)

    def test_live_source_index_count_drift_is_warning_and_strict_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            export = Path(tmp) / "analysis-project" / "exports" / "paper"
            export.mkdir(parents=True)
            (root / "_paperops" / "refs" / "imports").mkdir(parents=True, exist_ok=True)
            (root / "_paperops" / "refs" / "local" / "locations.toml").write_text(
                textwrap.dedent(
                    f"""\
                    [paths.runops_main]
                    kind = "runops_project"
                    host = "local"
                    path = "{export.parent.parent.as_posix()}"
                    """
                ),
                encoding="utf-8",
            )
            (export / "paper_bundle_source_index.csv").write_text(
                "artifact,source_exists\nfig-a,true\nfig-b,true\n",
                encoding="utf-8",
            )
            (export / "paper_bundle_integrity_manifest_context.csv").write_text(
                "artifact,sha256\nfig-a,aaa\nfig-b,bbb\n",
                encoding="utf-8",
            )
            (root / "_paperops" / "refs" / "imports" / "runops-main.toml").write_text(
                textwrap.dedent(
                    """\
                    schema_version = 1
                    id = "IMP-0002"
                    link_id = "runops-main"
                    state = "tracked_indexed_export"
                    bundle_label = "paper"
                    artifact_category_summary = "authoring QA"
                    claim_evidence_policy = "authoring-guard"
                    must_not_claim = ["physical evidence"]

                    [source]
                    commit = "abc123"
                    dirty = false

                    [export]
                    path = "exports/paper"

                    [source_index]
                    path = "paper_bundle_source_index.csv"
                    rows = 1
                    source_exists_false = 0

                    [integrity_manifest]
                    path = "paper_bundle_integrity_manifest_context.csv"
                    rows = 2
                    """
                ),
                encoding="utf-8",
            )

            advisory = run_check(root)
            strict = run_check(root, "--strict")

        self.assertEqual(advisory.returncode, 0, advisory.stdout + advisory.stderr)
        self.assertIn("source index rows drift", advisory.stdout)
        self.assertEqual(strict.returncode, 1)

    def test_unknown_link_id_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-demo"
            write_minimal_links(root)
            (root / "_paperops" / "refs" / "imports" / "unknown.toml").write_text(
                textwrap.dedent(
                    """\
                    schema_version = 1
                    id = "IMP-0003"
                    link_id = "missing-link"
                    state = "script_only_candidate"
                    artifact_category_summary = "candidate"
                    claim_evidence_policy = "needs-triage"
                    must_not_claim = ["supported evidence"]
                    """
                ),
                encoding="utf-8",
            )

            result = run_check(root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("missing-link", result.stdout)
        self.assertIn("refs/links.toml", result.stdout)


if __name__ == "__main__":
    unittest.main()
