from __future__ import annotations

import copy
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-paperops-models.py"


def story(story_id: str, status: str) -> dict[str, object]:
    return {
        "id": story_id,
        "label": f"Story {story_id}",
        "thesis": f"Thesis {story_id}",
        "result_order": ["RHI-0001"],
        "argument_move_ids": ["MOV-0001"],
        "status": status,
        "selection_reason": "Best supported." if status == "selected" else "",
        "rejection_reason": "Less direct." if status == "rejected" else "",
    }


def valid_documents() -> tuple[dict[str, object], dict[str, object]]:
    editorial: dict[str, object] = {
        "schema_version": 1,
        "model_id": "EDT-0001",
        "revision": 1,
        "reader_transformation": {
            "reader_before": "The mechanism is unresolved.",
            "reader_after": "The control identifies the mechanism.",
            "why_it_matters": "Competing explanations are separated.",
        },
        "story_candidates": [
            story("STY-0001", "selected"),
            story("STY-0002", "rejected"),
        ],
        "selected_story_id": "STY-0001",
        "single_candidate_reason": "",
        "claim_roles": {
            role: {"claim_ids": [], "none_reason": f"No {role} claim is assigned."}
            for role in ("foreground", "supporting", "supplement", "cut")
        },
        "argument_moves": [
            {
                "id": "MOV-0001",
                "position": 1,
                "stance": "assert",
                "reader_question": "What establishes the mechanism?",
                "assertion": "The controlled comparison establishes it.",
                "claim_ids": [],
                "result_item_ids": ["RHI-0001"],
                "next_move_id": "",
            }
        ],
        "visual_obligations": [
            {
                "id": "VIS-0001",
                "reader_task": "Compare the mechanisms.",
                "takeaway": "Only the controlled mechanism changes.",
                "claim_ids": [],
                "preferred_form": "paired plot",
                "status": "planned",
                "waiver_reason": "",
                "figure_ids": [],
            }
        ],
        "results_hierarchy": {
            "document": "_paperops/model/editorial/results-hierarchy.yml",
            "item_ids": ["RHI-0001"],
        },
        "extensions": {},
        "metadata": {"updated_at": "2026-07-11"},
    }
    results: dict[str, object] = {
        "schema_version": 1,
        "items": [
            {
                "id": "RHI-0001",
                "reader_question": "What changes?",
                "answer": "The controlled response changes.",
                "quantitative_evidence_and_unit_of_analysis": "Mean response per run.",
                "figure_table_role": "Main comparison.",
                "baseline_comparator_rationale": "The baseline isolates the control.",
                "consequence": "The mechanism is identified.",
                "next_item_id": "",
            }
        ],
    }
    return editorial, results


class PaperOpsModelCheckTest(unittest.TestCase):
    def write_documents(
        self,
        root: Path,
        editorial: dict[str, object],
        results: dict[str, object],
    ) -> tuple[Path, Path]:
        editorial_path = root / "editorial-model.yml"
        results_path = root / "results-hierarchy.yml"
        editorial_path.write_text(json.dumps(editorial, ensure_ascii=False), encoding="utf-8")
        results_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        return editorial_path, results_path

    def run_overrides(
        self,
        root: Path,
        editorial: dict[str, object],
        results: dict[str, object],
        *extra: object,
    ):
        editorial_path, results_path = self.write_documents(root, editorial, results)
        return run_python_script(
            SCRIPT,
            "--root",
            ROOT / "template",
            "--model",
            "editorial",
            "--document",
            editorial_path,
            "--results-document",
            results_path,
            *extra,
        )

    def test_starter_is_advisory_but_strict_fails_placeholders(self) -> None:
        advisory = run_python_script(SCRIPT, "--root", ROOT / "template")
        strict = run_python_script(SCRIPT, "--root", ROOT / "template", "--strict")

        self.assertEqual(advisory.returncode, 0, advisory.stderr)
        self.assertIn("# paperops-model-check", advisory.stdout)
        self.assertRegex(advisory.stdout, r"(?s)## Warnings.*`\[semantic\.placeholder\] [^`]+`: ")
        self.assertEqual(strict.returncode, 1)
        self.assertRegex(strict.stdout, r"(?s)## Errors.*`\[semantic\.placeholder\] [^`]+`: ")
        for section in ("Errors", "Warnings", "Info"):
            self.assertIn(f"## {section}", advisory.stdout)

    def test_schema_failure_stops_dependent_phases(self) -> None:
        editorial, results = valid_documents()
        editorial["unknown_field"] = True
        editorial["selected_story_id"] = "STY-missing"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(Path(tmp), editorial, results)

        self.assertEqual(result.returncode, 1)
        self.assertIn("[schema.additional] /unknown_field", result.stdout)
        self.assertNotIn("reference.dangling", result.stdout)
        self.assertNotIn("phase.prerequisite", result.stdout)

    def test_references_phase_reports_prerequisite_instead_of_schema_details(self) -> None:
        editorial, results = valid_documents()
        editorial["unknown_field"] = True
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("[phase.prerequisite]", result.stdout)
        self.assertNotIn("schema.additional", result.stdout)

    def test_references_phase_excludes_semantic_findings(self) -> None:
        editorial, results = valid_documents()
        editorial["story_candidates"] = [editorial["story_candidates"][0]]
        editorial["single_candidate_reason"] = ""
        editorial["selected_story_id"] = "STY-missing"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("reference.dangling", result.stdout)
        self.assertNotIn("semantic.story_count", result.stdout)

    def test_deferred_claim_and_figure_references_are_info_only(self) -> None:
        editorial, results = valid_documents()
        editorial["argument_moves"][0]["claim_ids"] = ["CLM-0001"]
        editorial["visual_obligations"][0]["figure_ids"] = ["FIG-0001"]
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(
                Path(tmp), editorial, results, "--phase", "references"
            )

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertRegex(result.stdout, r"(?s)## Info.*reference\.deferred")
        errors_section = result.stdout.split("## Warnings", 1)[0]
        self.assertNotIn("reference.deferred", errors_section)

    def test_print_hash_requires_a_clean_single_model(self) -> None:
        editorial, results = valid_documents()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = self.run_overrides(root, editorial, results, "--print-hash")
            invalid_editorial = copy.deepcopy(editorial)
            invalid_editorial["unknown_field"] = True
            invalid = self.run_overrides(
                root, invalid_editorial, results, "--print-hash"
            )

        self.assertEqual(valid.returncode, 0, valid.stderr)
        self.assertRegex(valid.stdout, r"^sha256:[0-9a-f]{64}\n?$")
        self.assertEqual(invalid.returncode, 1)
        self.assertNotRegex(invalid.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

        starter = run_python_script(
            SCRIPT,
            "--root",
            ROOT / "template",
            "--model",
            "editorial",
            "--print-hash",
        )
        self.assertEqual(starter.returncode, 1)
        self.assertIn("semantic.placeholder", starter.stdout)
        self.assertNotRegex(starter.stdout, r"(?m)^sha256:[0-9a-f]{64}$")

    def test_document_overrides_use_the_supplied_rhi_instead_of_starters(self) -> None:
        editorial, results = valid_documents()
        editorial["results_hierarchy"]["item_ids"] = ["RHI-custom"]
        editorial["story_candidates"][0]["result_order"] = ["RHI-custom"]
        editorial["story_candidates"][1]["result_order"] = ["RHI-custom"]
        editorial["argument_moves"][0]["result_item_ids"] = ["RHI-custom"]
        results["items"][0]["id"] = "RHI-custom"
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_overrides(Path(tmp), editorial, results)

        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("semantic.placeholder", result.stdout)
        self.assertNotIn("reference.dangling", result.stdout)

    def test_editorial_document_override_does_not_replace_default_results(self) -> None:
        editorial, _ = valid_documents()
        editorial["results_hierarchy"]["item_ids"] = ["RHI-missing"]
        with tempfile.TemporaryDirectory() as tmp:
            editorial_path = Path(tmp) / "editorial-model.yml"
            editorial_path.write_text(
                json.dumps(editorial, ensure_ascii=False), encoding="utf-8"
            )
            result = run_python_script(
                SCRIPT,
                "--root",
                ROOT / "template",
                "--model",
                "editorial",
                "--phase",
                "references",
                "--document",
                editorial_path,
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("reference.dangling", result.stdout)
        self.assertNotIn("phase.prerequisite", result.stdout)

    def test_unknown_model_and_phase_are_argparse_usage_errors(self) -> None:
        for args in (("--model", "unknown"), ("--phase", "unknown")):
            with self.subTest(args=args):
                result = run_python_script(SCRIPT, "--root", ROOT / "template", *args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("usage:", result.stderr)

    def test_copied_scaffold_preserves_starter_codes_and_severities(self) -> None:
        source = run_python_script(SCRIPT, "--root", ROOT / "template")
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            copied = run_python_script(
                target / "scripts" / "check-paperops-models.py", "--root", target
            )

        pattern = re.compile(r"`\[([^]]+)\] [^`]+`:.*", re.MULTILINE)

        def code_severity(report: str) -> set[tuple[str, str]]:
            current = ""
            found: set[tuple[str, str]] = set()
            for line in report.splitlines():
                if line.startswith("## "):
                    current = line[3:].lower().removesuffix("s")
                match = pattern.fullmatch(line.removeprefix("- "))
                if match:
                    found.add((match.group(1), current))
            return found

        self.assertEqual(source.returncode, 0, source.stderr)
        self.assertEqual(copied.returncode, 0, copied.stderr)
        self.assertEqual(code_severity(source.stdout), code_severity(copied.stdout))


if __name__ == "__main__":
    unittest.main()
