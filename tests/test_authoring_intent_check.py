from __future__ import annotations

import tempfile
import textwrap
import unittest

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-authoring-intent.py"
COLLECT_SCRIPT = ROOT / "template" / "scripts" / "collect-manuscript-review.py"


class AuthoringIntentCheckTest(unittest.TestCase):
    def test_strict_flags_authoring_intent_in_public_prose(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "ja" / "sections" / "40_discussion.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nこの論文の claim を強めるために必要な追加作業は四つである。\n",
                encoding="utf-8",
            )

            advisory = run_python_script(SCRIPT, "--root", target)
            strict = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(advisory.returncode, 0, advisory.stdout + advisory.stderr)
        self.assertIn("## Warnings", advisory.stdout)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("authoring intent", strict.stdout)
        self.assertIn("manuscript/ja/sections/40_discussion.tex", strict.stdout)
        self.assertIn("% INTENT:", strict.stdout)
        self.assertIn("_paperops/notes/", strict.stdout)

    def test_allows_authoring_intent_when_written_as_tex_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "ja" / "sections" / "40_discussion.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\n% INTENT: この論文の claim を強めるための追加作業を discussion boundary に移す。\n"
                + "% TODO-PAPER: 後で reviewer-facing limitation として整理する。\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("authoring intent leak は見つかりませんでした", result.stdout)

    def test_flags_english_authoring_intent_and_allows_suppression(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "en" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nThe additional work needed to strengthen the claim is summarized here.\n"
                + "% paperops: allow-authoring-intent -- discusses work plan as an object of study\n"
                + "An authoring note can itself be an empirical artifact in this methods paper.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("additional work needed to strengthen", result.stdout)
        self.assertNotIn("An authoring note can itself", result.stdout)

    def test_authoring_intent_guard_is_wired_into_finish_workflow(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in [
                "template/Makefile",
                "template/AGENTS.md",
                "template/CLAUDE.md",
                "template/README.md",
                "template/.agents/skills/finish-manuscript/SKILL.md",
                "template/.agents/skills/collect-manuscript-review/SKILL.md",
                "template/.agents/skills/review-public-manuscript/SKILL.md",
                "docs/cli.md",
                "docs/skill-catalog.md",
                "CHANGELOG.md",
            ]
        )
        for expected in [
            "authoring-intent-check",
            "check-authoring-intent.py",
            "% INTENT:",
            "% TODO-PAPER:",
            "authoring intent",
            "closes #71",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

    def test_collect_manuscript_review_collects_intent_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "ja" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\n% block: results-authoring-intent\n"
                + "% INTENT: AI Writer が本文に混ぜそうな作業意図をここへ退避する。\n",
                encoding="utf-8",
            )

            result = run_python_script(COLLECT_SCRIPT, "--root", target, "--date", "2026-06-28")
            review_ledger_exists = (
                target / "_paperops" / "notes" / "reviews" / "review-2026-06-28.md"
            ).is_file()
            legacy_ledger_exists = (target / "notes" / "reviews" / "review-2026-06-28.md").exists()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("% INTENT:", result.stdout)
        self.assertIn("`INTENT`", result.stdout)
        self.assertIn("results-authoring-intent", result.stdout)
        self.assertTrue(review_ledger_exists)
        self.assertFalse(legacy_ledger_exists)


if __name__ == "__main__":
    unittest.main()
