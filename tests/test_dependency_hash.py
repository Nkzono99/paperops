from __future__ import annotations

import copy
import sys
import unittest

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "template/scripts"))

from paperops_models import (  # noqa: E402
    CatalogObject,
    ObjectCatalog,
    dependency_hash,
    validate_dependency_state,
)
from paperops_schema import semantic_hash  # noqa: E402


def item(object_id: str, revision: int, document: dict, object_type: str = "result") -> CatalogObject:
    return CatalogObject(
        object_id,
        object_type,
        "research",
        document,
        revision,
        semantic_hash(document, excluded_paths=("/metadata/updated_at",)),
        f"/{object_id}",
    )


def graph(*objects: CatalogObject) -> ObjectCatalog:
    return ObjectCatalog({obj.object_id: obj for obj in objects}, ())


class DependencyHashTest(unittest.TestCase):
    def test_hash_is_stable_under_mapping_dependency_order_and_timestamp_only_changes(self) -> None:
        a = item("RES-0001", 1, {"value": 1, "metadata": {"updated_at": "old"}})
        b = item("RES-0002", 2, {"value": 2})
        owner = item("BLK-0001", 1, {"dependencies": [
            {"target_id": "RES-0002", "relation": "uses", "expected_revision": 2, "expected_hash": b.object_hash},
            {"target_id": "RES-0001", "relation": "uses", "expected_revision": 1, "expected_hash": a.object_hash},
        ]}, "block")
        first = dependency_hash(owner.object_id, graph(owner, a, b))
        reordered = copy.deepcopy(owner.document); reordered["dependencies"].reverse()
        owner2 = item("BLK-0001", 1, reordered, "block")
        self.assertEqual(first, dependency_hash(owner2.object_id, graph(owner2, a, b)))
        timestamp_changed = item(
            "RES-0001", 1, {"metadata": {"updated_at": "new"}, "value": 1}
        )
        self.assertEqual(
            first,
            dependency_hash(owner.object_id, graph(owner, timestamp_changed, b)),
        )

    def test_hash_changes_for_target_hash_revision_relation_addition_and_removal(self) -> None:
        target = item("RES-0001", 1, {"value": 1})
        owner = item("BLK-0001", 1, {"dependencies": [{"target_id": "RES-0001", "relation": "uses", "expected_revision": 1, "expected_hash": target.object_hash}]}, "block")
        baseline = dependency_hash(owner.object_id, graph(owner, target))
        mutations = [
            item("RES-0001", 2, {"value": 1}),
            item("RES-0001", 1, {"value": 2}),
        ]
        for changed in mutations:
            self.assertNotEqual(baseline, dependency_hash(owner.object_id, graph(owner, changed)))
        changed_owner = copy.deepcopy(owner.document); changed_owner["dependencies"][0]["relation"] = "supports"
        self.assertNotEqual(baseline, dependency_hash(owner.object_id, graph(item("BLK-0001", 1, changed_owner, "block"), target)))
        removed_owner = item("BLK-0001", 1, {"dependencies": []}, "block")
        self.assertNotEqual(
            baseline,
            dependency_hash(removed_owner.object_id, graph(removed_owner, target)),
        )
        second_target = item("RES-0002", 1, {"value": 2})
        added_document = copy.deepcopy(owner.document)
        added_document["dependencies"].append(
            {
                "target_id": "RES-0002",
                "relation": "uses",
                "expected_revision": 1,
                "expected_hash": second_target.object_hash,
            }
        )
        added_owner = item("BLK-0001", 1, added_document, "block")
        self.assertNotEqual(
            baseline,
            dependency_hash(
                added_owner.object_id, graph(added_owner, target, second_target)
            ),
        )

    def test_stale_revision_hash_dangling_and_cycle_are_distinct(self) -> None:
        target = item("RES-0001", 2, {"value": 1})
        owner_doc = {"dependencies": [{"target_id": "RES-0001", "relation": "uses", "expected_revision": 1, "expected_hash": "sha256:" + "0" * 64}]}
        owner = item("BLK-0001", 1, owner_doc, "block")
        codes = {f.code for f in validate_dependency_state(graph(owner, target))}
        self.assertIn("dependency.stale_revision", codes)
        self.assertIn("dependency.stale_hash", codes)
        missing = item("BLK-0002", 1, {"dependencies": [{"target_id": "RES-9999", "relation": "uses", "expected_hash": target.object_hash}]}, "block")
        self.assertIn("reference.dangling", {f.code for f in validate_dependency_state(graph(missing))})
        left = item("RES-0001", 1, {"dependencies": [{"target_id": "RES-0002", "relation": "uses", "expected_hash": target.object_hash}]})
        right = item("RES-0002", 1, {"dependencies": [{"target_id": "RES-0001", "relation": "uses", "expected_hash": left.object_hash}]})
        self.assertIn("dependency.cycle", {f.code for f in validate_dependency_state(graph(left, right))})


if __name__ == "__main__":
    unittest.main()
