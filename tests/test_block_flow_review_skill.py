from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class BlockFlowReviewSkillTemplateTest(unittest.TestCase):
    def test_review_block_flow_skill_defines_block_operations_and_author_stance(self) -> None:
        skill = read_template("template/.agents/skills/review-block-flow/SKILL.md")

        for required in [
            "review-block-flow",
            "block operation table",
            "reader_question",
            "author_move",
            "why_here",
            "next_block_expectation",
            "author stance",
            "move",
            "split",
            "merge",
            "delete",
            "add",
            "keep",
            "DRAFTED -> AUDITED",
            "section architecture",
            "薄い構成を保存しない",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

    def test_claude_wrapper_imports_block_flow_skill(self) -> None:
        wrapper = read_template("template/.claude/skills/review-block-flow/SKILL.md")

        self.assertIn(
            "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/review-block-flow/SKILL.md",
            wrapper,
        )

    def test_finish_and_section_compilers_route_through_block_flow_review(self) -> None:
        texts = {
            "finish": read_template("template/.agents/skills/finish-manuscript/SKILL.md"),
            "results": read_template("template/.agents/skills/compile-results-section/SKILL.md"),
            "discussion": read_template(
                "template/.agents/skills/compile-discussion-section/SKILL.md"
            ),
        }

        for name, text in texts.items():
            with self.subTest(name=name):
                self.assertIn("review-block-flow", text)
                self.assertIn("block operation table", text)

        self.assertIn("DRAFTED -> AUDITED", texts["finish"])
        self.assertIn("design-paper-figure", texts["finish"])
        self.assertIn("Figure design brief", texts["finish"])

    def test_downstream_docs_expose_block_flow_review(self) -> None:
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
            "review-block-flow",
            "block operation table",
            "author stance",
            "reader question",
            "move / split / merge / delete / add",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs)


if __name__ == "__main__":
    unittest.main()
