from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from tests.helpers import run_cli
from paperops.workflow_v2.mutation import semantic_hash


class ChangeCliTest(unittest.TestCase):
    def setup_request(self, parent: Path) -> tuple[Path, Path]:
        project = parent / "paper"
        code, _out, err = run_cli(["init", str(project)])
        self.assertEqual(code, 0, err)
        target = project / "_paperops/model/publication/publication-model.yml"
        document = yaml.safe_load(target.read_text()); digest = semantic_hash(document)
        document["revision"] = 1; document["venue"]["name"] = "CLI Venue"
        request = parent / "request.yml"
        request.write_text(yaml.safe_dump({"schema_version": 1, "reason": "Choose a venue.", "operations": [{"action": "upsert", "model": "publication", "record_type": "publication", "id": "PUB-main", "expected_revision": 0, "expected_hash": digest, "document": document}]}, sort_keys=False))
        return project, request

    def test_plan_status_diff_apply_and_rollback_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, request = self.setup_request(Path(tmp))
            with patch("pathlib.Path.cwd", return_value=project):
                code, raw, err = run_cli(["change", "plan", str(request), "--json"])
                self.assertEqual(code, 0, err); plan = json.loads(raw)
                self.assertNotIn("CLI Venue", raw); change_id = plan["change_id"]
                for action in ("status", "diff"):
                    code, raw, err = run_cli(["change", action, change_id, "--json"])
                    self.assertEqual(code, 0, err); self.assertEqual(json.loads(raw)["change_id"], change_id)
                code, _raw, _err = run_cli(["change", "apply", change_id, "--json"])
                self.assertEqual(code, 2)
                code, raw, err = run_cli(["change", "apply", change_id, "--yes", "--json"])
                self.assertEqual(code, 0, err); tx = json.loads(raw)["transaction_id"]
                code, raw, err = run_cli(["change", "rollback", tx, "--yes", "--json"])
                self.assertEqual(code, 0, err); self.assertTrue(json.loads(raw)["transaction_id"].startswith("RBK-"))

    def test_invalid_change_id_is_domain_error_without_local_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _request = self.setup_request(Path(tmp))
            with patch("pathlib.Path.cwd", return_value=project):
                code, raw, _err = run_cli(["change", "status", "bad", "--json"])
            self.assertEqual(code, 1)
            payload = json.loads(raw)
            self.assertEqual(payload["findings"][0]["code"], "change.invalid")
            self.assertNotIn(str(project), raw)


if __name__ == "__main__":
    unittest.main()
