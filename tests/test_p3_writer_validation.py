from __future__ import annotations

import hashlib
import json
import sys
import unittest

from tests.helpers import ROOT

sys.path.insert(0, str(ROOT / "src"))

from paperops.compiler.conservation import analyze_patch, validate_patch  # noqa: E402
from paperops.compiler.patches import WriterPatchResult  # noqa: E402
from paperops.compiler.privacy import contains_private_tex_material  # noqa: E402
from paperops.compiler.tex import parse_tex_bytes  # noqa: E402


HASH = "sha256:" + "a" * 64
IDENTITY = "manuscript/en/sections/30_results.tex"


def _state(content: bytes) -> dict[str, object]:
    return {
        "identity": IDENTITY,
        "type": "regular",
        "content_hash": "sha256:" + hashlib.sha256(content).hexdigest(),
        "size": len(content),
        "mode": 0o644,
    }


def _case(
    base_content: bytes,
    candidate_content: bytes,
    *,
    operation: str = "rewrite",
    candidate_extra: dict[str, object] | None = None,
):
    base_tex = parse_tex_bytes(IDENTITY, base_content).to_dict()
    candidate_tex = parse_tex_bytes(IDENTITY, candidate_content).to_dict()
    binding = {
        "typed_block_id": "BLK-0002",
        "raw_block_id": "results.main",
        "file_identity": IDENTITY,
        "language": "en",
        "claim_refs": ["CLM-0001"],
        "result_refs": ["RES-0001"],
        "figure_refs": ["FIG-0001"],
        "citation_keys": ["example2026"],
        "model_revision": 2,
        "model_hash": HASH,
    }
    base = {
        "files": [_state(base_content)],
        "tex_files": [base_tex],
        "bindings": [binding],
        "section_topology": [
            {
                "section_id": "SEC-0002",
                "move_bindings": [
                    {"move_id": "MOV-0001", "role": "primary", "reason": "result"}
                ],
            }
        ],
    }
    candidate = {"tex_files": [candidate_tex], **(candidate_extra or {})}
    change = {
        "typed_block_id": "BLK-0002",
        "raw_block_id": "results.main",
        "operation": operation,
        "authorization": operation,
        "model_revision": 2,
        "model_hash": HASH,
        "from": {"file": IDENTITY, "position": 0},
        "to": None if operation == "cut" else {"file": IDENTITY, "position": 0},
    }
    patch = WriterPatchResult(
        session_id="writer-v1-test",
        compile_id="compile-v1-test",
        status="ready",
        applicable=True,
        source_mode="authoritative",
        base_manifest_hash=HASH,
        candidate_snapshot_hash=HASH,
        authority=(),
        write_scope={"level": "block", "files": [IDENTITY], "block_ids": ["BLK-0002"]},
        target_files=(),
        changes=(change,),
        findings=(),
    )
    bundle = {
        "global_context": {
            "citation_registry": [
                {"identity": "manuscript/shared/bib/references.bib", "entry_keys": ["example2026"]}
            ]
        },
        "writer_packets": [],
    }
    return bundle, base, candidate, patch


class P3WriterValidationTest(unittest.TestCase):
    def test_occurrences_are_multisets_and_unexplained_removal_is_blocked(self) -> None:
        args = _case(
            b"% block: results.main\n\\cite{example2026,example2026}; 5 of 10.\n",
            b"% block: results.main\n\\cite{example2026}; revised.\n",
        )
        analysis = analyze_patch(*args)
        removed = [
            row for row in analysis.dispositions
            if row["disposition"] == "removed" and row["kind"] in {"citation", "quantity"}
        ]
        self.assertEqual({row["kind"] for row in removed}, {"citation", "quantity"})
        self.assertTrue(any(row.code == "write.conservation_removed" for row in analysis.findings))

    def test_whole_block_cut_authorizes_scientific_removal(self) -> None:
        args = _case(
            b"% block: results.main\n\\cite{example2026}; 5 of 10; \\label{fig:a}\\ref{fig:a}.\n",
            b"",
            operation="cut",
        )
        findings = validate_patch(*args)
        self.assertFalse(any(row.code == "write.conservation_removed" for row in findings))

    def test_unknown_reference_and_custom_citation_are_rejected(self) -> None:
        args = _case(
            b"% block: results.main\nBase.\n",
            b"% block: results.main\n\\cite{unknown2026} and \\mycite{example2026}.\n",
            candidate_extra={"custom_citation_commands": ["mycite"]},
        )
        codes = {row.code for row in validate_patch(*args)}
        self.assertIn("write.conservation_introduced", codes)
        self.assertIn("write.conservation_custom_citation_unsupported", codes)

    def test_structural_argument_move_and_mirror_digest_are_reported(self) -> None:
        args = _case(
            b"% block: results.main\nBase.\n",
            b"% block: results.main\nRewritten.\n",
        )
        analysis = analyze_patch(*args)
        self.assertTrue(any(row["kind"] == "argument_move" for row in analysis.dispositions))
        self.assertEqual(analysis.mirror_impacts[0]["status"], "freshness_drift")
        self.assertIn("legacy_ledger_hash", analysis.mirror_impacts[0])

    def test_tex_privacy_boundary_allows_public_and_relative_but_rejects_private(self) -> None:
        self.assertFalse(
            contains_private_tex_material(
                r"\\input{../shared/methods} https://doi.org/10.1000/test NumPy"
            )
        )
        private_values = (
            "secret at /private/reviewer/notes.txt",
            "https://alice:password@example.invalid/data",
            "raw reviewer comments",
            "token=abcdefghijklmnopqrstuvwxyz",
        )
        for value in private_values:
            with self.subTest(value=value):
                self.assertTrue(contains_private_tex_material(value))

    def test_report_is_deterministic_and_contains_no_raw_private_value(self) -> None:
        args = _case(
            b"% block: results.main\nBase.\n",
            b"% block: results.main\nRewritten.\n",
            candidate_extra={"privacy_violation": True},
        )
        first = analyze_patch(*args)
        second = analyze_patch(*args)
        self.assertEqual(first, second)
        public = json.dumps([row.to_dict() for row in first.findings])
        self.assertNotIn("reviewer", public)
        self.assertNotIn("/private", public)


if __name__ == "__main__":
    unittest.main()
