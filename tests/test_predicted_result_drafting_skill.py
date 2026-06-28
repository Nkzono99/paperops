from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script


COLLECT_SCRIPT = ROOT / "template" / "scripts" / "collect-manuscript-review.py"


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class PredictedResultDraftingSkillTemplateTest(unittest.TestCase):
    def test_skill_defines_predictive_result_scaffold_and_guardrails(self) -> None:
        skill = read_template("template/.agents/skills/draft-predicted-results/SKILL.md")

        for required in [
            "draft-predicted-results",
            "予測稿",
            "PREDICTED-RESULT",
            "SIM-REQUEST",
            "EXPECTATION-BASIS",
            "REPLACE-XX",
            "xx",
            "Future Work",
            "defensive",
            "analysis-needed",
            "_paperops/requests/analysis/",
            "現実的",
            "既存の延長線上",
            "must_not_claim",
            "ready-to-write",
            "投稿前に必ず実データへ置換",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

    def test_claude_wrapper_imports_predicted_result_skill(self) -> None:
        wrapper = read_template("template/.claude/skills/draft-predicted-results/SKILL.md")

        self.assertIn(
            "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/draft-predicted-results/SKILL.md",
            wrapper,
        )

    def test_route_skills_expose_predictive_result_path(self) -> None:
        texts = {
            "finish": read_template("template/.agents/skills/finish-manuscript/SKILL.md"),
            "scientific_gate": read_template("template/.agents/skills/scientific-gate/SKILL.md"),
            "results": read_template("template/.agents/skills/compile-results-section/SKILL.md"),
            "discussion": read_template(
                "template/.agents/skills/compile-discussion-section/SKILL.md"
            ),
            "finalize": read_template("template/.agents/skills/finalize-manuscript/SKILL.md"),
        }

        for name, text in texts.items():
            with self.subTest(name=name):
                self.assertIn("draft-predicted-results", text)

        self.assertIn("PREDICTED-RESULT", texts["scientific_gate"])
        self.assertIn("analysis-needed", texts["scientific_gate"])
        self.assertIn("xx", texts["finalize"])
        self.assertIn("投稿版", texts["finalize"])

    def test_downstream_docs_expose_predictive_result_drafting(self) -> None:
        docs = "\n".join(
            [
                read_template("docs/skill-catalog.md"),
                read_template("docs/architecture.md"),
                read_template("docs/current-specification.md"),
                read_template("template/AGENTS.md"),
                read_template("template/CLAUDE.md"),
                read_template("template/README.md"),
                read_template("CHANGELOG.md"),
            ]
        )

        for required in [
            "draft-predicted-results",
            "PREDICTED-RESULT",
            "SIM-REQUEST",
            "予測稿",
            "Future Work",
            "_paperops/requests/analysis/",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs)

    def test_goal_finish_routine_lists_predicted_result_skill(self) -> None:
        finish = read_template("template/.agents/skills/finish-manuscript/SKILL.md")
        catalog = read_template("docs/skill-catalog.md")
        agents = read_template("template/AGENTS.md")
        claude = read_template("template/CLAUDE.md")
        readme = read_template("template/README.md")

        self.assertIn("goal 中", finish)
        self.assertIn("draft-predicted-results", finish)
        self.assertRegex(catalog, r"### 原稿完成[\s\S]*draft-predicted-results")
        self.assertRegex(agents, r"原稿完成補助:.*draft-predicted-results")
        self.assertRegex(claude, r"原稿完成補助:.*draft-predicted-results")
        self.assertRegex(readme, r"/finish-manuscript.*draft-predicted-results")

    def test_collect_manuscript_review_collects_predicted_result_markers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = copy_template(tmp)
            section = target / "manuscript" / "ja" / "sections" / "30_results.tex"
            section.write_text(
                section.read_text(encoding="utf-8")
                + "\n% block: results-predicted-simulation\n"
                + "% PREDICTED-RESULT: 未実行シミュレーションの予測稿。AREQ-0002 が閉じるまで publish 不可。\n"
                + "% SIM-REQUEST: AREQ-0002; 既存条件 sweep の延長として追加実行する。\n"
                + "% EXPECTATION-BASIS: 既存 run の単調傾向と保存則から符号を予測する。\n"
                + "% REPLACE-XX: flux enhancement と uncertainty を実測値へ置換する。\n",
                encoding="utf-8",
            )

            result = run_python_script(COLLECT_SCRIPT, "--root", target, "--date", "2026-06-28")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for marker in [
            "`PREDICTED-RESULT`",
            "`SIM-REQUEST`",
            "`EXPECTATION-BASIS`",
            "`REPLACE-XX`",
            "results-predicted-simulation",
            "AREQ-0002",
        ]:
            with self.subTest(marker=marker):
                self.assertIn(marker, result.stdout)


if __name__ == "__main__":
    unittest.main()
