from __future__ import annotations

import hashlib
import os
import re
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import yaml

from tests.helpers import ROOT, run_python_script


sys.path.insert(0, str(ROOT / "src"))

from paperops.compiler.contracts import ResolvedContract, resolve_section_contract
from paperops.compiler.tex import (
    BlockInventory,
    ManuscriptSnapshot,
    TexBindingResult,
    TexFileSnapshot,
    bind_typed_tex_blocks,
    parse_tex_bytes,
    scan_manuscript,
)


HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def contract_project(parent: str) -> Path:
    root = Path(parent) / "paper-contract"
    write(
        root / "_paperops/defaults/contracts/results.yml",
        """\
section: results
purpose: State the approved result.
reader_question: What was observed?
logic_chain:
  - answer
  - quantitative_evidence
policy:
  scope: bounded
""",
    )
    return root


def legacy_block_hash(body: str) -> str:
    normalized = "\n".join(line.rstrip() for line in body.splitlines()).strip() + "\n"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def block_bodies(text: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    current = ""
    for line in text.splitlines():
        match = re.fullmatch(r"\s*%\s*block:\s*([A-Za-z0-9:._-]+)\s*", line)
        if match:
            current = match.group(1)
            blocks.setdefault(current, [])
        elif current:
            blocks[current].append(line)
    return {key: "\n".join(lines) for key, lines in blocks.items()}


def scanner_project(
    parent: str,
    *,
    ja_text: str | None = None,
    en_text: str | None = None,
) -> Path:
    root = Path(parent) / "paper-scan"
    ja_text = ja_text or """% block: BLK-0001
This raw marker only resembles a typed identity.
% block: results:primary.01
JA primary body.
% block: results:scope.01
JA scope body.
"""
    en_text = en_text or """% block: BLK-0001
This raw marker only resembles a typed identity.
% block: results:primary.01
EN primary body.
% block: results:scope.01
EN scope body.
"""
    write(root / "manuscript/ja/sections/30_results.tex", ja_text)
    write(root / "manuscript/en/sections/30_results.tex", en_text)
    write(
        root / "manuscript/mirror/map.toml",
        """\
version = 1
source_language = "ja"
target_language = "en"

[[file_pair]]
ja = "ja/sections/30_results.tex"
en = "en/sections/30_results.tex"
""",
    )
    ja_blocks = block_bodies(ja_text)
    en_blocks = block_bodies(en_text)
    shared_ids = sorted(set(ja_blocks) & set(en_blocks))
    ledger = {
        "version": 1,
        "blocks": [
            {
                "id": block_id,
                "source_file": "ja/sections/30_results.tex",
                "target_file": "en/sections/30_results.tex",
                "source_hash_at_last_sync": legacy_block_hash(ja_blocks[block_id]),
                "target_hash_at_last_sync": legacy_block_hash(en_blocks[block_id]),
                "status": "synced",
                "last_sync": "2026-07-12",
            }
            for block_id in shared_ids
        ],
    }
    write(
        root / "manuscript/mirror/block-ledger.yml",
        yaml.safe_dump(ledger, sort_keys=False),
    )
    write(
        root / "manuscript/mirror/terminology.yml",
        """\
source_language: ja
target_language: en
terms:
  - id: PUBLIC-SOFTWARE
    ja: 公開ソフトウェア
    en_public: OpenFOAM 11
    status: public
    first_definition_required: false
    first_definition_location: manuscript/en/sections/30_results.tex
    avoid: []
    allowed_context: [manuscript]
    replacement_rule: See doi:10.5281/zenodo.12345 and https://example.org/openfoam.
    figure_label_rule: Use the public software name.
    owner: ""
    last_reviewed: "2026-07-12"
""",
    )
    write(
        root / "_paperops/notes/views/concept-terms.md",
        """\
# Concept terms

## Concept term map

| term ID | canonical term | status | manuscript role | plain-language expansion | variants / avoid | first use | notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CT-0001 | boundary response | accepted | Results | response at the boundary | boundary-response | `manuscript/en/sections/30_results.tex` | public term |

## Usage audit
""",
    )
    return root


class ContractResolverTest(unittest.TestCase):
    def test_private_section_kind_is_rejected_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            private_kind = "sk-abcdefghijklmnop"
            with self.assertRaises(ValueError) as raised:
                resolve_section_contract(Path(tmp), private_kind)

        self.assertNotIn(private_kind, str(raised.exception))

    def test_default_only_contract_records_all_layers_and_deterministic_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)

            first = resolve_section_contract(root, "results")
            second = resolve_section_contract(root, "results")

        self.assertFalse(first.findings)
        self.assertEqual(first.effective["purpose"], "State the approved result.")
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        self.assertRegex(first.snapshot_hash, HASH_RE)
        self.assertEqual(
            tuple(layer.name for layer in first.layers),
            ("managed_default", "project_overlay", "writing_profile"),
        )
        self.assertEqual(tuple(layer.present for layer in first.layers), (True, False, False))
        self.assertRegex(first.layers[0].content_hash, HASH_RE)
        self.assertRegex(first.layers[0].semantic_hash, HASH_RE)
        self.assertEqual(first.trace["/purpose"], "managed_default")

    def test_partial_overlay_merges_recursively_and_traces_the_winning_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "_paperops/contracts/results.yml",
                """\
reader_question: Which comparison changed?
policy:
  scope: comparison-only
""",
            )

            resolved = resolve_section_contract(root, "results")

        self.assertFalse(resolved.findings)
        self.assertEqual(resolved.effective["purpose"], "State the approved result.")
        self.assertEqual(resolved.effective["reader_question"], "Which comparison changed?")
        self.assertEqual(resolved.effective["policy"]["scope"], "comparison-only")
        self.assertEqual(resolved.trace["/reader_question"], "project_overlay")
        self.assertEqual(resolved.trace["/policy/scope"], "project_overlay")
        self.assertTrue(resolved.layers[1].present)

    def test_ordered_list_replacement_requires_complete_list_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            overlay = root / "_paperops/contracts/results.yml"
            write(
                overlay,
                """\
logic_chain:
  - scope
  - consequence
""",
            )

            rejected = resolve_section_contract(root, "results")
            write(
                overlay,
                """\
_overlay:
  complete_lists:
    - /logic_chain
logic_chain:
  - scope
  - consequence
""",
            )
            accepted = resolve_section_contract(root, "results")

        self.assertIn(
            "compile.contract_list_replacement_undeclared",
            {finding.code for finding in rejected.findings},
        )
        self.assertEqual(rejected.effective["logic_chain"], ("answer", "quantitative_evidence"))
        self.assertFalse(accepted.findings)
        self.assertEqual(accepted.effective["logic_chain"], ("scope", "consequence"))
        self.assertEqual(accepted.trace["/logic_chain"], "project_overlay")

    def test_complete_list_metadata_requires_canonical_used_json_pointers(self) -> None:
        cases = {
            "/logic_chain/": "compile.contract_complete_list_invalid",
            "//logic_chain": "compile.contract_complete_list_invalid",
            "/logic~2chain": "compile.contract_complete_list_invalid",
            "/hard_rules": "compile.contract_complete_list_unused",
        }
        for pointer, expected_code in cases.items():
            with self.subTest(pointer=pointer), tempfile.TemporaryDirectory() as tmp:
                root = contract_project(tmp)
                write(
                    root / "_paperops/contracts/results.yml",
                    f"""\
_overlay:
  complete_lists:
    - {pointer}
reader_question: Must not partially win.
""",
                )

                resolved = resolve_section_contract(root, "results")

            self.assertIn(expected_code, {item.code for item in resolved.findings})
            self.assertEqual(resolved.effective["reader_question"], "What was observed?")

    def test_profile_contract_override_can_declare_a_complete_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: generic_research
overlays:
  generic_research:
    result_requirements: [main_observation]
    contract_overrides:
      _overlay:
        complete_lists: [/logic_chain]
      logic_chain: [scope, consequence]
venue_overlay: {}
author_preferences:
  token_count: 1200
  token_budget: 2400
section_depth: {}
""",
            )

            resolved = resolve_section_contract(root, "results")

        self.assertFalse(resolved.findings, resolved.findings)
        self.assertEqual(resolved.effective["logic_chain"], ("scope", "consequence"))
        self.assertEqual(resolved.trace["/logic_chain"], "writing_profile")

    def test_null_unknown_type_change_and_destructive_metadata_are_rejected(self) -> None:
        cases = {
            "purpose: null\n": "compile.contract_null",
            "unknown_contract_key: value\n": "compile.contract_unknown",
            "purpose:\n  - changed-type\n": "compile.contract_type_change",
            "_overlay:\n  remove:\n    - /purpose\n": "compile.contract_unknown_operation",
        }
        for body, expected_code in cases.items():
            with self.subTest(expected_code=expected_code):
                with tempfile.TemporaryDirectory() as tmp:
                    root = contract_project(tmp)
                    write(root / "_paperops/contracts/results.yml", body)

                    resolved = resolve_section_contract(root, "results")

                self.assertIn(expected_code, {finding.code for finding in resolved.findings})
                self.assertEqual(resolved.effective["purpose"], "State the approved result.")

    def test_writing_profile_projection_and_explicit_override_are_highest_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "_paperops/contracts/results.yml",
                "reader_question: Which project comparison changed?\n",
            )
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: computational_modeling
overlays:
  generic_research:
    result_requirements: [main_observation]
  computational_modeling:
    result_requirements: [estimand, denominator, scope_statement]
    figure_requirements: [primary_evidence]
    figure_defaults:
      max_main_sensitivity_figures: 1
    contract_overrides:
      reader_question: Which approved estimand changed?
venue_overlay:
  name: Example Journal
  checked_at: "2026-07-12"
  special_requirements: [data statement]
author_preferences:
  preferred_source_language: ja
section_depth:
  length_is_floor_not_target: true
  profile: full_article
""",
            )

            resolved = resolve_section_contract(root, "results")

        self.assertFalse(resolved.findings)
        self.assertEqual(resolved.effective["reader_question"], "Which approved estimand changed?")
        self.assertEqual(resolved.trace["/reader_question"], "writing_profile")
        profile = resolved.effective["writing_profile"]
        self.assertEqual(profile["paper_type"], "computational_modeling")
        self.assertEqual(
            profile["section_requirements"],
            ("estimand", "denominator", "scope_statement"),
        )
        self.assertEqual(profile["venue_overlay"]["name"], "Example Journal")
        self.assertEqual(
            resolved.trace["/writing_profile/section_requirements"],
            "writing_profile",
        )

    def test_duplicate_yaml_key_and_unknown_profile_key_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "_paperops/contracts/results.yml",
                "purpose: first\npurpose: second\n",
            )
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: generic_research
overlays:
  generic_research: {}
  unused_profile:
    remove: forbidden
venue_overlay: {}
author_preferences: {}
section_depth: {}
unexpected_profile_op: remove
""",
            )

            resolved = resolve_section_contract(root, "results")

        self.assertIn("compile.contract_duplicate_key", {item.code for item in resolved.findings})
        profile_unknown = [
            item for item in resolved.findings if item.code == "compile.contract_profile_unknown"
        ]
        self.assertGreaterEqual(len(profile_unknown), 2)

    def test_resolved_contract_owns_an_immutable_snapshot_but_to_dict_is_detached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_section_contract(contract_project(tmp), "results")

        with self.assertRaises(TypeError):
            resolved.effective["purpose"] = "mutated"  # type: ignore[index]
        with self.assertRaises((AttributeError, TypeError)):
            resolved.effective["logic_chain"].append("mutated")
        public = resolved.to_dict()
        public["effective"]["logic_chain"].append("detached")
        self.assertEqual(resolved.effective["logic_chain"], ("answer", "quantitative_evidence"))

    def test_invalid_overlay_or_profile_layer_is_rejected_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "_paperops/contracts/results.yml",
                "reader_question: Must not partially win.\nunknown_key: reject-layer\n",
            )
            overlay_invalid = resolve_section_contract(root, "results")
            (root / "_paperops/contracts/results.yml").unlink()
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: generic_research
overlays:
  generic_research:
    result_requirements: [main_observation]
    contract_overrides:
      reader_question: Must not partially win either.
      unknown_key: reject-layer
venue_overlay: {}
author_preferences: {}
section_depth: {}
""",
            )
            profile_invalid = resolve_section_contract(root, "results")

            root = contract_project(str(Path(tmp) / "metadata"))
            write(
                root / "_paperops/contracts/results.yml",
                '_overlay:\n  "Authorization: Bearer metadata-secret-value": opaque\n',
            )
            metadata_invalid = resolve_section_contract(root, "results")

        self.assertEqual(overlay_invalid.effective["reader_question"], "What was observed?")
        self.assertEqual(profile_invalid.effective["reader_question"], "What was observed?")
        self.assertNotIn("writing_profile", profile_invalid.effective)
        self.assertIn(
            "compile.contract_unknown_operation",
            {item.code for item in metadata_invalid.findings},
        )
        self.assertNotIn("metadata-secret-value", repr(metadata_invalid.to_dict()))

    def test_section_discriminator_cannot_be_changed_by_higher_layers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "_paperops/contracts/results.yml",
                "section: methods\nreader_question: Must not win.\n",
            )

            resolved = resolve_section_contract(root, "results")

        self.assertIn("compile.contract_section_override", {item.code for item in resolved.findings})
        self.assertEqual(resolved.effective["section"], "results")
        self.assertEqual(resolved.effective["reader_question"], "What was observed?")

    def test_all_contract_layers_reject_non_json_keys_and_yaml_date_scalars_without_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(
                root / "_paperops/contracts/results.yml",
                "policy:\n  7: invalid-non-string-key\n",
            )
            key_invalid = resolve_section_contract(root, "results")
            (root / "_paperops/contracts/results.yml").unlink()
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: generic_research
overlays:
  generic_research: {}
venue_overlay:
  checked_at: 2026-07-12
author_preferences: {}
section_depth: {}
""",
            )
            date_invalid = resolve_section_contract(root, "results")
            (root / "manuscript/writing-profile.yml").unlink()
            write(
                root / "_paperops/contracts/results.yml",
                "policy: &recursive\n  scope: *recursive\n",
            )
            recursive_invalid = resolve_section_contract(root, "results")

        self.assertIn("compile.contract_document_key", {item.code for item in key_invalid.findings})
        self.assertIn("compile.contract_document_value", {item.code for item in date_invalid.findings})
        self.assertTrue(
            {
                "compile.contract_document_value",
                "compile.contract_yaml_alias",
                "compile.contract_yaml_invalid",
            }
            & {item.code for item in recursive_invalid.findings},
        )
        self.assertRegex(key_invalid.layers[1].semantic_hash, HASH_RE)
        self.assertRegex(date_invalid.layers[2].semantic_hash, HASH_RE)

    def test_contract_snapshot_rejects_private_writer_facing_strings(self) -> None:
        private_values = (
            "Authorization: Bearer secret-token-value",
            "github_pat_abcdefghijklmnop",
            "glpat-abcdefghijklmnop",
        )
        for private_value in private_values:
            with self.subTest(private_value=private_value), tempfile.TemporaryDirectory() as tmp:
                root = contract_project(tmp)
                write(
                    root / "_paperops/contracts/results.yml",
                    f'purpose: "{private_value}"\n',
                )

                resolved = resolve_section_contract(root, "results")

            self.assertIn("compile.contract_privacy", {item.code for item in resolved.findings})
            self.assertNotIn(private_value, repr(resolved.to_dict()))
            self.assertEqual(resolved.effective["purpose"], "State the approved result.")

        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            write(root / "_paperops/contracts/results.yml", "purpose: github_pat_demo\n")
            short_dummy = resolve_section_contract(root, "results")
        self.assertFalse(short_dummy.findings, short_dummy.findings)
        self.assertEqual(short_dummy.effective["purpose"], "github_pat_demo")

    def test_contract_and_profile_reject_sensitive_mapping_keys_without_echoing_them(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            managed = root / "_paperops/defaults/contracts/results.yml"
            managed.write_text(
                managed.read_text(encoding="utf-8")
                + "private_key: opaque-contract-value\n",
                encoding="utf-8",
            )
            contract_invalid = resolve_section_contract(root, "results")

            root = contract_project(str(Path(tmp) / "profile"))
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: generic_research
overlays:
  generic_research: {}
venue_overlay: {}
author_preferences:
  api_key: opaque-profile-value
  token: opaque-token-value
  token_count: 1200
  token_budget: 2400
section_depth: {}
""",
            )
            profile_invalid = resolve_section_contract(root, "results")

        for resolved, private_value in (
            (contract_invalid, "opaque-contract-value"),
            (profile_invalid, "opaque-profile-value"),
        ):
            self.assertIn("compile.contract_privacy", {item.code for item in resolved.findings})
            public = repr(resolved.to_dict())
            self.assertNotIn(private_value, public)
            self.assertNotIn("private_key", public)
            self.assertNotIn("api_key", public)
            self.assertNotIn("opaque-token-value", public)

    def test_overlay_metadata_is_allowed_only_at_canonical_overlay_positions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            managed = root / "_paperops/defaults/contracts/results.yml"
            managed.write_text(
                managed.read_text(encoding="utf-8")
                + '_overlay:\n  note: "Authorization: Bearer managed-metadata-secret"\n',
                encoding="utf-8",
            )
            managed_invalid = resolve_section_contract(root, "results")

            root = contract_project(str(Path(tmp) / "inactive"))
            write(
                root / "manuscript/writing-profile.yml",
                """\
schema_version: 1
paper_type: generic_research
overlays:
  generic_research: {}
  inactive_profile:
    contract_overrides:
      _overlay:
        "Authorization: Bearer inactive-metadata-secret": opaque
venue_overlay: {}
author_preferences: {}
section_depth: {}
""",
            )
            inactive_invalid = resolve_section_contract(root, "results")

        for resolved, secret in (
            (managed_invalid, "managed-metadata-secret"),
            (inactive_invalid, "inactive-metadata-secret"),
        ):
            self.assertIn(
                "compile.contract_unknown_operation",
                {item.code for item in resolved.findings},
            )
            self.assertNotIn(secret, repr(resolved.to_dict()))

    def test_yaml_alias_expansion_is_rejected_with_one_stable_finding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            aliases = "[seed, seed, seed, seed, seed, seed, seed, seed]"
            write(
                root / "_paperops/contracts/results.yml",
                f"""\
seed: &seed {aliases}
level1: &level1 [*seed, *seed, *seed, *seed]
level2: [*level1, *level1, *level1, *level1]
""",
            )

            resolved = resolve_section_contract(root, "results")

        aliases = [item for item in resolved.findings if item.code == "compile.contract_yaml_alias"]
        self.assertEqual(len(aliases), 1)

    def test_deep_yaml_is_reported_instead_of_escaping_as_recursion_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            nested = "leaf: value\n"
            for index in range(550):
                nested = f"level{index}:\n" + textwrap.indent(nested, "  ")
            write(root / "_paperops/contracts/results.yml", nested)

            resolved = resolve_section_contract(root, "results")
            write(
                root / "_paperops/contracts/results.yml",
                "purpose: " + "9" * 5000 + "\n",
            )
            huge_integer = resolve_section_contract(root, "results")

        self.assertIn("compile.contract_yaml_invalid", {item.code for item in resolved.findings})
        self.assertIn(
            "compile.contract_yaml_invalid",
            {item.code for item in huge_integer.findings},
        )

    def test_contract_reads_optional_layers_from_the_held_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = contract_project(tmp)
            outside = Path(tmp) / "outside-contract"
            write(
                outside / "_paperops/defaults/contracts/results.yml",
                "section: results\npurpose: Outside replacement.\n",
            )
            held = Path(tmp) / "held-contract"
            swapped = False

            def swap(stage: str, identity: str) -> None:
                nonlocal swapped
                if not swapped and stage == "after_dir_fd_open" and identity == ".":
                    root.rename(held)
                    root.symlink_to(outside, target_is_directory=True)
                    swapped = True

            resolved = resolve_section_contract(root, "results", _capture_hook=swap)

        self.assertFalse(resolved.findings)
        self.assertEqual(resolved.effective["purpose"], "State the approved result.")

    def test_non_section_figures_contract_fails_the_section_discriminator_stably(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-contract"
            write(
                root / "_paperops/defaults/contracts/figures.yml",
                "schema_version: 1\ncontract: figures\npurpose: Plan figures.\n",
            )

            resolved = resolve_section_contract(root, "figures")

        self.assertIn("compile.contract_section_invariant", {item.code for item in resolved.findings})

    def test_all_canonical_template_section_contracts_resolve(self) -> None:
        for section_kind in (
            "introduction",
            "methods",
            "results",
            "discussion",
            "conclusion",
            "storyline",
        ):
            with self.subTest(section_kind=section_kind):
                resolved = resolve_section_contract(ROOT / "template", section_kind)

            self.assertFalse(resolved.findings, resolved.findings)
            self.assertEqual(resolved.effective["section"], section_kind)


class PureTexParserTest(unittest.TestCase):
    def test_public_snapshot_dtos_detach_mutable_sequence_inputs(self) -> None:
        citations = ["alpha2026"]
        inventory = BlockInventory(citations, [], [], [], [], [], [], [])
        marker_order = ["results.public"]
        tex_blocks: list[object] = []
        tex_findings: list[object] = []
        tex_file = TexFileSnapshot(
            "manuscript/en/results.tex",
            "sha256:" + "0" * 64,
            marker_order,
            tex_blocks,
            tex_findings,
        )
        read_files: list[object] = []
        manuscript = ManuscriptSnapshot(
            read_files,
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            "sha256:" + "1" * 64,
        )
        bindings: list[object] = []
        binding_result = TexBindingResult(bindings, [])
        layers: list[object] = []
        contract_findings: list[object] = []
        contract = ResolvedContract(
            "results",
            {},
            layers,
            {},
            contract_findings,
            "sha256:" + "2" * 64,
        )

        citations.append("mutated2026")
        marker_order.append("mutated")
        tex_blocks.append(object())
        tex_findings.append(object())
        read_files.append(object())
        bindings.append(object())
        layers.append(object())
        contract_findings.append(object())

        self.assertEqual(inventory.citation_keys, ("alpha2026",))
        self.assertEqual(tex_file.marker_order, ("results.public",))
        self.assertEqual(tex_file.blocks, ())
        self.assertEqual(tex_file.findings, ())
        self.assertEqual(manuscript.read_files, ())
        self.assertEqual(binding_result.bindings, ())
        self.assertEqual(contract.layers, ())
        self.assertEqual(contract.findings, ())

    def test_direct_parser_rejects_private_identity_without_echo(self) -> None:
        private_identity = "manuscript/en/Authorization: Bearer identity-secret.tex"

        with self.assertRaises(ValueError) as raised:
            parse_tex_bytes(private_identity, b"% block: results.public\nbody\n")

        self.assertNotIn("identity-secret", str(raised.exception))

    def test_oversized_quantity_is_a_stable_finding_not_an_integer_crash(self) -> None:
        huge = b"9" * 5000
        snapshot = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block: results.public\n" + huge + b" of 7 cases\n",
        )

        self.assertIn("compile.tex_quantity_invalid", {item.code for item in snapshot.findings})
        self.assertEqual(snapshot.blocks[0].inventory.quantities, ())
        self.assertNotIn("9" * 100, repr(snapshot.to_dict()))

        at_limit = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block: results.public\n" + b"9" * 512 + b" of 7 cases\n",
        )
        over_limit = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block: results.public\n" + b"9" * 513 + b" of 7 cases\n",
        )
        self.assertFalse(at_limit.findings, at_limit.findings)
        self.assertEqual(len(str(at_limit.blocks[0].inventory.quantities[0].value)), 512)
        self.assertIn("compile.tex_quantity_invalid", {item.code for item in over_limit.findings})

        ordinary = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block: results.public\n1234567890123456789 of 7 cases\n"
            b"intervening prose\n3 of 4 and 5 of 6 cases\n"
            b"6\n of\n 7 cases\n8 of 9 cases\n",
        )
        self.assertFalse(ordinary.findings, ordinary.findings)
        self.assertEqual(ordinary.blocks[0].inventory.quantities[0].value, 1234567890123456789)
        self.assertEqual(
            [item.line_number for item in ordinary.blocks[0].inventory.quantities],
            [2, 4, 4, 5, 8],
        )

    def test_colon_marker_and_exact_protected_inventories_are_structured(self) -> None:
        content = b"""% block: results:primary.01
Figure~\\cref{fig:phase,fig:boundary} reports 3 of 7 cases \\citep[see][p.~2]{alpha2026, beta2025}.
\\begin{figure}\\label{fig:phase}\\end{figure}
% PREDICTED-RESULT: status=analysis-needed; request=AREQ-0008
% SIM-REQUEST: AREQ-0008; run the registered analysis.
% EXPECTATION-BASIS: the approved model predicts a boundary.
% REPLACE-XX: replace after AREQ-0008 is reconciled.
Approximately xx cases remain; TODO add later authoring note.
"""

        snapshot = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            content,
        )

        self.assertFalse(snapshot.findings)
        self.assertEqual(snapshot.marker_order, ("results:primary.01",))
        self.assertRegex(snapshot.content_hash, HASH_RE)
        block = snapshot.blocks[0]
        self.assertEqual(block.marker_id, "results:primary.01")
        self.assertRegex(block.marker_hash, HASH_RE)
        self.assertRegex(block.body_hash, HASH_RE)
        self.assertRegex(block.region_hash, HASH_RE)
        self.assertEqual(block.inventory.citation_keys, ("alpha2026", "beta2025"))
        self.assertEqual(
            [(item.value, item.denominator, item.literal) for item in block.inventory.quantities],
            [(3, 7, "3 of 7")],
        )
        self.assertEqual(block.inventory.figure_labels, ("fig:phase",))
        self.assertEqual(
            block.inventory.figure_references,
            ("fig:phase", "fig:boundary"),
        )
        self.assertEqual(
            tuple(item.name for item in block.inventory.predicted_markers),
            ("PREDICTED-RESULT", "SIM-REQUEST", "EXPECTATION-BASIS", "REPLACE-XX"),
        )
        self.assertEqual(block.inventory.analysis_request_ids, ("AREQ-0008",))
        self.assertEqual(tuple(item.literal for item in block.inventory.placeholders), ("xx", "TODO"))
        self.assertIn("unresolved draft placeholder", tuple(item.kind for item in block.inventory.authoring_intents))
        self.assertEqual(
            set(block.protected_hashes),
            {
                "citations",
                "quantities",
                "figure_labels",
                "figure_references",
                "predicted_markers",
                "analysis_requests",
                "placeholders",
                "authoring_intents",
            },
        )
        self.assertTrue(all(HASH_RE.fullmatch(value) for value in block.protected_hashes.values()))
        public = snapshot.to_dict()
        self.assertNotIn("raw_tex", public)
        self.assertNotIn("content", public)
        self.assertNotIn(content.decode("utf-8"), repr(public))
        self.assertNotIn("run the registered analysis", repr(public))
        self.assertNotIn("the approved model predicts a boundary", repr(public))

        shifted = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            content.replace(b"% block: results:primary.01\n", b"% block: results:primary.01\n\n"),
        )
        self.assertNotEqual(block.body_hash, shifted.blocks[0].body_hash)
        self.assertEqual(block.protected_hashes, shifted.blocks[0].protected_hashes)
        with self.assertRaises(TypeError):
            block.protected_hashes["citations"] = "sha256:" + "0" * 64  # type: ignore[index]

    def test_duplicate_marker_is_not_coalesced_before_reporting(self) -> None:
        snapshot = parse_tex_bytes(
            "manuscript/ja/sections/30_results.tex",
            b"% block: results.same\nfirst\n% block: results.same\nsecond\n",
        )

        self.assertEqual(snapshot.marker_order, ("results.same", "results.same"))
        self.assertEqual(len(snapshot.blocks), 2)
        duplicate = [
            finding
            for finding in snapshot.findings
            if finding.code == "compile.tex_duplicate_block"
        ]
        self.assertEqual(len(duplicate), 1)
        self.assertEqual(duplicate[0].identity, "manuscript/ja/sections/30_results.tex")

    def test_malformed_block_directives_are_not_silently_treated_as_comments(self) -> None:
        snapshot = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block:\n% block: bad id\n% block: valid extra #\nordinary text\n",
        )

        invalid = [
            item for item in snapshot.findings if item.code == "compile.tex_invalid_block_id"
        ]
        self.assertEqual(len(invalid), 3)
        self.assertFalse(snapshot.marker_order)

    def test_private_marker_and_analysis_request_ids_are_not_emitted(self) -> None:
        snapshot = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block: sk-abcdefghijklmnop\nprivate marker body\n"
            b"% block: results.public\n% SIM-REQUEST: AREQ-ghp_abcdefghijklmnop\n",
        )

        self.assertIn("compile.privacy_private_public_text", {item.code for item in snapshot.findings})
        self.assertEqual(snapshot.marker_order, ("results.public",))
        self.assertEqual(snapshot.blocks[0].inventory.analysis_request_ids, ())
        public = repr(snapshot.to_dict())
        self.assertNotIn("sk-abcdefghijklmnop", public)
        self.assertNotIn("AREQ-ghp_abcdefghijklmnop", public)

    def test_public_inventory_preserves_doi_but_redacts_private_citation_and_figure_values(self) -> None:
        snapshot = parse_tex_bytes(
            "manuscript/en/sections/30_results.tex",
            b"% block: results.public\n\\cite{doi:10.1234/public,/LARGE1/private/source}\n"
            b"\\label{fig:results/main}\\ref{fig:results/main}\n"
            b"\\label{fig:/LARGE1/private/figure}\n",
        )

        self.assertEqual(snapshot.blocks[0].inventory.citation_keys, ("doi:10.1234/public",))
        self.assertEqual(snapshot.blocks[0].inventory.figure_labels, ("fig:results/main",))
        self.assertEqual(snapshot.blocks[0].inventory.figure_references, ("fig:results/main",))
        self.assertIn("compile.privacy_private_public_text", {item.code for item in snapshot.findings})
        public = repr(snapshot.to_dict())
        self.assertNotIn("/LARGE1/private/source", public)
        self.assertNotIn("fig:/LARGE1/private/figure", public)


class ManuscriptScannerTest(unittest.TestCase):
    def test_scan_preserves_map_paths_hashes_markers_and_explicit_typed_bindings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            ledger = root / "manuscript/mirror/block-ledger.yml"
            before = ledger.read_bytes()

            snapshot = scan_manuscript(root)
            binding = bind_typed_tex_blocks(
                snapshot,
                [
                    {
                        "id": "BLK-0001",
                        "ja_tex_block_id": "results:primary.01",
                        "en_tex_block_id": "results:primary.01",
                    }
                ],
            )

            after = ledger.read_bytes()

        self.assertFalse(snapshot.findings, snapshot.findings)
        self.assertEqual(before, after)
        self.assertRegex(snapshot.snapshot_hash, HASH_RE)
        self.assertEqual(
            snapshot.file_pairs[0].ja_identity,
            "manuscript/ja/sections/30_results.tex",
        )
        self.assertEqual(
            snapshot.file_pairs[0].en_identity,
            "manuscript/en/sections/30_results.tex",
        )
        self.assertEqual(snapshot.file_pairs[0].status, "exact")
        self.assertIn("BLK-0001", snapshot.tex_files[1].marker_order)
        self.assertIn("results:primary.01", snapshot.tex_files[1].marker_order)
        self.assertTrue(
            {
                "manuscript/mirror/map.toml",
                "manuscript/mirror/block-ledger.yml",
                "manuscript/mirror/terminology.yml",
                "_paperops/notes/views/concept-terms.md",
                "manuscript/ja/sections/30_results.tex",
                "manuscript/en/sections/30_results.tex",
            }.issubset(snapshot.read_paths)
        )
        self.assertTrue(all(HASH_RE.fullmatch(item.content_hash) for item in snapshot.read_files))
        self.assertFalse(binding.findings)
        self.assertEqual(
            [(item.typed_block_id, item.language, item.raw_block_id) for item in binding.bindings],
            [
                ("BLK-0001", "ja", "results:primary.01"),
                ("BLK-0001", "en", "results:primary.01"),
            ],
        )
        self.assertNotEqual(binding.bindings[0].raw_block_id, binding.bindings[0].typed_block_id)

    def test_explicit_raw_marker_cannot_be_reused_by_two_typed_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = scan_manuscript(scanner_project(tmp))

        binding = bind_typed_tex_blocks(
            snapshot,
            [
                {
                    "id": "BLK-0001",
                    "ja_tex_block_id": "results:primary.01",
                    "en_tex_block_id": "results:primary.01",
                },
                {
                    "id": "BLK-0002",
                    "ja_tex_block_id": "results:primary.01",
                    "en_tex_block_id": "results:primary.01",
                },
            ],
        )

        self.assertIn("compile.tex_binding_reused_raw", {item.code for item in binding.findings})
        self.assertEqual({item.typed_block_id for item in binding.bindings}, {"BLK-0001"})

    def test_typed_binding_is_atomic_and_both_languages_must_share_one_map_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            write(
                root / "manuscript/en/sections/unpaired.tex",
                "% block: results:unpaired.01\nUnpaired body.\n",
            )
            snapshot = scan_manuscript(root)

        binding = bind_typed_tex_blocks(
            snapshot,
            [
                {
                    "id": "BLK-0002",
                    "ja_tex_block_id": "results:primary.01",
                    "en_tex_block_id": "results:missing.01",
                },
                {
                    "id": "BLK-0003",
                    "ja_tex_block_id": "results:scope.01",
                    "en_tex_block_id": "results:unpaired.01",
                },
            ],
        )

        codes = {item.code for item in binding.findings}
        self.assertIn("compile.tex_binding_missing", codes)
        self.assertIn("compile.tex_binding_pair", codes)
        self.assertFalse(binding.bindings)

    def test_reordered_missing_and_duplicate_markers_are_reported_before_pairing(self) -> None:
        mutations = {
            "reordered": (
                "% block: results:scope.01\nEN scope body.\n% block: results:primary.01\nEN primary body.\n% block: BLK-0001\nThis raw marker only resembles a typed identity.\n",
                "compile.mirror_block_reordered",
            ),
            "missing": (
                "% block: results:scope.01\nEN scope body.\n",
                "compile.mirror_block_missing",
            ),
            "duplicate": (
                "% block: BLK-0001\nraw typed-like marker\n% block: results:primary.01\nfirst\n% block: results:primary.01\nsecond\n% block: results:scope.01\nEN scope body.\n",
                "compile.tex_duplicate_block",
            ),
        }
        ja = "% block: BLK-0001\nraw typed-like marker\n% block: results:primary.01\nJA primary body.\n% block: results:scope.01\nJA scope body.\n"
        for label, (en, expected) in mutations.items():
            with self.subTest(label=label):
                with tempfile.TemporaryDirectory() as tmp:
                    root = scanner_project(tmp, ja_text=ja, en_text=en)
                    snapshot = scan_manuscript(root)
                self.assertIn(expected, {finding.code for finding in snapshot.findings})

    def test_legacy_ledger_hash_is_separate_from_full_hash_and_reports_one_language_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            ja = root / "manuscript/ja/sections/30_results.tex"
            ja.write_text(
                ja.read_text(encoding="utf-8").replace("JA scope body.", "JA changed scope body."),
                encoding="utf-8",
            )

            snapshot = scan_manuscript(root)

        drift = [item for item in snapshot.freshness if item.status == "source_changed"]
        self.assertEqual(len(drift), 1)
        self.assertRegex(drift[0].source_hash_at_last_sync, r"^[0-9a-f]{16}$")
        self.assertRegex(drift[0].source_body_hash, HASH_RE)
        self.assertNotEqual(drift[0].source_hash_at_last_sync, drift[0].source_body_hash)
        self.assertIn(
            "compile.mirror_single_language_drift",
            {finding.code for finding in snapshot.findings},
        )

    def test_ledger_rows_must_belong_to_a_declared_map_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            ledger_path = root / "manuscript/mirror/block-ledger.yml"
            ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
            rejected_id = ledger["blocks"][0]["id"]
            ledger["blocks"][0]["target_file"] = "en/sections/unmapped.tex"
            ledger_path.write_text(yaml.safe_dump(ledger, sort_keys=False), encoding="utf-8")

            snapshot = scan_manuscript(root)

        self.assertIn("compile.mirror_ledger_pair", {item.code for item in snapshot.findings})
        self.assertNotIn(rejected_id, {item.raw_block_id for item in snapshot.freshness})

    def test_public_doi_https_and_software_survive_but_private_absolute_path_is_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            allowed = scan_manuscript(root)
            terminology = root / "manuscript/mirror/terminology.yml"
            terminology.write_text(
                terminology.read_text(encoding="utf-8").replace(
                    "OpenFOAM 11",
                    "/LARGE1/private/raw/run-007",
                ),
                encoding="utf-8",
            )
            rejected = scan_manuscript(root)

        self.assertFalse(allowed.findings, allowed.findings)
        public_rule = allowed.terminology_rules[0]
        self.assertEqual(public_rule.en_public, "OpenFOAM 11")
        self.assertIn("doi:10.5281/zenodo.12345", public_rule.replacement_rule)
        self.assertIn("https://example.org/openfoam", public_rule.replacement_rule)
        self.assertIn(
            "compile.privacy_private_public_text",
            {finding.code for finding in rejected.findings},
        )
        self.assertNotIn("/LARGE1/private/raw/run-007", repr(rejected.to_dict()))

    def test_all_public_terminology_and_concept_strings_apply_the_privacy_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            terminology = root / "manuscript/mirror/terminology.yml"
            terminology.write_text(
                terminology.read_text(encoding="utf-8").replace(
                    "allowed_context: [manuscript]",
                    "allowed_context: [/LARGE1/private/context]",
                ),
                encoding="utf-8",
            )
            concept = root / "_paperops/notes/views/concept-terms.md"
            concept.write_text(
                concept.read_text(encoding="utf-8").replace(
                    "`manuscript/en/sections/30_results.tex`",
                    "`C:\\private\\first-use.tex`",
                ),
                encoding="utf-8",
            )

            snapshot = scan_manuscript(root)

        privacy = [
            finding
            for finding in snapshot.findings
            if finding.code == "compile.privacy_private_public_text"
        ]
        self.assertGreaterEqual(len(privacy), 2)
        public = repr(snapshot.to_dict())
        self.assertNotIn("/LARGE1/private/context", public)
        self.assertNotIn("C:\\private\\first-use.tex", public)

    def test_private_credentials_traversal_unc_and_raw_review_text_are_redacted(self) -> None:
        private_values = (
            "Authorization: Bearer secret-token-value",
            "http://user:password@example.org/private",
            "../../private/reviewer.txt",
            r"\\server\share\private.txt",
            "raw reviewer correspondence",
        )
        for private_value in private_values:
            with self.subTest(private_value=private_value), tempfile.TemporaryDirectory() as tmp:
                root = scanner_project(tmp)
                terminology_path = root / "manuscript/mirror/terminology.yml"
                document = yaml.safe_load(terminology_path.read_text(encoding="utf-8"))
                document["terms"][0]["en_public"] = private_value
                terminology_path.write_text(
                    yaml.safe_dump(document, sort_keys=False),
                    encoding="utf-8",
                )

                snapshot = scan_manuscript(root)

            self.assertIn(
                "compile.privacy_private_public_text",
                {item.code for item in snapshot.findings},
            )
            self.assertNotIn(private_value, repr(snapshot.to_dict()))

    def test_public_yaml_status_and_mapping_key_type_errors_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            terminology_path = root / "manuscript/mirror/terminology.yml"
            terminology = yaml.safe_load(terminology_path.read_text(encoding="utf-8"))
            terminology[7] = "mixed-root-key"
            terminology["terms"][0][8] = "mixed-rule-key"
            terminology["terms"][0]["status"] = []
            terminology_path.write_text(
                yaml.safe_dump(terminology, sort_keys=False),
                encoding="utf-8",
            )
            write(
                root / "_paperops/requests/analysis/AREQ-0008.md",
                "---\nid: AREQ-0008\ntype: analysis_request\nstatus: []\n---\nbody\n",
            )
            ledger_path = root / "manuscript/mirror/block-ledger.yml"
            ledger = yaml.safe_load(ledger_path.read_text(encoding="utf-8"))
            ledger["blocks"][0]["status"] = "Authorization: Bearer ledger-secret"
            ledger_path.write_text(
                yaml.safe_dump(ledger, sort_keys=False),
                encoding="utf-8",
            )

            snapshot = scan_manuscript(root)
            write(
                root / "manuscript/mirror/terminology.yml",
                "value: " + "9" * 5000 + "\n",
            )
            huge_integer = scan_manuscript(root)

        codes = {item.code for item in snapshot.findings}
        self.assertIn("compile.terminology_key", codes)
        self.assertIn("compile.terminology_status", codes)
        self.assertIn("compile.analysis_request_status", codes)
        self.assertIn("compile.mirror_ledger_status", codes)
        self.assertNotIn("ledger-secret", repr(snapshot.to_dict()))
        self.assertIn(
            "compile.terminology_invalid",
            {item.code for item in huge_integer.findings},
        )

    def test_private_unknown_keys_paths_and_discovered_identities_do_not_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            map_path = root / "manuscript/mirror/map.toml"
            map_path.write_text(
                map_path.read_text(encoding="utf-8").replace(
                    "[[file_pair]]",
                    '"Authorization: Bearer map-secret-value" = "opaque"\n\n[[file_pair]]',
                    1,
                ),
                encoding="utf-8",
            )
            terminology = root / "manuscript/mirror/terminology.yml"
            terminology.write_text(
                terminology.read_text(encoding="utf-8")
                + '\n"Authorization: Bearer term-secret-value": opaque\n',
                encoding="utf-8",
            )
            write(
                root / "_paperops/refs/bib/imported/Authorization: Bearer file-secret.bib",
                "@article{privateIdentity2026, title={Private}}\n",
            )

            snapshot = scan_manuscript(root)

        codes = {item.code for item in snapshot.findings}
        self.assertIn("compile.mirror_map_unknown", codes)
        self.assertIn("compile.terminology_key", codes)
        self.assertIn("compile.manuscript_private_identity", codes)
        public = repr(snapshot.to_dict())
        for secret in (
            "map-secret-value",
            "term-secret-value",
            "file-secret",
            "privateIdentity2026",
        ):
            self.assertNotIn(secret, public)

    def test_private_map_pair_path_is_rejected_without_echoing_the_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            map_path = root / "manuscript/mirror/map.toml"
            map_path.write_text(
                map_path.read_text(encoding="utf-8").replace(
                    'ja = "ja/sections/30_results.tex"',
                    'ja = "ja/Authorization: Bearer pair-secret.tex"',
                ),
                encoding="utf-8",
            )

            snapshot = scan_manuscript(root)

        self.assertIn("compile.mirror_map_path", {item.code for item in snapshot.findings})
        self.assertNotIn("pair-secret", repr(snapshot.to_dict()))

    def test_pem_private_key_header_is_rejected_from_public_rules(self) -> None:
        for private_value in (
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "password=synthetic-private-value",
        ):
            with self.subTest(private_value=private_value), tempfile.TemporaryDirectory() as tmp:
                root = scanner_project(tmp)
                terminology = root / "manuscript/mirror/terminology.yml"
                terminology.write_text(
                    terminology.read_text(encoding="utf-8").replace(
                        "OpenFOAM 11",
                        private_value,
                    ),
                    encoding="utf-8",
                )

                snapshot = scan_manuscript(root)

            self.assertIn(
                "compile.privacy_private_public_text",
                {item.code for item in snapshot.findings},
            )
            self.assertNotIn(private_value, repr(snapshot.to_dict()))

    def test_analysis_request_cards_capture_only_validated_authority_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            write(
                root / "_paperops/requests/analysis/AREQ-0008.md",
                """\
---
id: AREQ-0008
type: analysis_request
status: open
---

Private working body /LARGE1/raw/reviewer-note must not be public.
""",
            )
            write(
                root / "_paperops/requests/analysis/nested/AREQ-9999.md",
                "---\nid: AREQ-9999\ntype: analysis_request\nstatus: open\n---\nnested\n",
            )

            snapshot = scan_manuscript(root)

        self.assertFalse(snapshot.findings, snapshot.findings)
        request = snapshot.analysis_requests[0]
        self.assertEqual(
            (request.request_id, request.status, request.identity),
            ("AREQ-0008", "open", "_paperops/requests/analysis/AREQ-0008.md"),
        )
        self.assertRegex(request.content_hash, HASH_RE)
        self.assertEqual(len(snapshot.analysis_requests), 1)
        self.assertNotIn("nested/AREQ-9999.md", snapshot.read_paths)
        self.assertNotIn("Private working body", repr(snapshot.to_dict()))
        self.assertNotIn("/LARGE1/raw/reviewer-note", repr(snapshot.to_dict()))

    def test_analysis_request_duplicate_id_bad_status_and_duplicate_frontmatter_key_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            request_dir = root / "_paperops/requests/analysis"
            write(
                request_dir / "AREQ-A.md",
                "---\nid: AREQ-0008\ntype: analysis_request\nstatus: mystery\n---\nbody\n",
            )
            write(
                request_dir / "AREQ-B.md",
                "---\nid: AREQ-0008\ntype: analysis_request\nstatus: open\nstatus: running\n---\nbody\n",
            )
            write(
                request_dir / "AREQ-C.md",
                "---\nid: AREQ-0008\ntype: analysis_request\nstatus: running\n---\nbody\n",
            )

            snapshot = scan_manuscript(root)

        codes = {finding.code for finding in snapshot.findings}
        self.assertIn("compile.analysis_request_status", codes)
        self.assertIn("compile.analysis_request_duplicate_key", codes)
        self.assertIn("compile.analysis_request_duplicate_id", codes)

    def test_private_analysis_request_id_and_deep_public_yaml_fail_stably(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            write(
                root / "_paperops/requests/analysis/AREQ-private.md",
                "---\nid: AREQ-ghp_abcdefghijklmnop\ntype: analysis_request\nstatus: open\n---\nbody\n",
            )
            nested = "leaf: value\n"
            for index in range(550):
                nested = f"level{index}:\n" + textwrap.indent(nested, "  ")
            write(root / "manuscript/mirror/terminology.yml", nested)

            snapshot = scan_manuscript(root)

        codes = {item.code for item in snapshot.findings}
        self.assertIn("compile.analysis_request_privacy", codes)
        self.assertIn("compile.terminology_invalid", codes)
        self.assertNotIn("ghp_abcdefghijklmnop", repr(snapshot.to_dict()))

    def test_deep_mirror_toml_is_reported_instead_of_escaping_as_recursion_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            write(
                root / "manuscript/mirror/map.toml",
                "x = " + "[" * 550 + "0" + "]" * 550 + "\n",
            )

            snapshot = scan_manuscript(root)
            write(
                root / "manuscript/mirror/map.toml",
                "x = " + "9" * 5000 + "\n",
            )
            huge_integer = scan_manuscript(root)

        self.assertIn("compile.mirror_map_invalid", {item.code for item in snapshot.findings})
        self.assertIn("compile.mirror_map_invalid", {item.code for item in huge_integer.findings})

    def test_bibliography_snapshot_exposes_keys_not_raw_body_and_checks_citations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            en = root / "manuscript/en/sections/30_results.tex"
            en.write_text(
                en.read_text(encoding="utf-8")
                .replace(
                    "EN primary body.",
                    "EN primary body \\citep{alpha2026,paren2026,imported2026,curated2026,missing2026,nested2026,elsewhere2026,nestedfake2026,fieldfake2026,stringfake2026,preamblefake2026,parenfake2026,unclosedfake2026}.",
                ),
                encoding="utf-8",
            )
            write(
                root / "manuscript/shared/bib/references.bib",
                """\
@article{alpha2026,
  title = {Public title},
  author = {M{\\\"u}ller},
  year = {2026},
  note = {An escaped \\} brace remains inside this field},
  note = {A literal @software{fieldfake2026, title={Nested fake}}},
  note = {private /LARGE1/raw/bibliography-body}
}
@comment{fake2026, must not become an entry}
@comment{ignored, @article{nestedfake2026, title={Nested fake}}}
@string{fakeMacro = "@software{stringfake2026, title={Nested fake}}"}
@preamble{"@article{preamblefake2026, title={Nested fake}}"}
@article(paren2026,
  title = {A result (bounded) @software{parenfake2026, title={Nested fake}}},
  author = {Public Author},
  year = {2026}
)
% @article{commented2026, title={Must not become an entry}}
""",
            )
            write(
                root / "manuscript/shared/bib/nested/ignored.bib",
                "@article{nested2026, title={Nested is not registry authority}}\n",
            )
            write(
                root / "manuscript/elsewhere/ignored.bib",
                "@article{elsewhere2026, title={Elsewhere is not registry authority}}\n",
            )
            write(
                root / "_paperops/refs/bib/imported/imported.bib",
                "@dataset(imported2026,\n  title={Imported registry entry},\n  author={Public Author},\n  year={2026}\n)\n",
            )
            write(
                root / "_paperops/refs/bib/curated/curated.bib",
                "@software{curated2026,\n  title={Curated registry entry},\n  author={Public Author},\n  year={2026}\n}\n",
            )
            write(
                root / "_paperops/refs/bib/curated/unclosed.bib",
                "@article{unfinished2026, title={Unclosed @software{unclosedfake2026, title={Fake}}\n",
            )
            write(
                root / "manuscript/shared/style/private-citation.tex",
                "\\cite{style-only-missing}\n",
            )

            snapshot = scan_manuscript(root)
            legacy = run_python_script(
                ROOT / "template/scripts/check-citations.py",
                "--root",
                root,
            )
            lint = run_python_script(
                ROOT / "template/scripts/lint-bib.py",
                "--root",
                root,
                "--mode",
                "starter",
            )
            write(
                root / "_paperops/refs/bib/curated/duplicate.bib",
                "@software{alpha2026, title={Duplicate key}}\n",
            )
            duplicate = scan_manuscript(root)

        bibliography = {item.identity: item for item in snapshot.bibliography_files}
        shared = bibliography["manuscript/shared/bib/references.bib"]
        self.assertEqual(shared.entry_keys, ("alpha2026", "paren2026"))
        self.assertRegex(shared.content_hash, HASH_RE)
        self.assertEqual(
            set(bibliography),
            {
                "manuscript/shared/bib/references.bib",
                "_paperops/refs/bib/imported/imported.bib",
                "_paperops/refs/bib/curated/curated.bib",
                "_paperops/refs/bib/curated/unclosed.bib",
            },
        )
        self.assertIn("compile.bibliography_invalid", {finding.code for finding in snapshot.findings})
        self.assertFalse(
            any(
                "unfinished2026" in bibliography_file.entry_keys
                for bibliography_file in snapshot.bibliography_files
            )
        )
        self.assertEqual(
            len([finding for finding in snapshot.findings if finding.code == "compile.citation_missing"]),
            9,
        )
        self.assertNotIn("nested/ignored.bib", snapshot.read_paths)
        self.assertNotIn("elsewhere/ignored.bib", snapshot.read_paths)
        self.assertNotIn("private /LARGE1/raw/bibliography-body", repr(snapshot.to_dict()))
        self.assertIn("compile.bibliography_duplicate_key", {finding.code for finding in duplicate.findings})
        self.assertEqual(legacy.returncode, 1)
        self.assertIn("nestedfake2026", legacy.stdout)
        for fake_key in (
            "fieldfake2026",
            "stringfake2026",
            "preamblefake2026",
            "parenfake2026",
            "unclosedfake2026",
        ):
            self.assertNotIn(fake_key, repr(snapshot.bibliography_files))
            self.assertNotIn(fake_key, lint.stdout)
        self.assertIn("4 エントリ", lint.stdout)

    def test_unsafe_discovery_trees_and_special_entries_are_rejected(self) -> None:
        for kind in ("analysis_symlink", "bib_fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = scanner_project(tmp)
                if kind == "analysis_symlink":
                    outside = root / "outside-analysis"
                    write(
                        outside / "AREQ-9999.md",
                        "---\nid: AREQ-9999\ntype: analysis_request\nstatus: open\n---\nsecret\n",
                    )
                    link = root / "_paperops/requests/analysis"
                    link.parent.mkdir(parents=True, exist_ok=True)
                    link.symlink_to(outside, target_is_directory=True)
                else:
                    fifo = root / "manuscript/shared/bib/blocked.bib"
                    fifo.parent.mkdir(parents=True, exist_ok=True)
                    os.mkfifo(fifo)

                snapshot = scan_manuscript(root)

            self.assertIn("compile.manuscript_unsafe_tree", {item.code for item in snapshot.findings})
            self.assertNotIn("AREQ-9999", repr(snapshot.to_dict()))

    def test_excessively_deep_authority_tree_is_rejected_before_recursion_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            deep = root / "manuscript/shared/bib"
            for index in range(140):
                deep /= f"d{index}"
            write(deep / "ignored.bib", "@article{deep2026, title={Deep}}\n")

            snapshot = scan_manuscript(root)

        self.assertIn("compile.manuscript_unsafe_tree", {item.code for item in snapshot.findings})
        self.assertNotIn("deep2026", repr(snapshot.to_dict()))

    def test_optional_tree_child_disappearance_is_unsafe_not_silently_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            raced = root / "_paperops/refs/bib/imported/race.bib"
            write(raced, "@article{race2026, title={Race}}\n")
            removed = False

            def remove_child(stage: str, identity: str) -> None:
                nonlocal removed
                if (
                    not removed
                    and stage == "before_final_open"
                    and identity == "_paperops/refs/bib/imported/race.bib"
                ):
                    raced.unlink()
                    removed = True

            snapshot = scan_manuscript(root, _capture_hook=remove_child)

        self.assertIn("compile.manuscript_unsafe_tree", {item.code for item in snapshot.findings})
        self.assertTrue(snapshot.file_pairs)
        self.assertNotIn("race2026", repr(snapshot.to_dict()))

    def test_one_held_manuscript_tree_keeps_map_tex_ledger_terms_and_bib_coherent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            manuscript = root / "manuscript"
            bibliography = manuscript / "shared/bib"
            write(bibliography / "safe.bib", "@article{safe2026, title={Safe}}\n")
            outside = root / "outside-manuscript"
            write(outside / "shared/bib/secret.bib", "@article{secret2026, title={Secret}}\n")
            write(
                outside / "mirror/map.toml",
                'version=1\nsource_language="ja"\ntarget_language="en"\nfile_pair=[]\n',
            )
            held = root / "held-manuscript"
            swapped = False

            def swap(stage: str, identity: str) -> None:
                nonlocal swapped
                if (
                    not swapped
                    and stage == "after_file_fd_open"
                    and identity == "manuscript/mirror/map.toml"
                ):
                    manuscript.rename(held)
                    manuscript.symlink_to(outside, target_is_directory=True)
                    swapped = True

            snapshot = scan_manuscript(root, _capture_hook=swap)

        keys = {
            key
            for bibliography_file in snapshot.bibliography_files
            for key in bibliography_file.entry_keys
        }
        self.assertEqual(keys, {"safe2026"})
        self.assertTrue(snapshot.file_pairs)
        self.assertTrue(all(pair.status == "exact" for pair in snapshot.file_pairs))
        self.assertNotIn("secret2026", repr(snapshot.to_dict()))

    def test_scanner_reads_all_authority_trees_from_the_held_project_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = scanner_project(tmp)
            outside = Path(tmp) / "outside-project"
            outside.mkdir()
            held = Path(tmp) / "held-project"
            swapped = False

            def swap(stage: str, identity: str) -> None:
                nonlocal swapped
                if not swapped and stage == "after_dir_fd_open" and identity == ".":
                    root.rename(held)
                    root.symlink_to(outside, target_is_directory=True)
                    swapped = True

            snapshot = scan_manuscript(root, _capture_hook=swap)

        self.assertFalse(snapshot.findings, snapshot.findings)
        self.assertTrue(snapshot.file_pairs)
        self.assertIn("manuscript/mirror/map.toml", snapshot.read_paths)

    def test_template_scanner_sanity_uses_real_map_ledger_terms_and_bibliography(self) -> None:
        snapshot = scan_manuscript(ROOT / "template")

        errors = [finding for finding in snapshot.findings if finding.severity == "error"]
        self.assertFalse(errors, errors)
        self.assertTrue(snapshot.file_pairs)
        self.assertTrue(all(pair.status == "exact" for pair in snapshot.file_pairs))
        self.assertFalse(
            {
                "compile.mirror_single_language_drift",
                "compile.mirror_both_languages_drift",
            }
            & {finding.code for finding in snapshot.findings}
        )



if __name__ == "__main__":
    unittest.main()
