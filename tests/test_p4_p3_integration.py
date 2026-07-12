from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from paperops.cli.manifest import read_manifest, write_manifest_data_atomic
from paperops.compiler.inputs import CompileInputError, load_compile_inputs
from paperops.compiler.types import CompileRequest, WriteScope
from paperops.workflow_v2.readiness import workflow_compile_findings


ROOT = Path(__file__).resolve().parents[1]
H = "sha256:" + "0" * 64


class P4P3IntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "paper"
        shutil.copytree(ROOT / "template", self.project)
        manifest_path = self.project / ".pops/manifest.toml"
        manifest_path.parent.mkdir(parents=True)
        write_manifest_data_atomic(manifest_path, {"workflow": {"mode": "v2-authoritative"}})
        issue = {"id": "ISS-0001", "record_type": "workflow_issue", "revision": 1, "status": "open", "impacts": [{"target_id": "SEC-0001", "target_type": "section", "expected_revision": 1, "expected_hash": H, "state": "open", "verification_refs": []}]}
        path = self.project / "_paperops/model/issues/workflow/ISS-0001.yml"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(issue) + "\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_only_selected_open_impact_blocks_compile(self) -> None:
        findings = workflow_compile_findings(self.project, ("SEC-0001",))
        self.assertEqual(findings[0].code, "compile.workflow_open_impact")
        self.assertEqual(workflow_compile_findings(self.project, ("SEC-0002",)), ())

    def test_authoritative_loader_checks_workflow_before_materialization(self) -> None:
        request = CompileRequest(("SEC-0001",), WriteScope("section", ("ja",), ("manuscript/main-ja.tex",), ("SEC-0001",), (), ("rewrite",)))
        with self.assertRaises(CompileInputError) as caught:
            load_compile_inputs(self.project, request)
        self.assertEqual(caught.exception.finding.code, "compile.workflow_open_impact")

    def test_legacy_mode_preserves_p3_behavior(self) -> None:
        manifest_path = self.project / ".pops/manifest.toml"
        write_manifest_data_atomic(manifest_path, {"workflow": {"mode": "legacy"}})
        self.assertEqual(workflow_compile_findings(self.project, ("SEC-0001",)), ())


if __name__ == "__main__":
    unittest.main()
