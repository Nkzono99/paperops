from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import run_cli
from tests.test_research_model import source

from paperops.change.planning import ChangePlanningError, plan_change, read_change_plan
from paperops.workflow_v2.mutation import semantic_hash


class ChangePlanningTest(unittest.TestCase):
    def project(self, parent: Path) -> Path:
        project = parent / "paper"
        code, _out, err = run_cli(["init", str(project)])
        self.assertEqual(code, 0, err)
        return project

    def request(self, parent: Path, operations: list[dict]) -> Path:
        path = parent / "request.yml"
        path.write_text(yaml.safe_dump({"schema_version": 1, "reason": "Apply a typed scientific change.", "operations": operations}, sort_keys=False), encoding="utf-8")
        return path

    def test_indexed_create_builds_record_and_index_replacements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            document = source(); document["claim_refs"] = []; document["manuscript_block_refs"] = []
            operation = {"action": "upsert", "model": "research", "record_type": "source", "id": "SRC-0001", "expected_revision": None, "expected_hash": "", "document": document}
            plan = plan_change(project, self.request(parent, [operation]))
            self.assertTrue(plan.change_id.startswith("CHG-"))
            self.assertEqual({item.identity for item in plan.replacements}, {"_paperops/model/research/sources/SRC-0001.yml", "_paperops/model/research/index.yml"})
            cached = read_change_plan(project, plan.change_id)
            self.assertEqual(cached.change_id, plan.change_id)
            self.assertNotIn(document["promotion_reason"], (project / ".paperops/changes" / plan.change_id / "plan.json").read_text())

    def test_aggregate_update_requires_current_revision_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            target = project / "_paperops/model/publication/publication-model.yml"
            document = yaml.safe_load(target.read_text()); current_hash = semantic_hash(document)
            document["revision"] = 1; document["venue"]["name"] = "Example Venue"
            valid = {"action": "upsert", "model": "publication", "record_type": "publication", "id": "PUB-main", "expected_revision": 0, "expected_hash": current_hash, "document": document}
            plan = plan_change(project, self.request(parent, [valid]))
            self.assertEqual(plan.affected_models, ("publication",))
            invalid = dict(valid); invalid["expected_hash"] = "sha256:" + "0" * 64
            with self.assertRaises(ChangePlanningError):
                plan_change(project, self.request(parent, [invalid]))

    def test_revisionless_results_hierarchy_uses_canonical_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            target = project / "_paperops/model/editorial/results-hierarchy.yml"
            document = yaml.safe_load(target.read_text()); digest = semantic_hash(document)
            document["items"][0]["answer"] = "A checked hierarchy answer."
            operation = {"action": "upsert", "model": "results_hierarchy", "record_type": "results_hierarchy", "id": "RHI-main", "expected_revision": 0, "expected_hash": digest, "document": document}
            plan = plan_change(project, self.request(parent, [operation]))
            self.assertEqual(plan.operations[0].candidate_revision, None)
            self.assertEqual(plan.replacements[0].identity, "_paperops/model/editorial/results-hierarchy.yml")

    def test_plan_is_deterministic_and_corrupt_cache_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            target = project / "_paperops/model/publication/publication-model.yml"
            document = yaml.safe_load(target.read_text()); digest = semantic_hash(document)
            document["revision"] = 1
            operation = {"action": "upsert", "model": "publication", "record_type": "publication", "id": "PUB-main", "expected_revision": 0, "expected_hash": digest, "document": document}
            request = self.request(parent, [operation])
            first = plan_change(project, request); second = plan_change(project, request)
            self.assertEqual(first.change_id, second.change_id)
            cache = project / ".paperops/changes" / first.change_id / "plan.json"
            cache.write_text("{}\n")
            with self.assertRaises(ChangePlanningError):
                plan_change(project, request)

    def test_read_rejects_traversal_and_does_not_create_missing_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            outside = parent / "escape"
            with self.assertRaises(ChangePlanningError):
                read_change_plan(project, "CHG-../../escape")
            self.assertFalse(outside.exists())
            missing = "CHG-" + "a" * 20
            with self.assertRaises(ChangePlanningError):
                read_change_plan(project, missing)
            self.assertFalse((project / ".paperops/changes" / missing).exists())

    def test_read_rejects_symlinked_change_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            change_id = "CHG-" + "b" * 20
            outside = parent / "outside"; outside.mkdir()
            changes = project / ".paperops/changes"; changes.mkdir(parents=True, exist_ok=True)
            (changes / change_id).symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ChangePlanningError, "unsafe"):
                read_change_plan(project, change_id)

    def test_read_rejects_symlinked_plan_and_payload_leaves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            target = project / "_paperops/model/publication/publication-model.yml"
            document = yaml.safe_load(target.read_text()); digest = semantic_hash(document)
            document["revision"] = 1
            operation = {"action": "upsert", "model": "publication", "record_type": "publication", "id": "PUB-main", "expected_revision": 0, "expected_hash": digest, "document": document}
            plan = plan_change(project, self.request(parent, [operation]))
            directory = project / ".paperops/changes" / plan.change_id
            for leaf in ("plan.json", "payload.json"):
                with self.subTest(leaf=leaf):
                    original = directory / leaf
                    outside = parent / f"outside-{leaf}"; outside.write_bytes(original.read_bytes())
                    original.unlink(); original.symlink_to(outside)
                    with self.assertRaises(ChangePlanningError):
                        read_change_plan(project, plan.change_id)
                    original.unlink(); original.write_bytes(outside.read_bytes()); original.chmod(0o600)

    def test_aggregate_id_is_registry_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp); project = self.project(parent)
            target = project / "_paperops/model/publication/publication-model.yml"
            document = yaml.safe_load(target.read_text()); digest = semantic_hash(document)
            document["revision"] = 1
            operation = {"action": "upsert", "model": "publication", "record_type": "publication", "id": "PUB-other", "expected_revision": 0, "expected_hash": digest, "document": document}
            with self.assertRaisesRegex(ChangePlanningError, "canonical"):
                plan_change(project, self.request(parent, [operation]))


if __name__ == "__main__":
    unittest.main()
