from __future__ import annotations

import unittest

from tests.helpers import ROOT


class P1ADocumentationTest(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def assert_surface_contains(self, path: str, required: list[str]) -> None:
        text = self.read(path)
        for value in required:
            with self.subTest(path=path, required=value):
                self.assertIn(value, text)

    def test_downstream_interfaces_define_managed_and_project_owned_contract(self) -> None:
        required = [
            "registry.yml",
            "paperops-managed",
            "editorial-model.yml",
            "project-owned",
            "schema",
            "references",
            "semantics",
            "hash",
            "make schema-check",
            "legacy controlled view",
            "P2",
        ]
        for path in ["template/AGENTS.md", "template/CLAUDE.md", "template/README.md"]:
            self.assert_surface_contains(path, required)

    def test_root_docs_state_current_p1b_scope_and_later_deferrals(self) -> None:
        required = [
            "P1-B",
            "Research",
            "Editorial",
            "Results hierarchy",
            "Manuscript",
            "Issue",
            "Publication",
            "schema",
            "references",
            "semantics",
            "P2",
            "P3",
            "P4",
            "hash",
        ]
        for path in [
            "README.md",
            "docs/architecture.md",
            "docs/current-specification.md",
            "docs/skill-catalog.md",
        ]:
            self.assert_surface_contains(path, required)

    def test_cli_docs_define_schema_check_phase_and_exit_behavior(self) -> None:
        self.assert_surface_contains(
            "docs/cli.md",
            [
                "make schema-check",
                "schema",
                "references",
                "semantics",
                "hash",
                "--strict",
                "exit 1",
                "reference.deferred",
            ],
        )

    def test_migration_and_changelog_preserve_opt_in_order(self) -> None:
        for path in ["docs/migrations/v0.md", "CHANGELOG.md"]:
            self.assert_surface_contains(
                path,
                [
                    "M0-0004",
                    "managed",
                    "project-owned",
                    "make schema-check",
                    "--strict",
                    "authority",
                    "legacy controlled view",
                ],
            )

    def test_fixture_and_hash_contract_is_documented(self) -> None:
        required = [
            "mechanism-led",
            "boundary-led",
            "negative-result-led",
            "canonical semantic-v1 hash",
        ]
        for path in ["README.md", "docs/current-specification.md", "docs/skill-catalog.md"]:
            self.assert_surface_contains(path, required)


if __name__ == "__main__":
    unittest.main()
