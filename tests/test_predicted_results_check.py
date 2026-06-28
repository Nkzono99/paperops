from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, make_var_tokens, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-predicted-results.py"


def write_predicted_block(
    project: Path,
    *,
    request_id: str = "AREQ-0008",
    complete_markers: bool = True,
    body: str = "The enhancement is approximately xx in Fig. xx.",
) -> None:
    section = project / "manuscript" / "en" / "sections" / "30_results.tex"
    markers = [
        f"% PREDICTED-RESULT: status=analysis-needed; publish=false; request={request_id}.",
    ]
    if complete_markers:
        markers.extend(
            [
                f"% SIM-REQUEST: {request_id}; extend the existing sweep with one additional simulation.",
                "% EXPECTATION-BASIS: prior run monotonicity and conservation constrain the expected sign.",
                "% REPLACE-XX: replace xx values, uncertainty, caption scope, and claim scope after execution.",
            ]
        )
    section.write_text(
        section.read_text(encoding="utf-8")
        + "\n% block: results-predicted-check\n"
        + "\n".join(markers)
        + "\n"
        + body
        + "\n",
        encoding="utf-8",
    )


def write_analysis_request(project: Path, request_id: str = "AREQ-0008", status: str = "predicted") -> None:
    card = project / "_paperops" / "requests" / "analysis" / f"{request_id}.md"
    card.parent.mkdir(parents=True, exist_ok=True)
    card.write_text(
        "\n".join(
            [
                "---",
                f"id: {request_id}",
                "type: analysis_request",
                f"status: {status}",
                "target_project_link: runops-main",
                "runops_id: draft:PAPER-REQ-0008",
                "---",
                "",
                "# Analysis Request",
                "",
                "## Prediction plan",
                "",
                "- estimand: flux enhancement",
                "- denominator: same simulated surface cells",
                "- unit of analysis: simulation run",
                "- comparison: baseline charging run",
                "- negative/null route: revise Results hierarchy and claim scope before submission.",
                "",
            ]
        ),
        encoding="utf-8",
    )


class PredictedResultsCheckTest(unittest.TestCase):
    def test_authoring_mode_reports_managed_prediction_without_failing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_predicted_block(project)
            write_analysis_request(project)

            result = run_python_script(SCRIPT, "--root", project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Warnings", result.stdout)
        self.assertIn("results-predicted-check", result.stdout)
        self.assertIn("AREQ-0008", result.stdout)
        self.assertIn("authoring source", result.stdout)

    def test_strict_mode_fails_on_predicted_markers_and_xx_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_predicted_block(project)
            write_analysis_request(project)

            result = run_python_script(SCRIPT, "--root", project, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("Errors", result.stdout)
        self.assertIn("PREDICTED-RESULT", result.stdout)
        self.assertIn("xx placeholder", result.stdout)
        self.assertIn("submission candidate", result.stdout)

    def test_warns_when_predicted_block_lacks_marker_set_or_request_card(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_predicted_block(project, request_id="AREQ-0999", complete_markers=False)

            result = run_python_script(SCRIPT, "--root", project)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("SIM-REQUEST", result.stdout)
        self.assertIn("EXPECTATION-BASIS", result.stdout)
        self.assertIn("REPLACE-XX", result.stdout)
        self.assertIn("AREQ-0999", result.stdout)
        self.assertIn("analysis request card", result.stdout)

    def test_submission_scope_strictly_rejects_predictions_in_submission_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            submission = project / "submission" / "demo"
            submission.mkdir(parents=True, exist_ok=True)
            (submission / "main.tex").write_text(
                "\n".join(
                    [
                        r"\section{Results}",
                        "% block: submission-predicted",
                        "% PREDICTED-RESULT: status=analysis-needed; publish=false; request=AREQ-0012.",
                        "The submitted result remains approximately xx.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", project, "--scope", "submission")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("submission/demo/main.tex", result.stdout)
        self.assertIn("PREDICTED-RESULT", result.stdout)

    def test_makefile_exposes_authoring_and_submission_prediction_gates(self) -> None:
        makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")
        audit_checks = make_var_tokens(makefile, "AUDIT_CHECKS")
        submission_gate_checks = make_var_tokens(makefile, "SUBMISSION_GATE_CHECKS")
        pre_submit_checks = make_var_tokens(makefile, "PRE_SUBMIT_CHECKS")

        self.assertIn("predicted-results-check:", makefile)
        self.assertIn("submission-gate: $(SUBMISSION_GATE_CHECKS)", makefile)
        self.assertIn("check-predicted-results.py --root .", makefile)
        self.assertIn("check-predicted-results.py --root . --scope all --strict", makefile)
        self.assertIn("predicted-results-check", audit_checks)
        self.assertIn("predicted-results-check", submission_gate_checks)
        self.assertIn("submission-gate", pre_submit_checks)


if __name__ == "__main__":
    unittest.main()
