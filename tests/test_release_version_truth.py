from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-release-version-truth.py"
SPEC = importlib.util.spec_from_file_location("check_release_version_truth", SCRIPT)
release_truth = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = release_truth
SPEC.loader.exec_module(release_truth)


def write_repo(root: Path, *, pyproject_version: str, src_version: str, changelog: str) -> None:
    (root / "src" / "paperops").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        "\n".join(
            [
                "[project]",
                'name = "paper-harness-cli"',
                f'version = "{pyproject_version}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    (root / "src" / "paperops" / "__init__.py").write_text(
        f'__version__ = "{src_version}"\n',
        encoding="utf-8",
    )
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")


class ReleaseVersionTruthTest(unittest.TestCase):
    def test_default_check_accepts_current_released_version_with_unreleased_notes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                pyproject_version="0.2.0",
                src_version="0.2.0",
                changelog="""# Change Log

## Unreleased

- Next change.

## 0.2.0 - 2026-05-14

- Released package.

## Template archive 0.3.0 - 2026-04-14

- Legacy template-only note.

## 0.1.0 - 2026-04-13

- First package release.
""",
            )

            facts = release_truth.check_release_version_truth(root)

        self.assertIn("pyproject/src version: 0.2.0", facts)

    def test_default_check_rejects_duplicate_package_release_heading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                pyproject_version="0.2.0",
                src_version="0.2.0",
                changelog="""# Change Log

## Unreleased

## 0.2.0 - 2026-05-14

## 0.2.0 - 2026-04-14
""",
            )

            with self.assertRaises(release_truth.CheckFailure) as raised:
                release_truth.check_release_version_truth(root)

        self.assertIn("duplicate package release heading", str(raised.exception))

    def test_default_check_rejects_metadata_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                pyproject_version="0.2.0",
                src_version="0.3.0",
                changelog="""# Change Log

## Unreleased

## 0.2.0 - 2026-05-14
""",
            )

            with self.assertRaises(release_truth.CheckFailure) as raised:
                release_truth.check_release_version_truth(root)

        self.assertIn("must match", str(raised.exception))

    def test_release_mode_rejects_existing_target_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                pyproject_version="0.3.0",
                src_version="0.3.0",
                changelog="""# Change Log

## Unreleased

## 0.3.0 - 2026-05-20

- Release notes.

## 0.2.0 - 2026-05-14

- Previous release.
""",
            )

            with self.assertRaises(release_truth.CheckFailure) as raised:
                release_truth.check_release_version_truth(
                    root,
                    release_version="0.3.0",
                    existing_tags={"v0.3.0"},
                )

        self.assertIn("already exists", str(raised.exception))

    def test_release_mode_requires_target_metadata_and_empty_unreleased(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(
                root,
                pyproject_version="0.2.0",
                src_version="0.2.0",
                changelog="""# Change Log

## Unreleased

- Not moved yet.

## 0.3.0 - 2026-05-20

- Release notes.

## 0.2.0 - 2026-05-14

- Previous release.
""",
            )

            with self.assertRaises(release_truth.CheckFailure) as raised:
                release_truth.check_release_version_truth(
                    root,
                    release_version="0.3.0",
                    existing_tags=set(),
                )

        message = str(raised.exception)
        self.assertIn("[project].version must be '0.3.0'", message)
        self.assertIn("'## Unreleased' must be empty", message)


if __name__ == "__main__":
    unittest.main()
