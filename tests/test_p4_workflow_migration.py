from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from paperops.cli.manifest import write_manifest
from paperops.workflow_v2.migration import plan_workflow_adoption, prepare_workflow_shadow, workflow_migration_status
from paperops.workflow_v2.migration_inventory import inventory_legacy_workflow
from paperops.workflow_v2.transaction import execute_workflow_apply, execute_workflow_rollback


ROOT = Path(__file__).resolve().parents[1]
H = "sha256:" + "0" * 64


class WorkflowMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "paper"
        shutil.copytree(ROOT / "template", self.project)
        write_manifest(self.project)
        current = json.loads((self.project / "_paperops/workflow/current-state.yml").read_text())
        current["review"]["major_concerns"] = [{"summary": "Bound the claim.", "target_id": "ISS-0001", "target_type": "workflow_issue", "target_revision": 1, "target_hash": H, "route": "editorial"}]
        (self.project / "_paperops/workflow/current-state.yml").write_text(json.dumps(current) + "\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_inventory_shadow_adopt_and_rollback_preserve_legacy(self) -> None:
        inventory = inventory_legacy_workflow(self.project)
        self.assertEqual(inventory.concern_count, 1)
        shadow = prepare_workflow_shadow(self.project)
        self.assertEqual(len(shadow.candidates), 1)
        legacy = (self.project / "_paperops/workflow/current-state.yml").read_bytes()
        plan = plan_workflow_adoption(self.project, shadow.migration_id)
        tx = execute_workflow_apply(self.project, plan.plan_id, confirmed=True)
        self.assertEqual(workflow_migration_status(self.project)["mode"], "v2-authoritative")
        self.assertNotEqual(workflow_migration_status(self.project)["last_adopt_transaction"], "pending")
        self.assertTrue((self.project / "_paperops/model/issues/workflow/ISS-0001.yml").is_file())
        self.assertEqual((self.project / "_paperops/workflow/current-state.yml").read_bytes(), legacy)
        execute_workflow_rollback(self.project, tx, confirmed=True)
        self.assertEqual(workflow_migration_status(self.project)["mode"], "legacy")
        self.assertFalse((self.project / "_paperops/model/issues/workflow/ISS-0001.yml").exists())

    def test_ambiguous_concern_is_deferred_not_invented(self) -> None:
        current = json.loads((self.project / "_paperops/workflow/current-state.yml").read_text())
        current["review"]["major_concerns"] = ["Unstructured concern"]
        (self.project / "_paperops/workflow/current-state.yml").write_text(json.dumps(current) + "\n")
        shadow = prepare_workflow_shadow(self.project, refresh=True)
        self.assertEqual(shadow.candidates, ())
        self.assertEqual(shadow.dispositions[0]["disposition"], "deferred")


if __name__ == "__main__":
    unittest.main()
