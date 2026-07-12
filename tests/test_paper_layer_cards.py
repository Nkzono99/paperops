from __future__ import annotations

import re
import tempfile
import unittest


from tests.helpers import ROOT, copy_template, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-paper-layer-cards.py"
STARTER_EXAMPLE_ID_RE = re.compile(
    r"\b(?:CLM|RES|SRC|FIG|GATE|RP|EP|AREQ|WREQ|RVW|FB|RSP|SG|ASM|UPG)-0001\b"
)


class PaperLayerCardsTest(unittest.TestCase):
    def test_template_layer_cards_are_valid(self) -> None:
        result = run_python_script(SCRIPT, "--root", ROOT / "template")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("paper typed layers", result.stdout)
        self.assertIn("typed model authority", result.stdout)

    def test_missing_typed_index_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            feedback_template = target / "_paperops" / "model" / "issues" / "index.yml"
            feedback_template.unlink()

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`_paperops/model/issues/index.yml` が見つかりません", result.stdout)

    def test_view_metadata_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            view = target / "_paperops" / "notes" / "views" / "result-pattern-map.md"
            view.write_text("# 結果パターンビュー\n", encoding="utf-8")

            result = run_python_script(SCRIPT, "--root", target)

        self.assertEqual(result.returncode, 1)
        self.assertIn("`_paperops/notes/views/result-pattern-map.md` に `view_type: pure_overview` がありません", result.stdout)

    def test_starter_views_mark_concrete_id_rows_as_examples(self) -> None:
        views_dir = ROOT / "template" / "_paperops" / "notes" / "views"
        for view in sorted(views_dir.glob("*.md")):
            if view.name == "README.md":
                continue
            text = view.read_text(encoding="utf-8")
            if not STARTER_EXAMPLE_ID_RE.search(text):
                continue
            with self.subTest(view=view.name):
                self.assertIn("starter_example_rows: true", text)
                self.assertIn("初期状態の `*-0001` 行は例示行", text)

    def test_source_templates_define_promotion_decisions(self) -> None:
        source_template = (
            ROOT / "template" / "_paperops" / "defaults" / "schemas" / "research-source.schema.json"
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
