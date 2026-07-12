from __future__ import annotations

import unittest
import tempfile
import json
from pathlib import Path

from paperops.workflow_v2.catalog import WorkflowCatalogSnapshot, load_workflow_catalog
from paperops.workflow_v2.graph import build_dependency_graph, plan_workflow_impact
from paperops.workflow_v2.types import WorkflowEdge, WorkflowNode


H = "sha256:" + "0" * 64


class WorkflowGraphTest(unittest.TestCase):
    def test_direct_transitive_and_unaffected_are_deterministic(self) -> None:
        snapshot = WorkflowCatalogSnapshot(
            nodes=(
                WorkflowNode("CLM-0001", "claim", 1, H),
                WorkflowNode("SEC-0001", "section", 1, H),
                WorkflowNode("BLK-0001", "block", 1, H),
                WorkflowNode("SEC-0002", "section", 1, H),
            ),
            edges=(
                WorkflowEdge("CLM-0001", "BLK-0001", "claim_ref"),
                WorkflowEdge("BLK-0001", "SEC-0001", "block_member"),
            ),
            facts=(),
            findings=(),
        )
        graph = build_dependency_graph(snapshot)
        plan = plan_workflow_impact(graph, changed_ids=("CLM-0001",))
        rows = {(r.target_id, r.impact) for r in plan.impacts}
        self.assertIn(("BLK-0001", "direct"), rows)
        self.assertIn(("SEC-0001", "transitive"), rows)
        self.assertIn(("SEC-0002", "unaffected"), rows)

    def test_cycle_is_safe_and_unknown_id_blocks_plan(self) -> None:
        snapshot = WorkflowCatalogSnapshot(
            nodes=(WorkflowNode("SEC-0001", "section", 1, H), WorkflowNode("BLK-0001", "block", 1, H)),
            edges=(WorkflowEdge("SEC-0001", "BLK-0001", "dependency"), WorkflowEdge("BLK-0001", "SEC-0001", "dependency")),
            facts=(), findings=(),
        )
        graph = build_dependency_graph(snapshot)
        self.assertTrue(plan_workflow_impact(graph, changed_ids=("SEC-0001",)).ready)
        unknown = plan_workflow_impact(graph, changed_ids=("CLM-9999",))
        self.assertFalse(unknown.ready)
        self.assertEqual(unknown.findings[0].code, "workflow.changed.unknown")

    def test_aggregate_editorial_objects_enter_the_typed_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "_paperops/model/editorial/editorial-model.yml"
            path.parent.mkdir(parents=True)
            path.write_text(json.dumps({"model_id": "EDT-0001", "revision": 2, "story_candidates": [{"story_id": "STY-0001"}], "argument_moves": [{"move_id": "MOV-0001", "claim_ids": ["CLM-0001"]}], "visual_obligations": [{"visual_id": "VIS-0001", "figure_ids": []}]}) + "\n")
            snapshot = load_workflow_catalog(root)
            types = {node.object_id: node.object_type for node in snapshot.nodes}
            self.assertEqual(types["STY-0001"], "story")
            self.assertEqual(types["MOV-0001"], "move")
            self.assertEqual(types["VIS-0001"], "visual")


if __name__ == "__main__":
    unittest.main()
