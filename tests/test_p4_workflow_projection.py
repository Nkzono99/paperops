from __future__ import annotations

import unittest

from paperops.workflow_v2.catalog import WorkflowCatalogSnapshot
from paperops.workflow_v2.graph import build_dependency_graph
from paperops.workflow_v2.profile import WorkflowProfile
from paperops.workflow_v2.projection import project_workflow_status


PROFILE = WorkflowProfile(
    1,
    ("INGESTED", "MODELED", "ARCHITECTED", "DRAFTED", "PUBLISHABLE"),
    ("research", "editorial", "manuscript", "publication"),
    ("scientific", "editorial", "submission"),
    (("claim", "research"),),
    ("dependency",),
)


class WorkflowProjectionTest(unittest.TestCase):
    def test_highest_satisfied_stage_and_axes_are_independent(self) -> None:
        cases = (
            ({"ingested": True}, "INGESTED"),
            ({"ingested": True, "modeled": True}, "MODELED"),
            ({"ingested": True, "modeled": True, "architected": True}, "ARCHITECTED"),
            ({"ingested": True, "modeled": True, "architected": True, "drafted": True}, "DRAFTED"),
            ({"ingested": True, "modeled": True, "architected": True, "drafted": True, "publishable": True}, "PUBLISHABLE"),
        )
        for facts, expected in cases:
            snapshot = WorkflowCatalogSnapshot(nodes=(), edges=(), facts=tuple(sorted(facts.items())), findings=())
            projection = project_workflow_status(snapshot, build_dependency_graph(snapshot), PROFILE)
            self.assertEqual(projection.stage, expected)

    def test_review_activity_does_not_change_macro_stage(self) -> None:
        base = {"ingested": True, "modeled": True, "architected": True, "review_axis": "idle"}
        active = dict(base, review_axis="active")
        first = WorkflowCatalogSnapshot((), (), tuple(sorted(base.items())), ())
        second = WorkflowCatalogSnapshot((), (), tuple(sorted(active.items())), ())
        self.assertEqual(
            project_workflow_status(first, build_dependency_graph(first), PROFILE).stage,
            project_workflow_status(second, build_dependency_graph(second), PROFILE).stage,
        )


if __name__ == "__main__":
    unittest.main()
