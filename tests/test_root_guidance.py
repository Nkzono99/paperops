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

    def test_root_smoke_policy_is_not_contradictory(self) -> None:
        expected = "`template/` 配下変更、リスクの高い変更、公開前確認では `make smoke`"
        for name in ["AGENTS.md", "CLAUDE.md"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            with self.subTest(name=name):
                self.assertIn(expected, text)
                self.assertNotIn("マージ前に `make smoke` を実行する", text)
                self.assertNotIn("`make smoke` は必須 gate ではない。", text)

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

    def test_downstream_readme_treats_setup_as_existing_repo_adoption(self) -> None:
        readme = (ROOT / "template" / "README.md").read_text(encoding="utf-8")

        self.assertIn("pops init", readme)
        self.assertIn("すでに `.pops/manifest.toml` を持つ", readme)
        self.assertIn("既存 repo を paperops 管理に採用するときだけ", readme)
        self.assertIn("uvx --from paper-harness-cli pops doctor", readme)
        self.assertNotIn("`uvx --from paper-harness-cli pops setup` と `pops doctor`", readme)

    def test_cli_docs_explain_legacy_managed_update_horizon(self) -> None:
        cli = (ROOT / "docs" / "cli.md").read_text(encoding="utf-8")

        self.assertIn("legacy top-level の `contracts/*` と `workflow/*`", cli)
        self.assertIn("新規 scaffold の正道ではなく", cli)
        self.assertIn("M0-0002", cli)

    def test_root_docs_index_typed_results_hierarchy_boundary(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in [
                "README.md",
                "docs/architecture.md",
                "docs/current-specification.md",
                "docs/skill-catalog.md",
                "CHANGELOG.md",
            ]
        )

        self.assertIn("_paperops/model/editorial/results-hierarchy.yml", combined)
        self.assertIn("typed Results hierarchy", combined)
        self.assertIn("legacy Markdown", combined)


if __name__ == "__main__":
    unittest.main()
