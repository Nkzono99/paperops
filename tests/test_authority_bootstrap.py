from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import copy_template

from paperops.authority_bootstrap import bootstrap_v2_authority
from paperops.cli.manifest import read_manifest, write_manifest
from paperops.model_state import MODEL_NAMES, read_model_states


class AuthorityBootstrapTest(unittest.TestCase):
    def test_bootstrap_makes_all_models_and_workflow_v2_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_manifest(project)

            hashes = bootstrap_v2_authority(project)

            self.assertEqual(tuple(hashes), MODEL_NAMES)
            states = read_model_states(project)
            for name in MODEL_NAMES:
                with self.subTest(model=name):
                    self.assertEqual(states[name].mode, "v2-authoritative")
                    self.assertEqual(states[name].current_hash, hashes[name])
                    self.assertRegex(hashes[name], r"^sha256:[0-9a-f]{64}$")
                    self.assertEqual(states[name].last_shadow_transaction, "")
                    self.assertEqual(states[name].last_adopt_transaction, "")
                    self.assertEqual(states[name].origin, "init-v2")
            manifest = read_manifest(project / ".pops" / "manifest.toml")
            self.assertEqual(manifest["workflow"]["mode"], "v2-authoritative")

    def test_failed_validation_does_not_change_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = copy_template(tmp)
            write_manifest(project)
            before = (project / ".pops" / "manifest.toml").read_bytes()
            (project / "_paperops" / "model" / "publication" / "publication-model.yml").write_text(
                "not: [valid\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(ValueError, "publication"):
                bootstrap_v2_authority(project)

            self.assertEqual((project / ".pops" / "manifest.toml").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
