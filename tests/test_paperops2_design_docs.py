from __future__ import annotations

from collections import Counter
import re
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

    def markdown_section(self, text: str, heading: str) -> str:
        lines = text.splitlines()
        start = lines.index(heading)
        end = next(
            (index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")),
            len(lines),
        )
        return "\n".join(lines[start:end])

    def makefile_python_gates(self) -> set[str]:
        gates = set()
        for makefile, prefix in [("Makefile", ""), ("template/Makefile", "template/")]:
            for script in re.findall(r"\$\(PYTHON\)\s+([^\s]+\.py)\b", self.read(makefile)):
                rel = f"{prefix}{script}" if prefix and not script.startswith("template/") else script
                if rel.endswith("cli-smoke.py") or rel.endswith("collect-note-context.py"):
                    continue
                gates.add(rel)
        return gates

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

    def test_authority_layout_matches_current_paths_and_defers_future_layout(self) -> None:
        text = self.read("docs/adr/0001-authority-ownership-layout.md")
        current_layout = self.markdown_section(text, "## Current physical layout")
        for required in [
            "`_paperops/defaults/contracts/` | paperops-managed default",
            "`_paperops/contracts/` | project-owned contract overlay",
            "`_paperops/model/editorial/` | project-owned typed state",
            "`.paperops/cache/` | generated cache",
            "repo 外 | local/confidential state",
            "`manuscript/` | living human-edited manuscript source",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, current_layout)

        future_layout = self.markdown_section(text, "## Future layout candidates")
        for required in ["project-state/", ".paperops-cache/", "local-state/", "snapshots/"]:
            with self.subTest(required=required):
                self.assertIn(required, future_layout)
        self.assertIn("非規範的", future_layout)
        self.assertIn("後続の migration ADR", future_layout)

    def test_current_layout_splits_mixed_view_and_submission_authorities(self) -> None:
        text = self.read("docs/adr/0001-authority-ownership-layout.md")
        rows = {
            cells[0].removeprefix("`").removesuffix("`"): cells
            for cells in self.disposition_rows(text, "## Current physical layout")
            if len(cells) == 3
        }
        expected = {
            "_paperops/notes/views/ (pure overview views)": "generated read-only projection",
            "_paperops/notes/views/ (controlled authoring views)": "project-owned editable decision",
            "submission/ (mutable candidate)": "derived replaceable artifact",
            "submission/ (submitted round snapshots)": "immutable publication evidence",
        }
        for asset, authority in expected.items():
            with self.subTest(asset=asset):
                self.assertIn(asset, rows)
                if asset in rows:
                    self.assertEqual(rows[asset][1], authority)

        if not expected.keys() <= rows.keys():
            return

        view_notes = " ".join(
            rows[asset][2]
            for asset in expected
            if asset.startswith("_paperops/notes/views/")
        )
        self.assertIn("同一 container", view_notes)
        self.assertIn("file type ごとに authority が異なる", view_notes)
        self.assertIn(
            "living `manuscript/` とは別",
            rows["submission/ (mutable candidate)"][2],
        )
        self.assertIn(
            "candidate と authority を混同しない",
            rows["submission/ (submitted round snapshots)"][2],
        )

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
            "template/_paperops/defaults/workflow/",
            "template/_paperops/contracts/",
            "template/_paperops/model/",
            "template/_paperops/claims/",
            "template/_paperops/evidence/",
            "template/_paperops/evidence/figures/",
            "template/_paperops/evidence/results/",
            "template/_paperops/evidence/sources/",
            "template/_paperops/refs/",
            "template/_paperops/notes/views/ (pure overview views)",
            "template/_paperops/notes/views/ (controlled authoring views)",
            "template/_paperops/review/",
            "template/_paperops/requests/",
            "template/_paperops/workflow/",
            "template/story/",
            "template/manuscript/",
            "template/submission/ (mutable candidate)",
            "template/submission/ (submitted round snapshots)",
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
        checker_files |= {
            "template/scripts/lint-bib.py",
            "template/scripts/mirror-check.py",
            "template/scripts/mirror-freshness-check.py",
            "template/scripts/readiness-check.py",
        }
        root_checkers = {
            "scripts/check-release-version-truth.py",
            "scripts/check-scaffold-package-boundary.py",
        }
        expected = {
            "## Root governance layer": root_families
            | root_skills
            | root_checkers
            | self.make_targets("Makefile"),
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

        for asset in [
            "template/scripts/check-paperops-models.py",
            "template/Makefile::schema-check",
        ]:
            with self.subTest(asset=asset, check="P1-A explicit inventory"):
                self.assertIn(asset, downstream_rows)

        root_rows = {
            cells[0].removeprefix("`").removesuffix("`"): cells
            for cells in self.disposition_rows(text, "## Root governance layer")
            if len(cells) == 8
        }
        self.assertIn("Makefile::schema-check", root_rows)

    def test_disposition_splits_overview_and_controlled_authoring_views(self) -> None:
        text = self.read("docs/paperops2-disposition.md")
        rows = {
            cells[0].removeprefix("`").removesuffix("`"): cells
            for cells in self.disposition_rows(text, "## Downstream template layer")
            if len(cells) == 8
        }
        overview = rows["template/_paperops/notes/views/ (pure overview views)"]
        controlled = rows["template/_paperops/notes/views/ (controlled authoring views)"]
        self.assertEqual(overview[3], "redirect")
        self.assertIn("generated read-only projection", overview[2])
        self.assertEqual(controlled[3], "adapt")
        self.assertIn("project-owned", controlled[2])
        self.assertIn("human-written", controlled[4])
        self.assertIn("P1", controlled[5])
        self.assertIn("compatibility readers", controlled[6])
        self.assertIn("strict validation", controlled[7])

        adr_rows = {
            cells[0].removeprefix("`").removesuffix("`"): cells
            for cells in self.disposition_rows(
                self.read("docs/adr/0001-authority-ownership-layout.md"),
                "## Current physical layout",
            )
            if len(cells) == 3
        }
        for asset in [
            "_paperops/notes/views/ (pure overview views)",
            "_paperops/notes/views/ (controlled authoring views)",
        ]:
            with self.subTest(adr_asset=asset):
                self.assertIn(asset, adr_rows)
        if not {
            "_paperops/notes/views/ (pure overview views)",
            "_paperops/notes/views/ (controlled authoring views)",
        } <= adr_rows.keys():
            return
        self.assertEqual(
            overview[2],
            adr_rows["_paperops/notes/views/ (pure overview views)"][1],
        )
        self.assertEqual(
            controlled[2],
            adr_rows["_paperops/notes/views/ (controlled authoring views)"][1],
        )

    def test_disposition_has_all_current_downstream_authority_families(self) -> None:
        text = self.read("docs/paperops2-disposition.md")
        rows = {
            cells[0].removeprefix("`").removesuffix("`"): cells
            for cells in self.disposition_rows(text, "## Downstream template layer")
            if len(cells) == 8
        }
        expected_authorities = {
            "template/_paperops/defaults/workflow/": "paperops-managed workflow default",
            "template/_paperops/contracts/": "project-owned contract overlay",
            "template/_paperops/refs/": "project-owned research/provenance state",
            "template/story/": "project-owned human story concept",
            "template/submission/ (mutable candidate)": "derived replaceable artifact",
            "template/submission/ (submitted round snapshots)": "immutable publication evidence",
        }
        for asset, authority in expected_authorities.items():
            with self.subTest(asset=asset):
                self.assertIn(asset, rows)
                if asset in rows:
                    self.assertEqual(len(rows[asset]), 8)
                    self.assertEqual(rows[asset][2], authority)
                    self.assertTrue(all(rows[asset]))

        if not expected_authorities.keys() <= rows.keys():
            return

        self.assertIn("raw/private/local", rows["template/_paperops/refs/"][6])
        self.assertIn("追跡外", rows["template/_paperops/refs/"][6])
        self.assertIn(
            "living manuscript と分離",
            rows["template/submission/ (mutable candidate)"][6],
        )
        self.assertIn(
            "candidate と authority を混同しない",
            rows["template/submission/ (submitted round snapshots)"][6],
        )

    def test_checker_inventory_covers_every_deterministic_make_gate(self) -> None:
        text = self.read("docs/paperops2-disposition.md")
        self.assertIn(
            "deterministic gate として Makefile から起動される Python entrypoint",
            text,
        )
        documented = {
            cells[0].removeprefix("`").removesuffix("`")
            for heading in ["## Root governance layer", "## Downstream template layer"]
            for cells in self.disposition_rows(text, heading)
            if len(cells) == 8
        }
        expected = self.makefile_python_gates() | {"scripts/check-release-version-truth.py"}
        self.assertEqual(expected - documented, set())

    def test_rfc_and_matrix_have_exact_cross_links(self) -> None:
        rfc = self.read("docs/rfcs/0001-paperops-2.md")
        matrix = self.read("docs/paperops2-disposition.md")
        self.assertIn("[Disposition matrix](../paperops2-disposition.md)", rfc)
        for link in [
            "[RFC 0001](rfcs/0001-paperops-2.md)",
            "[ADR 0001](adr/0001-authority-ownership-layout.md)",
            "[ADR 0002](adr/0002-cli-agent-compiler-boundary.md)",
            "[ADR 0003](adr/0003-revision-state-hash.md)",
        ]:
            with self.subTest(link=link):
                self.assertIn(link, matrix)

    def test_rfc_compatibility_invariant_is_complete_in_its_own_section(self) -> None:
        invariant = self.markdown_section(
            self.read("docs/rfcs/0001-paperops-2.md"), "## 互換 invariant"
        )
        for required in [
            "JA/EN mirror",
            "block ID",
            "quantity",
            "figure",
            "citation",
            "authoring intent",
            "predicted result",
            "analysis request",
            "claim",
            "move",
            "block",
            "selective stale",
            "living manuscript",
            "immutable submission snapshot",
            "paperops-managed default",
            "project-owned state",
            "migration validation",
            "legacy deletion",
            "conflict stop",
            "strict",
            "advisory",
            "diagnostic",
            "starter",
            "raw reviewer text",
            "credential",
            "absolute path",
            "unpublished raw data",
            "generated cache",
            "tracked state に含めない",
        ]:
            with self.subTest(required=required):
                self.assertIn(required, invariant)

    def test_fixture_policy_uses_synthetic_cases_and_reserves_paths(self) -> None:
        text = self.read("docs/paperops2-evaluation-fixtures.md")
        self.assertIn("各 case は最低2つの story candidates を持つ", text)
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

    def test_changelog_keeps_p0a_design_separate_from_p1_delivery(
        self,
    ) -> None:
        text = self.read("CHANGELOG.md")
        entries = [
            line
            for line in text.splitlines()
            if line.startswith("- ")
            and "段階再設計" in line
            and "合成 fixture 方針" in line
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
