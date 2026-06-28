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


if __name__ == "__main__":
    unittest.main()
