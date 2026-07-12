from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT
from tests.test_p3_compile_materialize import approved_project


class P3DistributionTest(unittest.TestCase):
    def test_isolated_wheel_runs_compile_and_write_lifecycle(self) -> None:
        uv = shutil.which("uv")
        if uv is None:
            self.skipTest("uv is required for the wheel distribution check")
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = approved_project(base / "fixture")
            dist = base / "dist"
            subprocess.run(
                [uv, "build", "--wheel", "--out-dir", str(dist)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            wheel = next(dist.glob("*.whl"))
            venv = base / "venv"
            subprocess.run([uv, "venv", "--python", sys.executable, str(venv)], check=True, capture_output=True, text=True)
            python = venv / "bin/python"
            subprocess.run(
                [uv, "pip", "install", "--python", str(python), str(wheel)],
                check=True,
                capture_output=True,
                text=True,
            )
            pops = venv / "bin/pops"
            environment = {
                key: value for key, value in os.environ.items()
                if key not in {"PYTHONPATH", "PYTHONHOME", "PAPEROPS_SCAFFOLD_SOURCE"}
            }
            environment["PYTHONNOUSERSITE"] = "1"

            imported = subprocess.run(
                [python, "-c", "import paperops, pathlib; print(pathlib.Path(paperops.__file__).as_posix())"],
                env=environment, check=True, capture_output=True, text=True,
            ).stdout.strip()
            self.assertIn("venv", imported)
            self.assertNotIn(str(ROOT / "src"), imported)

            prepared = self.run_json(
                pops,
                ["compile", "prepare", "SEC-0002", str(project), "--scope", "block", "--block", "BLK-0002", "--json"],
                environment,
            )
            compile_id = prepared["result"]["compile_id"]
            started = self.run_json(
                pops,
                ["write", "start", compile_id, str(project), "--json"],
                environment,
            )
            session_id = started["session_id"]
            identity = "manuscript/en/sections/30_results.tex"
            living = project / identity
            original = living.read_bytes()
            candidate = project / ".paperops/writer" / session_id / "workspace" / identity
            candidate.write_text(
                candidate.read_text().replace(
                    "% block: results.traceability.01",
                    "% block: results.traceability.01\nAn installed-wheel revision.",
                ),
                encoding="utf-8",
            )
            self.run_json(pops, ["write", "check", session_id, str(project), "--json"], environment)
            applied = self.run_json(
                pops,
                ["write", "apply", session_id, str(project), "--yes", "--json"],
                environment,
            )
            repeated = self.run_json(
                pops,
                ["write", "apply", session_id, str(project), "--yes", "--json"],
                environment,
            )
            self.assertTrue(repeated["reused"])
            self.run_json(
                pops,
                ["write", "rollback", applied["transaction_id"], str(project), "--json"],
                environment,
            )
            self.assertEqual(living.read_bytes(), original)

    def run_json(self, pops: Path, argv: list[str], environment: dict[str, str]):
        result = subprocess.run(
            [pops, *argv], env=environment, check=False, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
