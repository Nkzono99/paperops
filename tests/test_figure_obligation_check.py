from __future__ import annotations

import tempfile
import textwrap
import unittest
import subprocess
import sys
from pathlib import Path
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "template" / "scripts" / "check-figure-obligations.py"


def write_research(root: Path, documents: list[dict]) -> None:
    records = []
    for document in documents:
        kind = document["record_type"]
        path = root / f"_paperops/model/research/{kind}s/{document['id']}.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False))
        records.append({"id": document["id"], "record_type": kind, "document": path.relative_to(root).as_posix(), "expected_revision": 1, "expected_hash": "sha256:" + "0" * 64})
    index = root / "_paperops/model/research/index.yml"; index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(yaml.safe_dump({"model_name": "research", "schema_version": 1, "index_revision": 1, "records": records, "extensions": {}, "metadata": {"updated_at": ""}}, sort_keys=False))


def run_python_script(script: Path, *args: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *[str(arg) for arg in args]],
        check=False,
        capture_output=True,
        text=True,
    )


class FigureObligationCheckTest(unittest.TestCase):
    def test_fails_when_declared_visual_obligation_has_no_figure_route(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_research(root, [{"id": "CLM-0001", "record_type": "claim", "status": "approved", "gate_status": "ready_to_write", "visual_obligation_refs": ["VO-STATE-0001"], "no_figure_reason": ""}])

            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 1)
        self.assertIn("VO-STATE-0001", result.stdout)
        self.assertIn("figure obligation", result.stdout)

    def test_passes_when_visual_obligation_is_satisfied_by_figure_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_research(root, [
                {"id": "CLM-0001", "record_type": "claim", "status": "approved", "gate_status": "ready_to_write", "visual_obligation_refs": ["VO-CRITERION-0001"], "no_figure_reason": ""},
                {"id": "FIG-0001", "record_type": "figure", "status": "draft", "manuscript_role": "main", "visual_obligation_refs": ["VO-CRITERION-0001"]},
            ])

            result = run_python_script(SCRIPT, "--root", root)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("visual obligation", result.stdout)

    def test_strict_fails_supported_claim_without_obligation_or_no_figure_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_research(root, [{"id": "CLM-0001", "record_type": "claim", "status": "approved", "gate_status": "ready_to_write", "visual_obligation_refs": [], "no_figure_reason": ""}])

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("CLM-0001", result.stdout)
        self.assertIn("no_figure_reason", result.stdout)


if __name__ == "__main__":
    unittest.main()
