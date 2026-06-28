from __future__ import annotations

import unittest

from tests.helpers import ROOT


class RootGuidanceTest(unittest.TestCase):
    def test_root_guidance_points_to_existing_skill_directories(self) -> None:
        for name in ["AGENTS.md", "CLAUDE.md"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertNotIn(".Codex/skills", text)
                self.assertIn(".agents/skills/", text)
                self.assertIn(".claude/skills/", text)

    def test_root_agents_and_claude_share_harnessops_boundary(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        boundary = "HOPS 関連 skill は HarnessOps plugin から参照し、この repo には vendor しない。"

        self.assertIn(boundary, agents)
        self.assertIn(boundary, claude)

    def test_root_readme_describes_modern_paperops_internal_layout(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        for legacy_path in [
            "`evidence/`:",
            "`claims/`:",
            "`review/`:",
            "`requests/`:",
            "`notes/views/`:",
            "`contracts/`:",
            "`workflow/`:",
            "`refs/`:",
        ]:
            with self.subTest(legacy_path=legacy_path):
                self.assertNotIn(legacy_path, readme)
        for modern_path in [
            "`_paperops/evidence/`",
            "`_paperops/claims/`",
            "`_paperops/review/`",
            "`_paperops/requests/`",
            "`_paperops/notes/views/`",
            "`_paperops/contracts/`",
            "`_paperops/workflow/`",
            "`_paperops/refs/`",
        ]:
            with self.subTest(modern_path=modern_path):
                self.assertIn(modern_path, readme)


if __name__ == "__main__":
    unittest.main()
