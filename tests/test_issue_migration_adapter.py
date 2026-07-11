from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests.helpers import copy_template
from tests.test_issue_model import analysis_request, feedback, response, review_round, writing_request

from paperops.model_migration.adapters.issue import IssueAdapter
from paperops.model_migration.catalog import validate_conservation
from paperops.model_migration.types import MigrationInput
from paperops.model_validation import run_model_validation


ROOTS = {
    "feedback": "_paperops/review/feedback",
    "analysis_request": "_paperops/requests/analysis",
    "writing_request": "_paperops/requests/writing",
    "response": "_paperops/review/responses",
    "review_round": "_paperops/review/rounds",
}


class IssueMigrationAdapterTest(unittest.TestCase):
    def test_all_lifecycle_records_preserve_structured_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self.project(Path(tmp))
            candidate = IssueAdapter().materialize(MigrationInput(project, "issue", ()))
            self.assertEqual([f for f in candidate.findings if f.severity == "error"], [])
            self.assertEqual(validate_conservation(candidate.inventory, candidate), ())
            emitted = {item.object_id: json.loads(item.content) for item in candidate.documents}
            self.assertEqual(emitted["AREQ-0001"]["prediction"]["state"], "predicted")
            self.assertEqual(emitted["AREQ-0001"]["reconciliation"]["human_signoff"], "approved")
            self.assertTrue(emitted["RSP-0001"]["closure_audit"]["criteria_met"])
            self.assertEqual(emitted["RVW-0001"]["integration_decisions"][0]["decision"], "accepted_to_feedback_card")
            self.assertEqual(emitted["FB-0001"]["local_reference_id"], "LOC-0001")
            for document in candidate.documents:
                path = project / document.relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(document.content)
            self.assertTrue(run_model_validation(project, "issue", phase="schema", strict=True).ok)

    def test_raw_reviewer_text_paths_and_credentials_never_enter_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            documents = self.documents()
            documents[0]["raw_reviewer_text"] = "secret review at /private/reviewer.txt token=abc"
            documents[0]["public_summary"] = "/private/reviewer.txt"
            project = self.project(Path(tmp), documents)
            candidate = IssueAdapter().materialize(MigrationInput(project, "issue", ()))
            self.assertIn("migration.confidential", [item.code for item in candidate.findings])
            payload = b"".join(item.content for item in candidate.documents)
            self.assertNotIn(b"secret review", payload)
            self.assertNotIn(b"/private/reviewer.txt", payload)
            self.assertNotIn(b"token=abc", payload)

    def test_multiple_issue_hashes_are_stable_and_unknown_fields_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            documents = self.documents()
            second = feedback()
            second["id"] = "FB-0002"
            second["related_card_refs"] = ["legacy:FB-0002"]
            second["mystery"] = True
            documents.append(second)
            project = self.project(Path(tmp), documents)
            adapter = IssueAdapter()
            first = adapter.materialize(MigrationInput(project, "issue", ()))
            repeated = adapter.materialize(MigrationInput(project, "issue", ()))
            self.assertEqual([d.semantic_hash for d in first.documents], [d.semantic_hash for d in repeated.documents])
            self.assertIn("migration.unknown_field", [item.code for item in first.findings])
            self.assertEqual(sum(item.object_id == "FB-0002" for item in first.documents), 1)

    def project(self, parent: Path, documents: list[dict] | None = None) -> Path:
        project = copy_template(parent)
        for relative in ROOTS.values():
            shutil.rmtree(project / relative)
            (project / relative).mkdir(parents=True)
        for document in documents or self.documents():
            path = project / ROOTS[document["record_type"]] / f"{document['id']}.md"
            path.write_text(self.render(document))
        return project

    @staticmethod
    def documents() -> list[dict]:
        return [feedback(), analysis_request(), writing_request(), response(), review_round()]

    @staticmethod
    def render(document: dict) -> str:
        value = copy.deepcopy(document)
        record_type = value.pop("record_type")
        value.pop("schema_version")
        metadata = value.pop("metadata")
        lines = ["---", f"type: {record_type}"]
        lines.extend(f"{key}: {json.dumps(item, ensure_ascii=False, separators=(',', ':'))}" for key, item in value.items())
        lines.extend([f"created: {metadata['created_at']}", f"updated: {metadata['updated_at']}", "---", ""])
        return "\n".join(lines)


if __name__ == "__main__":
    unittest.main()
