from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from paperops.cli.main import build_parser, main
from paperops.cli.manifest import write_manifest_data_atomic


ROOT = Path(__file__).resolve().parents[1]


class WorkflowReadonlyCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "paper"
        shutil.copytree(ROOT / "template", self.project)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_parser_exposes_json_status_and_plan(self) -> None:
        args = build_parser().parse_args(["workflow", "status", str(self.project), "--json"])
        self.assertTrue(args.json)
        args = build_parser().parse_args(["workflow", "plan", str(self.project), "--changed", "CLM-0001", "--json"])
        self.assertEqual(args.changed, ["CLM-0001"])

    def test_json_status_is_projection_and_does_not_mutate_tracked_files(self) -> None:
        before = {p.relative_to(self.project).as_posix(): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        output = StringIO()
        with redirect_stdout(output):
            code = main(["workflow", "status", str(self.project), "--json"])
        self.assertEqual(code, 0)
        self.assertIn(json.loads(output.getvalue())["stage"], {"INGESTED", "MODELED", "ARCHITECTED", "DRAFTED", "PUBLISHABLE"})
        after = {p.relative_to(self.project).as_posix(): p.read_bytes() for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_unknown_changed_id_creates_blocked_ignored_plan(self) -> None:
        output = StringIO()
        with redirect_stdout(output):
            code = main(["workflow", "plan", str(self.project), "--changed", "CLM-9999", "--json"])
        self.assertEqual(code, 1)
        payload = json.loads(output.getvalue())
        plan = self.project / ".paperops/workflow/plans" / payload["plan_id"] / "plan.json"
        self.assertTrue(plan.is_file())
        self.assertFalse(payload["ready"])

    def test_v2_mode_uses_projection_and_disables_legacy_writers(self) -> None:
        manifest = self.project / ".pops/manifest.toml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        write_manifest_data_atomic(manifest, {"workflow": {"mode": "v2-authoritative"}})
        current = self.project / "_paperops/workflow/current-state.yml"
        before = current.read_bytes()
        self.assertEqual(main(["workflow", "status", str(self.project)]), 0)
        self.assertEqual(main(["workflow", "invalidate", "CLM-0001", str(self.project)]), 2)
        self.assertEqual(current.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
