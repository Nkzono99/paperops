from __future__ import annotations

import unittest

from tests.helpers import ROOT


HOPS_SKILL_NAMES = {"harnessops-bridge"}


def is_hops_skill(name: str) -> bool:
    return name.startswith("hops-") or name in HOPS_SKILL_NAMES


class HopsPluginSkillBoundaryTest(unittest.TestCase):
    def test_repo_does_not_vendor_hops_plugin_skills(self) -> None:
        vendored: list[str] = []
        for rel_dir in [
            ".agents/skills",
            ".claude/skills",
            "template/.agents/skills",
            "template/.claude/skills",
        ]:
            skill_root = ROOT / rel_dir
            if not skill_root.exists():
                continue
            for path in sorted(skill_root.iterdir()):
                if path.is_dir() and is_hops_skill(path.name):
                    vendored.append(f"{rel_dir}/{path.name}")

        self.assertEqual(
            [],
            vendored,
            "HOPS skills are provided by the HarnessOps plugin; do not vendor repo-local copies.",
        )


if __name__ == "__main__":
    unittest.main()
