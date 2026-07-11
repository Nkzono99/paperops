from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import yaml

from paperops.model_state import read_model_states, write_model_states
from tests.helpers import ROOT
from tests.test_p3_compile_inputs import (
    authoritative_project,
    compile_request,
    shadow_project,
)


sys.path.insert(0, str(ROOT / "src"))


def _section_document(loaded):
    return next(
        item
        for item in loaded.documents
        if item.identity == "_paperops/model/manuscript/sections/SEC-0001.yml"
    )


def _section_object(loaded):
    return next(item for item in loaded.objects if item.object_id == "SEC-0001")


class P3CompileSnapshotConsistencyTest(unittest.TestCase):
    def test_authority_dto_and_readiness_use_one_immutable_snapshot(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp), approved_section=True)
            section = (
                project
                / "_paperops/model/manuscript/sections/SEC-0001.yml"
            )
            approved = section.read_bytes()
            document = yaml.safe_load(approved)
            document["approvals"] = []
            unapproved = yaml.safe_dump(document, sort_keys=False).encode("utf-8")

            original_authority = inputs._authoritative_snapshots
            original_loader = inputs._load_model_inputs

            def authority_then_swap(root):
                result = original_authority(root)
                section.write_bytes(unapproved)
                return result

            def dto_then_swap(root, authority):
                result = original_loader(root, authority)
                section.write_bytes(approved)
                return result

            try:
                with patch.object(
                    inputs,
                    "_authoritative_snapshots",
                    side_effect=authority_then_swap,
                ), patch.object(
                    inputs,
                    "_load_model_inputs",
                    side_effect=dto_then_swap,
                ):
                    loaded = inputs.load_compile_inputs(project, request)
            finally:
                section.write_bytes(approved)

        self.assertTrue(loaded.readiness.ok, loaded.readiness.findings)
        self.assertTrue(_section_document(loaded).document["approvals"])

    def test_snapshot_hash_and_full_content_hash_bind_approval_content(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            approved_project, _ = authoritative_project(
                Path(tmp) / "approved",
                approved_section=True,
            )
            unapproved_project, _ = authoritative_project(
                Path(tmp) / "unapproved",
                approved_section=False,
            )
            approved = inputs.load_compile_inputs(approved_project, request)
            unapproved = inputs.load_compile_inputs(unapproved_project, request)

        self.assertEqual(
            tuple(item.model_hash for item in approved.authority),
            tuple(item.model_hash for item in unapproved.authority),
        )
        self.assertEqual(
            _section_document(approved).semantic_hash,
            _section_document(unapproved).semantic_hash,
        )
        self.assertNotEqual(
            _section_document(approved).content_hash,
            _section_document(unapproved).content_hash,
        )
        self.assertNotEqual(
            _section_object(approved).content_hash,
            _section_object(unapproved).content_hash,
        )
        self.assertRegex(approved.snapshot_hash, r"^sha256:[0-9a-f]{64}$")
        self.assertNotEqual(approved.snapshot_hash, unapproved.snapshot_hash)

    def test_non_compile_manifest_state_does_not_change_snapshot_hash(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp), approved_section=True)
            before = inputs.load_compile_inputs(project, request)
            states = read_model_states(project)
            states["issue"] = replace(
                states["issue"],
                mode="shadow-compare",
                last_shadow_transaction=(
                    "model-20260712T000000000000Z-aaaaaaaaaaaa"
                ),
            )
            write_model_states(project, states)
            after = inputs.load_compile_inputs(project, request)

            for identity, replacement in (
                (
                    "_paperops/defaults/schemas/issue-index.schema.json",
                    b"{not valid json",
                ),
                (
                    "_paperops/model/issues/index.yml",
                    b"- not-an-issue-index\n",
                ),
                (
                    "_paperops/defaults/schemas/publication-model.schema.json",
                    b"{not valid json",
                ),
                (
                    "_paperops/model/publication/publication-model.yml",
                    b"- not-a-publication-model\n",
                ),
            ):
                path = project / identity
                original = path.read_bytes()
                path.write_bytes(replacement)
                try:
                    isolated = inputs.load_compile_inputs(project, request)
                finally:
                    path.write_bytes(original)
                self.assertEqual(
                    before.snapshot_hash,
                    isolated.snapshot_hash,
                    identity,
                )
            missing_schema = (
                project
                / "_paperops/defaults/schemas/issue-index.schema.json"
            )
            backup_schema = missing_schema.with_suffix(".json.missing")
            missing_schema.rename(backup_schema)
            try:
                isolated = inputs.load_compile_inputs(project, request)
            finally:
                backup_schema.rename(missing_schema)
            self.assertEqual(before.snapshot_hash, isolated.snapshot_hash)

        self.assertEqual(before.snapshot_hash, after.snapshot_hash)

    def test_compile_schema_raw_change_changes_snapshot_hash(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp), approved_section=True)
            before = inputs.load_compile_inputs(project, request)
            schema = (
                project
                / "_paperops/defaults/schemas/manuscript-section.schema.json"
            )
            schema.write_bytes(schema.read_bytes() + b"\n")
            after = inputs.load_compile_inputs(project, request)

        self.assertNotEqual(before.snapshot_hash, after.snapshot_hash)

    def test_snapshot_captures_only_declared_checker_sources(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp), approved_section=True)
            package = project / "scripts/paperops_models"
            package.mkdir()
            (package / "__init__.py").write_text(
                "raise RuntimeError('unbound package executed')\n",
                encoding="utf-8",
            )
            cache = project / "scripts/__pycache__"
            cache.mkdir(exist_ok=True)
            (cache / "paperops_models.unchecked.pyc").write_bytes(
                b"unbound-bytecode-sentinel"
            )
            (project / "scripts/paperops_models.so").write_bytes(
                b"unbound-extension-sentinel"
            )
            snapshot = Path(tmp) / "captured"
            inputs._capture_authoritative_project(project, snapshot)
            captured_scripts = {
                path.relative_to(snapshot).as_posix()
                for path in (snapshot / "scripts").rglob("*")
                if path.is_file()
            }
            loaded = inputs.load_compile_inputs(project, request)

        self.assertEqual(
            captured_scripts,
            set(inputs._CHECKER_SCRIPT_IDENTITIES),
        )
        self.assertTrue(loaded.readiness.ok, loaded.readiness.findings)


class P3CompileFdTraversalTest(unittest.TestCase):
    def test_nested_parent_baseexception_closes_ancestor_descriptors(self) -> None:
        safe_fs = importlib.import_module("paperops.compiler.safe_fs")
        for exception_type in (KeyboardInterrupt, SystemExit):
            with self.subTest(
                exception=exception_type.__name__
            ), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                nested = root / "first/second"
                nested.mkdir(parents=True)
                (nested / "model.yml").write_bytes(b"safe: true\n")
                opened: list[int] = []
                closed: list[int] = []
                original_open = safe_fs.os.open
                original_close = safe_fs.os.close

                def tracking_open(path, flags, *args, **kwargs):
                    descriptor = original_open(path, flags, *args, **kwargs)
                    opened.append(descriptor)
                    return descriptor

                def tracking_close(descriptor):
                    closed.append(descriptor)
                    return original_close(descriptor)

                def injected_hook(stage: str, identity: str) -> None:
                    if (
                        stage == "after_dir_fd_open"
                        and identity == "first/second"
                    ):
                        raise exception_type()

                with patch.object(
                    safe_fs.os,
                    "open",
                    side_effect=tracking_open,
                ), patch.object(
                    safe_fs.os,
                    "close",
                    side_effect=tracking_close,
                ):
                    with safe_fs.SafeProjectReader(
                        root,
                        hook=injected_hook,
                    ) as reader:
                        with self.assertRaises(exception_type):
                            reader.read_bytes("first/second/model.yml")

                self.assertCountEqual(opened, closed)

    def test_fstat_and_post_open_hook_failures_close_owned_descriptors(self) -> None:
        safe_fs = importlib.import_module("paperops.compiler.safe_fs")
        failures = (
            "directory_fstat",
            "directory_hook",
            "file_fstat",
            "file_hook",
        )
        for failure in failures:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                parent = root / "registered"
                parent.mkdir()
                (parent / "model.yml").write_bytes(b"safe: true\n")
                opened: list[int] = []
                closed: list[int] = []
                names: dict[int, str] = {}
                original_open = safe_fs.os.open
                original_close = safe_fs.os.close
                original_fstat = safe_fs.os.fstat

                def tracking_open(path, flags, *args, **kwargs):
                    descriptor = original_open(path, flags, *args, **kwargs)
                    opened.append(descriptor)
                    names[descriptor] = str(path)
                    return descriptor

                def tracking_close(descriptor):
                    closed.append(descriptor)
                    return original_close(descriptor)

                def injected_fstat(descriptor):
                    if (
                        failure == "directory_fstat"
                        and names.get(descriptor) == "registered"
                    ) or (
                        failure == "file_fstat"
                        and names.get(descriptor) == "model.yml"
                    ):
                        raise OSError("injected fstat failure")
                    return original_fstat(descriptor)

                def injected_hook(stage: str, identity: str) -> None:
                    if (
                        failure == "directory_hook"
                        and stage == "after_dir_fd_open"
                        and identity == "registered"
                    ) or (
                        failure == "file_hook"
                        and stage == "after_file_fd_open"
                        and identity == "registered/model.yml"
                    ):
                        raise RuntimeError("injected post-open hook failure")

                expected = (
                    safe_fs.SafeCaptureError
                    if failure.endswith("fstat")
                    else RuntimeError
                )
                with patch.object(
                    safe_fs.os,
                    "open",
                    side_effect=tracking_open,
                ), patch.object(
                    safe_fs.os,
                    "close",
                    side_effect=tracking_close,
                ), patch.object(
                    safe_fs.os,
                    "fstat",
                    side_effect=injected_fstat,
                ):
                    with safe_fs.SafeProjectReader(
                        root,
                        hook=injected_hook,
                    ) as reader:
                        with self.assertRaises(expected):
                            reader.read_bytes("registered/model.yml")

                self.assertCountEqual(opened, closed)

    def test_opened_leaf_inode_is_used_after_path_is_replaced(self) -> None:
        safe_fs = importlib.import_module("paperops.compiler.safe_fs")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "model.yml"
            held = root / "held-model.yml"
            outside = root / "outside.yml"
            target.write_bytes(b"safe: true\n")
            outside.write_bytes(b"secret: must-not-read\n")

            def swap(stage: str, identity: str) -> None:
                if stage == "after_file_fd_open" and identity == "model.yml":
                    target.rename(held)
                    target.symlink_to(outside)

            with safe_fs.SafeProjectReader(root, hook=swap) as reader:
                content = reader.read_bytes("model.yml")

        self.assertEqual(content, b"safe: true\n")

    def test_opened_parent_dirfd_is_used_after_path_is_replaced(self) -> None:
        safe_fs = importlib.import_module("paperops.compiler.safe_fs")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            parent = root / "registered"
            held = root / "held-registered"
            outside = root / "outside"
            parent.mkdir()
            outside.mkdir()
            (parent / "model.yml").write_bytes(b"safe: true\n")
            (outside / "model.yml").write_bytes(b"secret: must-not-read\n")

            def swap(stage: str, identity: str) -> None:
                if stage == "after_dir_fd_open" and identity == "registered":
                    parent.rename(held)
                    parent.symlink_to(outside, target_is_directory=True)

            with safe_fs.SafeProjectReader(root, hook=swap) as reader:
                content = reader.read_bytes("registered/model.yml")

        self.assertEqual(content, b"safe: true\n")

    def test_final_open_swap_to_symlink_is_rejected_without_reading_target(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "model.yml"
            outside = root / "outside.yml"
            target.write_text("safe: true\n", encoding="utf-8")
            outside.write_text("secret: must-not-read\n", encoding="utf-8")

            def swap() -> None:
                target.unlink()
                target.symlink_to(outside)

            try:
                inputs._read_registered_bytes(
                    root,
                    "model.yml",
                    _before_final_open=swap,
                )
            except inputs.CompileInputError as error:
                self.assertEqual(error.finding.code, "compile.input_path")
            else:
                self.fail("final-component symlink swap was accepted")

    def test_final_open_swap_to_fifo_never_blocks(self) -> None:
        source = """
import os
import sys
from pathlib import Path
from paperops.compiler.inputs import CompileInputError, _read_registered_bytes
root = Path(sys.argv[1])
target = root / "model.yml"
target.write_text("safe: true\\n", encoding="utf-8")
def swap():
    target.unlink()
    os.mkfifo(target)
try:
    _read_registered_bytes(root, "model.yml", _before_final_open=swap)
except CompileInputError as error:
    raise SystemExit(0 if error.finding.code == "compile.input_path" else 3)
raise SystemExit(2)
"""
        with tempfile.TemporaryDirectory() as tmp:
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(ROOT / "src")
            try:
                result = subprocess.run(
                    [sys.executable, "-c", source, tmp],
                    check=False,
                    timeout=2.0,
                    env=environment,
                )
            except subprocess.TimeoutExpired:
                self.fail("final-component FIFO swap blocked the reader")
        self.assertEqual(result.returncode, 0)

    def test_shadow_copy_does_not_reopen_sources_through_pathlib(self) -> None:
        inputs = importlib.import_module("paperops.compiler.inputs")
        for forbidden_method in ("iterdir", "read_bytes"):
            with self.subTest(method=forbidden_method), tempfile.TemporaryDirectory() as tmp:
                source, transaction_id = shadow_project(Path(tmp))
                destination = Path(tmp) / "destination"
                with patch.object(
                    Path,
                    forbidden_method,
                    side_effect=AssertionError(
                        f"Path.{forbidden_method} reopened an untrusted source"
                    ),
                ):
                    inputs._capture_shadow_project(
                        source,
                        destination,
                        transaction_id,
                    )
                self.assertTrue(
                    (destination / "scripts/check-paperops-models.py").is_file()
                )


if __name__ == "__main__":
    unittest.main()
