from __future__ import annotations

import unittest

from tests.helpers import ROOT


def read_template(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class DevelopManuscriptContentSkillTest(unittest.TestCase):
    def test_skill_exists_as_content_only_authoring_entry(self) -> None:
        skill = read_template(
            "template/.agents/skills/develop-manuscript-content/SKILL.md"
        )
        wrapper = read_template(
            "template/.claude/skills/develop-manuscript-content/SKILL.md"
        )

        for required in [
            "name: develop-manuscript-content",
            "manuscript content",
            "claims",
            "storyline",
            "figure story",
            "Results hierarchy",
            "Discussion functions",
            "Methods definition",
            "section compiler",
            "review-block-flow",
            "draft-predicted-results",
            "content-first-gate",
            "submission metadata",
            "ORCID",
            "affiliation",
            "license",
            "submission-gate",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)

        self.assertIn(
            "@${CLAUDE_SKILL_DIR}/../../../.agents/skills/develop-manuscript-content/SKILL.md",
            wrapper,
        )

    def test_docs_route_content_authoring_before_submission_hygiene(self) -> None:
        docs = "\n".join(
            [
                read_template("docs/skill-catalog.md"),
                read_template("template/README.md"),
                read_template("template/AGENTS.md"),
                read_template("template/CLAUDE.md"),
                read_template("template/.agents/skills/finish-manuscript/SKILL.md"),
                read_template("CHANGELOG.md"),
            ]
        )

        for required in [
            "develop-manuscript-content",
            "原稿内容",
            "投稿メタデータ",
            "ORCID",
            "submission-gate",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, docs)


if __name__ == "__main__":
    unittest.main()
