from __future__ import annotations

import tempfile
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-paper-layer-cards.py"


class PaperLayerCardsTest(unittest.TestCase):
    def test_template_layer_cards_are_valid(self) -> None:
        result = run_python_script(SCRIPT, "--root", ROOT / "template")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("paper layer cards", result.stdout)
        self.assertIn("カード層と互換ビューの外形に問題は見つかりませんでした", result.stdout)

    def test_missing_feedback_template_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            feedback_template = target / "_paperops" / "review" / "feedback" / "feedback-card-template.md"
            if feedback_template.exists():
                feedback_template.unlink()

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`_paperops/review/feedback/feedback-card-template.md` が見つかりません", result.stdout)

    def test_view_metadata_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            view = target / "_paperops" / "notes" / "views" / "result-pattern-map.md"
            view.write_text("# 結果パターンビュー\n", encoding="utf-8")

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`_paperops/notes/views/result-pattern-map.md` に `view_type: pure_overview` がありません", result.stdout)

    def test_source_templates_define_promotion_decisions(self) -> None:
        source_template = (
            ROOT / "template" / "_paperops" / "evidence" / "sources" / "source-card-template.md"
        ).read_text(encoding="utf-8")
        summary_template = (
            ROOT / "template" / "_paperops" / "refs" / "summaries" / "summary-template.md"
        ).read_text(encoding="utf-8")
        related_work = (
            ROOT / "template" / "_paperops" / "notes" / "related-work-map.md"
        ).read_text(encoding="utf-8")

        for required in [
            "promotion_decision",
            "promotion_required_when",
            "claim_boundary",
            "parameter_choice",
            "reviewer_objection",
            "method_precedent",
            "source card に昇格",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, source_template + "\n" + summary_template + "\n" + related_work)


if __name__ == "__main__":
    unittest.main()
