from __future__ import annotations

import unittest

from tests.helpers import ROOT


class CurrentSpecificationIndexTest(unittest.TestCase):
    def test_current_specification_is_short_index_not_duplicate_spec(self) -> None:
        spec = (ROOT / "docs" / "current-specification.md").read_text(encoding="utf-8")
        lines = spec.splitlines()

        self.assertLessEqual(len(lines), 120)
        self.assertIn("正本ではなく", spec)
        self.assertIn("source of truth", spec)
        self.assertNotIn("docs/release.md", spec)
        self.assertIn(".agents/skills/release/SKILL.md", spec)
        self.assertEqual(
            [
                "## Source Of Truth",
                "## Current Invariants",
                "## Update Rule",
            ],
            [line for line in lines if line.startswith("## ")],
        )
        for required in [
            "docs/architecture.md",
            "docs/cli.md",
            "docs/migrations/",
            "template/.agents/skills/*/SKILL.md",
            "template/scripts/check-skill-mirror.py",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, spec)

    def test_current_specification_points_to_actual_bib_roots(self) -> None:
        spec = (ROOT / "docs" / "current-specification.md").read_text(encoding="utf-8")

        self.assertIn("manuscript/shared/bib/", spec)
        self.assertIn("_paperops/refs/bib/curated/", spec)
        self.assertIn("_paperops/refs/bib/imported/", spec)
        self.assertIn("legacy `refs/bib/`", spec)


if __name__ == "__main__":
    unittest.main()
