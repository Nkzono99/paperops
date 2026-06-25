from __future__ import annotations

import tempfile
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-argument-focus.py"


class ArgumentFocusCheckTest(unittest.TestCase):
    def test_strict_fails_on_local_condition_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "ja" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\n12 条件中 2 条件で正の work が残ったが、これは直接証明ではない。\n"
                + "8 条件中 0 条件であり、screening に限定する。\n"
                + "この結果は bracket であり、robust ranking は主張しない。\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("ローカル条件数の列挙", result.stdout)
        self.assertIn("防御的・限定的な表現", result.stdout)
        self.assertIn("/map-result-patterns", result.stdout)
        self.assertIn("/contextualize-conditions", result.stdout)

    def test_missing_condition_context_map_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            (target / "notes" / "views" / "condition-context-map.md").unlink()
            (target / "notes" / "condition-context-map.md").unlink()

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`notes/views/condition-context-map.md` が見つかりません", result.stdout)

    def test_missing_result_pattern_map_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            (target / "notes" / "views" / "result-pattern-map.md").unlink()
            (target / "notes" / "result-pattern-map.md").unlink()

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`notes/views/result-pattern-map.md` が見つかりません", result.stdout)

    def test_warns_on_comparator_and_equilibrium_overclaim_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "en" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\nThe surface representation is lost in a center-charge approximation.\n"
                + "The completed run reaches charging equilibrium at the final snapshot.\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("direct comparator", result.stdout)
        self.assertIn("run completion と physical equilibrium", result.stdout)

    def test_warns_when_notes_compress_handoff_into_label_only_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            note = target / "notes" / "handoff.md"
            note.write_text(
                note.read_text(encoding="utf-8")
                + "\n- RR-0009 current-balance gap\n"
                + "- figure-redesign-open\n",
                encoding="utf-8",
            )

            result = run_python_script(SCRIPT, "--root", target, "--strict")

        self.assertEqual(result.returncode, 1)
        self.assertIn("notes/handoff.md", result.stdout)
        self.assertIn("ラベルだけ", result.stdout)
        self.assertIn("前提・判断根拠・本文への影響", result.stdout)

    def test_ignores_yaml_frontmatter_when_scanning_note_labels(self) -> None:
        result = run_python_script(SCRIPT, "--root", ROOT / "template")

        self.assertEqual(result.returncode, 0)
        self.assertNotIn("notes/views/result-pattern-map.md:2", result.stdout)
        self.assertNotIn("view_type", result.stdout)


if __name__ == "__main__":
    unittest.main()
