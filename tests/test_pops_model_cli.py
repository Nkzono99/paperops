from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import copy_template, run_cli

from paperops.cli.main import build_parser
from paperops.model_state import MODEL_NAMES, manifest_bytes, read_model_states


class PopsModelCliTest(unittest.TestCase):
    def test_parser_exposes_exactly_five_public_model_actions(self) -> None:
        parser = build_parser()
        model_action = next(
            action for action in parser._actions if getattr(action, "dest", None) == "command"
        ).choices["model"]
        actions = next(
            action for action in model_action._actions if getattr(action, "dest", None) == "model_action"
        ).choices
        self.assertEqual(set(actions), {"status", "validate", "diff", "adopt", "rollback"})

    def test_unknown_model_and_action_are_usage_errors(self) -> None:
        for argv in (["model", "unknown"], ["model", "status", "bogus"]):
            with self.subTest(argv=argv), self.assertRaises(SystemExit) as raised:
                run_cli(argv)
            self.assertEqual(raised.exception.code, 2)

    def test_status_defaults_show_all_six_models_in_human_and_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            code, human, err = run_cli(["model", "status", "all", str(project)])
            self.assertEqual(code, 0, err)
            code, raw, err = run_cli(["model", "status", "all", str(project), "--json"])
            self.assertEqual(code, 0, err)
            payload = json.loads(raw)
            self.assertEqual(set(payload["models"]), set(MODEL_NAMES))
            self.assertTrue(all(value["mode"] == "legacy-authoritative" for value in payload["models"].values()))
            for name in MODEL_NAMES:
                self.assertIn(name, human)

    def test_non_project_status_is_a_stable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = run_cli(["model", "status", "all", tmp, "--json"])
            self.assertEqual(code, 2)
            payload = json.loads(out)
            self.assertEqual(payload["findings"][0]["code"], "state.project_missing")
            self.assertEqual(err, "")

    def test_validate_preserves_checker_findings_in_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            index = project / "_paperops/model/research/index.yml"
            index.write_text("model_name: research\nschema_version: 1\nrecords: wrong\n")
            code, raw, _err = run_cli(["model", "validate", "research", str(project), "--json"])
            self.assertEqual(code, 1)
            payload = json.loads(raw)
            self.assertTrue(any(item["code"].startswith("schema.") for item in payload["findings"]))
            self.assertNotIn(str(project), raw)

    def test_successful_diff_persists_shadow_only_and_refresh_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            publication_path = project / "_paperops/model/publication/publication-model.yml"
            publication = yaml.safe_load(publication_path.read_text())
            ledger = project / "_paperops/workflow/submission-ledger.yml"
            ledger.write_text(yaml.safe_dump({"schema_version": 1, "migration_publication": publication}, sort_keys=False))
            tracked_before = publication_path.read_bytes()

            code, raw, err = run_cli(["model", "diff", "publication", str(project), "--json"])
            self.assertEqual(code, 0, err)
            first = json.loads(raw)
            transaction_id = first["transaction_id"]
            self.assertEqual(publication_path.read_bytes(), tracked_before)
            self.assertEqual(read_model_states(project)["publication"].mode, "shadow-compare")
            self.assertTrue((project / ".paperops/migrations" / transaction_id / "report.json").is_file())

            code, raw, _err = run_cli(["model", "diff", "publication", str(project), "--json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(raw)["transaction_id"], transaction_id)

            code, raw, _err = run_cli(["model", "diff", "publication", str(project), "--refresh", "--json"])
            self.assertEqual(code, 0)
            self.assertNotEqual(json.loads(raw)["transaction_id"], transaction_id)
            self.assertEqual(publication_path.read_bytes(), tracked_before)

    def test_failed_diff_writes_report_but_does_not_advance_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            before = manifest_bytes(project)
            code, raw, _err = run_cli(["model", "diff", "publication", str(project), "--json"])
            self.assertEqual(code, 1)
            payload = json.loads(raw)
            self.assertTrue((project / ".paperops/migrations" / payload["transaction_id"] / "report.json").is_file())
            self.assertEqual(manifest_bytes(project), before)


if __name__ == "__main__":
    unittest.main()
