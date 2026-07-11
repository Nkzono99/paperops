from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from paperops.model_migration.staging import (
    StagingError,
    new_transaction_id,
    snapshot_paths,
    transaction_paths,
    verify_snapshot,
    write_report,
)
from paperops.model_migration.types import (
    CandidateDocument,
    InventoryItem,
    MigrationFinding,
    MigrationReport,
)


class ModelMigrationStagingTest(unittest.TestCase):
    def test_transaction_id_is_deterministic_path_safe_and_utc(self) -> None:
        transaction_id = new_transaction_id(
            datetime(2026, 7, 11, 3, 4, 5, 123456, tzinfo=timezone.utc),
            b"fixed entropy",
        )
        self.assertEqual(
            transaction_id,
            "model-20260711T030405123456Z-4f6dcc2a5ebb",
        )
        self.assertNotIn("/", transaction_id)

    def test_transaction_paths_reject_traversal_and_windows_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for unsafe in ("../escape", "a/b", r"C:\\escape", "", "."):
                with self.subTest(unsafe=unsafe):
                    with self.assertRaises(StagingError) as raised:
                        transaction_paths(root, unsafe)
                    self.assertEqual(raised.exception.code, "transaction.path")

    def test_transaction_paths_are_confined_to_ignored_paperops_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = transaction_paths(root, "model-20260711T030405Z-abcdef123456")
            self.assertEqual(paths.candidate_dir, root / ".paperops/migrations/model-20260711T030405Z-abcdef123456/candidate")
            self.assertEqual(paths.snapshot_dir, root / ".paperops/snapshots/model-20260711T030405Z-abcdef123456")
            self.assertFalse(paths.migration_dir.exists())

    def test_report_json_is_deterministic_and_markdown_is_only_a_projection(self) -> None:
        report = self.report()
        with tempfile.TemporaryDirectory() as left_tmp, tempfile.TemporaryDirectory() as right_tmp:
            left = transaction_paths(Path(left_tmp), report.transaction_id)
            right = transaction_paths(Path(right_tmp), report.transaction_id)
            write_report(left, report)
            write_report(right, report)
            left_json = left.report_json_path.read_bytes()
            self.assertEqual(left_json, right.report_json_path.read_bytes())
            self.assertTrue(left_json.endswith(b"\n"))
            payload = json.loads(left_json)
            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(payload["inventory"][0]["disposition"], "mapped")
            self.assertIn("# Model migration report", left.report_markdown_path.read_text())
            self.assertNotEqual(
                left.report_markdown_path.read_text(),
                left.report_json_path.read_text(),
            )

    def test_report_redacts_credentials_private_values_and_absolute_locations(self) -> None:
        report = self.report(
            finding=MigrationFinding(
                code="migration.confidential",
                pointer="/token",
                message="read /private/work/raw.txt with https://alice:secret@example.test/x?token=abc",
                severity="warning",
                source_path="_paperops/review/round.md",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = transaction_paths(Path(tmp), report.transaction_id)
            write_report(paths, report)
            rendered = paths.report_json_path.read_text()
        self.assertNotIn("/private/work/raw.txt", rendered)
        self.assertNotIn("secret", rendered)
        self.assertNotIn("token=abc", rendered)
        self.assertIn("[redacted]", rendered)

    def test_report_rejects_non_relative_source_and_candidate_paths(self) -> None:
        for report in (
            self.report(source_path="../source.md"),
            self.report(candidate_path=r"C:\\candidate.yml"),
        ):
            with self.subTest(report=report):
                with tempfile.TemporaryDirectory() as tmp:
                    paths = transaction_paths(Path(tmp), report.transaction_id)
                    with self.assertRaises(StagingError) as raised:
                        write_report(paths, report)
                    self.assertEqual(raised.exception.code, "transaction.path")

    def test_snapshot_preserves_bytes_modes_and_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "_paperops/model/research/index.yml"
            source.parent.mkdir(parents=True)
            source.write_bytes(b"schema_version: 1\n")
            source.chmod(0o640)
            manifest_path = snapshot_paths(
                root,
                "model-20260711T030405Z-abcdef123456",
                (Path("_paperops/model/research"),),
            )
            payload = json.loads(manifest_path.read_text())
            entry = payload["files"][0]
            copied = manifest_path.parent / entry["path"]
            self.assertEqual(copied.read_bytes(), source.read_bytes())
            self.assertEqual(entry["mode"], "0640")
            self.assertEqual(entry["size"], len(source.read_bytes()))
            self.assertRegex(entry["sha256"], r"^sha256:[0-9a-f]{64}$")
            self.assertEqual(verify_snapshot(root, payload["transaction_id"]), ())

    def test_snapshot_rejects_escape_symlink_and_special_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            outside = root.parent / "paperops-staging-outside"
            outside.write_text("outside")
            outside_dir = root.parent / "paperops-staging-outside-dir"
            outside_dir.mkdir()
            (outside_dir / "secret").write_text("outside")
            (root / "link").symlink_to(outside)
            (root / "link-dir").symlink_to(outside_dir, target_is_directory=True)
            os.mkfifo(root / "fifo")
            try:
                for relative, code in (
                    (Path("../escape"), "transaction.path"),
                    (Path("link"), "transaction.symlink"),
                    (Path("link-dir/secret"), "transaction.symlink"),
                    (Path("fifo"), "transaction.special_file"),
                ):
                    with self.subTest(relative=relative):
                        with self.assertRaises(StagingError) as raised:
                            snapshot_paths(
                                root,
                                "model-20260711T030405Z-abcdef123456",
                                (relative,),
                            )
                        self.assertEqual(raised.exception.code, code)
            finally:
                outside.unlink(missing_ok=True)
                (outside_dir / "secret").unlink(missing_ok=True)
                outside_dir.rmdir()

    def test_snapshot_rejects_symlinked_paperops_state_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as state_tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("source")
            (root / ".paperops").symlink_to(Path(state_tmp), target_is_directory=True)
            with self.assertRaises(StagingError) as raised:
                snapshot_paths(
                    root,
                    "model-20260711T030405Z-abcdef123456",
                    (Path("source.txt"),),
                )
            self.assertEqual(raised.exception.code, "transaction.symlink")
            paths = transaction_paths(
                root, "model-20260711T030405Z-abcdef123456"
            )
            with self.assertRaises(StagingError) as raised:
                write_report(paths, self.report())
            self.assertEqual(raised.exception.code, "transaction.symlink")

    def test_verify_snapshot_reports_hash_and_manifest_path_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / ".pops/manifest.toml"
            source.parent.mkdir()
            source.write_text("version = 1\n")
            transaction_id = "model-20260711T030405Z-abcdef123456"
            manifest_path = snapshot_paths(root, transaction_id, (Path(".pops/manifest.toml"),))
            copied = manifest_path.parent / ".pops/manifest.toml"
            copied.write_text("tampered\n")
            findings = verify_snapshot(root, transaction_id)
            self.assertEqual(findings[0].code, "transaction.snapshot_hash")

            payload = json.loads(manifest_path.read_text())
            payload["files"][0]["path"] = "../escape"
            manifest_path.write_text(json.dumps(payload))
            findings = verify_snapshot(root, transaction_id)
            self.assertEqual(findings[0].code, "transaction.snapshot_manifest")

    def test_verify_snapshot_rejects_symlinked_state_even_when_contents_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as state_tmp:
            root = Path(tmp)
            source = root / "source.txt"
            source.write_text("source")
            transaction_id = "model-20260711T030405Z-abcdef123456"
            snapshot_paths(root, transaction_id, (Path("source.txt"),))
            shutil.copytree(root / ".paperops", Path(state_tmp) / ".paperops")
            (root / ".paperops").rename(root / ".paperops-original")
            (root / ".paperops").symlink_to(
                Path(state_tmp) / ".paperops", target_is_directory=True
            )
            findings = verify_snapshot(root, transaction_id)
            self.assertEqual(findings[0].code, "transaction.snapshot_manifest")

    @staticmethod
    def report(
        *,
        finding: MigrationFinding | None = None,
        source_path: str = "_paperops/claims/claims/CLM-0001.md",
        candidate_path: str = "_paperops/model/research/claims/CLM-0001.yml",
    ) -> MigrationReport:
        return MigrationReport(
            schema_version=1,
            transaction_id="model-20260711T030405Z-abcdef123456",
            model_name="research",
            adapter_version=1,
            inventory=(
                InventoryItem(
                    family="claim.scope",
                    legacy_id="CLM-0001",
                    source_path=source_path,
                    pointer="/scope",
                    source_hash="sha256:" + "1" * 64,
                    disposition="mapped",
                    target_id="CLM-0001",
                ),
            ),
            candidates=(
                CandidateDocument(
                    relative_path=candidate_path,
                    object_id="CLM-0001",
                    semantic_hash="sha256:" + "2" * 64,
                ),
            ),
            findings=(finding,) if finding else (),
        )


if __name__ == "__main__":
    unittest.main()
