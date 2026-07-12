from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import yaml

from paperops.change.request import ChangeRequestError, load_change_request


class ChangeRequestTest(unittest.TestCase):
    def write(self, parent: Path, payload: dict, suffix: str = ".yml") -> Path:
        path = parent / f"change{suffix}"
        if suffix == ".json":
            path.write_text(json.dumps(payload), encoding="utf-8")
        else:
            path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
        return path

    def base(self) -> dict:
        return {
            "schema_version": 1,
            "reason": "Add a bounded research claim.",
            "operations": [
                {
                    "action": "upsert",
                    "model": "research",
                    "record_type": "claim",
                    "id": "CLM-0001",
                    "expected_revision": None,
                    "expected_hash": "",
                    "document": {"id": "CLM-0001", "revision": 1},
                }
            ],
        }

    def test_yaml_and_json_load_to_immutable_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            for suffix in (".yml", ".json"):
                request = load_change_request(self.write(parent, self.base(), suffix))
                self.assertEqual(request.schema_version, 1)
                self.assertEqual(request.operations[0].object_id, "CLM-0001")
                with self.assertRaises(AttributeError):
                    request.reason = "changed"  # type: ignore[misc]

    def test_unknown_field_and_unsafe_identity_are_rejected(self) -> None:
        cases = []
        unknown = self.base(); unknown["extra"] = True; cases.append(unknown)
        unsafe = self.base(); unsafe["operations"][0]["id"] = "../CLM-0001"; cases.append(unsafe)
        model = self.base(); model["operations"][0]["model"] = "other"; cases.append(model)
        aggregate = self.base(); aggregate["operations"][0].update(model="publication", record_type="claim", id="CLM-0001"); cases.append(aggregate)
        with tempfile.TemporaryDirectory() as tmp:
            for index, payload in enumerate(cases):
                with self.subTest(index=index), self.assertRaises(ChangeRequestError):
                    load_change_request(self.write(Path(tmp), payload))

    def test_update_delete_require_both_preconditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for action in ("upsert", "delete"):
                payload = self.base()
                operation = payload["operations"][0]
                operation["action"] = action
                operation["expected_revision"] = 1
                operation["expected_hash"] = ""
                if action == "delete":
                    operation.pop("document")
                with self.subTest(action=action), self.assertRaises(ChangeRequestError):
                    load_change_request(self.write(Path(tmp), payload))

    def test_external_document_and_sensitive_material_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            external = self.base(); external["operations"][0]["document"] = "/tmp/private.yml"
            secret = self.base(); secret["operations"][0]["document"]["api_token"] = "secret"
            raw = self.base(); raw["raw_review"] = "not public"
            for payload in (external, secret, raw):
                with self.assertRaises(ChangeRequestError):
                    load_change_request(self.write(parent, payload))


if __name__ == "__main__":
    unittest.main()
