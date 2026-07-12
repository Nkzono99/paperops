from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from paperops.workflow_v2.profile import WorkflowProfileError, load_workflow_profile
from paperops.workflow_v2.types import (
    MACRO_STAGES,
    ImpactRow,
    WorkflowFinding,
    WorkflowProjection,
)


ROOT = Path(__file__).resolve().parents[1]


class WorkflowTypesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        source = ROOT / "template" / "_paperops" / "defaults" / "workflow"
        target = self.root / "_paperops" / "defaults" / "workflow"
        target.parent.mkdir(parents=True)
        shutil.copytree(source, target)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_exact_stages_and_managed_registry(self) -> None:
        self.assertEqual(
            MACRO_STAGES,
            ("INGESTED", "MODELED", "ARCHITECTED", "DRAFTED", "PUBLISHABLE"),
        )
        profile = load_workflow_profile(self.root)
        self.assertEqual(profile.routes, ("research", "editorial", "manuscript", "publication"))
        self.assertIn("scientific_scope", profile.approval_kinds)
        self.assertIn("editorial_choice", profile.approval_kinds)
        self.assertIn("submission", profile.approval_kinds)

    def test_dtos_are_immutable_and_canonical(self) -> None:
        finding = WorkflowFinding("workflow.test", "/x", "stable", "warning")
        row = ImpactRow("CLM-0001", "SEC-0001", "direct", "claim_ref")
        result = WorkflowProjection(
            stage="MODELED",
            satisfied_stages=("INGESTED", "MODELED"),
            reasons=(finding,),
            review_axis="idle",
            submission_axis="not_started",
            section_axis=(("SEC-0001", "current"),),
            approval_axis=(("CLM-0001:scientific", "current"),),
            stale_impacts=(row,),
        )
        self.assertEqual(result.to_dict()["stage"], "MODELED")
        with self.assertRaises(Exception):
            result.stage = "DRAFTED"  # type: ignore[misc]

    def test_profile_is_closed_and_never_falls_back(self) -> None:
        profile = self.root / "_paperops/defaults/workflow/profile.yml"
        original = profile.read_text(encoding="utf-8")
        profile.write_text(original + "unknown: true\n", encoding="utf-8")
        with self.assertRaises(WorkflowProfileError):
            load_workflow_profile(self.root)
        profile.unlink()
        with self.assertRaises(WorkflowProfileError):
            load_workflow_profile(self.root)

    def test_symlink_profile_is_rejected(self) -> None:
        profile = self.root / "_paperops/defaults/workflow/profile.yml"
        real = self.root / "profile-real.yml"
        real.write_text(profile.read_text(encoding="utf-8"), encoding="utf-8")
        profile.unlink()
        os.symlink(real, profile)
        with self.assertRaises(WorkflowProfileError):
            load_workflow_profile(self.root)


if __name__ == "__main__":
    unittest.main()
