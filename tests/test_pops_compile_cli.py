from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import copy_template, run_cli
from tests.test_p3_compile_inputs import tracked_tree_snapshot
from tests.test_p3_compile_materialize import approved_project

from paperops.cli.main import build_parser
from paperops.cli.compile_commands import render_compile_result
from paperops.model_migration.types import MigrationFinding


class PopsCompileCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = approved_project(Path(cls._tmp.name))

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        compile_root = self.project / ".paperops/compile"
        if compile_root.exists():
            import shutil

            shutil.rmtree(compile_root)

    def test_parser_exposes_exactly_three_compile_actions(self) -> None:
        parser = build_parser()
        compile_parser = next(
            action for action in parser._actions if getattr(action, "dest", None) == "command"
        ).choices["compile"]
        actions = next(
            action for action in compile_parser._actions if getattr(action, "dest", None) == "compile_action"
        ).choices
        self.assertEqual(set(actions), {"status", "prepare", "compare"})

    def test_prepare_status_compare_share_versioned_json_domain_results(self) -> None:
        before = tracked_tree_snapshot(self.project)
        code, raw, error = run_cli(["compile", "prepare", "all", str(self.project), "--json"])
        self.assertEqual(code, 0, error)
        prepared = json.loads(raw)
        self.assertEqual(prepared["schema_version"], 1)
        self.assertEqual(prepared["action"], "prepare")
        compile_id = prepared["result"]["compile_id"]

        code, raw, error = run_cli(["compile", "status", "all", str(self.project), "--json"])
        self.assertEqual(code, 0, error)
        status = json.loads(raw)
        self.assertEqual(status["action"], "status")
        self.assertIn(compile_id, [item["compile_id"] for item in status["results"]])

        code, raw, error = run_cli(
            ["compile", "compare", compile_id, compile_id, str(self.project), "--json"]
        )
        self.assertEqual(code, 0, error)
        compared = json.loads(raw)
        self.assertEqual(compared["action"], "compare")
        self.assertEqual(compared["result"]["changes"], [])
        self.assertEqual(before, tracked_tree_snapshot(self.project))
        self.assertNotIn(str(self.project), raw)

        code, human, error = run_cli(
            ["compile", "compare", compile_id, compile_id, str(self.project)]
        )
        self.assertEqual(code, 0, error)
        self.assertEqual(human.strip(), render_compile_result(compared))

    def test_repeat_and_refresh_are_explicit_runtime_facts(self) -> None:
        first = json.loads(
            run_cli(["compile", "prepare", "SEC-0002", str(self.project), "--json"])[1]
        )
        second = json.loads(
            run_cli(["compile", "prepare", "SEC-0002", str(self.project), "--json"])[1]
        )
        refreshed = json.loads(
            run_cli(
                ["compile", "prepare", "SEC-0002", str(self.project), "--refresh", "--json"]
            )[1]
        )
        self.assertEqual(first["result"]["compile_id"], second["result"]["compile_id"])
        self.assertTrue(second["result"]["reused"])
        self.assertTrue(refreshed["result"]["refreshed"])

    def test_block_scope_and_shadow_non_applicability_are_derived_by_domain(self) -> None:
        code, raw, error = run_cli(
            [
                "compile", "prepare", "SEC-0002", str(self.project),
                "--scope", "block", "--block", "BLK-0002", "--json",
            ]
        )
        self.assertEqual(code, 0, error)
        scope = json.loads(raw)["result"]
        self.assertTrue(scope["applicable"])

        code, raw, error = run_cli(
            [
                "compile", "prepare", "SEC-0002", str(self.project),
                "--shadow", "model-20260712T999999999999Z-999999999999", "--json",
            ]
        )
        self.assertEqual(code, 1, error)
        shadow = json.loads(raw)["result"]
        self.assertFalse(shadow["applicable"])
        self.assertEqual(shadow["status"], "blocked")

    def test_legacy_authority_is_a_domain_blocker_not_a_usage_or_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            project = copy_template(temporary)
            code, raw, error = run_cli(
                ["compile", "prepare", "all", str(project), "--json"]
            )
        self.assertEqual(code, 1, error)
        payload = json.loads(raw)
        self.assertTrue(payload["findings"])
        self.assertNotIn("traceback", raw.lower())
        self.assertNotIn(str(project), raw)

    def test_invalid_scope_shapes_and_ids_are_usage_results(self) -> None:
        cases = (
            ["compile", "prepare", "all", str(self.project), "--scope", "block", "--block", "BLK-0001"],
            ["compile", "prepare", "all", str(self.project), "--scope", "section"],
            ["compile", "prepare", "SEC-0001", str(self.project), "--scope", "manuscript"],
            ["compile", "prepare", "SEC-0001", str(self.project), "--scope", "block"],
            ["compile", "prepare", "SEC-0001", str(self.project), "--block", "BLK-0001"],
            ["compile", "compare", "../private", "compile-v1-ok", str(self.project)],
        )
        for argv in cases:
            with self.subTest(argv=argv):
                code, output, error = run_cli([*argv, "--json"])
                self.assertEqual(code, 2, error)
                payload = json.loads(output)
                self.assertTrue(payload["findings"])
                self.assertNotIn(str(self.project), output)
                self.assertNotIn("traceback", output.lower())

    def test_non_project_is_stable_and_compile_bypasses_update_notice(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch("paperops.cli.main.maybe_print_update_notice") as notice:
                code, raw, error = run_cli(
                    ["compile", "status", "all", temporary, "--json"]
                )
            self.assertEqual(code, 2, error)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "compile.project_missing")
            notice.assert_not_called()

    def test_recovery_blocks_before_compile_authority_is_read(self) -> None:
        with patch(
            "paperops.cli.compile_commands.recover_incomplete_transactions",
            return_value=(MigrationFinding("transaction.conflict", "/", "private detail"),),
        ) as recovery, patch(
            "paperops.cli.compile_commands.resolve_compile_request"
        ) as resolver:
            code, raw, error = run_cli(
                ["compile", "status", "all", str(self.project), "--json"]
            )
        self.assertEqual(code, 1, error)
        self.assertEqual(json.loads(raw)["findings"][0]["code"], "compile.recovery_blocked")
        recovery.assert_called_once()
        resolver.assert_not_called()
        self.assertNotIn("private detail", raw)


if __name__ == "__main__":
    unittest.main()
