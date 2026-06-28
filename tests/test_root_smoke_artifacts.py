from __future__ import annotations

import unittest

from tests.helpers import ROOT


class RootSmokeArtifactTest(unittest.TestCase):
    def test_root_smoke_writes_generated_reports_outside_template_tree(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

        self.assertIn(
            "--report .paperops/cache/template/mirror-smoke-check.md",
            makefile,
        )
        self.assertIn(
            "--output .paperops/cache/template/session-context.generated.md",
            makefile,
        )
        self.assertNotIn(
            "--report template/manuscript/mirror/reports/smoke-check.md",
            makefile,
        )
        self.assertNotIn(
            "--output template/_paperops/notes/session-context.generated.md",
            makefile,
        )

    def test_root_cache_is_ignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

        self.assertIn(".paperops/cache/", gitignore)


if __name__ == "__main__":
    unittest.main()
