from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path
import yaml

from tests.helpers import ROOT, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-quantity-integrity.py"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")


def write_results(root: Path, documents: list[dict]) -> None:
    records = []
    for document in documents:
        path = root / f"_paperops/model/research/results/{document['id']}.yml"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False))
        records.append({"id": document["id"], "record_type": "result", "document": path.relative_to(root).as_posix(), "expected_revision": 1, "expected_hash": "sha256:" + "0" * 64})
    index = root / "_paperops/model/research/index.yml"; index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(yaml.safe_dump({"model_name": "research", "schema_version": 1, "index_revision": 1, "records": records, "extensions": {}, "metadata": {"updated_at": ""}}, sort_keys=False))


class QuantityIntegrityCheckTest(unittest.TestCase):
    def test_strict_fails_on_unregistered_public_count_fraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_results(root, [])
            write_text(
                root / "manuscript" / "en" / "sections" / "00_abstract.tex",
                r"""
                We found release-compatible behavior in 128 of 140 selected candidates.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("未登録の数量表現", result.stdout)
        self.assertIn("128 of 140", result.stdout)

    def test_passes_when_public_count_fraction_is_declared_by_result_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_results(root, [{"id": "RES-0001", "record_type": "result", "quantity_contracts": [{"id": "QTY-0001", "value": "128", "denominator": "140", "unit_of_analysis": "selected candidate", "estimand": "endpoint positive work", "aggregation": "none", "independence": "temporally correlated snapshots", "source_artifact_id": "artifact:work-summary", "manuscript_block_refs": ["BLK-0001"]}]}])
            write_text(
                root / "manuscript" / "en" / "sections" / "00_abstract.tex",
                r"""
                We found release-compatible behavior in 128 of 140 selected candidates.
                """,
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("quantity integrity", result.stdout)


if __name__ == "__main__":
    unittest.main()
