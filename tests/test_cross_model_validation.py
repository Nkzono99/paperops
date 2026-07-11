from __future__ import annotations

import sys
import unittest

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "template/scripts"))

import paperops_models  # noqa: E402
from paperops_models import CatalogObject, ObjectCatalog, validate_cross_model_references  # noqa: E402
from paperops_schema import load_registry, semantic_hash  # noqa: E402


def obj(object_id: str, object_type: str, model: str, document: dict) -> CatalogObject:
    return CatalogObject(object_id, object_type, model, document, 1, semantic_hash(document), f"/{object_id}")


class CrossModelValidationTest(unittest.TestCase):
    def test_reference_contract_types_are_registered(self) -> None:
        registry = load_registry(ROOT / "template")
        self.assertEqual(
            paperops_models.validate_reference_contract_definition(registry), []
        )

    def test_unknown_contract_type_is_rejected(self) -> None:
        original = paperops_models.REFERENCE_CONTRACTS
        try:
            paperops_models.REFERENCE_CONTRACTS = {
                **original,
                "unknown_source": {"refs": frozenset({"unknown_target"})},
            }
            findings = paperops_models.validate_reference_contract_definition(
                load_registry(ROOT / "template")
            )
        finally:
            paperops_models.REFERENCE_CONTRACTS = original
        self.assertEqual(
            {finding.code for finding in findings},
            {"registry.reference_contract"},
        )

    def test_resolves_editorial_research_manuscript_and_issue_edges(self) -> None:
        objects = [
            obj("CLM-0001", "claim", "research", {"gate_id": "GATE-0001", "result_refs": ["RES-0001"], "figure_refs": ["FIG-0001"]}),
            obj("GATE-0001", "scientific_gate", "research", {"claim_id": "CLM-0001"}),
            obj("RES-0001", "result", "research", {"claim_refs": ["CLM-0001"]}),
            obj("FIG-0001", "figure", "research", {"claim_refs": ["CLM-0001"]}),
            obj("MOV-0001", "move", "editorial", {"claim_ids": ["CLM-0001"], "result_item_ids": ["RHI-0001"]}),
            obj("RHI-0001", "results_item", "results_hierarchy", {}),
            obj("SEC-0001", "section", "manuscript", {"editorial_move_refs": ["MOV-0001"], "research_refs": ["CLM-0001"]}),
            obj("BLK-0001", "block", "manuscript", {"section_id": "SEC-0001", "claim_refs": ["CLM-0001"], "result_refs": ["RES-0001"], "figure_refs": ["FIG-0001"], "source_refs": []}),
            obj("FB-0001", "feedback", "issue", {"targets": [{"kind": "manuscript_block", "id": "BLK-0001"}]}),
        ]
        self.assertEqual(validate_cross_model_references(ObjectCatalog({o.object_id: o for o in objects}, ())), [])

    def test_dangling_wrong_type_and_duplicate_cardinality_are_distinct(self) -> None:
        claim = obj("CLM-0001", "claim", "research", {"gate_id": "RES-0001", "result_refs": ["RES-9999"], "figure_refs": []})
        result = obj("RES-0001", "result", "research", {})
        block = obj("BLK-0001", "block", "manuscript", {"section_id": "SEC-9999", "claim_refs": ["CLM-0001", "CLM-0001"], "result_refs": [], "figure_refs": [], "source_refs": []})
        catalog = ObjectCatalog({o.object_id: o for o in (claim, result, block)}, ())
        codes = {finding.code for finding in validate_cross_model_references(catalog)}
        self.assertEqual({"reference.dangling", "reference.type", "reference.cardinality"}, codes)


if __name__ == "__main__":
    unittest.main()
