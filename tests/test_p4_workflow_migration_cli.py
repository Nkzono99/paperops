from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from paperops.cli.main import build_parser, main
from paperops.cli.manifest import write_manifest


ROOT = Path(__file__).resolve().parents[1]


class WorkflowMigrationCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "paper"
        shutil.copytree(ROOT / "template", self.project)
        write_manifest(self.project)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_status_diff_and_adopt_parser(self) -> None:
        args = build_parser().parse_args(["workflow", "migrate", "status", "--path", str(self.project), "--json"])
        self.assertEqual(args.migrate_action, "status")
        self.assertEqual(main(["workflow", "migrate", "status", "--path", str(self.project), "--json"]), 0)
        self.assertEqual(main(["workflow", "migrate", "diff", "--path", str(self.project), "--json"]), 1)


if __name__ == "__main__":
    unittest.main()
