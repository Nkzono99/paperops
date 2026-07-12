from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import yaml

from tests.helpers import ROOT, copy_template, make_var_tokens, run_python_script


SCRIPT = ROOT / "template" / "scripts" / "check-block-flow-review.py"


def write_manuscript(root: Path, *, ordered: list[str], blocks: list[dict], status: str = "verified") -> None:
    section = {"id": "SEC-0001", "record_type": "section", "section_kind": "results", "status": status, "ordered_block_ids": ordered}
    documents = [section, *blocks]; records = []
    for document in documents:
        folder = "sections" if document["record_type"] == "section" else "blocks"
        path = root / f"_paperops/model/manuscript/{folder}/{document['id']}.yml"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(document, sort_keys=False))
        records.append({"id": document["id"], "record_type": document["record_type"], "document": path.relative_to(root).as_posix(), "expected_revision": 1, "expected_hash": "sha256:" + "0" * 64})
    index = root / "_paperops/model/manuscript/index.yml"; index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(yaml.safe_dump({"model_name": "manuscript", "schema_version": 1, "index_revision": 1, "records": records, "extensions": {}, "metadata": {"updated_at": ""}}, sort_keys=False))


class BlockFlowReviewCheckTest(unittest.TestCase):
    def test_strict_requires_ordered_blocks_for_verified_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            write_manuscript(root, ordered=[], blocks=[])

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("ordered block", result.stdout)

    def test_strict_rejects_missing_typed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            write_manuscript(root, ordered=["BLK-0001"], blocks=[])

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("BLK-0001", result.stdout)

    def test_passes_when_verified_section_has_typed_block_operations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            write_manuscript(root, ordered=["BLK-0001"], blocks=[{"id": "BLK-0001", "record_type": "block", "section_id": "SEC-0001", "reader_task": "Understand the bounded result.", "operation": "keep"}])

            result = run_python_script(SCRIPT, "--root", root, "--strict")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("block-flow review に問題は見つかりませんでした", result.stdout)

    def test_makefiles_wire_block_flow_check_to_audit_and_finish(self) -> None:
        root_makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        template_makefile = (ROOT / "template" / "Makefile").read_text(encoding="utf-8")

        for makefile in [root_makefile, template_makefile]:
            with self.subTest(makefile=makefile[:20]):
                self.assertIn("block-flow-review-check:", makefile)
                self.assertIn("check-block-flow-review.py --root", makefile)
                self.assertIn("--strict", makefile)

        self.assertIn("block-flow-review-check", make_var_tokens(root_makefile, "SMOKE_CHECKS"))
        self.assertIn("block-flow-review-check", make_var_tokens(root_makefile, "FINISH_MANUSCRIPT_CHECKS"))
        self.assertIn("block-flow-review-check", make_var_tokens(template_makefile, "AUDIT_CHECKS"))
        self.assertIn("block-flow-review-check", make_var_tokens(template_makefile, "FINISH_MANUSCRIPT_CHECKS"))


if __name__ == "__main__":
    unittest.main()
