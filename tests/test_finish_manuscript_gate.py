from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FinishManuscriptGateTest(unittest.TestCase):
    def test_template_makefile_runs_section_contracts_as_audit_and_finish_strict_gate(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("section-contract-check", makefile)
        self.assertRegex(makefile, r"audit:.*section-contract-check")
        self.assertIn("scripts/check-section-contracts.py --root . --strict", makefile)
        self.assertIn("scripts/check-public-terms.py --root . --strict", makefile)

    def test_root_smoke_includes_section_contract_advisory_check(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("section-contract-check", makefile)
        self.assertRegex(makefile, r"smoke:.*section-contract-check")
        self.assertIn("template/scripts/check-section-contracts.py --root template", makefile)

    def test_root_makefile_mirrors_finish_gate_for_prediction_and_claim_evidence(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn("predicted-results-check", makefile)
        self.assertRegex(makefile, r"smoke:.*predicted-results-check")
        self.assertIn("template/scripts/check-predicted-results.py --root template", makefile)
        self.assertIn("template/scripts/check-predicted-results.py --root template --scope all --strict", makefile)
        self.assertIn("template/scripts/check-claim-evidence.py --root template --strict", makefile)


if __name__ == "__main__":
    unittest.main()
