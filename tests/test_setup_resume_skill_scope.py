from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SetupResumeSkillScopeTest(unittest.TestCase):
    def read_skill(self, name: str) -> str:
        return (ROOT / "template" / ".agents" / "skills" / name / "SKILL.md").read_text(
            encoding="utf-8"
        )

    def test_setup_separates_lightweight_detection_from_semantic_initialization(self) -> None:
        setup = self.read_skill("setup")

        for required in [
            "軽量確認",
            "意味論スターター",
            "必要時に読む",
            "_handoff/",
            "refs/local/locations.toml",
            "uvx",
            "make ci",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, setup)

        self.assertLess(len(setup.splitlines()), 190)

    def test_resume_session_uses_required_and_on_demand_reading(self) -> None:
        resume = self.read_skill("resume-session")

        for required in [
            "常時読む",
            "必要時に読む",
            "notes/handoff.md",
            "manuscript/mirror/status.md",
            "scientific-gate",
            "review/feedback/",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, resume)

        self.assertLess(len(resume.splitlines()), 70)

    def test_resolve_local_paths_is_runops_directory_link_skill(self) -> None:
        skill = self.read_skill("resolve-local-paths")

        for required in [
            "runops ディレクトリリンク",
            "`runops-main`",
            "pops links list --resolve-local",
            "research-request-handoff-check",
            "job submit は行わない",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, skill)


if __name__ == "__main__":
    unittest.main()
