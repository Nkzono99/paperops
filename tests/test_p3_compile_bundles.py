from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from tests.helpers import ROOT

import sys

sys.path.insert(0, str(ROOT / "src"))

from paperops.compiler.bundles import (  # noqa: E402
    BundleVerificationError,
    load_verified_bundle,
    prepare_bundle,
)
from paperops.compiler.compare import _projection, compare_bundles  # noqa: E402
from tests.test_p3_compile_inputs import tracked_tree_snapshot  # noqa: E402
from tests.test_p3_compile_materialize import (  # noqa: E402
    approved_project,
    approved_request,
)


class P3CompileBundlePersistenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = approved_project(Path(cls._tmp.name))
        cls.request = approved_request()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        compile_root = self.project / ".paperops/compile"
        if compile_root.exists():
            import shutil

            shutil.rmtree(compile_root)

    def test_repeat_reuses_verified_byte_identical_bundle_without_tracked_writes(self) -> None:
        before = tracked_tree_snapshot(self.project)
        first = prepare_bundle(self.project, self.request)
        self.assertTrue(first.ok, first.findings)
        bundle_dir = self.project / ".paperops/compile" / first.compile_id
        first_bytes = {
            path.relative_to(bundle_dir).as_posix(): path.read_bytes()
            for path in sorted(bundle_dir.rglob("*"))
            if path.is_file()
        }

        second = prepare_bundle(self.project, self.request)
        refreshed = prepare_bundle(self.project, self.request, refresh=True)

        self.assertTrue(second.reused)
        self.assertTrue(refreshed.refreshed)
        self.assertEqual(first.compile_id, second.compile_id)
        self.assertEqual(first.to_dict()["artifacts"], second.to_dict()["artifacts"])
        self.assertEqual(
            first_bytes,
            {
                path.relative_to(bundle_dir).as_posix(): path.read_bytes()
                for path in sorted(bundle_dir.rglob("*"))
                if path.is_file()
            },
        )
        self.assertEqual(before, tracked_tree_snapshot(self.project))

    def test_loader_rejects_missing_extra_symlink_and_hash_corruption(self) -> None:
        result = prepare_bundle(self.project, self.request)
        self.assertTrue(result.ok, result.findings)
        bundle_dir = self.project / ".paperops/compile" / result.compile_id
        packet = next((bundle_dir / "packets").glob("*.json"))
        original = packet.read_bytes()

        packet.write_bytes(original + b" ")
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, result.compile_id)
        packet.write_bytes(original)
        extra = bundle_dir / "extra.json"
        extra.write_text("{}\n", encoding="utf-8")
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, result.compile_id)
        extra.unlink()
        extra_directory = bundle_dir / "unexpected"
        extra_directory.mkdir()
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, result.compile_id)
        extra_directory.rmdir()
        packet.unlink()
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, result.compile_id)
        packet.write_bytes(original)
        packet.unlink()
        packet.symlink_to(bundle_dir / "bundle.json")
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, result.compile_id)

    def test_generated_state_namespace_cannot_be_a_symlink(self) -> None:
        state = self.project / ".paperops/compile"
        with tempfile.TemporaryDirectory() as temporary:
            state.symlink_to(Path(temporary), target_is_directory=True)
            try:
                with self.assertRaises(BundleVerificationError):
                    prepare_bundle(self.project, self.request)
            finally:
                state.unlink()

    def test_compare_is_deterministic_allowlisted_and_does_not_rank(self) -> None:
        result = prepare_bundle(self.project, self.request)
        comparison = compare_bundles(
            self.project,
            result.compile_id,
            result.compile_id,
        )
        payload = comparison.to_dict()
        self.assertEqual(payload["changes"], [])
        self.assertEqual(payload["left_compile_id"], result.compile_id)
        self.assertNotIn("better", json.dumps(payload, sort_keys=True).lower())
        self.assertNotIn(str(self.project), json.dumps(payload, sort_keys=True))

    def test_compare_projection_contains_exact_semantic_allowlist(self) -> None:
        projection = _projection(
            {
                "request": {"targets": ["SEC-0001"], "write_scope": {"level": "section"}},
                "global_context": {
                    "selected_story": {"id": "STY-0001"},
                    "rejected_stories": [{"id": "STY-0002", "rejection_reason": "bounded"}],
                    "ordered_moves": [{"id": "MOV-0001"}],
                    "claim_roles": {"primary": {"claim_ids": ["CLM-0001"]}},
                    "evidence_ladder": ["RHI-0001"],
                    "section_block_map": [{"section_id": "SEC-0001"}],
                    "visual_obligations": [{"id": "VIS-0001"}],
                    "private_raw": "must not be projected",
                },
            }
        )
        self.assertEqual(
            set(projection),
            {
                "selected_story", "rejected_stories", "move_order", "claim_roles",
                "result_order", "section_placement", "visual_obligations", "targets",
                "write_scope",
            },
        )
        self.assertNotIn("private_raw", json.dumps(projection, sort_keys=True))

    def test_blocked_compile_uses_diagnostic_namespace_without_partial_success(self) -> None:
        blocked_request = replace(
            self.request,
            targets=("SEC-9999",),
            write_scope=replace(
                self.request.write_scope,
                section_ids=("SEC-9999",),
                block_ids=(),
                files=(),
            ),
        )
        result = prepare_bundle(self.project, blocked_request)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, "blocked")
        self.assertFalse(
            (self.project / ".paperops/compile" / result.compile_id).exists()
        )
        diagnostic = self.project / result.diagnostic_path
        self.assertTrue(diagnostic.is_file())
        public = diagnostic.read_text(encoding="utf-8")
        self.assertNotIn(str(self.project), public)
        self.assertNotIn("traceback", public.lower())

    def test_corrupt_existing_requires_refresh_and_refresh_repairs_it(self) -> None:
        result = prepare_bundle(self.project, self.request)
        packet = next(
            (self.project / ".paperops/compile" / result.compile_id / "packets").glob("*.json")
        )
        packet.write_bytes(packet.read_bytes() + b" ")
        with self.assertRaises(BundleVerificationError):
            prepare_bundle(self.project, self.request)
        repaired = prepare_bundle(self.project, self.request, refresh=True)
        self.assertTrue(repaired.ok)
        self.assertTrue(repaired.refreshed)
        load_verified_bundle(self.project, result.compile_id)

    def test_approval_content_change_produces_a_new_compile_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            changed = approved_project(
                Path(temporary),
                approval_note="A distinct current human approval.",
            )
            other = prepare_bundle(changed, self.request)
        baseline = prepare_bundle(self.project, self.request)
        self.assertNotEqual(baseline.compile_id, other.compile_id)

    def test_loader_rejects_invalid_id_and_bundle_dto_tampering(self) -> None:
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, "../private")
        result = prepare_bundle(self.project, self.request)
        bundle_path = self.project / ".paperops/compile" / result.compile_id / "bundle.json"
        document = json.loads(bundle_path.read_text(encoding="utf-8"))
        document["bundle"]["unknown"] = "forbidden"
        from paperops.compiler.storage import canonical_json_bytes

        bundle_path.write_bytes(canonical_json_bytes(document))
        with self.assertRaises(BundleVerificationError):
            load_verified_bundle(self.project, result.compile_id)

    def test_failed_publish_cleans_staging_directory(self) -> None:
        import paperops.compiler.bundles as bundles

        real_rename = bundles.os.rename

        def fail_publish(source, destination):
            if Path(destination).parent.name == "compile":
                raise OSError("simulated publish failure")
            return real_rename(source, destination)

        with patch("paperops.compiler.bundles.os.rename", side_effect=fail_publish):
            with self.assertRaises(OSError):
                prepare_bundle(self.project, self.request)
        compile_root = self.project / ".paperops/compile"
        self.assertEqual(list(compile_root.glob(".stage-*")), [])


if __name__ == "__main__":
    unittest.main()
