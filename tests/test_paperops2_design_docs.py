from __future__ import annotations

from collections import Counter
import unittest

from tests.helpers import ROOT


class PaperOps2DesignDocsTest(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def make_targets(self, rel: str) -> set[str]:
        targets = set()
        for line in self.read(rel).splitlines():
            if not line or line[0].isspace() or ":" not in line:
                continue
            target = line.split(":", 1)[0]
            if all(char.isalnum() or char in "._-" for char in target):
                targets.add(f"{rel}::{target}")
        return targets

    def disposition_rows(self, text: str, heading: str) -> list[list[str]]:
        lines = text.splitlines()
        start = lines.index(heading) + 1
        end = next(
            (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
            len(lines),
        )
        rows = []
        for line in lines[start:end]:
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells[0] == "asset" or all(set(cell) <= {"-"} for cell in cells):
                continue
            rows.append(cells)
        return rows

    def test_rfc_defines_success_retreat_and_rollout(self) -> None:
        text = self.read("docs/rfcs/0001-paperops-2.md")
        for required in [
            "## 成功指標",
            "## 撤退条件",
            "## 段階導入",
            "legacy-authoritative",
            "shadow",
            "v2-authoritative",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_adrs_split_authority_execution_and_state(self) -> None:
        expected = {
            "docs/adr/0001-authority-ownership-layout.md": [
                "paperops-managed default",
                "project-owned typed state",
                "writable",
                "per-ID record",
            ],
            "docs/adr/0002-cli-agent-compiler-boundary.md": [
                "deterministic",
                "Agent",
                "Writer packet",
                "暗黙実行しない",
            ],
            "docs/adr/0003-revision-state-hash.md": [
                "macro state",
                "object revision",
                "canonical hash",
                "dependency hash",
            ],
        }
        for path, required_values in expected.items():
            text = self.read(path)
            for required in required_values:
                with self.subTest(path=path, required=required):
                    self.assertIn(required, text)

    def test_writer_and_macro_state_have_single_authority_boundaries(self) -> None:
        expected = {
            "docs/rfcs/0001-paperops-2.md": [
                "Writer は patch を生成するだけ",
                "deterministic applicator",
            ],
            "docs/adr/0001-authority-ownership-layout.md": [
                "Writer は patch を生成するだけ",
                "authority へ直接書き込まない",
            ],
            "docs/adr/0002-cli-agent-compiler-boundary.md": [
                "承認済み patch は human または将来の deterministic applicator が適用する",
                "authority へ直接書き込まない",
            ],
            "docs/adr/0003-revision-state-hash.md": [
                "read-only deterministic projection",
                "writable authority ではない",
                "下位の authority fact/revision",
            ],
        }
        for path, required_values in expected.items():
            text = self.read(path)
            for required in required_values:
                with self.subTest(path=path, required=required):
                    self.assertIn(required, text)

    def test_disposition_matrix_covers_layers_and_all_decisions(self) -> None:
        text = self.read("docs/paperops2-disposition.md")
        for required in [
            "## Root governance layer",
            "## Downstream template layer",
            "retain",
            "adapt",
            "redirect",
            "deprecate",
            "remove",
            "investigate",
            "writer before",
            "writer after",
            "removal condition",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_disposition_matrix_has_complete_structured_rows(self) -> None:
        text = self.read("docs/paperops2-disposition.md")
        root_families = {
            "src/paperops/cli/",
            ".agents/skills/",
            ".claude/skills/",
            "scripts/",
            "Makefile",
            ".github/workflows/",
            "docs/",
        }
        downstream_families = {
            "template/_paperops/defaults/schemas/",
            "template/_paperops/defaults/contracts/",
            "template/_paperops/model/",
            "template/_paperops/claims/",
            "template/_paperops/evidence/",
            "template/_paperops/evidence/figures/",
            "template/_paperops/evidence/results/",
            "template/_paperops/evidence/sources/",
            "template/_paperops/notes/views/",
            "template/_paperops/review/",
            "template/_paperops/requests/",
            "template/_paperops/workflow/",
            "template/manuscript/",
            "template/.agents/skills/",
            "template/.claude/skills/",
            "template/scripts/check-*.py",
            "template/Makefile",
        }
        root_skills = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / ".agents" / "skills").glob("*/SKILL.md")
        }
        template_skills = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "template" / ".agents" / "skills").glob("*/SKILL.md")
        }
        checker_files = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "template" / "scripts").glob("check-*.py")
        }
        expected = {
            "## Root governance layer": root_families | root_skills | self.make_targets("Makefile"),
            "## Downstream template layer": downstream_families
            | template_skills
            | checker_files
            | self.make_targets("template/Makefile"),
        }
        allowed_dispositions = {"retain", "adapt", "redirect", "deprecate", "investigate"}

        for heading, expected_assets in expected.items():
            rows = self.disposition_rows(text, heading)
            assets = []
            for row_number, cells in enumerate(rows, start=1):
                with self.subTest(heading=heading, row=row_number, check="column count"):
                    self.assertEqual(len(cells), 8)
                if len(cells) != 8:
                    continue
                asset = cells[0].removeprefix("`").removesuffix("`")
                assets.append(asset)
                with self.subTest(asset=asset, check="non-empty cells"):
                    self.assertTrue(all(cells))
                with self.subTest(asset=asset, check="disposition"):
                    self.assertIn(cells[3], allowed_dispositions)
                if cells[3] == "investigate":
                    reason_fields = f"{cells[6]} {cells[7]}"
                    with self.subTest(asset=asset, check="investigate reason"):
                        self.assertIn("理由:", reason_fields)

            counts = Counter(assets)
            with self.subTest(heading=heading, check="asset set"):
                self.assertEqual(set(assets), expected_assets)
            with self.subTest(heading=heading, check="duplicates"):
                self.assertEqual(
                    {asset for asset, count in counts.items() if count > 1},
                    set(),
                )

        downstream_rows = {
            cells[0].removeprefix("`").removesuffix("`"): cells
            for cells in self.disposition_rows(text, "## Downstream template layer")
            if len(cells) == 8
        }
        model_row = downstream_rows["template/_paperops/model/"]
        self.assertEqual(model_row[3], "investigate")
        self.assertIn("modelごとに単一writerをP1で決定する必要がある", model_row[6])

    def test_fixture_policy_uses_synthetic_cases_and_reserves_paths(self) -> None:
        text = self.read("docs/paperops2-evaluation-fixtures.md")
        for required in [
            "tests/fixtures/editorial/mechanism-led/",
            "tests/fixtures/editorial/boundary-led/",
            "tests/fixtures/editorial/negative-result-led/",
            "story candidates",
            "selection reason",
            "rejection reason",
            "Results hierarchy",
            "claim role",
            "argument move",
            "期待 diagnostic",
            "合成データ",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_fixture_policy_keeps_private_raw_data_outside_repo_and_defers_fixtures(
        self,
    ) -> None:
        text = self.read("docs/paperops2-evaluation-fixtures.md")
        for required in [
            "private 案件と raw data は repo に追跡しない",
            "sanitized aggregate だけを残す",
            "schema 適合 fixture 本体は P1 で追加する",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, text)

    def test_current_specification_indexes_paperops2_design_sources(self) -> None:
        text = self.read("docs/current-specification.md")
        rows = []
        for line in text.splitlines():
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if cells and cells[0] == "PaperOps 2 design":
                rows.append(cells)

        self.assertEqual(len(rows), 1)
        self.assertEqual(len(rows[0]), 3)
        source_of_truth = rows[0][1]
        for path in [
            "docs/rfcs/0001-paperops-2.md",
            "docs/adr/",
            "docs/paperops2-disposition.md",
            "docs/paperops2-evaluation-fixtures.md",
        ]:
            with self.subTest(path=path):
                self.assertIn(path, source_of_truth)

    def test_readme_links_to_paperops2_rfc(self) -> None:
        text = self.read("README.md")
        self.assertIn(
            "[docs/rfcs/0001-paperops-2.md](docs/rfcs/0001-paperops-2.md)",
            text,
        )

    def test_unreleased_changelog_keeps_p0a_design_separate_from_p1_delivery(
        self,
    ) -> None:
        text = self.read("CHANGELOG.md")
        unreleased = text.split("## Unreleased", 1)[1].split("\n## ", 1)[0]
        entries = [
            line
            for line in unreleased.splitlines()
            if line.startswith("- ") and "PaperOps 2" in line
        ]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        for required in [
            "RFC",
            "authority / ownership",
            "CLI / Agent / compiler",
            "revision / hash",
            "disposition",
            "合成 fixture 方針",
            "設計資料として追加した",
            "P1 以降",
            "提供済みとするものではない",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, entry)
        self.assertNotRegex(
            entry,
            r"P1 以降.{0,120}(?:提供済み|実装済み)(?!とするものではない)",
        )
