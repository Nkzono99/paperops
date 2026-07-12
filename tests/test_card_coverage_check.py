from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import yaml

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-card-coverage.py"


def add_record(root: Path, model: str, folder: str, document: dict) -> None:
    index_path = root / ("_paperops/model/manuscript/index.yml" if model == "manuscript" else "_paperops/model/research/index.yml")
    index = yaml.safe_load(index_path.read_text())
    path = index_path.parent / folder / f"{document['id']}.yml"; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    index["records"].append({"id": document["id"], "record_type": document["record_type"], "document": path.relative_to(root).as_posix(), "expected_revision": 1, "expected_hash": "sha256:" + "0" * 64})
    index_path.write_text(yaml.safe_dump(index, sort_keys=False))


class CardCoverageCheckTest(unittest.TestCase):
    def test_template_card_coverage_check_is_advisory_by_default(self) -> None:
        result = run_python_script(SCRIPT, "--root", ROOT / "template")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("card-coverage-check", result.stdout)

    def test_strict_mode_reports_unregistered_figures_citations_and_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            result_path = root / "manuscript" / "en" / "sections" / "30_results.tex"
            result_path.write_text(
                "\\section{Results}\n"
                "% block: results.new_claim.01\n"
                "Figure~\\ref{fig:new} cites \\cite{Key2026}.\n"
                "\\begin{figure}[ht]\n"
                "\\includegraphics{../shared/figures/new.png}\n"
                "\\caption{New figure.}\n"
                "\\label{fig:new}\n"
                "\\end{figure}\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("unregistered figure asset", result.stdout)
        self.assertIn("new.png", result.stdout)
        self.assertIn("unregistered citation key", result.stdout)
        self.assertIn("Key2026", result.stdout)
        self.assertIn("unregistered manuscript block", result.stdout)
        self.assertIn("results.new_claim.01", result.stdout)

    def test_registered_cards_satisfy_strict_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            result_path = root / "manuscript" / "en" / "sections" / "30_results.tex"
            result_path.write_text(
                "\\section{Results}\n"
                "% block: results.new_claim.01\n"
                "Figure~\\ref{fig:new} cites \\cite{Key2026}.\n"
                "\\begin{figure}[ht]\n"
                "\\includegraphics{../shared/figures/new.png}\n"
                "\\caption{New figure.}\n"
                "\\label{fig:new}\n"
                "\\end{figure}\n",
                encoding="utf-8",
            )
            add_record(root, "research", "figures", {"id": "FIG-9001", "record_type": "figure", "figure_ref": "manuscript/shared/figures/new.png"})
            add_record(root, "research", "sources", {"id": "SRC-9001", "record_type": "source", "citation_keys": ["Key2026"]})
            add_record(root, "manuscript", "blocks", {"id": "BLK-9001", "record_type": "block", "en_tex_block_id": "results.new_claim.01"})

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("coverage gaps are not detected", result.stdout)


if __name__ == "__main__":
    unittest.main()
