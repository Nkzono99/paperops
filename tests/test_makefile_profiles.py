from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, make_var_tokens


class MakefileProfileTest(unittest.TestCase):
    def test_makefiles_prefer_python311_before_plain_python(self) -> None:
        for path in [ROOT / "Makefile", ROOT / "template" / "Makefile"]:
            makefile = path.read_text(encoding="utf-8")
            with self.subTest(path=path):
                self.assertIn("resolve-python.sh", makefile)
                self.assertIn("PYTHON_BOOTSTRAP ?= $(PYTHON_FALLBACK)", makefile)
                self.assertIn("$(PYTHON_FALLBACK)", makefile)
                self.assertNotIn("command -v python3 2>/dev/null || command -v python", makefile)

    def test_python_resolver_requires_python311_or_newer(self) -> None:
        resolver = ROOT / "template" / "scripts" / "resolve-python.sh"
        bash = shutil.which("bash")
        self.assertIsNotNone(bash)

        with tempfile.TemporaryDirectory() as tmp:
            fake_bin = Path(tmp) / "bin"
            fake_bin.mkdir()
            self.write_fake_python(fake_bin / "python3", exit_code=1)
            self.write_fake_python(fake_bin / "python", exit_code=1)
            env = os.environ.copy()
            env["PATH"] = str(fake_bin)

            failed = subprocess.run(
                [str(bash), str(resolver), tmp],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

            self.write_fake_python(fake_bin / "python3.11", exit_code=0)
            passed = subprocess.run(
                [str(bash), str(resolver), tmp],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )

        self.assertEqual(failed.returncode, 1)
        self.assertIn("requires Python 3.11 or newer", failed.stderr)
        self.assertEqual(passed.returncode, 0, passed.stderr)
        self.assertTrue(passed.stdout.strip().endswith("python3.11"))

    @staticmethod
    def write_fake_python(path: Path, *, exit_code: int) -> None:
        path.write_text(
            "#!/bin/sh\n"
            f"exit {exit_code}\n",
            encoding="utf-8",
        )
        path.chmod(0o755)

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

    def test_schema_check_is_wired_to_advisory_profiles_only(self) -> None:
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        template_makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        self.assertIn("schema-check:", root_makefile)
        self.assertIn(
            "$(PYTHON) template/scripts/check-paperops-models.py --root template",
            root_makefile,
        )
        self.assertIn("schema-check", make_var_tokens(root_makefile, "SMOKE_CHECKS"))
        self.assertNotIn(
            "schema-check", make_var_tokens(root_makefile, "FINISH_MANUSCRIPT_CHECKS")
        )

        self.assertIn("schema-check:", template_makefile)
        self.assertIn(
            "$(PYTHON) scripts/check-paperops-models.py --root .", template_makefile
        )
        self.assertIn("schema-check", make_var_tokens(template_makefile, "AUDIT_CHECKS"))
        self.assertNotIn(
            "schema-check",
            make_var_tokens(template_makefile, "FINISH_MANUSCRIPT_CHECKS"),
        )
        self.assertNotIn(
            "schema-check", make_var_tokens(template_makefile, "PRE_SUBMIT_CHECKS")
        )

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

    def test_template_pre_submit_rechecks_warning_capable_content_gates_as_strict(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        for command in [
            "scripts/check-argument-focus.py --root . --strict",
            "scripts/check-card-coverage.py --root . --strict",
        ]:
            with self.subTest(command=command):
                self.assertIn(command, makefile)


if __name__ == "__main__":
    unittest.main()
