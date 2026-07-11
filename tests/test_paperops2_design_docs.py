from __future__ import annotations

import unittest

from tests.helpers import ROOT


class PaperOps2DesignDocsTest(unittest.TestCase):
    def read(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

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
