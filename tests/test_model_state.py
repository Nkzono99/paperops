from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from paperops.cli.manifest import (
    read_manifest,
    write_manifest,
    write_manifest_data_atomic,
)
from paperops.model_state import (
    AUTHORITY_MODES,
    MODEL_NAMES,
    ModelAuthorityState,
    ModelStateError,
    manifest_bytes,
    read_model_states,
    write_model_states,
)


HASH = "sha256:" + "a" * 64


class ModelStateTest(unittest.TestCase):
    def test_absent_manifest_defaults_all_six_models_to_legacy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            states = read_model_states(root)

        self.assertEqual(tuple(states), MODEL_NAMES)
        self.assertEqual(
            {state.mode for state in states.values()}, {"legacy-authoritative"}
        )
        self.assertTrue(all(state.current_hash == "" for state in states.values()))
        self.assertEqual(
            AUTHORITY_MODES,
            ("legacy-authoritative", "shadow-compare", "v2-authoritative"),
        )

    def test_round_trip_preserves_unknown_manifest_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / ".pops/manifest.toml"
            manifest.parent.mkdir(parents=True)
            manifest.write_text(
                '[project]\ntool = "pops"\n\n[custom]\nnote = "keep"\n',
                encoding="utf-8",
            )
            states = read_model_states(root)
            states["research"] = ModelAuthorityState(
                "research",
                mode="shadow-compare",
                current_hash=HASH,
                last_shadow_transaction="model-20260711T120000Z-abc123",
            )

            write_model_states(root, states)
            write_manifest(root, template_ref="local:test")
            document = read_manifest(manifest)

        self.assertEqual(document["custom"], {"note": "keep"})
        self.assertEqual(document["models"]["research"]["mode"], "shadow-compare")
        self.assertEqual(document["models"]["research"]["current_hash"], HASH)
        self.assertEqual(set(document["models"]), set(MODEL_NAMES))

    def test_rejects_unknown_model_invalid_mode_hash_and_transaction(self) -> None:
        valid = ModelAuthorityState("research")
        mutations = (
            {**{name: ModelAuthorityState(name) for name in MODEL_NAMES}, "other": valid},
            {**{name: ModelAuthorityState(name) for name in MODEL_NAMES}, "research": ModelAuthorityState("research", mode="other")},
            {**{name: ModelAuthorityState(name) for name in MODEL_NAMES}, "research": ModelAuthorityState("research", current_hash="sha256:BAD")},
            {**{name: ModelAuthorityState(name) for name in MODEL_NAMES}, "research": ModelAuthorityState("research", last_shadow_transaction="../escape")},
        )
        with tempfile.TemporaryDirectory() as tmp:
            for states in mutations:
                with self.subTest(states=states["research"]):
                    with self.assertRaises(ModelStateError):
                        write_model_states(Path(tmp), states)

    def test_manifest_bytes_distinguishes_missing_and_existing_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(manifest_bytes(root))
            path = root / ".pops/manifest.toml"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"")
            self.assertEqual(manifest_bytes(root), b"")

    def test_atomic_writer_keeps_original_and_removes_temp_on_replace_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".pops/manifest.toml"
            path.parent.mkdir(parents=True)
            path.write_text('[project]\ntool = "old"\n', encoding="utf-8")
            before = path.read_bytes()

            with patch("paperops.cli.manifest.os.replace", side_effect=OSError("boom")):
                with self.assertRaises(OSError):
                    write_manifest_data_atomic(path, {"project": {"tool": "new"}})

            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.glob(".manifest.toml.*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
