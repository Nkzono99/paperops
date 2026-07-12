from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "template/scripts"))

from paperops.compiler import prepare_bundle  # noqa: E402
from paperops.compiler.requests import resolve_compile_request  # noqa: E402
from paperops.compiler.write_transaction import (  # noqa: E402
    HardCrashSimulation,
    InjectedWriteFailure,
    WriteTransactionError,
    execute_write_apply,
    execute_write_rollback,
    plan_write_apply,
    plan_write_rollback,
    recover_incomplete_writes,
)
from paperops.compiler.writer import build_patch, start_writer_session  # noqa: E402
from tests.test_p3_compile_materialize import approved_project  # noqa: E402


class P3WriteTransactionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.project = approved_project(Path(cls._tmp.name))
        request = resolve_compile_request(
            cls.project,
            "SEC-0002",
            scope="block",
            block_ids=("BLK-0002",),
        )
        cls.compile_result = prepare_bundle(cls.project, request)
        cls.identity = "manuscript/en/sections/30_results.tex"
        cls.original = (cls.project / cls.identity).read_bytes()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def setUp(self) -> None:
        (self.project / self.identity).write_bytes(self.original)
        shutil.rmtree(self.project / ".paperops/writer", ignore_errors=True)

    def checked_session(self):
        session = start_writer_session(self.project, self.compile_result.compile_id)
        candidate = self.project / ".paperops/writer" / session.session_id / "workspace" / self.identity
        text = candidate.read_text(encoding="utf-8")
        candidate.write_text(
            text.replace(
                "% block: results.traceability.01",
                "% block: results.traceability.01\nA transaction-tested revision.",
            ),
            encoding="utf-8",
        )
        patch = build_patch(self.project, session.session_id)
        self.assertTrue(patch.ok, patch.findings)
        return session, candidate, patch

    def test_plan_requires_confirmation_and_does_not_mutate_living_tex(self) -> None:
        session, _candidate, _patch = self.checked_session()
        before = (self.project / self.identity).read_bytes()
        with self.assertRaises(WriteTransactionError) as caught:
            plan_write_apply(self.project, session.session_id)
        self.assertEqual(caught.exception.finding.code, "write.confirmation_required")
        plan = plan_write_apply(self.project, session.session_id, confirmed=True)
        self.assertEqual((self.project / self.identity).read_bytes(), before)
        self.assertTrue(plan.confirmed)

    def test_apply_and_rollback_are_journaled_and_repeat_is_no_op(self) -> None:
        session, candidate, patch = self.checked_session()
        post = candidate.read_bytes()
        plan = plan_write_apply(self.project, session.session_id, confirmed=True)
        result = execute_write_apply(plan)
        self.assertTrue(result.ok)
        self.assertEqual((self.project / self.identity).read_bytes(), post)
        journal = json.loads(
            (
                self.project / ".paperops/writer" / session.session_id
                / "transactions" / result.transaction_id / "journal.json"
            ).read_text()
        )
        self.assertEqual(journal["patch_hash"], patch.patch_hash)
        self.assertEqual(journal["state"], "committed")
        self.assertTrue(plan_write_apply(self.project, session.session_id, confirmed=True).no_op)

        rollback = plan_write_rollback(self.project, result.transaction_id)
        rolled = execute_write_rollback(rollback)
        self.assertTrue(rolled.ok)
        self.assertEqual((self.project / self.identity).read_bytes(), self.original)
        self.assertTrue(plan_write_rollback(self.project, result.transaction_id).no_op)

    def test_normal_failure_is_compensated_in_same_call(self) -> None:
        session, _candidate, _patch = self.checked_session()
        plan = plan_write_apply(self.project, session.session_id, confirmed=True)
        with self.assertRaises(InjectedWriteFailure):
            execute_write_apply(plan, fail_at="after:replace:0")
        self.assertEqual((self.project / self.identity).read_bytes(), self.original)
        journal = json.loads(
            (_tx(self.project, session.session_id, plan.transaction_id) / "journal.json").read_text()
        )
        self.assertEqual(journal["state"], "rolled_back")

        session, _candidate, _patch = self.checked_session()
        plan = plan_write_apply(self.project, session.session_id, confirmed=True)
        with self.assertRaises(InjectedWriteFailure):
            execute_write_apply(plan, fail_at="after:validated")
        self.assertEqual((self.project / self.identity).read_bytes(), self.original)
        journal = json.loads(
            (_tx(self.project, session.session_id, plan.transaction_id) / "journal.json").read_text()
        )
        self.assertEqual(journal["state"], "rolled_back")

    def test_hard_crash_recovery_restores_only_known_hashes(self) -> None:
        session, _candidate, _patch = self.checked_session()
        plan = plan_write_apply(self.project, session.session_id, confirmed=True)
        with self.assertRaises(HardCrashSimulation):
            execute_write_apply(plan, fail_at="hard-after:replace:0")
        self.assertNotEqual((self.project / self.identity).read_bytes(), self.original)
        self.assertEqual(recover_incomplete_writes(self.project), ())
        self.assertEqual((self.project / self.identity).read_bytes(), self.original)

    def test_unknown_manual_edit_blocks_recovery_and_rollback(self) -> None:
        session, _candidate, _patch = self.checked_session()
        applied = execute_write_apply(
            plan_write_apply(self.project, session.session_id, confirmed=True)
        )
        living = self.project / self.identity
        living.write_bytes(living.read_bytes() + b"\n% human edit\n")
        with self.assertRaises(WriteTransactionError) as caught:
            plan_write_rollback(self.project, applied.transaction_id)
        self.assertEqual(caught.exception.finding.code, "write.rollback_conflict")
        self.assertIn(b"human edit", living.read_bytes())

    def test_unknown_manual_edit_during_crash_recovery_is_left_untouched(self) -> None:
        session, _candidate, _patch = self.checked_session()
        plan = plan_write_apply(self.project, session.session_id, confirmed=True)
        with self.assertRaises(HardCrashSimulation):
            execute_write_apply(plan, fail_at="hard-after:replace:0")
        living = self.project / self.identity
        living.write_bytes(living.read_bytes() + b"\n% unknown manual edit\n")
        unknown = living.read_bytes()
        findings = recover_incomplete_writes(self.project)
        self.assertEqual(findings[0].code, "write.recovery_conflict")
        self.assertEqual(living.read_bytes(), unknown)


def _tx(root: Path, session_id: str, transaction_id: str) -> Path:
    return root / ".paperops/writer" / session_id / "transactions" / transaction_id


if __name__ == "__main__":
    unittest.main()
