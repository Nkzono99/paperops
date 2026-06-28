from __future__ import annotations

import unittest
from pathlib import Path

from tests.helpers import make_var_tokens


ROOT = Path(__file__).resolve().parents[1]


class FinishManuscriptGateTest(unittest.TestCase):
    def test_template_makefile_runs_section_contracts_as_audit_and_finish_strict_gate(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")
        audit_checks = make_var_tokens(makefile, "AUDIT_CHECKS")
        finish_checks = make_var_tokens(makefile, "FINISH_MANUSCRIPT_CHECKS")

        self.assertIn("section-contract-check", makefile)
        self.assertIn("audit: $(AUDIT_CHECKS)", makefile)
        self.assertIn("section-contract-check", audit_checks)
        self.assertIn("section-contract-check", finish_checks)
        self.assertIn("scripts/check-section-contracts.py --root . --strict", makefile)
        self.assertIn("scripts/check-public-terms.py --root . --strict", makefile)

    def test_root_smoke_includes_section_contract_advisory_check(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        smoke_checks = make_var_tokens(makefile, "SMOKE_CHECKS")

        self.assertIn("section-contract-check", makefile)
        self.assertIn("smoke: $(SMOKE_CHECKS)", makefile)
        self.assertIn("section-contract-check", smoke_checks)
        self.assertIn("template/scripts/check-section-contracts.py --root template", makefile)

    def test_root_makefile_mirrors_finish_gate_for_prediction_and_claim_evidence(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        smoke_checks = make_var_tokens(makefile, "SMOKE_CHECKS")

        self.assertIn("predicted-results-check", makefile)
        self.assertIn("predicted-results-check", smoke_checks)
        self.assertIn("template/scripts/check-predicted-results.py --root template", makefile)
        self.assertIn("template/scripts/check-predicted-results.py --root template --scope all --strict", makefile)
        self.assertIn("template/scripts/check-claim-evidence.py --root template --strict", makefile)


if __name__ == "__main__":
    unittest.main()
