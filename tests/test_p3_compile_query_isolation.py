from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from paperops import model_validation
from tests.helpers import run_python_script
from tests.test_p3_compile_inputs import CHECKER, authoritative_project


class P3CompileQueryIsolationTest(unittest.TestCase):
    def test_internal_compile_query_is_closed_and_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp))
            valid = run_python_script(
                CHECKER,
                "--root",
                project,
                "--model",
                "research",
                "--phase",
                "all",
                "--json",
                "--print-hash",
                "--internal-compile-query",
            )
            help_result = run_python_script(CHECKER, "--help")
            invalid_cases = (
                (
                    "missing_query",
                    "--model",
                    "research",
                    "--json",
                    "--internal-compile-query",
                ),
                (
                    "global_model",
                    "--json",
                    "--print-hash",
                    "--object-id",
                    "SEC-0001",
                    "--internal-compile-query",
                ),
                (
                    "non_compile_model",
                    "--model",
                    "issue",
                    "--json",
                    "--print-hash",
                    "--internal-compile-query",
                ),
                (
                    "non_json",
                    "--model",
                    "research",
                    "--print-hash",
                    "--internal-compile-query",
                ),
                (
                    "different_phase",
                    "--model",
                    "research",
                    "--phase",
                    "schema",
                    "--json",
                    "--print-hash",
                    "--internal-compile-query",
                ),
                (
                    "strict",
                    "--model",
                    "research",
                    "--strict",
                    "--json",
                    "--print-hash",
                    "--internal-compile-query",
                ),
            )
            rejected = [
                (
                    name,
                    run_python_script(CHECKER, "--root", project, *arguments),
                )
                for name, *arguments in invalid_cases
            ]

        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertNotIn("internal-compile-query", help_result.stdout)
        for name, result in rejected:
            with self.subTest(name=name):
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("Traceback", result.stderr)

    def test_p3_wrappers_ignore_non_compile_schema_and_catalog_damage(self) -> None:
        mutations = {
            "issue_schema": (
                "_paperops/defaults/schemas/issue-index.schema.json",
                b"{not valid json",
            ),
            "publication_schema": (
                "_paperops/defaults/schemas/publication-model.schema.json",
                b"{not valid json",
            ),
            "issue_catalog": (
                "_paperops/model/issues/index.yml",
                b"- not-an-issue-index\n",
            ),
            "publication_catalog": (
                "_paperops/model/publication/publication-model.yml",
                b"- not-a-publication-model\n",
            ),
        }
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp))
            for name, (identity, invalid_content) in mutations.items():
                with self.subTest(name=name):
                    path = project / identity
                    original = path.read_bytes()
                    path.write_bytes(invalid_content)
                    try:
                        research_hash = model_validation.run_model_hash(
                            project,
                            "research",
                        )
                        section_hash = model_validation.run_model_hash(
                            project,
                            "manuscript",
                            "SEC-0001",
                        )
                        readiness = (
                            model_validation.run_manuscript_compile_readiness(
                                project,
                                ("SEC-0001",),
                            )
                        )
                    finally:
                        path.write_bytes(original)

                    self.assertTrue(research_hash.ok, research_hash.findings)
                    self.assertTrue(section_hash.ok, section_hash.findings)
                    self.assertTrue(readiness.ok, readiness.findings)

            for identity in (
                "_paperops/defaults/schemas/issue-index.schema.json",
                "_paperops/defaults/schemas/publication-model.schema.json",
            ):
                with self.subTest(name=f"missing:{identity}"):
                    path = project / identity
                    backup = path.with_suffix(path.suffix + ".missing")
                    path.rename(backup)
                    try:
                        research_hash = model_validation.run_model_hash(
                            project,
                            "research",
                        )
                        readiness = (
                            model_validation.run_manuscript_compile_readiness(
                                project,
                                ("SEC-0001",),
                            )
                        )
                    finally:
                        backup.rename(path)
                    self.assertTrue(research_hash.ok, research_hash.findings)
                    self.assertTrue(readiness.ok, readiness.findings)

    def test_compile_model_damage_remains_visible_to_p3_wrappers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp))

            research_schema = (
                project
                / "_paperops/defaults/schemas/research-index.schema.json"
            )
            original_schema = research_schema.read_bytes()
            research_schema.write_bytes(b"{not valid json")
            try:
                research_hash = model_validation.run_model_hash(
                    project,
                    "research",
                )
            finally:
                research_schema.write_bytes(original_schema)
            self.assertFalse(research_hash.ok)
            self.assertTrue(research_hash.findings)

            manuscript_index = project / "_paperops/model/manuscript/index.yml"
            original_index = manuscript_index.read_bytes()
            manuscript_index.write_bytes(b"- not-a-manuscript-index\n")
            try:
                section_hash = model_validation.run_model_hash(
                    project,
                    "manuscript",
                    "SEC-0001",
                )
                readiness = model_validation.run_manuscript_compile_readiness(
                    project,
                    ("SEC-0001",),
                )
            finally:
                manuscript_index.write_bytes(original_index)
            self.assertFalse(section_hash.ok)
            self.assertTrue(section_hash.findings)
            self.assertFalse(readiness.ok)
            self.assertTrue(readiness.findings)

    def test_public_global_object_hash_query_remains_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project, _ = authoritative_project(Path(tmp))
            result = run_python_script(
                CHECKER,
                "--root",
                project,
                "--json",
                "--print-hash",
                "--object-id",
                "SEC-0001",
            )

        self.assertEqual(
            result.returncode,
            0,
            result.stdout + result.stderr,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["model"], "all")
        self.assertRegex(
            payload["hashes"]["SEC-0001"],
            r"^sha256:[0-9a-f]{64}$",
        )


if __name__ == "__main__":
    unittest.main()
