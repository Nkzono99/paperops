from __future__ import annotations

import tempfile
import textwrap
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "readiness-check.py"
MIRROR_FRESHNESS_SCRIPT = ROOT / "template" / "scripts" / "mirror-freshness-check.py"


class ReadinessCheckTest(unittest.TestCase):
    def test_starter_smoke_summarizes_expected_placeholders(self) -> None:
        result = run_python_script(
            SCRIPT,
            "--root",
            ROOT / "template",
            "--allow-placeholders",
            "--starter-smoke",
            encoding="utf-8",
            errors="replace",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("starter scaffold", result.stdout)
        self.assertNotIn("README.md:1", result.stdout)
        self.assertNotIn("_paperops/notes/reviewer-model.md:46", result.stdout)
        self.assertLessEqual(result.stdout.count("- "), 6)

    def test_root_template_readiness_uses_starter_smoke_profile(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn(
            "template/scripts/readiness-check.py --root template --allow-placeholders --starter-smoke",
            makefile,
        )

    def test_starter_smoke_still_rejects_broken_managed_metadata_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            metadata = target / "manuscript" / "publication-metadata.toml"
            metadata.write_text(
                metadata.read_text(encoding="utf-8").replace(
                    'source_language = "ja"',
                    'source_language = ""',
                ),
                encoding="utf-8",
            )

            result = run_python_script(
                SCRIPT,
                "--root",
                target,
                "--allow-placeholders",
                "--starter-smoke",
                encoding="utf-8",
                errors="replace",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("starter scaffold metadata default `manuscript.source_language` is missing", result.stdout)

    def test_requires_decision_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            (target / "_paperops" / "notes" / "decision-log.md").unlink()

            result = run_python_script(SCRIPT, "--root", target, "--allow-placeholders")

        self.assertEqual(result.returncode, 1)
        self.assertIn("`_paperops/notes/decision-log.md` が見つかりません", result.stdout)

    def test_warns_when_public_bibliography_includes_mypapers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            main_tex = target / "manuscript" / "ja" / "main.tex"
            main_tex.write_text(
                main_tex.read_text(encoding="utf-8").replace(
                    r"\bibliography{references}",
                    r"\bibliography{references,mypapers}",
                ),
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--allow-placeholders")

        self.assertEqual(result.returncode, 0)
        self.assertIn("bibliography に `mypapers` が含まれています", result.stdout)

    def test_submission_mode_flags_metadata_human_verification_and_frontmatter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            submission = target / "submission" / "demo-venue"
            submission.mkdir()
            (submission / "main.tex").write_text(
                textwrap.dedent(
                    r"""\
                    \documentclass{article}
                    \title{Title Goes Here}
                    \author{Author A}
                    \begin{document}
                    \begin{keypoints}
                    \item TODO
                    \end{keypoints}
                    \begin{abstract}
                    TBD
                    \end{abstract}
                    Open Research Statement: TBD.
                    \end{document}
                    """
                ),
                encoding="utf-8",
            )

            result = run_python_script(
                SCRIPT,
                "--root",
                target,
                "--allow-placeholders",
                "--require-submission",
            )

        self.assertEqual(result.returncode, 1)
        for expected in [
            "author 1 に ORCID がありません",
            "author 1 に email がありません",
            "`licenses.code` が未記入です",
            "`open_research.data_doi_or_persistent_url` が未記入です",
            "`human_verification.pdf_reviewed` が承認されていません",
            "`submission/demo-venue/main.tex` の front matter にスターター用プレースホルダーが残っています",
            "`submission/demo-venue/main.tex` の Key Points が未確定です",
            "`submission/demo-venue/main.tex` の Open Research Statement が未確定です",
        ]:
            self.assertIn(expected, result.stdout)

    def test_submission_mode_requires_data_software_citation_key_in_bib(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            metadata = target / "manuscript" / "publication-metadata.toml"
            metadata.write_text(
                metadata.read_text(encoding="utf-8").replace(
                    'data_software_citation_key = ""',
                    'data_software_citation_key = "DATASET2026"',
                ),
                encoding="utf-8",
            )
            submission = target / "submission" / "demo-venue"
            submission.mkdir()
            (submission / "main.tex").write_text(
                "\\documentclass{article}\n\\begin{document}\nReady.\n\\end{document}\n",
                encoding="utf-8",
            )

            result = run_python_script(
                SCRIPT,
                "--root",
                target,
                "--allow-placeholders",
                "--require-submission",
            )

        self.assertEqual(result.returncode, 1)
        self.assertIn("data/software citation key `DATASET2026` が `.bib` にありません", result.stdout)

    def test_mirror_freshness_strict_fails_on_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            ledger = target / "manuscript" / "mirror" / "block-ledger.yml"
            ledger.unlink()

            non_strict = run_python_script(
                MIRROR_FRESHNESS_SCRIPT,
                "--root",
                target / "manuscript",
            )
            strict = run_python_script(
                MIRROR_FRESHNESS_SCRIPT,
                "--root",
                target / "manuscript",
                "--strict",
            )

        self.assertEqual(non_strict.returncode, 0)
        self.assertEqual(strict.returncode, 1)
        self.assertIn("--update", strict.stdout)


if __name__ == "__main__":
    unittest.main()
