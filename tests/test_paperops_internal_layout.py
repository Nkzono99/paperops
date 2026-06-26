from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import ROOT


SCRIPTS = ROOT / "template" / "scripts"
sys.path.insert(0, str(SCRIPTS))


class PaperopsInternalLayoutTest(unittest.TestCase):
    def test_internal_path_prefers_versioned_paperops_surface(self) -> None:
        from paperops_paths import display_path, internal_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "workflow" / "current-state.yml"
            modern = root / "_paperops" / "workflow" / "current-state.yml"
            legacy.parent.mkdir(parents=True)
            modern.parent.mkdir(parents=True)
            legacy.write_text("legacy: true\n", encoding="utf-8")
            modern.write_text("modern: true\n", encoding="utf-8")

            resolved = internal_path(root, "workflow", "current-state.yml")

            self.assertEqual(modern, resolved)
            self.assertEqual("_paperops/workflow/current-state.yml", display_path(root, resolved))

    def test_internal_path_falls_back_to_legacy_surface(self) -> None:
        from paperops_paths import display_path, internal_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "workflow" / "current-state.yml"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("legacy: true\n", encoding="utf-8")

            resolved = internal_path(root, "workflow", "current-state.yml")

            self.assertEqual(legacy, resolved)
            self.assertEqual("workflow/current-state.yml", display_path(root, resolved))

    def test_internal_path_uses_defaults_when_project_overlay_is_absent(self) -> None:
        from paperops_paths import display_path, internal_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "_paperops" / "defaults" / "contracts" / "results.yml"
            default.parent.mkdir(parents=True)
            default.write_text("default: true\n", encoding="utf-8")

            resolved = internal_path(root, "contracts", "results.yml")

            self.assertEqual(default, resolved)
            self.assertEqual("_paperops/defaults/contracts/results.yml", display_path(root, resolved))

    def test_internal_path_prefers_project_overlay_over_defaults(self) -> None:
        from paperops_paths import internal_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            default = root / "_paperops" / "defaults" / "contracts" / "results.yml"
            overlay = root / "_paperops" / "contracts" / "results.yml"
            default.parent.mkdir(parents=True)
            overlay.parent.mkdir(parents=True)
            default.write_text("default: true\n", encoding="utf-8")
            overlay.write_text("overlay: true\n", encoding="utf-8")

            resolved = internal_path(root, "contracts", "results.yml")

            self.assertEqual(overlay, resolved)

    def test_internal_glob_reads_modern_and_legacy_without_duplicates(self) -> None:
        from paperops_paths import internal_glob

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            modern = root / "_paperops" / "claims" / "claims" / "CLM-0001.md"
            legacy = root / "claims" / "claims" / "CLM-0001.md"
            modern.parent.mkdir(parents=True)
            legacy.parent.mkdir(parents=True)
            modern.write_text("modern\n", encoding="utf-8")
            legacy.write_text("legacy\n", encoding="utf-8")

            matches = internal_glob(root, "claims/claims/*.md")

            self.assertEqual([modern], matches)


if __name__ == "__main__":
    unittest.main()
