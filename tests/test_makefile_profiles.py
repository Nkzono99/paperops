from __future__ import annotations

import unittest

from tests.helpers import ROOT, make_var_tokens


class MakefileProfileTest(unittest.TestCase):
    def test_root_smoke_uses_named_check_profile(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        smoke_checks = make_var_tokens(makefile, "SMOKE_CHECKS")
        finish_checks = make_var_tokens(makefile, "FINISH_MANUSCRIPT_CHECKS")

        self.assertIn("smoke: $(SMOKE_CHECKS)", makefile)
        self.assertIn("finish-manuscript-check: $(FINISH_MANUSCRIPT_CHECKS)", makefile)
        for target in [
            "cli-smoke",
            "section-contract-check",
            "section-depth-check",
            "predicted-results-check",
            "template-readiness-check",
        ]:
            with self.subTest(target=target):
                self.assertIn(target, smoke_checks)
        for target in [
            "section-contract-check",
            "predicted-results-check",
            "claim-evidence-check",
        ]:
            with self.subTest(target=target):
                self.assertIn(target, finish_checks)

    def test_template_profiles_group_ci_audit_finish_and_submission_targets(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("ci: $(CI_CHECKS) build-ja build-en", makefile)
        self.assertIn("audit: $(AUDIT_CHECKS)", makefile)
        self.assertIn("finish-manuscript-check: $(FINISH_MANUSCRIPT_CHECKS)", makefile)
        self.assertIn("submission-gate: $(SUBMISSION_GATE_CHECKS)", makefile)
        self.assertIn("pre-submit: $(PRE_SUBMIT_CHECKS)", makefile)

        expected = {
            "CI_CHECKS": ["lint-bib", "citation-check", "paper-layer-card-check"],
            "AUDIT_CHECKS": [
                "concept-term-check",
                "argument-focus-check",
                "section-depth-check",
                "research-request-handoff-check",
            ],
            "FINISH_MANUSCRIPT_CHECKS": [
                "storyline-check",
                "section-contract-check",
                "predicted-results-check",
                "claim-evidence-check",
            ],
            "SUBMISSION_GATE_CHECKS": [
                "public-terms-check",
                "authoring-intent-check",
                "research-request-handoff-check",
                "submission-drift-check",
            ],
            "PRE_SUBMIT_CHECKS": [
                "ci",
                "audit",
                "finish-manuscript-check",
                "lint-bib-pre-submit",
                "mirror-strict-check",
                "submission-gate",
            ],
        }
        for variable, targets in expected.items():
            tokens = make_var_tokens(makefile, variable)
            for target in targets:
                with self.subTest(variable=variable, target=target):
                    self.assertIn(target, tokens)


if __name__ == "__main__":
    unittest.main()
