from __future__ import annotations

import importlib
import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

from tests.helpers import ROOT, copy_template, run_cli, run_python_script


sys.path.insert(0, str(ROOT / "template/scripts"))

from paperops.compiler import CompileRequest, WriteScope  # noqa: E402
from paperops import model_validation  # noqa: E402
from paperops.model_state import read_model_states, write_model_states  # noqa: E402
from paperops_schema import semantic_hash  # noqa: E402
from tests.test_p3_manuscript_contract import (  # noqa: E402
    add_current_editorial_approval,
    valid_section,
)
from tests.test_paperops_model_check import valid_documents  # noqa: E402
from tests import test_research_migration_adapter as research_fixtures  # noqa: E402


CHECKER = ROOT / "template/scripts/check-paperops-models.py"


def compile_request(
    *,
    source_mode: str,
    transaction_id: str = "",
    targets: tuple[str, ...] = (),
) -> CompileRequest:
    return CompileRequest(
        targets=targets,
        write_scope=WriteScope(
            level="section" if targets else "manuscript",
            languages=("ja",),
            files=("manuscript/ja/main.tex",),
            section_ids=targets,
        ),
        source_mode=source_mode,
        shadow_transaction_id=transaction_id,
    )


def write_section(project: Path, section: dict[str, object]) -> None:
    section_id = str(section["id"])
    relative = f"_paperops/model/manuscript/sections/{section_id}.yml"
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(section, sort_keys=False), encoding="utf-8")
    index_path = project / "_paperops/model/manuscript/index.yml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8"))
    index["records"].append(
        {
            "id": section_id,
            "record_type": "section",
            "document": relative,
            "expected_revision": section["revision"],
            "expected_hash": semantic_hash(
                section,
                excluded_paths=("/approvals", "/metadata/updated_at"),
            ),
        }
    )
    index_path.write_text(yaml.safe_dump(index, sort_keys=False), encoding="utf-8")


def authoritative_project(
    parent: Path,
    *,
    approved_section: bool = True,
) -> tuple[Path, dict[str, str]]:
    project = research_fixtures.ResearchMigrationAdapterTest().project(parent)
    transactions: dict[str, str] = {}

    def adopt(model: str) -> str:
        code, raw, error = run_cli(
            ["model", "diff", model, str(project), "--json"]
        )
        if code != 0:
            raise AssertionError(error or raw)
        transaction_id = str(json.loads(raw)["transaction_id"])
        code, raw, error = run_cli(
            ["model", "adopt", model, str(project), "--yes", "--json"]
        )
        if code != 0:
            raise AssertionError(error or raw)
        return transaction_id

    transactions["research"] = adopt("research")
    editorial, results = valid_documents()
    editorial_root = project / "_paperops/model/editorial"
    (editorial_root / "editorial-model.yml").write_text(
        yaml.safe_dump(editorial, sort_keys=False),
        encoding="utf-8",
    )
    (editorial_root / "results-hierarchy.yml").write_text(
        yaml.safe_dump(results, sort_keys=False),
        encoding="utf-8",
    )
    (project / "_paperops/notes/views/storyline.md").unlink()
    transactions["editorial"] = adopt("editorial")
    transactions["results_hierarchy"] = transactions["editorial"]

    selected = valid_section("SEC-0001")
    selected["editorial_move_refs"] = []
    selected["research_refs"] = []
    selected["move_bindings"] = []
    if approved_section:
        add_current_editorial_approval(selected)
    manifest = project / "_paperops/contracts/manuscript-migration.yml"
    manifest.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "marker_check": False,
                "sections": [selected],
                "blocks": [],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    transactions["manuscript"] = adopt("manuscript")
    return project, transactions


def shadow_project(
    parent: Path,
    model: str = "research",
) -> tuple[Path, str]:
    project, _ = authoritative_project(parent)
    code, raw, error = run_cli(
        [
            "model",
            "diff",
            model,
            str(project),
            "--refresh",
            "--json",
        ]
    )
    if code != 0:
        raise AssertionError(error or raw)
    return project, str(json.loads(raw)["transaction_id"])


def tracked_tree_snapshot(project: Path) -> tuple[tuple[str, int, bytes], ...]:
    rows: list[tuple[str, int, bytes]] = []
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if relative.parts[0] == ".paperops":
            continue
        metadata = path.lstat()
        content = path.read_bytes() if stat.S_ISREG(metadata.st_mode) else b""
        rows.append((relative.as_posix(), metadata.st_mode, content))
    return tuple(rows)


def selected_tree_snapshot(
    project: Path,
    identities: tuple[str, ...],
) -> tuple[tuple[str, int, int, bytes], ...]:
    rows: list[tuple[str, int, int, bytes]] = []
    selected: set[Path] = set()
    for identity in identities:
        root = project / identity
        selected.add(root)
        if root.is_dir():
            selected.update(root.rglob("*"))
    for path in sorted(selected):
        metadata = path.lstat()
        content = path.read_bytes() if stat.S_ISREG(metadata.st_mode) else b""
        rows.append(
            (
                path.relative_to(project).as_posix(),
                stat.S_IFMT(metadata.st_mode),
                stat.S_IMODE(metadata.st_mode),
                content,
            )
        )
    return tuple(rows)


class P3CheckerQueryTest(unittest.TestCase):
    def test_run_model_hash_returns_the_current_model_hash(self) -> None:
        runner = getattr(model_validation, "run_model_hash")
        result = runner(ROOT / "template", "research")

        self.assertTrue(result.ok, result.findings)
        self.assertRegex(result.hashes["research"], r"^sha256:[0-9a-f]{64}$")

    def test_compile_readiness_query_checks_only_selected_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            selected = valid_section("SEC-0001")
            selected["editorial_move_refs"] = []
            selected["research_refs"] = []
            selected["move_bindings"] = []
            add_current_editorial_approval(selected)
            unselected = valid_section("SEC-0002")
            unselected["editorial_move_refs"] = []
            unselected["research_refs"] = []
            unselected["move_bindings"] = []
            write_section(project, selected)
            write_section(project, unselected)

            runner = getattr(
                model_validation,
                "run_manuscript_compile_readiness",
            )
            result = runner(project, ("SEC-0001",))

        self.assertTrue(result.ok, result.findings)
        self.assertEqual(result.model, "manuscript")

        missing = runner(ROOT / "template", ("SEC-9999",))
        self.assertFalse(missing.ok)
        self.assertEqual(
            missing.findings[0].code,
            "compile.target_missing",
        )

    def test_object_hash_query_returns_the_registered_object_hash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            section = valid_section("SEC-0001")
            section["editorial_move_refs"] = []
            section["research_refs"] = []
            section["move_bindings"] = []
            write_section(project, section)
            editorial, results = valid_documents()
            editorial_root = project / "_paperops/model/editorial"
            (editorial_root / "editorial-model.yml").write_text(
                yaml.safe_dump(editorial, sort_keys=False),
                encoding="utf-8",
            )
            (editorial_root / "results-hierarchy.yml").write_text(
                yaml.safe_dump(results, sort_keys=False),
                encoding="utf-8",
            )

            result = model_validation.run_model_hash(
                project,
                "manuscript",
                "SEC-0001",
            )
            wrong_owner = model_validation.run_model_hash(
                project,
                "research",
                "SEC-0001",
            )
            global_query = run_python_script(
                CHECKER,
                "--root", project,
                "--json",
                "--print-hash",
                "--object-id", "SEC-0001",
            )

        self.assertTrue(result.ok, result.findings)
        self.assertRegex(
            result.hashes["SEC-0001"],
            r"^sha256:[0-9a-f]{64}$",
        )
        self.assertFalse(wrong_owner.ok)
        self.assertEqual(wrong_owner.findings[0].code, "reference.dangling")
        self.assertEqual(
            global_query.returncode,
            0,
            global_query.stdout + global_query.stderr,
        )
        self.assertRegex(
            json.loads(global_query.stdout)["hashes"]["SEC-0001"],
            r"^sha256:[0-9a-f]{64}$",
        )

    def test_hash_query_rejects_missing_malformed_or_mismatched_output(self) -> None:
        valid_hash = "sha256:" + "a" * 64
        payloads = (
            (
                "malformed",
                "print('not json')\n",
            ),
            (
                "bool_schema_version",
                "import json\n"
                + f"print(json.dumps({{'schema_version': True, 'ok': True, 'model': 'research', 'phase': 'all', 'findings': [], 'hashes': {{'research': '{valid_hash}'}}}}))\n",
            ),
            (
                "float_schema_version",
                "import json\n"
                + f"print(json.dumps({{'schema_version': 1.0, 'ok': True, 'model': 'research', 'phase': 'all', 'findings': [], 'hashes': {{'research': '{valid_hash}'}}}}))\n",
            ),
            (
                "status",
                "import json, sys\n"
                + f"print(json.dumps({{'schema_version': 1, 'ok': True, 'model': 'research', 'phase': 'all', 'findings': [], 'hashes': {{'research': '{valid_hash}'}}}}))\n"
                + "sys.exit(1)\n",
            ),
            (
                "model",
                "import json\n"
                + f"print(json.dumps({{'schema_version': 1, 'ok': True, 'model': 'editorial', 'phase': 'all', 'findings': [], 'hashes': {{'research': '{valid_hash}'}}}}))\n",
            ),
            (
                "key",
                "import json\n"
                + "print(json.dumps({'schema_version': 1, 'ok': True, 'model': 'research', 'phase': 'all', 'findings': [], 'hashes': {}}))\n",
            ),
            (
                "digest",
                "import json\n"
                + "print(json.dumps({'schema_version': 1, 'ok': True, 'model': 'research', 'phase': 'all', 'findings': [], 'hashes': {'research': 'sha256:INVALID'}}))\n",
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            missing = model_validation.run_model_hash(Path(tmp), "research")
        self.assertEqual(missing.findings[0].code, "validation.checker_missing")

        for name, source in payloads:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                checker = root / "scripts/check-paperops-models.py"
                checker.parent.mkdir(parents=True)
                checker.write_text(source, encoding="utf-8")
                result = model_validation.run_model_hash(root, "research")
            self.assertFalse(result.ok)
            self.assertEqual(
                result.findings[0].code,
                "validation.version"
                if name in {"bool_schema_version", "float_schema_version"}
                else "validation.output",
            )

    def test_checker_queries_reject_unsafe_identifiers_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            results = (
                model_validation.run_model_hash(root, "../research"),
                model_validation.run_model_hash(root, "research", "CLM/0001"),
                model_validation.run_manuscript_compile_readiness(
                    root,
                    ("../SEC-0001",),
                ),
            )
        self.assertEqual(
            [result.findings[0].code for result in results],
            ["validation.request"] * 3,
        )

    def test_compile_readiness_cli_rejects_invalid_direct_combinations(self) -> None:
        cases = (
            (
                "wrong_model",
                "--model", "research", "--compile-readiness",
                "--section-id", "SEC-0001",
            ),
            (
                "missing_section",
                "--model", "manuscript", "--compile-readiness",
            ),
            (
                "hash_combination",
                "--model", "manuscript", "--compile-readiness",
                "--section-id", "SEC-0001", "--print-hash",
            ),
            (
                "document_combination",
                "--model", "manuscript", "--compile-readiness",
                "--section-id", "SEC-0001", "--document", "ignored.yml",
            ),
        )
        for case in cases:
            with self.subTest(case=case[0]):
                result = run_python_script(
                    CHECKER,
                    "--root", ROOT / "template",
                    *case[1:],
                )
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)


class P3CompileSourceModeTest(unittest.TestCase):
    def test_source_mode_and_shadow_transaction_must_match(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        load_compile_inputs = inputs_module.load_compile_inputs
        error_type = inputs_module.CompileInputError

        cases = (
            compile_request(
                source_mode="authoritative",
                transaction_id="model-20260712T000000000000Z-aaaaaaaaaaaa",
            ),
            compile_request(source_mode="shadow"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            for request in cases:
                with self.subTest(request=request.to_dict()), self.assertRaises(
                    error_type
                ) as raised:
                    load_compile_inputs(project, request)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.authority_source",
                )


class P3AuthoritativeInputTest(unittest.TestCase):
    def test_legacy_and_mixed_authority_are_rejected(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(source_mode="authoritative")
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(
                raised.exception.finding.code,
                "compile.authority_state",
            )

            states = read_model_states(project)
            research = states["research"]
            states["research"] = research.__class__(
                "research",
                "v2-authoritative",
                "sha256:" + "a" * 64,
                "",
                "model-bootstrap-0001",
            )
            write_model_states(project, states)
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(
                raised.exception.finding.code,
                "compile.authority_state",
            )

    def test_real_p2_adoptions_load_and_tampered_target_is_rejected(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, transactions = authoritative_project(Path(tmp))
            loaded = inputs_module.load_compile_inputs(project, request)
            repeated = inputs_module.load_compile_inputs(project, request)

            self.assertEqual(loaded.source_mode, "authoritative")
            self.assertTrue(loaded.applicable)
            self.assertEqual(
                tuple(item.model_name for item in loaded.authority),
                ("research", "editorial", "results_hierarchy", "manuscript"),
            )
            for item in loaded.authority:
                self.assertEqual(item.mode, "v2-authoritative")
                self.assertRegex(item.model_hash, r"^sha256:[0-9a-f]{64}$")
                self.assertEqual(item.transaction_id, transactions[item.model_name])
            self.assertEqual(
                transactions["editorial"],
                transactions["results_hierarchy"],
            )
            self.assertTrue(loaded.readiness.ok, loaded.readiness.findings)
            self.assertEqual(loaded.readiness.model, "manuscript")
            document_identities = tuple(item.identity for item in loaded.documents)
            self.assertEqual(
                document_identities[0],
                "_paperops/model/research/index.yml",
            )
            self.assertIn(
                "_paperops/model/manuscript/sections/SEC-0001.yml",
                document_identities,
            )
            object_ids = tuple(item.object_id for item in loaded.objects)
            self.assertIn("STY-0001", object_ids)
            self.assertIn("RHI-0001", object_ids)
            self.assertIn("SEC-0001", object_ids)
            self.assertFalse(
                any(str(project) in repr(item) for item in loaded.documents)
            )
            self.assertEqual(loaded, repeated)
            model_order = {
                name: index
                for index, name in enumerate(
                    ("research", "editorial", "results_hierarchy", "manuscript")
                )
            }
            self.assertEqual(
                list(loaded.objects),
                sorted(
                    loaded.objects,
                    key=lambda item: (
                        model_order[item.model_name],
                        item.object_id,
                        item.identity,
                    ),
                ),
            )
            with self.assertRaises(TypeError):
                loaded.documents[0].document["mutated"] = True
            with self.assertRaises(TypeError):
                loaded.readiness.hashes["mutated"] = "sha256:" + "a" * 64
            self.assertNotIn(
                "The mechanism is unresolved.",
                repr(next(item for item in loaded.documents if item.model_name == "editorial")),
            )

            index = project / "_paperops/model/research/index.yml"
            index.write_text(index.read_text() + "# post-adoption edit\n")
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(
                raised.exception.finding.code,
                "transaction.target_changed",
            )

    def test_later_non_compile_model_update_does_not_invalidate_authority(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, transactions = authoritative_project(Path(tmp))
            ledger = project / "_paperops/workflow/submission-ledger.yml"
            publication_document = yaml.safe_load(
                (
                    project
                    / "_paperops/model/publication/publication-model.yml"
                ).read_text(encoding="utf-8")
            )
            ledger.write_text(
                yaml.safe_dump(
                    {
                        "schema_version": 1,
                        "migration_publication": publication_document,
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )
            code, raw, error = run_cli(
                ["model", "diff", "publication", str(project), "--json"]
            )
            self.assertEqual(code, 0, error or raw)

            loaded = inputs_module.load_compile_inputs(project, request)

        self.assertTrue(loaded.applicable)
        self.assertEqual(
            tuple(item.transaction_id for item in loaded.authority),
            (
                transactions["research"],
                transactions["editorial"],
                transactions["results_hierarchy"],
                transactions["manuscript"],
            ),
        )

    def test_committed_journal_contract_and_checker_schema_are_revalidated(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        request = compile_request(
            source_mode="authoritative",
            targets=("SEC-0001",),
        )
        with tempfile.TemporaryDirectory() as tmp:
            project, transactions = authoritative_project(Path(tmp))
            journal = (
                project
                / ".paperops/migrations"
                / transactions["research"]
                / "journal.json"
            )
            original = journal.read_bytes()
            mutations = (
                ("extra", lambda value: value.__setitem__("unexpected", True), "compile.authority_journal"),
                ("bool_schema", lambda value: value.__setitem__("schema_version", True), "compile.authority_journal"),
                ("float_schema", lambda value: value.__setitem__("schema_version", 1.0), "compile.authority_journal"),
                ("schema", lambda value: value.__setitem__("schema_version", 2), "state.inconsistent"),
                ("action", lambda value: value.__setitem__("action", "rollback"), "compile.authority_journal"),
                ("state", lambda value: value.__setitem__("state", "planned"), "state.inconsistent"),
                (
                    "transaction",
                    lambda value: value.__setitem__(
                        "transaction_id",
                        "model-20260712T000000000000Z-aaaaaaaaaaaa",
                    ),
                    "state.inconsistent",
                ),
                ("model", lambda value: value.__setitem__("model_name", "manuscript"), "compile.authority_journal"),
                ("models", lambda value: value.__setitem__("models", []), "compile.authority_journal"),
                ("targets", lambda value: value.__setitem__("targets", []), "compile.authority_journal"),
                (
                    "state_hash",
                    lambda value: value["state_hashes"].__setitem__(
                        "research", "sha256:" + "b" * 64
                    ),
                    "state.inconsistent",
                ),
                (
                    "target_hash",
                    lambda value: value["targets"][0].__setitem__(
                        "candidate_hash", "sha256:" + "b" * 64
                    ),
                    "transaction.target_changed",
                ),
            )
            for name, mutate, expected in mutations:
                with self.subTest(name=name):
                    payload = json.loads(original)
                    mutate(payload)
                    journal.write_text(json.dumps(payload))
                    with self.assertRaises(inputs_module.CompileInputError) as raised:
                        inputs_module.load_compile_inputs(project, request)
                    self.assertEqual(raised.exception.finding.code, expected)
            journal.write_bytes(original)

            latest_journal = (
                project
                / ".paperops/migrations"
                / transactions["manuscript"]
                / "journal.json"
            )
            latest_before = latest_journal.read_bytes()
            payload = json.loads(latest_before)
            payload["manifest_candidate_hash"] = "invalid"
            latest_journal.write_text(json.dumps(payload))
            try:
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module.load_compile_inputs(project, request)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.authority_journal",
                )
            finally:
                latest_journal.write_bytes(latest_before)

            real_journal = journal.with_name("journal-real.json")
            journal.rename(real_journal)
            journal.symlink_to(real_journal)
            try:
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module.load_compile_inputs(project, request)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.authority_journal",
                )
            finally:
                journal.unlink(missing_ok=True)
                real_journal.rename(journal)

            schema = project / "_paperops/defaults/schemas/research-index.schema.json"
            schema_before = schema.read_bytes()
            schema.write_text("{ malformed schema")
            try:
                with self.assertRaises(inputs_module.CompileInputError):
                    inputs_module.load_compile_inputs(project, request)
            finally:
                schema.write_bytes(schema_before)

    def test_compile_readiness_findings_are_retained_for_authoritative_and_shadow_input(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(
                Path(tmp),
                approved_section=False,
            )
            loaded = inputs_module.load_compile_inputs(
                project,
                compile_request(
                    source_mode="authoritative",
                    targets=("SEC-0001",),
                ),
            )
            self.assertFalse(loaded.readiness.ok)
            self.assertEqual(
                loaded.readiness.findings[0].code,
                "compile.plan_approval",
            )
            self.assertTrue(loaded.documents)

        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp))
            manifest = project / "_paperops/contracts/manuscript-migration.yml"
            payload = yaml.safe_load(manifest.read_text())
            payload["sections"][0]["approvals"] = []
            manifest.write_text(yaml.safe_dump(payload, sort_keys=False))
            code, raw, error = run_cli(
                [
                    "model",
                    "diff",
                    "manuscript",
                    str(project),
                    "--refresh",
                    "--json",
                ]
            )
            self.assertEqual(code, 0, error or raw)
            transaction_id = str(json.loads(raw)["transaction_id"])
            loaded = inputs_module.load_compile_inputs(
                project,
                compile_request(
                    source_mode="shadow",
                    transaction_id=transaction_id,
                    targets=("SEC-0001",),
                ),
            )
            self.assertFalse(loaded.readiness.ok)
            self.assertEqual(
                loaded.readiness.findings[0].code,
                "compile.plan_approval",
            )
            self.assertTrue(loaded.documents)

    def test_request_targets_must_equal_write_scope_sections(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp))
            request = CompileRequest(
                targets=("SEC-0001",),
                write_scope=WriteScope(
                    level="section",
                    languages=("ja",),
                    files=("manuscript/ja/main.tex",),
                    section_ids=("SEC-0002",),
                ),
            )
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
        self.assertEqual(raised.exception.finding.code, "compile.target")


class P3ShadowInputTest(unittest.TestCase):
    def test_shadow_is_isolated_non_applicable_and_strictly_bound_to_report(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        with tempfile.TemporaryDirectory() as tmp:
            project, transaction_id = shadow_project(Path(tmp))
            request = compile_request(
                source_mode="shadow",
                transaction_id=transaction_id,
                targets=("SEC-0001",),
            )
            index = project / "_paperops/model/research/index.yml"
            manifest = project / ".pops/manifest.toml"
            before = tracked_tree_snapshot(project)
            candidate_root = (
                project / ".paperops/migrations" / transaction_id / "candidate"
            )
            undeclared = (
                candidate_root
                / "_paperops/model/research/claims/CLM-9999.yml"
            )
            undeclared.parent.mkdir(parents=True, exist_ok=True)
            undeclared.write_text("private: /outside/undeclared\n")
            ignored_before = selected_tree_snapshot(
                project,
                (
                    ".pops/manifest.toml",
                    f".paperops/migrations/{transaction_id}",
                ),
            )

            loaded = inputs_module.load_compile_inputs(project, request)

            self.assertEqual(loaded.source_mode, "shadow")
            self.assertFalse(loaded.applicable)
            self.assertTrue(loaded.readiness.ok, loaded.readiness.findings)
            self.assertEqual(loaded.authority[0].mode, "shadow")
            self.assertEqual(loaded.authority[0].transaction_id, transaction_id)
            self.assertNotIn("CLM-9999", [item.object_id for item in loaded.objects])
            self.assertEqual(before, tracked_tree_snapshot(project))
            self.assertEqual(
                ignored_before,
                selected_tree_snapshot(
                    project,
                    (
                        ".pops/manifest.toml",
                        f".paperops/migrations/{transaction_id}",
                    ),
                ),
            )

            report = project / ".paperops/migrations" / transaction_id / "report.json"
            original_report = report.read_bytes()
            payload = json.loads(original_report)
            payload["transaction_id"] = (
                "model-20260712T000000000000Z-aaaaaaaaaaaa"
            )
            report.write_text(json.dumps(payload))
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(raised.exception.finding.code, "compile.shadow_report")
            report.write_bytes(original_report)

            report.unlink()
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(raised.exception.finding.code, "compile.shadow_report")
            report.write_bytes(original_report)

            payload = json.loads(original_report)
            record_row = next(
                item
                for item in payload["candidates"]
                if item["object_id"] == "CLM-0001"
            )
            record_row["semantic_hash"] = "sha256:" + "b" * 64
            report.write_text(json.dumps(payload))
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(
                raised.exception.finding.code,
                "compile.shadow_candidate",
            )
            report.write_bytes(original_report)

            declared = candidate_root / "_paperops/model/research/index.yml"
            declared.write_text(declared.read_text() + "# tampered\n")
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module.load_compile_inputs(project, request)
            self.assertEqual(
                raised.exception.finding.code,
                "compile.shadow_candidate",
            )
            self.assertEqual(before, tracked_tree_snapshot(project))

    def test_shadow_report_rejects_malformed_rows_drift_and_unsafe_files(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        with tempfile.TemporaryDirectory() as tmp:
            project, transaction_id = shadow_project(Path(tmp))
            request = compile_request(
                source_mode="shadow",
                transaction_id=transaction_id,
                targets=("SEC-0001",),
            )
            before = tracked_tree_snapshot(project)
            migration = project / ".paperops/migrations" / transaction_id
            report = migration / "report.json"
            original_report = report.read_bytes()

            def rejected(payload: dict[str, object], expected: str) -> None:
                report.write_text(json.dumps(payload))
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module.load_compile_inputs(project, request)
                self.assertEqual(raised.exception.finding.code, expected)
                report.write_bytes(original_report)

            payload = json.loads(original_report)
            payload["schema_version"] = 2
            rejected(payload, "compile.shadow_report")

            payload = json.loads(original_report)
            payload["schema_version"] = 1.0
            rejected(payload, "compile.shadow_report")

            payload = json.loads(original_report)
            payload["model_name"] = "manuscript"
            rejected(payload, "compile.authority_state")

            payload = json.loads(original_report)
            payload["candidates"].append(dict(payload["candidates"][0]))
            rejected(payload, "compile.shadow_report")

            payload = json.loads(original_report)
            payload["candidates"][0]["relative_path"] = "../escape.yml"
            rejected(payload, "compile.shadow_report")

            payload = json.loads(original_report)
            payload["findings"].append(
                {
                    "code": "migration.note",
                    "pointer": "/",
                    "message": "unsafe source identity",
                    "severity": "warning",
                    "source_path": "../escape.md",
                }
            )
            rejected(payload, "compile.shadow_report")

            payload = json.loads(original_report)
            root_row = next(
                item
                for item in payload["candidates"]
                if item["relative_path"] == "_paperops/model/research/index.yml"
            )
            root_row["object_id"] = "research-alias"
            rejected(payload, "compile.shadow_report")

            payload = json.loads(original_report)
            source_identity = payload["inventory"][0]["source_path"]
            source = project / source_identity
            source_before = source.read_bytes()
            source.write_bytes(source_before + b"\n# drift\n")
            try:
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module.load_compile_inputs(project, request)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.shadow_source",
                )
            finally:
                source.write_bytes(source_before)

            payload = json.loads(original_report)
            record = next(
                item
                for item in payload["candidates"]
                if item["object_id"] == "CLM-0001"
            )
            candidate = migration / "candidate" / record["relative_path"]
            real_candidate = candidate.with_name(candidate.name + ".real")
            candidate.rename(real_candidate)
            candidate.symlink_to(real_candidate)
            try:
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module.load_compile_inputs(project, request)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.shadow_candidate",
                )
            finally:
                candidate.unlink(missing_ok=True)
                real_candidate.rename(candidate)

            payload = json.loads(original_report)
            template_row = next(
                item
                for item in payload["candidates"]
                if item["object_id"] == "CLM-0001"
            )
            extra_identity = "_paperops/model/research/claims/CLM-9999.yml"
            extra = migration / "candidate" / extra_identity
            extra.parent.mkdir(parents=True, exist_ok=True)
            extra.write_bytes((migration / "candidate" / template_row["relative_path"]).read_bytes())
            extra_row = dict(template_row)
            extra_row["relative_path"] = extra_identity
            extra_row["object_id"] = "CLM-9999"
            extra_row["content_hash"] = "sha256:" + hashlib.sha256(
                extra.read_bytes()
            ).hexdigest()
            payload["candidates"].append(extra_row)
            try:
                rejected(payload, "compile.shadow_validation")
            finally:
                extra.unlink(missing_ok=True)

            self.assertEqual(before, tracked_tree_snapshot(project))

    def test_editorial_pair_and_manuscript_shadow_keep_fixed_authority_order(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        cases = {
            "editorial": (
                "_paperops/model/editorial/editorial-model.yml",
                ("v2-authoritative", "shadow", "shadow", "v2-authoritative"),
            ),
            "manuscript": (
                "_paperops/model/manuscript/index.yml",
                ("v2-authoritative", "v2-authoritative", "v2-authoritative", "shadow"),
            ),
        }
        for model, (tracked_identity, expected_modes) in cases.items():
            with self.subTest(model=model), tempfile.TemporaryDirectory() as tmp:
                project, transaction_id = shadow_project(Path(tmp), model)
                tracked = project / tracked_identity
                before = tracked.read_bytes()
                loaded = inputs_module.load_compile_inputs(
                    project,
                    compile_request(
                        source_mode="shadow",
                        transaction_id=transaction_id,
                        targets=("SEC-0001",),
                    ),
                )
                self.assertEqual(
                    tuple(item.model_name for item in loaded.authority),
                    ("research", "editorial", "results_hierarchy", "manuscript"),
                )
                self.assertEqual(
                    tuple(item.mode for item in loaded.authority),
                    expected_modes,
                )
                self.assertFalse(loaded.applicable)
                self.assertTrue(loaded.readiness.ok, loaded.readiness.findings)
                self.assertEqual(tracked.read_bytes(), before)


class P3RegisteredInputSafetyTest(unittest.TestCase):
    def test_authority_manifest_preflight_rejects_symlink_and_fifo(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            (project / ".pops").mkdir(parents=True)
            write_model_states(project, read_model_states(project))
            manifest = project / ".pops/manifest.toml"
            outside = project / "manifest-real.toml"
            manifest.rename(outside)
            manifest.symlink_to(outside)
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module._read_states(project)
            self.assertEqual(
                raised.exception.finding.code,
                "compile.authority_state",
            )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".pops").mkdir()
            os.mkfifo(root / ".pops/manifest.toml")
            source = (
                "import sys\n"
                "from pathlib import Path\n"
                "from paperops.compiler.inputs import CompileInputError, _read_states\n"
                "try:\n"
                "    _read_states(Path(sys.argv[1]))\n"
                "except CompileInputError as error:\n"
                "    raise SystemExit(0 if error.finding.code == 'compile.authority_state' else 3)\n"
                "raise SystemExit(2)\n"
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = str(ROOT / "src")
            try:
                completed = subprocess.run(
                    [sys.executable, "-c", source, str(root)],
                    check=False,
                    timeout=1.0,
                    env=environment,
                )
            except subprocess.TimeoutExpired:
                self.fail("authority manifest FIFO was opened before file-type validation")
            self.assertEqual(completed.returncode, 0)

    def test_registered_yaml_rejects_symlink_components_and_special_files(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        reader = getattr(inputs_module, "_read_registered_yaml")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real = root / "real"
            real.mkdir()
            (real / "document.yml").write_text("schema_version: 1\n")
            (root / "linked").symlink_to(real, target_is_directory=True)
            os.mkfifo(root / "special.yml")
            for relative in (
                "linked/document.yml",
                "special.yml",
            ):
                with self.subTest(relative=relative), self.assertRaises(
                    inputs_module.CompileInputError
                ) as raised:
                    reader(root, relative)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.input_path",
                )

    def test_index_record_path_must_stay_in_its_registered_prefix(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        loader = getattr(inputs_module, "_load_index_records")
        index = {
            "model_name": "research",
            "records": [
                {
                    "id": "CLM-0001",
                    "record_type": "claim",
                    "document": "../outside.yml",
                    "expected_revision": 1,
                    "expected_hash": "sha256:" + "a" * 64,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(
            inputs_module.CompileInputError
        ) as raised:
            loader(Path(tmp), "research", index)
        self.assertEqual(raised.exception.finding.code, "compile.input_path")

    def test_duplicate_index_record_identity_is_rejected_before_snapshot(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        section = valid_section("SEC-0001")
        section["editorial_move_refs"] = []
        section["research_refs"] = []
        section["move_bindings"] = []
        expected_hash = semantic_hash(
            section,
            excluded_paths=("/approvals", "/metadata/updated_at"),
        )
        identity = "_paperops/model/manuscript/sections/SEC-0001.yml"
        row = {
            "id": "SEC-0001",
            "record_type": "section",
            "document": identity,
            "expected_revision": 1,
            "expected_hash": expected_hash,
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            document = root / identity
            document.parent.mkdir(parents=True)
            document.write_text(yaml.safe_dump(section, sort_keys=False))
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                inputs_module._load_index_records(
                    root,
                    "manuscript",
                    {"model_name": "manuscript", "records": [row, dict(row)]},
                )
        self.assertEqual(raised.exception.finding.code, "compile.input_document")

    def test_shadow_copy_rejects_symlink_and_special_checker_components(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        copier = getattr(inputs_module, "_copy_shadow_project")
        for unsafe in ("symlink", "special"):
            with self.subTest(unsafe=unsafe), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                source = root / "source"
                destination = root / "destination"
                outside = root / "outside"
                outside.mkdir()
                (outside / "check-paperops-models.py").write_text("pass\n")
                if unsafe == "symlink":
                    source.mkdir()
                    (source / "scripts").symlink_to(
                        outside,
                        target_is_directory=True,
                    )
                else:
                    (source / "scripts").mkdir(parents=True)
                    os.mkfifo(source / "scripts/check-paperops-models.py")
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    copier(source, destination)
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.shadow_copy",
                )

    def test_authority_journal_preflight_rejects_fifo_without_opening_it(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        preflight = getattr(inputs_module, "_preflight_authority_journal")
        transaction_id = "model-20260712T000000000000Z-aaaaaaaaaaaa"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            journal = (
                root
                / ".paperops/migrations"
                / transaction_id
                / "journal.json"
            )
            journal.parent.mkdir(parents=True)
            os.mkfifo(journal)
            with self.assertRaises(inputs_module.CompileInputError) as raised:
                preflight(root, transaction_id)
        self.assertEqual(
            raised.exception.finding.code,
            "compile.authority_journal",
        )

    def test_snapshot_rejects_private_values_and_noncanonical_identities(self) -> None:
        inputs_module = importlib.import_module("paperops.compiler.inputs")
        private_values = (
            {"extensions": {"x-path": "/private/raw/output.h5"}},
            {"extensions": {"x-note": "copied from /home/alice/raw/output.h5"}},
            {"extensions": {"x-note": r"copied from C:\\Users\\alice\\output.h5"}},
            {"extensions": {"x-note": "inspect file:///home/alice/raw/output.h5"}},
            {"extensions": {"x-note": "load ../../private/raw/output.h5"}},
            {"extensions": {"x-url": "https://alice:secret@example.test/data"}},
            {"extensions": {"x-token": "token=plaintext"}},
            {"extensions": {"x-note": "Authorization: Bearer abcdefghijklmnop"}},
            {"extensions": {"x-note": "Authorization: Basic YWxpY2U6c2VjcmV0"}},
            {"extensions": {"x-note": "OPENAI_API_KEY = sk-private-value"}},
        )
        for index, value in enumerate(private_values):
            with self.subTest(index=index):
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module._frozen_mapping(value, "model.yml")
                self.assertEqual(
                    raised.exception.finding.code,
                    "compile.input_privacy",
                )
                self.assertNotIn("alice", raised.exception.finding.message)
                self.assertNotIn("private-value", raised.exception.finding.message)
        public_values = (
            {"extensions": {"x-doi": "doi:10.1234/example.1"}},
            {"extensions": {"x-url": "https://example.org/public/article"}},
        )
        for index, value in enumerate(public_values):
            with self.subTest(public_index=index):
                frozen = inputs_module._frozen_mapping(value, "model.yml")
                self.assertEqual(dict(frozen["extensions"]), value["extensions"])
        for identity in ("./model.yml", "model//record.yml"):
            with self.subTest(identity=identity):
                with self.assertRaises(inputs_module.CompileInputError) as raised:
                    inputs_module._registered_identity(identity)
                self.assertEqual(raised.exception.finding.code, "compile.input_path")


if __name__ == "__main__":
    unittest.main()
