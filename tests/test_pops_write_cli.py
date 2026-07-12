from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import ROOT, run_cli

sys.path.insert(0, str(ROOT / "src"))

from paperops.cli.main import build_parser  # noqa: E402
from paperops.cli.write_commands import render_write_result  # noqa: E402
from tests.test_p3_compile_materialize import approved_project


class PopsWriteCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = approved_project(Path(cls._tmp.name))
        code, raw, error = run_cli(
            [
                "compile", "prepare", "SEC-0002", str(cls.project),
                "--scope", "block", "--block", "BLK-0002", "--json",
            ]
        )
        if code:
            raise AssertionError(error or raw)
        cls.compile_id = json.loads(raw)["result"]["compile_id"]
        cls.identity = "manuscript/en/sections/30_results.tex"
        cls.original = (cls.project / cls.identity).read_bytes()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        (self.project / self.identity).write_bytes(self.original)
        shutil.rmtree(self.project / ".paperops/writer", ignore_errors=True)

    def start_and_edit(self) -> str:
        code, raw, error = run_cli(
            ["write", "start", self.compile_id, str(self.project), "--json"]
        )
        self.assertEqual(code, 0, error)
        session_id = json.loads(raw)["session_id"]
        candidate = self.project / ".paperops/writer" / session_id / "workspace" / self.identity
        candidate.write_text(
            candidate.read_text().replace(
                "% block: results.traceability.01",
                "% block: results.traceability.01\nA CLI-tested revision.",
            ),
            encoding="utf-8",
        )
        return session_id

    def test_parser_exposes_exactly_six_write_actions_and_only_apply_has_yes(self) -> None:
        parser = build_parser()
        top = next(action for action in parser._actions if getattr(action, "dest", None) == "command")
        write = top.choices["write"]
        actions = next(action for action in write._actions if getattr(action, "dest", None) == "write_action").choices
        self.assertEqual(set(actions), {"start", "status", "check", "diff", "apply", "rollback"})
        for name, action in actions.items():
            options = {option for item in action._actions for option in item.option_strings}
            self.assertEqual("--yes" in options, name == "apply")

    def test_full_authoritative_lifecycle_and_human_json_parity(self) -> None:
        session_id = self.start_and_edit()
        code, raw, error = run_cli(["write", "check", session_id, str(self.project), "--json"])
        self.assertEqual(code, 0, error)
        checked = json.loads(raw)
        self.assertEqual(checked["result"]["conservation_result"], "passed")
        self.assertNotIn("CLI-tested revision", raw)

        code, human, error = run_cli(["write", "diff", session_id, str(self.project)])
        self.assertEqual(code, 0, error)
        diff_json = json.loads(
            run_cli(["write", "diff", session_id, str(self.project), "--json"])[1]
        )
        self.assertEqual(human.strip(), render_write_result(diff_json))

        code, raw, error = run_cli(["write", "apply", session_id, str(self.project), "--json"])
        self.assertEqual(code, 2, error)
        self.assertEqual(json.loads(raw)["findings"][0]["code"], "write.confirmation_required")
        code, raw, error = run_cli(["write", "apply", session_id, str(self.project), "--yes", "--json"])
        self.assertEqual(code, 0, error)
        applied = json.loads(raw)
        transaction_id = applied["transaction_id"]
        self.assertIn(b"CLI-tested revision", (self.project / self.identity).read_bytes())
        repeated = json.loads(
            run_cli(["write", "apply", session_id, str(self.project), "--yes", "--json"])[1]
        )
        self.assertTrue(repeated["reused"])

        code, raw, error = run_cli(["write", "rollback", transaction_id, str(self.project), "--json"])
        self.assertEqual(code, 0, error)
        self.assertEqual((self.project / self.identity).read_bytes(), self.original)
        repeat = json.loads(
            run_cli(["write", "rollback", transaction_id, str(self.project), "--json"])[1]
        )
        self.assertTrue(repeat["reused"])

    def test_status_and_check_do_not_mutate_living_tex(self) -> None:
        session_id = self.start_and_edit()
        before = (self.project / self.identity).read_bytes()
        for action in ("status", "check", "diff"):
            code, _raw, error = run_cli(["write", action, session_id, str(self.project), "--json"])
            self.assertEqual(code, 0, error)
            self.assertEqual((self.project / self.identity).read_bytes(), before)

    def test_invalid_id_nonproject_and_private_exception_are_stable(self) -> None:
        for action, identifier in (("start", "../private"), ("status", "/absolute"), ("rollback", "C:\\private")):
            code, raw, error = run_cli(["write", action, identifier, str(self.project), "--json"])
            self.assertEqual(code, 2, error)
            self.assertEqual(json.loads(raw)["findings"][0]["code"], "write.id_invalid")
            self.assertNotIn(str(self.project), raw)
        with tempfile.TemporaryDirectory() as temporary:
            code, raw, error = run_cli(["write", "status", "writer-v1-safe", temporary, "--json"])
        self.assertEqual(code, 2, error)
        self.assertEqual(json.loads(raw)["findings"][0]["code"], "write.project_missing")

        with patch("paperops.cli.write_commands.inspect_writer_session", side_effect=RuntimeError("/private/raw reviewer")):
            code, raw, error = run_cli(["write", "status", "writer-v1-safe", str(self.project), "--json"])
        self.assertEqual(code, 1, error)
        self.assertNotIn("private", raw)
        self.assertNotIn("reviewer", raw)

    def test_write_bypasses_update_notice(self) -> None:
        with patch("paperops.cli.main.maybe_print_update_notice") as notice:
            run_cli(["write", "status", "writer-v1-missing", str(self.project), "--json"])
        notice.assert_not_called()


if __name__ == "__main__":
    unittest.main()
