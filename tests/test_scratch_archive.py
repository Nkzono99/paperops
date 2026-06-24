from __future__ import annotations

import hashlib
import tempfile
import unittest
import zipfile
from pathlib import Path

from tests.helpers import ROOT, run_cli, run_python_script


class ScratchArchiveTest(unittest.TestCase):
    def test_scratch_archive_reset_and_restore_uses_split_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(target)])
            self.assertEqual(code, 0, err)

            intro = target / "manuscript" / "ja" / "sections" / "10_intro.tex"
            intro.write_text(intro.read_text(encoding="utf-8") + "\n% CUSTOM-DRAFT\n", encoding="utf-8")
            summary = target / "refs" / "summaries" / "custom.md"
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text("# CUSTOM REF\n", encoding="utf-8")
            handoff_secret = target / "_handoff" / "secret.txt"
            handoff_secret.write_text("do not archive by default\n", encoding="utf-8")

            code, out, err = run_cli(
                [
                    "scratch",
                    "archive",
                    str(target),
                    "--id",
                    "rewrite-001",
                    "--label",
                    "before rewrite",
                    "--part-size-bytes",
                    "256",
                ]
            )

            self.assertEqual(code, 0, err)
            self.assertIn("Archived scratch state: rewrite-001", out)
            archive_dir = target / "_archives" / "rewrite-001"
            self.assertTrue((target / "_archives" / "AGENTS.md").is_file())
            self.assertTrue((archive_dir / "manifest.toml").is_file())
            self.assertFalse((archive_dir / "archive.zip").exists())
            self.assertGreaterEqual(len(sorted(archive_dir.glob("archive.zip.part*"))), 2)

            code, _out, err = run_cli(["scratch", "reset", str(target), "--yes"])

            self.assertEqual(code, 0, err)
            self.assertNotIn("CUSTOM-DRAFT", intro.read_text(encoding="utf-8"))
            self.assertFalse(summary.exists())
            self.assertFalse(handoff_secret.exists())
            self.assertTrue((target / "_archives" / "rewrite-001" / "manifest.toml").is_file())

            code, out, err = run_cli(["scratch", "inspect", str(target), "rewrite-001"])

            self.assertEqual(code, 0, err)
            self.assertIn("rewrite-001", out)
            self.assertIn("before rewrite", out)
            self.assertNotIn("CUSTOM-DRAFT", out)

            code, _out, err = run_cli(["scratch", "restore", str(target), "rewrite-001", "--yes"])

            self.assertEqual(code, 0, err)
            self.assertIn("CUSTOM-DRAFT", intro.read_text(encoding="utf-8"))
            self.assertEqual(summary.read_text(encoding="utf-8"), "# CUSTOM REF\n")
            self.assertFalse(handoff_secret.exists())

    def test_archive_seal_check_accepts_template_and_rejects_expanded_archive(self) -> None:
        script = ROOT / "template" / "scripts" / "check-archive-seal.py"

        ok = run_python_script(script, "--root", ROOT / "template")
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(root)])
            self.assertEqual(code, 0, err)
            expanded = root / "_archives" / "bad-archive" / "manuscript"
            expanded.mkdir(parents=True)
            (expanded / "main.tex").write_text("leaked past draft\n", encoding="utf-8")

            result = run_python_script(script, "--root", root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("expanded archive content", result.stdout)

    def test_restore_rejects_unsafe_archive_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(root)])
            self.assertEqual(code, 0, err)

            code, _out, err = run_cli(["scratch", "restore", str(root), "../outside", "--yes"])

            self.assertEqual(code, 2)
            self.assertIn("archive id", err)

    def test_restore_rejects_archive_members_outside_scratch_layers_before_reset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "paper-demo"
            code, _out, err = run_cli(["init", str(root)])
            self.assertEqual(code, 0, err)
            intro = root / "manuscript" / "ja" / "sections" / "10_intro.tex"
            original_intro = intro.read_text(encoding="utf-8")

            archive_dir = root / "_archives" / "rogue"
            archive_dir.mkdir(parents=True)
            bundle = Path(tmp) / "archive.zip"
            with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(".git/config", "malicious\n")
            payload = bundle.read_bytes()
            (archive_dir / "archive.zip.part0001").write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            (archive_dir / "manifest.toml").write_text(
                "\n".join(
                    [
                        "[scratch_archive]",
                        'id = "rogue"',
                        'label = "rogue"',
                        'created_at = "2026-01-01T00:00:00Z"',
                        'format = "split-zip"',
                        f'bundle_sha256 = "{digest}"',
                        "part_size_bytes = 1048576",
                        "include_handoff = false",
                        'paths = ["manuscript"]',
                        'parts = ["archive.zip.part0001"]',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            code, _out, err = run_cli(["scratch", "restore", str(root), "rogue", "--yes"])

            self.assertEqual(code, 2)
            self.assertIn("unsafe archive member", err)
            self.assertEqual(intro.read_text(encoding="utf-8"), original_intro)


if __name__ == "__main__":
    unittest.main()
