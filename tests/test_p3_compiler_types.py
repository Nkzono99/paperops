from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from paperops.compiler import (
    AuthoritySnapshot,
    CompileBundle,
    CompileFinding,
    CompilePaths,
    CompileRequest,
    InputSnapshot,
    SectionPlan,
    WriteScope,
    WriterPacket,
    WriterPaths,
    atomic_write_json,
    canonical_json_bytes,
    compile_paths,
    semantic_hash,
    writer_paths,
)


HASH = "sha256:" + "a" * 64


class P3CompilerTypesTest(unittest.TestCase):
    def test_write_scope_is_immutable_and_json_compatible(self) -> None:
        scope = WriteScope(
            level="block",
            languages=("ja",),
            files=("manuscript/ja/results.tex",),
            section_ids=("SEC-RESULTS",),
            block_ids=("BLK-0001",),
            allowed_operations=("rewrite",),
        )

        self.assertEqual(
            scope.to_dict(),
            {
                "level": "block",
                "languages": ["ja"],
                "files": ["manuscript/ja/results.tex"],
                "section_ids": ["SEC-RESULTS"],
                "block_ids": ["BLK-0001"],
                "allowed_operations": ["rewrite"],
            },
        )
        json.dumps(scope.to_dict(), allow_nan=False)
        with self.assertRaises(FrozenInstanceError):
            scope.level = "section"  # type: ignore[misc]

    def test_canonical_json_is_order_stable_but_list_order_sensitive(self) -> None:
        self.assertEqual(
            canonical_json_bytes({"b": 2, "a": [1, 2]}),
            canonical_json_bytes({"a": [1, 2], "b": 2}),
        )
        self.assertNotEqual(
            semantic_hash({"a": [1, 2]}),
            semantic_hash({"a": [2, 1]}),
        )
        self.assertRegex(semantic_hash({"a": 1}), r"^sha256:[0-9a-f]{64}$")

    def test_canonical_json_is_utf8_newline_terminated_and_finite(self) -> None:
        rendered = canonical_json_bytes({"label": "結果", "value": 1.5})

        self.assertEqual(rendered, '{"label":"結果","value":1.5}\n'.encode("utf-8"))
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                canonical_json_bytes({"value": value})

    def test_generated_paths_are_confined_to_ignored_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compiled = compile_paths(root, "compile-001")
            writer = writer_paths(root, "session-001")

            self.assertEqual(
                compiled.compile_dir,
                root / ".paperops/compile/compile-001",
            )
            self.assertEqual(compiled.bundle_path, compiled.compile_dir / "bundle.json")
            self.assertEqual(
                compiled.global_context_path,
                compiled.compile_dir / "context/global.json",
            )
            self.assertEqual(
                writer.workspace_dir,
                root / ".paperops/writer/session-001/workspace",
            )
            self.assertEqual(writer.patch_path, writer.writer_dir / "patch.json")

    def test_path_dto_direct_construction_enforces_layout_and_safe_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compiled = compile_paths(root, "compile-001")
            writer = writer_paths(root, "session-001")

            self.assertIsInstance(compiled, CompilePaths)
            self.assertIsInstance(writer, WriterPaths)
            self.assertEqual(
                compiled.to_dict(),
                {
                    "compile_id": "compile-001",
                    "compile_dir": ".paperops/compile/compile-001",
                    "bundle_path": ".paperops/compile/compile-001/bundle.json",
                    "report_path": ".paperops/compile/compile-001/report.json",
                    "context_dir": ".paperops/compile/compile-001/context",
                    "global_context_path": (
                        ".paperops/compile/compile-001/context/global.json"
                    ),
                    "plans_dir": ".paperops/compile/compile-001/plans",
                    "packets_dir": ".paperops/compile/compile-001/packets",
                },
            )
            self.assertEqual(
                writer.to_dict(),
                {
                    "session_id": "session-001",
                    "writer_dir": ".paperops/writer/session-001",
                    "workspace_dir": ".paperops/writer/session-001/workspace",
                    "base_manifest_path": (
                        ".paperops/writer/session-001/base-manifest.json"
                    ),
                    "patch_path": ".paperops/writer/session-001/patch.json",
                    "report_path": ".paperops/writer/session-001/report.json",
                    "journal_path": ".paperops/writer/session-001/journal.json",
                },
            )

            for invalid in (
                lambda: replace(compiled, compile_id="../escape"),
                lambda: replace(
                    compiled,
                    compile_dir=root / "outside" / "compile-001",
                ),
                lambda: replace(
                    compiled,
                    bundle_path=Path("/outside/bundle.json"),
                ),
                lambda: replace(writer, session_id="../escape"),
                lambda: replace(
                    writer,
                    writer_dir=root / "outside" / "session-001",
                ),
                lambda: replace(
                    writer,
                    patch_path=Path("/outside/patch.json"),
                ),
            ):
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    invalid()

    def test_generated_paths_reject_escape_and_absolute_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for value in ("../escape", "/absolute", "C:\\escape", "a/b", ""):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    compile_paths(root, value)
                with self.subTest(value=value), self.assertRaises(ValueError):
                    writer_paths(root, value)

    def test_input_snapshot_rejects_non_relative_identity(self) -> None:
        for identity in ("/private/result.yml", "../escape", "C:\\result.yml"):
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                InputSnapshot(
                    identity=identity,
                    input_type="claim",
                    semantic_hash=HASH,
                    relation="supports",
                )

        snapshot = InputSnapshot(
            identity="_paperops/model/research/claims/CLM-0001.yml",
            input_type="claim",
            semantic_hash=HASH,
            relation="supports",
            model_name="research",
            revision=1,
        )
        self.assertEqual(
            snapshot.to_dict()["identity"],
            "_paperops/model/research/claims/CLM-0001.yml",
        )

    def test_compiler_dto_graph_is_json_compatible(self) -> None:
        scope = WriteScope(
            level="block",
            languages=("ja",),
            files=("manuscript/ja/results.tex",),
            section_ids=("SEC-RESULTS",),
            block_ids=("BLK-0001",),
            allowed_operations=("rewrite",),
        )
        request = CompileRequest(("SEC-RESULTS",), scope)
        authority = AuthoritySnapshot(
            model_name="research",
            mode="v2-authoritative",
            model_hash=HASH,
            transaction_id="model-001",
        )
        snapshot = InputSnapshot(
            identity="CLM-0001",
            input_type="claim",
            semantic_hash=HASH,
            relation="supports",
            model_name="research",
            revision=1,
        )
        plan = SectionPlan(
            section_id="SEC-RESULTS",
            revision=1,
            semantic_hash=HASH,
            section_kind="results",
            ordered_block_ids=("BLK-0001",),
            inputs=(snapshot,),
            projection={
                "schema_version": 1,
                "move_bindings": [],
                "extensions": {"x-test-reader-question": "What changes?"},
            },
        )
        packet = WriterPacket(
            packet_id="packet-001",
            compile_id="compile-001",
            authority=(authority,),
            write_scope=scope,
            inputs=(snapshot,),
            read_context={
                "schema_version": 1,
                "global": ".paperops/compile/compile-001/context/global.json",
                "extensions": {"x-test-paths": ["manuscript/ja/results.tex"]},
            },
            payload={
                "schema_version": 1,
                "section_plan": "SEC-RESULTS",
                "extensions": {},
            },
        )
        finding = CompileFinding(
            code="compile.example",
            pointer="/inputs/0",
            message="example diagnostic",
            severity="info",
            identity="CLM-0001",
        )
        bundle = CompileBundle(
            compile_id="compile-001",
            source_mode="authoritative",
            request=request,
            authority=(authority,),
            inputs=(snapshot,),
            section_plans=(plan,),
            writer_packets=(packet,),
            findings=(finding,),
        )

        payload = bundle.to_dict()
        json.dumps(payload, ensure_ascii=False, allow_nan=False)
        self.assertEqual(payload["writer_packets"][0]["write_scope"], scope.to_dict())
        self.assertEqual(payload["inputs"][0]["identity"], "CLM-0001")

    def test_ordered_dto_fields_reject_sets_and_mappings(self) -> None:
        for unordered in ({"ja"}, frozenset({"ja"}), {"ja": True}):
            with self.subTest(unordered=unordered), self.assertRaises(TypeError):
                WriteScope(
                    level="block",
                    languages=unordered,  # type: ignore[arg-type]
                    files=("manuscript/ja/results.tex",),
                )

        scope = WriteScope(
            level="block",
            languages=("ja",),
            files=("manuscript/ja/results.tex",),
        )
        authority = AuthoritySnapshot(
            model_name="research",
            mode="v2-authoritative",
            model_hash=HASH,
        )
        snapshot = InputSnapshot(
            identity="CLM-0001",
            input_type="claim",
            semantic_hash=HASH,
            relation="supports",
        )
        for unordered in (
            {authority},
            frozenset({authority}),
            {authority: "accidental mapping value"},
        ):
            with self.subTest(unordered=unordered), self.assertRaises(TypeError):
                WriterPacket(
                    packet_id="packet-001",
                    compile_id="compile-001",
                    authority=unordered,  # type: ignore[arg-type]
                    write_scope=scope,
                    inputs=(snapshot,),
                )

    def test_atomic_json_is_canonical_and_newline_terminated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "bundle.json"

            atomic_write_json(path, {"b": 2, "a": "結果"})

            self.assertEqual(
                path.read_bytes(),
                canonical_json_bytes({"a": "結果", "b": 2}),
            )
            self.assertTrue(path.read_bytes().endswith(b"\n"))

    def test_atomic_json_cleans_temporary_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            path.write_bytes(b"old\n")

            with patch(
                "paperops.compiler.storage.os.replace",
                side_effect=OSError("injected replace failure"),
            ):
                with self.assertRaises(OSError):
                    atomic_write_json(path, {"new": True})

            self.assertEqual(path.read_bytes(), b"old\n")
            self.assertEqual(list(path.parent.glob(f".{path.name}.tmp-*")), [])

    def test_atomic_json_fsyncs_same_directory_temp_and_cleans_fsync_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bundle.json"
            with (
                patch(
                    "paperops.compiler.storage.tempfile.mkstemp",
                    wraps=tempfile.mkstemp,
                ) as make_temp,
                patch("paperops.compiler.storage.os.fsync", wraps=os.fsync) as fsync,
            ):
                atomic_write_json(path, {"ok": True})

            self.assertEqual(make_temp.call_args.kwargs["dir"], path.parent)
            self.assertTrue(
                make_temp.call_args.kwargs["prefix"].startswith(
                    f".{path.name}.tmp-"
                )
            )
            fsync.assert_called_once()

            path.write_bytes(b"old\n")
            with patch(
                "paperops.compiler.storage.os.fsync",
                side_effect=OSError("injected fsync failure"),
            ):
                with self.assertRaises(OSError):
                    atomic_write_json(path, {"new": True})

            self.assertEqual(path.read_bytes(), b"old\n")
            self.assertEqual(list(path.parent.glob(f".{path.name}.tmp-*")), [])


if __name__ == "__main__":
    unittest.main()
