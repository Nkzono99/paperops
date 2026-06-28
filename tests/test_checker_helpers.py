from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "template" / "scripts"))

from paperops_checks import Finding, emit_findings, frontmatter, read_text  # noqa: E402


class CheckerHelperTest(unittest.TestCase):
    def test_emit_findings_keeps_checker_report_shape_and_exit_code(self) -> None:
        out = io.StringIO()
        findings = [
            Finding("warning", "soft issue"),
            Finding("error", "hard issue"),
        ]

        with redirect_stdout(out):
            code = emit_findings(
                "demo-check",
                findings,
                success_message="clean",
                fail_on_warnings=False,
            )

        self.assertEqual(code, 1)
        self.assertIn("# demo-check", out.getvalue())
        self.assertIn("## Errors", out.getvalue())
        self.assertIn("- hard issue", out.getvalue())
        self.assertIn("## Warnings", out.getvalue())
        self.assertIn("- soft issue", out.getvalue())

    def test_emit_findings_can_fail_on_warnings(self) -> None:
        out = io.StringIO()

        with redirect_stdout(out):
            code = emit_findings(
                "demo-check",
                [Finding("warning", "soft issue")],
                success_message="clean",
                fail_on_warnings=True,
            )

        self.assertEqual(code, 1)
        self.assertIn("## Warnings", out.getvalue())

    def test_emit_findings_prints_success_message_when_clean(self) -> None:
        out = io.StringIO()

        with redirect_stdout(out):
            code = emit_findings("demo-check", [], success_message="clean")

        self.assertEqual(code, 0)
        self.assertIn("clean", out.getvalue())

    def test_frontmatter_and_read_text_use_checker_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "card.md"
            path.write_bytes(
                b"---\nid: CARD-1\nfield: value\n---\n\n# Body\ninvalid: \xff\n"
            )

            text = read_text(path)

        self.assertIn("invalid", text)
        self.assertEqual(frontmatter(text), "id: CARD-1\nfield: value")


if __name__ == "__main__":
    unittest.main()
