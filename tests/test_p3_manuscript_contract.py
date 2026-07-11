from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT, copy_template, run_python_script


SCRIPTS = ROOT / "template/scripts"
SCHEMAS = ROOT / "template/_paperops/defaults/schemas"
CHECKER = SCRIPTS / "check-paperops-models.py"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(SCRIPTS))

from paperops.compiler import (  # noqa: E402
    AuthoritySnapshot,
    CompileBundle,
    CompileFinding,
    CompileRequest,
    InputSnapshot,
    SectionPlan,
    WriteScope,
    WriterPacket,
)
import paperops_models  # noqa: E402
from paperops_models import (  # noqa: E402
    CatalogObject,
    ObjectCatalog,
    validate_manuscript_semantics,
)
from paperops_schema import load_document, semantic_hash, validate_schema  # noqa: E402


HASH = "sha256:" + "a" * 64
HASH_EXCLUSIONS = ("/approvals", "/metadata/updated_at")
GENERATED_SCHEMA_NAMES = (
    "compile-bundle",
    "section-plan",
    "writer-packet",
    "writer-patch",
)


def valid_section(
    section_id: str = "SEC-0001",
    *,
    move_id: str = "MOV-0001",
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "section",
        "id": section_id,
        "revision": 1,
        "status": "planned",
        "dependencies": [],
        "approvals": [],
        "extensions": {},
        "metadata": {"updated_at": "2026-07-12"},
        "section_kind": "results",
        "ordered_block_ids": [],
        "contract_refs": ["contract:results"],
        "editorial_move_refs": [move_id],
        "research_refs": [],
        "source_language": "ja",
        "mirror_policy": "ja_primary",
        "compiled_manifest_ref": "",
        "dependency_hash": "",
        "last_verified_dependency_hash": "",
    }


def valid_block() -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "block",
        "id": "BLK-0001",
        "revision": 1,
        "status": "planned",
        "dependencies": [],
        "approvals": [],
        "extensions": {},
        "metadata": {"updated_at": "2026-07-12"},
        "section_id": "SEC-0001",
        "position": 1,
        "block_kind": "evidence",
        "reader_task": "State the principal result.",
        "operation": "add",
        "ja_tex_block_id": "results:block-1:ja",
        "en_tex_block_id": "results:block-1:en",
        "claim_refs": [],
        "result_refs": [],
        "source_refs": [],
        "figure_refs": [],
        "citation_keys": [],
        "compiled_from": None,
        "dependency_hash": "",
        "last_verified_dependency_hash": "",
        "allowed_operations": ["add", "rewrite"],
        "forbidden_scope_expansion": [],
    }


def catalog(*documents: dict[str, object]) -> ObjectCatalog:
    objects: dict[str, CatalogObject] = {}
    for document in documents:
        object_id = str(document["id"])
        object_type = str(document["record_type"])
        objects[object_id] = CatalogObject(
            object_id=object_id,
            object_type=object_type,
            model_name="manuscript",
            document=document,
            revision=int(document["revision"]),
            object_hash=semantic_hash(document, excluded_paths=HASH_EXCLUSIONS),
            pointer=f"/{object_id}",
        )
    return ObjectCatalog(objects, ())


def add_current_editorial_approval(section: dict[str, object]) -> None:
    section_hash = semantic_hash(section, excluded_paths=HASH_EXCLUSIONS)
    approvals = section["approvals"]
    assert isinstance(approvals, list)
    approvals.append(
        {
            "approval_id": "APR-0001",
            "kind": "editorial_choice",
            "decision": "approved",
            "object_revision": section["revision"],
            "object_hash": section_hash,
            "actor": "human",
            "note": "Approved for compile.",
        }
    )


def ready_section(
    section_id: str,
    role: str,
    *,
    move_id: str = "MOV-0001",
) -> dict[str, object]:
    section = valid_section(section_id, move_id=move_id)
    section["move_bindings"] = [
        {
            "move_id": move_id,
            "role": role,
            "reason": f"{role} placement",
        }
    ]
    section["dependencies"] = [
        {
            "target_id": move_id,
            "relation": "guided_by",
            "expected_hash": HASH,
        }
    ]
    add_current_editorial_approval(section)
    return section


def finding_rows(findings: object) -> list[tuple[str, str, str]]:
    assert isinstance(findings, list)
    return [
        (finding.code, finding.pointer, finding.message)
        for finding in findings
    ]


def generated_documents() -> dict[str, dict[str, object]]:
    scope = WriteScope(
        level="section",
        languages=("ja",),
        files=("manuscript/ja/results.tex",),
        section_ids=("SEC-0001",),
        block_ids=("BLK-0001",),
        allowed_operations=("rewrite", "add"),
    )
    request = CompileRequest(("SEC-0001",), scope)
    authority = AuthoritySnapshot(
        model_name="manuscript",
        mode="v2-authoritative",
        model_hash=HASH,
        transaction_id="txn-001",
    )
    snapshot = InputSnapshot(
        identity="_paperops/model/manuscript/sections/SEC-0001.yml",
        input_type="section",
        semantic_hash=HASH,
        relation="target",
        model_name="manuscript",
        revision=1,
    )
    plan = SectionPlan(
        section_id="SEC-0001",
        revision=1,
        semantic_hash=HASH,
        section_kind="results",
        ordered_block_ids=("BLK-0001",),
        inputs=(snapshot,),
        projection={
            "schema_version": 1,
            "move_bindings": [
                {
                    "move_id": "MOV-0001",
                    "role": "primary",
                    "reason": "principal result",
                }
            ],
            "extensions": {},
        },
    )
    packet = WriterPacket(
        packet_id="packet-001",
        compile_id="compile-001",
        authority=(authority,),
        write_scope=scope,
        inputs=(snapshot,),
        read_context={
            "schema_version": 1,
            "global": ".paperops/compile/compile-001/context/global.json",
            "extensions": {},
        },
        payload={
            "schema_version": 1,
            "section_plan": "SEC-0001",
            "extensions": {},
        },
    )
    finding = CompileFinding(
        code="compile.example",
        pointer="/inputs/0",
        message="example diagnostic",
        severity="info",
        identity="_paperops/model/manuscript/sections/SEC-0001.yml",
    )
    plan = SectionPlan(
        section_id=plan.section_id,
        revision=plan.revision,
        semantic_hash=plan.semantic_hash,
        section_kind=plan.section_kind,
        ordered_block_ids=plan.ordered_block_ids,
        inputs=plan.inputs,
        projection=plan.projection,
        findings=(finding,),
    )
    bundle = CompileBundle(
        compile_id="compile-001",
        source_mode="authoritative",
        request=request,
        authority=(authority,),
        inputs=(snapshot,),
        section_plans=(plan,),
        writer_packets=(packet,),
        findings=(finding,),
    )
    patch = {
        "schema_version": 1,
        "session_id": "session-001",
        "compile_id": "compile-001",
        "changes": [
            {
                "path": "manuscript/ja/results.tex",
                "block_id": "BLK-0001",
                "operation": "rewrite",
                "preimage_hash": HASH,
                "replacement_hash": "sha256:" + "b" * 64,
            }
        ],
        "findings": [finding.to_dict()],
    }
    return {
        "compile-bundle": bundle.to_dict(),
        "section-plan": plan.to_dict(),
        "writer-packet": packet.to_dict(),
        "writer-patch": patch,
    }


class P3ManuscriptContractTest(unittest.TestCase):
    def schema_findings(
        self,
        schema_name: str,
        document: dict[str, object],
    ):
        schema = load_document(SCHEMAS / f"{schema_name}.schema.json")
        return validate_schema(document, schema)

    def compile_readiness(self, *documents: dict[str, object]):
        validator = getattr(
            paperops_models,
            "validate_manuscript_compile_readiness",
        )
        return validator(catalog(*documents))

    def test_generated_schemas_accept_task1_and_provisional_patch_v1_shapes(
        self,
    ) -> None:
        documents = generated_documents()
        for schema_name in GENERATED_SCHEMA_NAMES:
            with self.subTest(schema=schema_name):
                schema = load_document(SCHEMAS / f"{schema_name}.schema.json")
                self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
                self.assertIs(schema["additionalProperties"], False)
                self.assertEqual(validate_schema(documents[schema_name], schema), [])

    def test_versioned_payload_envelopes_are_closed_except_extensions(self) -> None:
        mutations = (
            ("section-plan", ("projection",), "/projection/unknown"),
            ("writer-packet", ("read_context",), "/read_context/unknown"),
            ("writer-packet", ("payload",), "/payload/unknown"),
            (
                "compile-bundle",
                ("section_plans", 0, "projection"),
                "/section_plans/0/projection/unknown",
            ),
            (
                "compile-bundle",
                ("writer_packets", 0, "read_context"),
                "/writer_packets/0/read_context/unknown",
            ),
            (
                "compile-bundle",
                ("writer_packets", 0, "payload"),
                "/writer_packets/0/payload/unknown",
            ),
        )
        for schema_name, path, pointer in mutations:
            with self.subTest(schema=schema_name, path=path):
                candidate = copy.deepcopy(generated_documents()[schema_name])
                target: object = candidate
                for token in path:
                    target = target[token]  # type: ignore[index]
                assert isinstance(target, dict)
                target["unknown"] = True
                self.assertIn(
                    ("schema.additional", pointer),
                    [
                        (finding.code, finding.pointer)
                        for finding in self.schema_findings(schema_name, candidate)
                    ],
                )

        for schema_name, path, _pointer in mutations:
            for mutation, expected_code in (
                ("missing", "schema.required"),
                ("wrong", "schema.const"),
            ):
                with self.subTest(schema=schema_name, path=path, version=mutation):
                    candidate = copy.deepcopy(generated_documents()[schema_name])
                    target: object = candidate
                    for token in path:
                        target = target[token]  # type: ignore[index]
                    assert isinstance(target, dict)
                    if mutation == "missing":
                        del target["schema_version"]
                    else:
                        target["schema_version"] = 2
                    version_pointer = (
                        "/" + "/".join(str(token) for token in path) + "/schema_version"
                    )
                    self.assertIn(
                        (expected_code, version_pointer),
                        [
                            (finding.code, finding.pointer)
                            for finding in self.schema_findings(schema_name, candidate)
                        ],
                    )

        for schema_name, path in (
            ("section-plan", ("projection", "extensions")),
            ("writer-packet", ("read_context", "extensions")),
            ("writer-packet", ("payload", "extensions")),
        ):
            with self.subTest(schema=schema_name, extension=path):
                candidate = copy.deepcopy(generated_documents()[schema_name])
                target: object = candidate
                for token in path:
                    target = target[token]  # type: ignore[index]
                assert isinstance(target, dict)
                target["x-lab-provisional"] = {"opaque": [1, "two"]}
                self.assertEqual(self.schema_findings(schema_name, candidate), [])

    def test_major_nested_generated_objects_reject_unknown_fields(self) -> None:
        mutations = (
            ("compile-bundle", ("request",), "/request/unknown"),
            ("compile-bundle", ("authority", 0), "/authority/0/unknown"),
            (
                "compile-bundle",
                ("request", "write_scope"),
                "/request/write_scope/unknown",
            ),
            ("compile-bundle", ("findings", 0), "/findings/0/unknown"),
            (
                "compile-bundle",
                ("section_plans", 0),
                "/section_plans/0/unknown",
            ),
            (
                "compile-bundle",
                ("writer_packets", 0),
                "/writer_packets/0/unknown",
            ),
            ("section-plan", ("inputs", 0), "/inputs/0/unknown"),
            ("writer-packet", ("authority", 0), "/authority/0/unknown"),
            ("writer-patch", ("changes", 0), "/changes/0/unknown"),
            ("writer-patch", ("findings", 0), "/findings/0/unknown"),
        )
        for schema_name, path, pointer in mutations:
            with self.subTest(schema=schema_name, path=path):
                candidate = copy.deepcopy(generated_documents()[schema_name])
                target: object = candidate
                for token in path:
                    target = target[token]  # type: ignore[index]
                assert isinstance(target, dict)
                target["unknown"] = True
                self.assertIn(
                    ("schema.additional", pointer),
                    [
                        (finding.code, finding.pointer)
                        for finding in self.schema_findings(schema_name, candidate)
                    ],
                )

    def test_generated_schema_revisions_are_positive(self) -> None:
        mutations = (
            ("section-plan", ("revision",)),
            ("section-plan", ("inputs", 0, "revision")),
            ("writer-packet", ("inputs", 0, "revision")),
            ("compile-bundle", ("inputs", 0, "revision")),
            ("compile-bundle", ("section_plans", 0, "revision")),
            ("compile-bundle", ("section_plans", 0, "inputs", 0, "revision")),
        )
        for schema_name, path in mutations:
            for invalid in (0, -1):
                with self.subTest(schema=schema_name, path=path, revision=invalid):
                    candidate = copy.deepcopy(generated_documents()[schema_name])
                    target: object = candidate
                    for token in path[:-1]:
                        target = target[token]  # type: ignore[index]
                    target[path[-1]] = invalid  # type: ignore[index]
                    pointer = "/" + "/".join(str(token) for token in path)
                    self.assertIn(
                        ("schema.minimum", pointer),
                        [
                            (finding.code, finding.pointer)
                            for finding in self.schema_findings(schema_name, candidate)
                        ],
                    )

    def test_shared_generated_schema_definitions_remain_structurally_equal(
        self,
    ) -> None:
        schemas = {
            name: load_document(SCHEMAS / f"{name}.schema.json")
            for name in GENERATED_SCHEMA_NAMES
        }
        for definition in ("safeId", "hash", "relativePath"):
            values = [schemas[name]["$defs"][definition] for name in GENERATED_SCHEMA_NAMES]
            self.assertTrue(all(value == values[0] for value in values[1:]), definition)
        for definition, names in (
            ("strings", ("compile-bundle", "section-plan", "writer-packet")),
            ("extensions", ("compile-bundle", "section-plan", "writer-packet")),
            ("input", ("compile-bundle", "section-plan", "writer-packet")),
            ("finding", ("compile-bundle", "section-plan", "writer-patch")),
            ("authority", ("compile-bundle", "writer-packet")),
            ("writeScope", ("compile-bundle", "writer-packet")),
            ("projectionMoveBinding", ("compile-bundle", "section-plan")),
            ("sectionProjection", ("compile-bundle", "section-plan")),
            ("readContext", ("compile-bundle", "writer-packet")),
            ("writerPayload", ("compile-bundle", "writer-packet")),
        ):
            values = [schemas[name]["$defs"][definition] for name in names]
            self.assertTrue(all(value == values[0] for value in values[1:]), definition)

        for standalone, embedded in (
            ("section-plan", "sectionPlan"),
            ("writer-packet", "writerPacket"),
        ):
            standalone_shape = {
                key: schemas[standalone][key]
                for key in ("type", "required", "properties", "additionalProperties")
            }
            self.assertEqual(
                standalone_shape,
                schemas["compile-bundle"]["$defs"][embedded],
            )

    def test_generated_schemas_reject_unknown_top_level_fields(self) -> None:
        for schema_name, document in generated_documents().items():
            with self.subTest(schema=schema_name):
                candidate = copy.deepcopy(document)
                candidate["unknown_generated_field"] = True
                findings = self.schema_findings(schema_name, candidate)
                self.assertIn("schema.additional", [finding.code for finding in findings])

    def test_packet_input_requires_identity_type_hash_and_relation(self) -> None:
        packet = generated_documents()["writer-packet"]
        for field in ("identity", "type", "hash", "relation"):
            with self.subTest(field=field):
                candidate = copy.deepcopy(packet)
                del candidate["inputs"][0][field]
                findings = self.schema_findings("writer-packet", candidate)
                self.assertIn(
                    ("schema.required", f"/inputs/0/{field}"),
                    [(finding.code, finding.pointer) for finding in findings],
                )

        unknown = copy.deepcopy(packet)
        unknown["inputs"][0]["parallel_hash"] = HASH
        self.assertIn(
            "schema.additional",
            [finding.code for finding in self.schema_findings("writer-packet", unknown)],
        )

    def test_generated_read_and_write_paths_must_be_project_relative(self) -> None:
        for invalid in (
            "/absolute/results.tex",
            "../escape.tex",
            "C:\\escape.tex",
            "manuscript/ja/results\x00.tex",
            "manuscript/ja/",
        ):
            with self.subTest(kind="read", path=invalid):
                packet = generated_documents()["writer-packet"]
                packet["inputs"][0]["identity"] = invalid
                self.assertTrue(self.schema_findings("writer-packet", packet))
            with self.subTest(kind="write", path=invalid):
                packet = generated_documents()["writer-packet"]
                packet["write_scope"]["files"] = [invalid]
                self.assertTrue(self.schema_findings("writer-packet", packet))
            with self.subTest(kind="patch", path=invalid):
                patch = generated_documents()["writer-patch"]
                patch["changes"][0]["path"] = invalid
                self.assertTrue(self.schema_findings("writer-patch", patch))

    def test_move_bindings_are_additive_and_match_editorial_refs(self) -> None:
        section = valid_section()
        section["move_bindings"] = [
            {
                "move_id": "MOV-0001",
                "role": "primary",
                "reason": "principal result",
            }
        ]
        self.assertEqual(self.schema_findings("manuscript-section", section), [])
        self.assertEqual(validate_manuscript_semantics(catalog(section)), [])

    def test_move_binding_role_and_shape_are_closed(self) -> None:
        for mutation in (
            {"move_id": "MOV-0001", "role": "secondary", "reason": "invalid"},
            {"move_id": "MOV-0001", "role": "echo", "reason": ""},
            {
                "move_id": "MOV-0001",
                "role": "echo",
                "reason": "recall",
                "unknown": True,
            },
        ):
            with self.subTest(binding=mutation):
                section = valid_section()
                section["move_bindings"] = [mutation]
                self.assertTrue(self.schema_findings("manuscript-section", section))

    def test_binding_projection_mismatch_has_stable_compile_finding(self) -> None:
        section = valid_section()
        section["move_bindings"] = [
            {"move_id": "MOV-0002", "role": "primary", "reason": "other move"}
        ]
        findings = validate_manuscript_semantics(catalog(section))
        self.assertIn(
            ("compile.move_binding_mismatch", "/SEC-0001/move_bindings"),
            [(finding.code, finding.pointer) for finding in findings],
        )

    def test_primary_placement_is_compile_only_and_primary_plus_echo_is_valid(
        self,
    ) -> None:
        primary = ready_section("SEC-0001", "primary")
        echo = ready_section("SEC-0002", "echo")
        self.assertEqual(validate_manuscript_semantics(catalog(primary, echo)), [])
        self.assertEqual(self.compile_readiness(primary, echo), [])

    def test_echo_only_and_duplicate_primary_have_one_canonical_finding_per_move(
        self,
    ) -> None:
        echo = ready_section("SEC-0001", "echo")
        self.assertEqual(
            finding_rows(self.compile_readiness(echo)),
            [
                (
                    "compile.move_primary",
                    "/SEC-0001/editorial_move_refs/0",
                    "move `MOV-0001` requires exactly one primary section placement; found 0",
                )
            ],
        )

        first = ready_section("SEC-0001", "primary")
        second = ready_section("SEC-0002", "primary")
        expected = [
            (
                "compile.move_primary",
                "/SEC-0001/editorial_move_refs/0",
                "move `MOV-0001` requires exactly one primary section placement; found 2",
            )
        ]
        self.assertEqual(finding_rows(self.compile_readiness(first, second)), expected)
        self.assertEqual(finding_rows(self.compile_readiness(second, first)), expected)
        self.assertNotIn(
            "compile.move_primary",
            [finding.code for finding in validate_manuscript_semantics(catalog(first, second))],
        )

    def test_readiness_orders_distinct_primary_findings_by_move_id(self) -> None:
        second_move = ready_section("SEC-0002", "echo", move_id="MOV-0002")
        first_move = ready_section("SEC-0001", "echo", move_id="MOV-0001")
        expected = [
            (
                "compile.move_primary",
                "/SEC-0001/editorial_move_refs/0",
                "move `MOV-0001` requires exactly one primary section placement; found 0",
            ),
            (
                "compile.move_primary",
                "/SEC-0002/editorial_move_refs/0",
                "move `MOV-0002` requires exactly one primary section placement; found 0",
            ),
        ]
        self.assertEqual(
            finding_rows(self.compile_readiness(second_move, first_move)),
            expected,
        )

    def test_compile_readiness_requires_primary_approval_and_dependency_coverage(
        self,
    ) -> None:
        section = valid_section()
        ordinary_findings = validate_manuscript_semantics(catalog(section))
        self.assertNotIn(
            "compile.move_primary",
            [finding.code for finding in ordinary_findings],
        )

        findings = self.compile_readiness(section)
        codes = {finding.code for finding in findings}
        self.assertIn("compile.move_primary", codes)
        self.assertIn("compile.plan_approval", codes)
        self.assertIn("compile.dependency_coverage", codes)

        ready = valid_section()
        ready["move_bindings"] = [
            {
                "move_id": "MOV-0001",
                "role": "primary",
                "reason": "principal result",
            }
        ]
        ready["dependencies"] = [
            {
                "target_id": "MOV-0001",
                "relation": "guided_by",
                "expected_hash": HASH,
            }
        ]
        add_current_editorial_approval(ready)
        self.assertEqual(self.compile_readiness(ready), [])

    def test_add_is_a_canonical_manuscript_block_operation(self) -> None:
        self.assertEqual(self.schema_findings("manuscript-block", valid_block()), [])
        operations = {
            "keep",
            "compress",
            "move",
            "merge",
            "split",
            "cut",
            "rewrite",
            "add",
        }
        schema = load_document(SCHEMAS / "manuscript-block.schema.json")
        self.assertEqual(set(schema["properties"]["operation"]["enum"]), operations)
        self.assertEqual(
            set(schema["properties"]["allowed_operations"]["items"]["enum"]),
            operations,
        )

    def test_empty_starter_remains_advisory_compatible(self) -> None:
        self.assertEqual(self.compile_readiness(), [])
        result = run_python_script(
            CHECKER,
            "--root",
            ROOT / "template",
            "--model",
            "manuscript",
            "--phase",
            "all",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_ordinary_checker_does_not_apply_compile_only_primary_rule(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = copy_template(tmp)
            sections = (
                ready_section("SEC-0001", "primary"),
                ready_section("SEC-0002", "primary"),
                valid_section("SEC-0003"),
            )
            section_dir = root / "_paperops/model/manuscript/sections"
            section_dir.mkdir(parents=True, exist_ok=True)
            records: list[dict[str, object]] = []
            for section in sections:
                relative = (
                    f"_paperops/model/manuscript/sections/{section['id']}.yml"
                )
                (root / relative).write_text(
                    json.dumps(section, ensure_ascii=False),
                    encoding="utf-8",
                )
                records.append(
                    {
                        "id": section["id"],
                        "record_type": "section",
                        "document": relative,
                        "expected_revision": section["revision"],
                        "expected_hash": semantic_hash(
                            section,
                            excluded_paths=HASH_EXCLUSIONS,
                        ),
                    }
                )
            index = {
                "model_name": "manuscript",
                "schema_version": 1,
                "index_revision": 1,
                "records": records,
                "extensions": {},
                "metadata": {"updated_at": "2026-07-12"},
            }
            (root / "_paperops/model/manuscript/index.yml").write_text(
                json.dumps(index, ensure_ascii=False),
                encoding="utf-8",
            )

            result = run_python_script(
                CHECKER,
                "--root",
                root,
                "--model",
                "manuscript",
                "--phase",
                "semantics",
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("compile.move_primary", result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
