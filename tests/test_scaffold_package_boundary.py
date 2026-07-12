from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT


def load_boundary_module():
    script = ROOT / "scripts" / "check-scaffold-package-boundary.py"
    spec = importlib.util.spec_from_file_location("check_scaffold_package_boundary", script)
    if spec is None or spec.loader is None:
        raise AssertionError(f"could not load {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScaffoldPackageBoundaryTest(unittest.TestCase):
    def test_canary_source_is_staged_without_mutating_template_source(self) -> None:
        module = load_boundary_module()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "template"
            source.mkdir()
            (source / "README.md").write_text("starter scaffold\n", encoding="utf-8")

            staged = module.create_canary_scaffold_source(source, tmp_path / "work")

            self.assertEqual((source / "README.md").read_text(encoding="utf-8"), "starter scaffold\n")
            for rel in module.CANARY_RELS:
                self.assertFalse((source / rel).exists(), rel)
                self.assertTrue((staged / rel).is_file(), rel)

    def test_canary_paths_cover_modern_and_legacy_generated_artifacts(self) -> None:
        module = load_boundary_module()

        self.assertIn("_paperops/notes/session-context.generated.md", module.CANARY_RELS)
        self.assertIn("notes/session-context.generated.md", module.CANARY_RELS)
        self.assertIn("_paperops/refs/source-reach/canary/raw/cookie.txt", module.CANARY_RELS)
        self.assertIn("refs/source-reach/canary/raw/cookie.txt", module.CANARY_RELS)
        self.assertIn("_paperops/refs/source-reach/canary/doctor.generated.json", module.CANARY_RELS)
        self.assertIn("_paperops/refs/source-reach/canary/capture.generated.json", module.CANARY_RELS)
        self.assertIn("scripts/__pycache__/check.cpython-311.pyc", module.CANARY_RELS)
        self.assertIn("scripts/check.pyc", module.CANARY_RELS)
        self.assertIn(".paperops/cache/context.generated.md", module.CANARY_RELS)
        self.assertIn(".tools/tex/bin", module.CANARY_RELS)
        self.assertIn("submission/agu/build/main.pdf", module.CANARY_RELS)
        self.assertIn("submission/agu/.tools/local.txt", module.CANARY_RELS)
        self.assertIn("tex-env.toml", module.CANARY_RELS)
        self.assertIn("_paperops/refs/papers/paper.pdf", module.CANARY_RELS)
        self.assertIn("_paperops/refs/research/scan/results/raw.json", module.CANARY_RELS)
        self.assertIn("_paperops/refs/research/scan/report.generated.md", module.CANARY_RELS)
        self.assertIn("_paperops/refs/research/scan/raw-findings.json", module.CANARY_RELS)

    def test_allowed_exception_parent_directories_are_not_reported_as_blocked(self) -> None:
        module = load_boundary_module()
        with tempfile.TemporaryDirectory() as tmp:
            init_dir = Path(tmp) / "paper-demo"
            for rel in module.REQUIRED_RELS:
                path = init_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("required\n", encoding="utf-8")
            keep = init_dir / "_paperops" / "refs" / "papers" / ".gitkeep"
            keep.parent.mkdir(parents=True, exist_ok=True)
            keep.write_text("", encoding="utf-8")

            module.check_init_contents(init_dir)

    def test_release_boundary_requires_typed_models_and_forbids_legacy_authority(self) -> None:
        module = load_boundary_module()

        self.assertIn("_paperops/defaults/schemas/registry.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/model/research/index.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/model/editorial/editorial-model.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/model/editorial/results-hierarchy.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/model/manuscript/index.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/model/issues/index.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/model/publication/publication-model.yml", module.REQUIRED_RELS)
        self.assertIn("_paperops/workflow/current-state.yml", module.FORBIDDEN_RELS)
        self.assertIn("_paperops/claims/", module.FORBIDDEN_RELS)


if __name__ == "__main__":
    unittest.main()
