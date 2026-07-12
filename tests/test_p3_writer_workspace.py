from __future__ import annotations

import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT

import sys

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "template/scripts"))

from paperops.compiler import prepare_bundle  # noqa: E402
from paperops.compiler.requests import resolve_compile_request  # noqa: E402
from paperops.compiler.writer import (  # noqa: E402
    build_patch,
    inspect_writer_session,
    start_writer_session,
)
from paperops.compiler.safe_fs import SafeCaptureError  # noqa: E402
from paperops.compiler.storage import canonical_json_bytes  # noqa: E402
from paperops.compiler.tex import parse_tex_bytes  # noqa: E402
from paperops.compiler.writer import _patch_from_candidate  # noqa: E402
from tests.test_p3_compile_inputs import tracked_tree_snapshot  # noqa: E402
from tests.test_p3_compile_materialize import approved_project  # noqa: E402
from paperops_schema import load_document, validate_schema  # noqa: E402


class P3WriterWorkspaceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = approved_project(Path(cls._tmp.name))
        request = resolve_compile_request(cls.project, "SEC-0002", scope="block", block_ids=("BLK-0002",))
        cls.compile_result = prepare_bundle(cls.project, request)

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        writer = self.project / ".paperops/writer"
        if writer.exists():
            import shutil

            shutil.rmtree(writer)

    def start(self):
        result = start_writer_session(self.project, self.compile_result.compile_id)
        self.assertTrue(result.ok, result.findings)
        return result

    def test_start_copies_complete_manuscript_and_binds_immutable_session(self) -> None:
        before = tracked_tree_snapshot(self.project)
        result = self.start()
        session = self.project / ".paperops/writer" / result.session_id
        workspace = session / "workspace/manuscript"
        self.assertTrue((workspace / "ja/sections/30_results.tex").is_file())
        self.assertTrue((workspace / "en/sections/30_results.tex").is_file())
        self.assertTrue((session / "session.json").is_file())
        self.assertTrue((session / "base-manifest.json").is_file())
        self.assertTrue((session / "transactions").is_dir())
        manifest = json.loads((session / "base-manifest.json").read_text())
        self.assertEqual(
            {item["identity"] for item in manifest["files"]},
            {
                path.relative_to(self.project).as_posix()
                for path in (self.project / "manuscript").rglob("*")
                if path.is_file()
            },
        )
        self.assertEqual(before, tracked_tree_snapshot(self.project))
        self.assertNotIn(str(self.project), json.dumps(result.to_dict(), ensure_ascii=False))
        self.assertNotIn("submission", str(workspace))
        self.assertTrue(inspect_writer_session(self.project, result.session_id).ok)

    def test_selected_block_content_edit_builds_structured_patch_without_tex(self) -> None:
        result = self.start()
        target = (
            self.project
            / ".paperops/writer"
            / result.session_id
            / "workspace/manuscript/en/sections/30_results.tex"
        )
        text = target.read_text(encoding="utf-8")
        target.write_text(
            text.replace(
                "% block: results.traceability.01",
                "% block: results.traceability.01\nA revised bounded result sentence.",
            ),
            encoding="utf-8",
        )
        patch = build_patch(self.project, result.session_id)
        self.assertTrue(patch.ok, patch.findings)
        payload = patch.to_dict()
        self.assertEqual(payload["status"], "ready")
        self.assertEqual(payload["changes"][0]["typed_block_id"], "BLK-0002")
        public = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("A revised bounded result sentence", public)
        self.assertNotIn("\\section", public)
        schema = load_document(
            ROOT / "template/_paperops/defaults/schemas/writer-patch.schema.json"
        )
        self.assertEqual(validate_schema(payload, schema), [])

        first_bytes = (
            self.project / ".paperops/writer" / result.session_id / "patch.json"
        ).read_bytes()
        repeated = build_patch(self.project, result.session_id)
        self.assertEqual(repeated.patch_hash, patch.patch_hash)
        self.assertEqual(
            first_bytes,
            (self.project / ".paperops/writer" / result.session_id / "patch.json").read_bytes(),
        )

    def test_other_block_preamble_and_unplanned_marker_are_blocked_or_replanned(self) -> None:
        result = self.start()
        workspace = self.project / ".paperops/writer" / result.session_id / "workspace/manuscript"
        other = workspace / "en/sections/20_method.tex"
        other.write_text(other.read_text() + "\nOutside scope.\n", encoding="utf-8")
        blocked = build_patch(self.project, result.session_id)
        self.assertEqual(blocked.status, "blocked")
        self.assertTrue(any(item.code == "write.scope_violation" for item in blocked.findings))

        other.write_bytes((self.project / "manuscript/en/sections/20_method.tex").read_bytes())
        target = workspace / "en/sections/30_results.tex"
        target.write_text(target.read_text() + "\n% block: unplanned.new\nText.\n", encoding="utf-8")
        replanned = build_patch(self.project, result.session_id)
        self.assertEqual(replanned.status, "replan_required", replanned.findings)

    def test_living_drift_and_candidate_symlink_block_without_stale_ready_patch(self) -> None:
        result = self.start()
        living = self.project / "manuscript/en/sections/30_results.tex"
        original = living.read_bytes()
        living.write_bytes(original + b"\n% manual drift\n")
        try:
            blocked = build_patch(self.project, result.session_id)
            self.assertEqual(blocked.status, "blocked")
            self.assertTrue(any(item.code == "write.base_drift" for item in blocked.findings))
        finally:
            living.write_bytes(original)

        candidate = (
            self.project
            / ".paperops/writer"
            / result.session_id
            / "workspace/manuscript/en/sections/30_results.tex"
        )
        candidate.unlink()
        candidate.symlink_to("20_method.tex")
        blocked = build_patch(self.project, result.session_id)
        self.assertEqual(blocked.status, "blocked")
        patch_path = self.project / ".paperops/writer" / result.session_id / "patch.json"
        self.assertEqual(json.loads(patch_path.read_text())["status"], "blocked")

    def test_preamble_bibliography_duplicate_marker_and_binary_are_rejected(self) -> None:
        result = self.start()
        workspace = self.project / ".paperops/writer" / result.session_id / "workspace/manuscript"
        target = workspace / "en/sections/30_results.tex"
        original = target.read_bytes()

        target.write_bytes(b"Preamble outside a block.\n" + original)
        self.assertEqual(build_patch(self.project, result.session_id).status, "blocked")
        target.write_bytes(original)

        bibliography = workspace / "shared/bib/references.bib"
        bibliography.write_bytes(bibliography.read_bytes() + b"\n% changed\n")
        self.assertEqual(build_patch(self.project, result.session_id).status, "blocked")
        bibliography.write_bytes(
            (self.project / "manuscript/shared/bib/references.bib").read_bytes()
        )

        target.write_bytes(
            original
            + b"\n% block: results.traceability.01\nDuplicate marker.\n"
        )
        self.assertEqual(build_patch(self.project, result.session_id).status, "blocked")
        target.write_bytes(b"\xff\xfe")
        self.assertEqual(build_patch(self.project, result.session_id).status, "blocked")

    def test_hardlinked_source_and_tampered_session_state_are_rejected(self) -> None:
        source = self.project / "manuscript/en/sections/30_results.tex"
        hardlink = self.project / "manuscript/hardlink.tex"
        hardlink.hardlink_to(source)
        try:
            with self.assertRaises(SafeCaptureError):
                start_writer_session(self.project, self.compile_result.compile_id)
        finally:
            hardlink.unlink()

        result = self.start()
        manifest_path = (
            self.project / ".paperops/writer" / result.session_id / "base-manifest.json"
        )
        manifest = json.loads(manifest_path.read_text())
        manifest["extensions"] = {"x-test-tamper": True}
        manifest_path.write_bytes(canonical_json_bytes(manifest))
        with self.assertRaises(SafeCaptureError):
            inspect_writer_session(self.project, result.session_id)

    def test_model_authorized_add_cut_and_move_are_structured_operations(self) -> None:
        identity = "manuscript/en/sections/30_results.tex"
        hash_value = "sha256:" + "a" * 64

        def state(content: bytes) -> dict[str, object]:
            return {
                "identity": identity,
                "type": "regular",
                "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
                "size": len(content),
                "mode": 0o644,
            }

        cases = (
            (
                "add",
                b"% block: a\nA\n",
                b"% block: a\nA\n% block: b\nB\n",
                "b",
            ),
            (
                "cut",
                b"% block: a\nA\n% block: b\nB\n",
                b"% block: a\nA\n",
                "b",
            ),
            (
                "move",
                b"% block: a\nA\n% block: b\nB\n",
                b"% block: b\nB\n% block: a\nA\n",
                "b",
            ),
        )
        for operation, base_content, candidate_content, raw_id in cases:
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temporary:
                candidate_root = Path(temporary)
                target = candidate_root / identity
                target.parent.mkdir(parents=True)
                target.write_bytes(candidate_content)
                base_state = state(base_content)
                candidate_state = state(candidate_content)
                manifest = {
                    "files": [base_state],
                    "tex_files": [parse_tex_bytes(identity, base_content).to_dict()],
                    "bindings": [
                        {
                            "typed_block_id": "BLK-0002",
                            "raw_block_id": raw_id,
                            "file_identity": identity,
                            "operation": operation,
                            "allowed_operations": [operation],
                            "model_revision": 1,
                            "model_hash": hash_value,
                            "authorization_reason": "current typed Manuscript block plan",
                        }
                    ],
                    "write_scope": {
                        "level": "section",
                        "files": [identity],
                        "block_ids": ["BLK-0002"],
                    },
                    "authority": [],
                }
                session = {
                    "compile_id": "compile-v1-test",
                    "applicable": True,
                    "source_mode": "authoritative",
                    "base_manifest_hash": hash_value,
                }
                result = _patch_from_candidate(
                    "writer-v1-test",
                    session,
                    manifest,
                    {identity: base_state},
                    {identity: candidate_state},
                    candidate_root,
                )
                self.assertEqual(result.status, "ready", result.findings)
                self.assertEqual(result.changes[0]["operation"], operation)


if __name__ == "__main__":
    unittest.main()
