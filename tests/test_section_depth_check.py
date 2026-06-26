from __future__ import annotations

import tempfile
import textwrap
import unittest

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-section-depth.py"


class SectionDepthCheckTest(unittest.TestCase):
    def test_section_depth_gate_is_wired_into_finish_manuscript_workflow(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in [
                "Makefile",
                "template/Makefile",
                "template/manuscript/writing-profile.yml",
                "template/_paperops/defaults/contracts/results.yml",
                "template/_paperops/defaults/contracts/discussion.yml",
                "template/.agents/skills/finish-manuscript/SKILL.md",
                "template/.agents/skills/compile-results-section/SKILL.md",
                "template/.agents/skills/compile-discussion-section/SKILL.md",
                "template/.agents/skills/review-public-manuscript/SKILL.md",
                "docs/architecture.md",
                "docs/skill-catalog.md",
            ]
        )
        for expected in [
            "section-depth-check",
            "check-section-depth.py",
            "section_depth",
            "length_is_floor_not_target",
            "ja_chars",
            "en_words",
            "one-paragraph subsections",
        ]:
            with self.subTest(expected=expected):
                self.assertIn(expected, combined)

    def test_strict_flags_short_results_and_discussion_with_language_specific_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            write_profile(
                target,
                """
                section_depth:
                  soft_floor:
                    full_article:
                      results:
                        ja_chars: 120
                        en_words: 80
                        min_paragraphs: 2
                      discussion:
                        ja_chars: 120
                        en_words: 80
                        min_paragraphs: 2
                """,
            )
            write_section(target, "ja", "30_results.tex", "短い結果です。")
            write_section(target, "en", "30_results.tex", "Short result.")
            write_section(target, "ja", "40_discussion.tex", "短い考察です。")
            write_section(target, "en", "40_discussion.tex", "Short discussion.")

            warning = run_python_script(SCRIPT, "--root", target)
            strict = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(warning.returncode, 0, warning.stdout + warning.stderr)
        self.assertIn("## Warnings", warning.stdout)
        self.assertEqual(strict.returncode, 1)
        for expected in [
            "manuscript/ja/sections/30_results.tex",
            "日本語文字数",
            "manuscript/en/sections/30_results.tex",
            "English word count",
            "Results / Discussion の薄さは section-depth blocker",
        ]:
            self.assertIn(expected, strict.stdout)

    def test_counts_japanese_characters_and_english_words_after_stripping_tex_noise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            write_profile(
                target,
                """
                section_depth:
                  subsection_policy:
                    min_paragraphs_per_subsection: 1
                  soft_floor:
                    full_article:
                      results:
                        ja_chars: 25
                        en_words: 9
                        min_paragraphs: 1
                      discussion:
                        ja_chars: 25
                        en_words: 9
                        min_paragraphs: 1
                """,
            )
            ja_body = r"""
            % コメントだけで長さを稼いではいけない長い長いコメント
            \subsection{見出し}
            \textbf{観察結果は明確であり比較条件ごとの差も本文で説明できる。}
            """
            en_body = r"""
            % This long comment must not count as section depth.
            \subsection{Heading}
            \textbf{The observed contrast is explicit and tied to quantitative evidence.}
            """
            for language in ["ja", "en"]:
                write_section(target, language, "30_results.tex", ja_body if language == "ja" else en_body)
                write_section(target, language, "40_discussion.tex", ja_body if language == "ja" else en_body)

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("section-depth-check", result.stdout)


def write_profile(target, section_depth: str) -> None:
    profile = target / "manuscript" / "writing-profile.yml"
    text = profile.read_text(encoding="utf-8")
    marker = "\nsection_depth:\n"
    if marker in text:
        text = text.split(marker, 1)[0].rstrip() + "\n\n"
    else:
        text = text.rstrip() + "\n\n"
    profile.write_text(
        text + textwrap.dedent(section_depth).lstrip(),
        encoding="utf-8",
    )


def write_section(target, language: str, name: str, body: str) -> None:
    path = target / "manuscript" / language / "sections" / name
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
