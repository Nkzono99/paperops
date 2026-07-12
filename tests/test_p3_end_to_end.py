from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import run_cli
from tests.test_p3_compile_materialize import approved_project


class P3EndToEndTest(unittest.TestCase):
    def test_authoritative_candidate_scope_conservation_apply_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = approved_project(Path(temporary))
            prepared = json.loads(
                run_cli([
                    "compile", "prepare", "SEC-0002", str(project),
                    "--scope", "block", "--block", "BLK-0002", "--json",
                ])[1]
            )
            started = json.loads(
                run_cli(["write", "start", prepared["result"]["compile_id"], str(project), "--json"])[1]
            )
            session_id = started["session_id"]
            identity = "manuscript/en/sections/30_results.tex"
            living = project / identity
            original = living.read_bytes()
            candidate = project / ".paperops/writer" / session_id / "workspace" / identity
            candidate.write_text(
                candidate.read_text().replace(
                    "% block: results.traceability.01",
                    "% block: results.traceability.01\nA final P3 lifecycle revision.",
                ), encoding="utf-8",
            )
            checked = json.loads(run_cli(["write", "check", session_id, str(project), "--json"])[1])
            self.assertTrue(checked["ok"])
            self.assertEqual(checked["result"]["conservation_result"], "passed")
            applied = json.loads(
                run_cli(["write", "apply", session_id, str(project), "--yes", "--json"])[1]
            )
            self.assertIn(b"final P3", living.read_bytes())
            code, _raw, _error = run_cli(
                ["write", "rollback", applied["transaction_id"], str(project), "--json"]
            )
            self.assertEqual(code, 0)
            self.assertEqual(living.read_bytes(), original)
            self.assertFalse((project / "submission/.paperops").exists())


if __name__ == "__main__":
    unittest.main()
